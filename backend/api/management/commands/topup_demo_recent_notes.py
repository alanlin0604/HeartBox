"""Fill the gap between a demo account's newest note and today.

The seed commands distribute notes across ``signup → today``, so an account
looks healthy the day it is seeded and then quietly rots: every dashboard
window that is relative to *now* ("last 30 days", weekday averages, the mood
trend line) empties out as the seed date recedes. Measured 2026-08-19, three
of the four zh-TW accounts had **zero** notes in the last 30 days — charts
rendered blank on accounts that had 50+ entries.

Re-running the seed command fixes it but regenerates everything through the
full ``ai_engine.analyze`` pipeline (~260-320s per note on Qwen2.5-7B: the
JSON-constrained sentiment step alone is 60-68s). This command instead adds
only what is missing:

  * Existing notes, tags and streaks are left alone.
  * New notes are drawn from the same content pools and profile bands the
    account was originally seeded with, so the narrative stays consistent.
  * Note density matches what the account already has, so a "power user"
    stays a power user and a casual one stays casual.
  * ``ai_feedback`` comes from the live LLM via ``ai_engine.generate_feedback``
    — one free-form call per note (~7-25s), skipping the expensive sentiment
    step because the profile bands already supply the score. Pass
    ``--offline-feedback`` to use the curated pools instead and skip the GPU
    entirely.

Run:
    python manage.py topup_demo_recent_notes --dry-run
    python manage.py topup_demo_recent_notes                       # all stale accounts
    python manage.py topup_demo_recent_notes --accounts test2 test3
    python manage.py topup_demo_recent_notes --offline-feedback    # no GPU needed

Sleep / health / habit data rots the same way but is cheap to regenerate,
so that stays in ``seed_demo_health_data`` (which writes a rolling window
ending today). A full refresh is both:

    python manage.py topup_demo_recent_notes
    python manage.py seed_demo_health_data
"""
from __future__ import annotations

import random
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Max, Min
from django.utils import timezone

from api.models import JournalStreak, MoodNote, Tag

from .seed_demo_test_accounts import (
    ACCOUNTS as ZH_ACCOUNTS,
    CONTENT_POOLS as ZH_POOLS,
    pick_ai_feedback as zh_pick_ai_feedback,
    pick_band,
    pick_sentiment,
    pick_weather as zh_pick_weather,
)
from .seed_demo_test_accounts_en import (
    ACCOUNTS as EN_ACCOUNTS,
    CONTENT_POOLS as EN_POOLS,
    pick_ai_feedback as en_pick_ai_feedback,
    pick_stress,
    pick_weather as en_pick_weather,
)

User = get_user_model()

# username -> (spec, pools, weather_fn, offline_feedback_fn)
REGISTRY = {}
for _spec in ZH_ACCOUNTS:
    REGISTRY[_spec['username']] = (_spec, ZH_POOLS, zh_pick_weather, zh_pick_ai_feedback)
for _spec in EN_ACCOUNTS:
    REGISTRY[_spec['username']] = (_spec, EN_POOLS, en_pick_weather, en_pick_ai_feedback)


class Command(BaseCommand):
    help = "Add recent notes to demo accounts whose newest entry has gone stale."

    def add_arguments(self, parser):
        parser.add_argument(
            '--accounts', nargs='+', default=sorted(REGISTRY),
            help='Subset of usernames to top up (default: every demo account).',
        )
        parser.add_argument(
            '--window-days', type=int, default=30,
            help=(
                'Recent window that must carry the account\'s normal note density '
                '(default 30, matching get_mood_trends lookback).'
            ),
        )
        parser.add_argument(
            '--offline-feedback', action='store_true',
            help='Use the curated feedback pools instead of calling the LLM.',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Report what would be written without touching the DB.',
        )
        parser.add_argument('--seed', type=int, default=20260819)

    def handle(self, *args, **opts):
        rng = random.Random(opts['seed'])
        dry = opts['dry_run']
        use_llm = not opts['offline_feedback']

        targets = [n for n in opts['accounts'] if n in REGISTRY]
        unknown = [n for n in opts['accounts'] if n not in REGISTRY]
        for n in unknown:
            self.stdout.write(self.style.WARNING(f'skip unknown demo account: {n}'))

        if use_llm and not dry:
            from ._llm_preflight import check_llm_reachable
            problem = check_llm_reachable()
            if problem:
                self.stdout.write(self.style.ERROR(f'ERROR: {problem}'))
                self.stdout.write(self.style.ERROR(
                    'Refusing to run: every note would fall back to the offline '
                    'pool and the summary would still read as success. Pass '
                    '--offline-feedback to choose the curated pools deliberately.'
                ))
                return
            self.stdout.write(self.style.WARNING(
                'Feedback comes from the live LLM (~7-25s per note). Keep '
                'GPU-heavy apps closed — under VRAM pressure the provider times '
                'out and notes quietly fall back to the offline pool.'
            ))

        total = 0
        for username in targets:
            try:
                total += self._topup_one(
                    username, rng, use_llm=use_llm, dry=dry,
                    window_days=opts['window_days'],
                )
            except Exception as e:                                        # noqa: BLE001
                self.stdout.write(self.style.ERROR(f'  ! {username} failed: {e}'))

        verb = 'would write' if dry else 'wrote'
        self.stdout.write(self.style.SUCCESS(f'\nDone. {verb} {total} notes.'))

    # ------------------------------------------------------------------

    def _topup_one(self, username, rng, *, use_llm, dry, window_days):
        spec, pools, weather_fn, offline_feedback_fn = REGISTRY[username]

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.WARNING(f'skip — user does not exist: {username}'))
            return 0

        try:
            tz = ZoneInfo(user.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            tz = timezone.get_current_timezone()
        today = timezone.now().astimezone(tz).date()

        # Soft-deleted notes are invisible to every chart (analytics filters
        # is_deleted=False), so they must not count here either. test1 had 14
        # recent notes in the trash; measuring against all rows made it look
        # 3 days stale when its newest *visible* note was 50 days old, and the
        # top-up added a single note to an account whose charts were empty.
        active = MoodNote.objects.filter(user=user, is_deleted=False)
        agg = active.aggregate(lo=Min('created_at'), hi=Max('created_at'))
        if agg['hi'] is None:
            self.stdout.write(self.style.WARNING(
                f'skip — {username} has no visible notes to extend; seed it first'
            ))
            return 0

        first_date = agg['lo'].astimezone(tz).date()
        last_date = agg['hi'].astimezone(tz).date()

        # Match the density the account already has rather than the seed
        # command's target count — test1 has been written to by hand since
        # seeding, and forcing it back to the nominal rate would show up as a
        # visible change in its posting cadence.
        existing = active.count()
        span_days = max(1, (last_date - first_date).days)
        density = existing / span_days

        # Work over whichever is longer: the stale tail since the newest
        # visible note, or the recent window the charts read. A gap-only rule
        # misses an account that posted yesterday but has a hole behind it;
        # a window-only rule under-fills an account that stopped months ago.
        start = min(last_date, today - timedelta(days=window_days))
        span = max(1, (today - start).days)
        candidate_days = [start + timedelta(days=i) for i in range(1, span + 1)]

        have = {
            n.created_at.astimezone(tz).date()
            for n in active.filter(created_at__gte=timezone.now() - timedelta(days=span))
        }
        free_days = [d for d in candidate_days if d <= today and d not in have]

        expected = round(density * span)
        actual = sum(1 for d in candidate_days if d in have)
        deficit = expected - actual
        if deficit < 1 or not free_days:
            self.stdout.write(
                f'  {username}: up to date ({actual} notes in the last {span}d, '
                f'density implies ~{expected})'
            )
            return 0

        n_new = min(deficit, len(free_days))
        chosen = sorted(rng.sample(free_days, n_new))

        if dry:
            self.stdout.write(
                f'  {username}: newest visible {last_date} ({(today - last_date).days}d ago), '
                f'density {density:.2f}/day, {actual}/{expected} notes in last {span}d '
                f'→ would add {len(chosen)} through {today}'
            )
            return len(chosen)

        tag_objs = {t.name: t for t in Tag.objects.filter(user=user)}
        mix = dict(spec['sentiment_mix'])
        mix_pos = mix.get('pos', 33)
        mix_neu = mix.get('neu', 34)
        mix_neg = mix.get('neg', 33)
        pools_for_profile = pools[spec['profile']]
        baseline = spec['baseline']
        activities = spec['activities']

        written = 0
        llm_failures = 0
        with transaction.atomic():
            for i, entry_date in enumerate(chosen):
                band = pick_band(mix_pos, mix_neu, mix_neg, rng)
                template_band, stress_band, content, hinted_tags = rng.choice(
                    pools_for_profile[band]
                )
                weather, temp = weather_fn(rng, entry_date.month)
                sentiment = pick_sentiment(template_band, baseline, rng)
                if weather == 'sunny':
                    sentiment = min(1.0, sentiment + 0.05)
                elif weather in ('rainy', 'stormy'):
                    sentiment = max(-1.0, sentiment - 0.04)
                sentiment = round(sentiment, 3)

                if use_llm:
                    from api.services.ai_engine import ai_engine
                    try:
                        feedback = ai_engine.generate_feedback(content, sentiment)
                    except Exception as e:                                # noqa: BLE001
                        llm_failures += 1
                        self.stdout.write(self.style.WARNING(
                            f'    [{username}] LLM feedback failed on '
                            f'{i + 1}/{len(chosen)} ({e}); using offline pool'
                        ))
                        feedback = offline_feedback_fn(sentiment, rng)
                else:
                    feedback = offline_feedback_fn(sentiment, rng)

                n_acts = rng.randint(0, min(3, len(activities)))
                note = MoodNote(
                    user=user,
                    sentiment_score=sentiment,
                    stress_index=pick_stress(stress_band, rng),
                    ai_feedback=feedback,
                    metadata={
                        'weather': weather,
                        'temperature': temp,
                        'activities': rng.sample(activities, n_acts) if n_acts else [],
                    },
                )
                note.set_content(content)
                note.save()

                relevant = [tag_objs[t] for t in hinted_tags if t in tag_objs]
                if relevant and rng.random() < 0.75:
                    note.tags.add(rng.choice(relevant))
                if tag_objs and rng.random() < 0.30:
                    note.tags.add(rng.choice(list(tag_objs.values())))

                entry_dt = datetime.combine(
                    entry_date,
                    time(hour=rng.randint(8, 23), minute=rng.randint(0, 59)),
                    tzinfo=tz,
                )
                MoodNote.objects.filter(pk=note.pk).update(
                    created_at=entry_dt, updated_at=entry_dt,
                )
                written += 1

                if use_llm and (i + 1) % 5 == 0:
                    self.stdout.write(
                        f'    [{username}] {i + 1}/{len(chosen)} done '
                        f'({llm_failures} LLM failures)'
                    )

            # Refresh the streak so the profile header matches the new notes.
            latest = MoodNote.objects.filter(
                user=user, is_deleted=False,
            ).order_by('-created_at').first()
            grand_total = MoodNote.objects.filter(user=user, is_deleted=False).count()
            JournalStreak.objects.update_or_create(
                user=user,
                defaults={
                    'current_streak': 1 if latest else 0,
                    'longest_streak': max(1, grand_total // 7),
                    'last_entry_date': latest.created_at.astimezone(tz).date() if latest else None,
                    'total_entries': grand_total,
                },
            )

        note_src = 'LLM' if use_llm else 'pool'
        extra = f' ({llm_failures} fell back to pool)' if llm_failures else ''
        self.stdout.write(self.style.SUCCESS(
            f'  [OK] {username}: +{written} notes through {today} '
            f'(had {actual}/{expected} in last {span}d, density {density:.2f}/day, '
            f'feedback={note_src}{extra})'
        ))
        return written
