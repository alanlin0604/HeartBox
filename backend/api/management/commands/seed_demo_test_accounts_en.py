"""Seed 3 English-only demo accounts (test1_en, test2_en, test3_en).

Why this exists as a separate command instead of a flag on
``seed_demo_test_accounts``:

  1. The zh-TW demo accounts (test/test1/test2/test3) carry hand-written
     Traditional-Chinese journal content. Switching the UI language to
     English translates the *chrome* but not the seeded rows — journals,
     tags, AI feedback, habit names and community posts all stay Chinese,
     so an overseas reviewer sees a half-translated app.
  2. The zh-TW command fills ``ai_feedback`` by calling the real
     ``ai_engine.analyze`` pipeline. That pipeline normalises every reply
     to Traditional Chinese with OpenCC (commit db1e39c), so feeding it
     English journals would still hand back Chinese feedback. These
     accounts therefore use offline sentiment / stress / feedback pools —
     the same approach ``seed_demo_population`` uses. Side benefit: this
     command runs in seconds and needs no GPU, so it is safe to run
     mid-demo.

Profiles mirror their zh-TW counterparts one-for-one so the two language
tracks tell the same story:

  test1_en — volatile, high & low swings (relationship + work drama)
  test2_en — positive-leaning (gratitude, growth, exercise, learning)
  test3_en — negative-leaning, themed for RAG retrieval (anxiety,
             burnout, insomnia, perfectionism)

Each account spans 2026-03-01 → today, gets 50-60 backdated MoodNotes
with sentiment_score / stress_index / metadata / AI feedback, plus an
English tag palette and activity set. Timestamps are generated in
``America/Los_Angeles`` (the account's stored timezone) so the analytics
middleware, streak dates and weekday charts stay coherent for a reviewer
in a Western timezone. Password equals the username (test1_en/test1_en).

Idempotent: if a user already exists their notes / tags are wiped and
regenerated, but the user row itself is preserved (so the JWT, GCS
upload path etc don't change between reseeds).

Run:
    python manage.py seed_demo_test_accounts_en
    python manage.py seed_demo_test_accounts_en --reset   # also delete the User rows

Health / sleep / habit / community data for these accounts comes from
``seed_demo_health_data`` (they are listed in its PROFILES table), so the
usual full refresh is:

    python manage.py seed_demo_test_accounts_en
    python manage.py seed_demo_health_data
"""
from __future__ import annotations

import random
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from api.models import JournalStreak, MoodNote, Tag

User = get_user_model()

# Distinct from the zh-TW '[demo-test]' marker so the two sets can be
# told apart in the admin user list and in cleanup queries.
DEMO_BIO_PREFIX = '[demo-test-en]'
WINDOW_START = datetime(2026, 3, 1)
# These accounts exist for overseas reviewers, so everything (stored tz,
# generated timestamps, weather/temperature climate) is US West Coast.
ACCOUNT_TIMEZONE = 'America/Los_Angeles'
TZ = ZoneInfo(ACCOUNT_TIMEZONE)

ACCOUNTS = [
    {
        'username': 'test1_en',
        'password': 'test1_en',
        'profile': 'volatile',
        'note_count': 60,
        'baseline': 0.0,
        'sentiment_mix': [('pos', 40), ('neu', 20), ('neg', 40)],
        'tag_palette': [
            ('Work', '#8b5cf6'), ('Relationship', '#ec4899'), ('Emotions', '#a855f7'),
            ('Friends', '#f43f5e'), ('Family', '#ec4899'),
        ],
        'activities': ['social', 'work', 'gaming', 'music', 'movie'],
    },
    {
        'username': 'test2_en',
        'password': 'test2_en',
        'profile': 'positive',
        'note_count': 50,
        'baseline': 0.35,
        'sentiment_mix': [('pos', 55), ('neu', 35), ('neg', 10)],
        'tag_palette': [
            ('Gratitude', '#f59e0b'), ('Exercise', '#10b981'), ('Learning', '#06b6d4'),
            ('Friends', '#f43f5e'), ('Health', '#14b8a6'), ('Growth', '#eab308'),
        ],
        'activities': ['exercise', 'social', 'reading', 'music', 'nature', 'meditation'],
    },
    {
        'username': 'test3_en',
        'password': 'test3_en',
        'profile': 'negative',
        'note_count': 50,
        'baseline': -0.3,
        'sentiment_mix': [('pos', 15), ('neu', 25), ('neg', 60)],
        'tag_palette': [
            ('Work', '#8b5cf6'), ('Emotions', '#a855f7'), ('Sleep', '#3b82f6'),
            ('Health', '#14b8a6'), ('Reflection', '#64748b'),
        ],
        'activities': ['work', 'reading', 'gaming'],
    },
]

# ---------------------------------------------------------------------------
# Content pools — themed by profile, mirroring the zh-TW pools entry by
# entry so the two language tracks show the same narrative arc.
# Each entry: (band, stress_band, content, hinted_tags)
#   band:        'pos' | 'neu' | 'neg'
#   stress_band: 'low' | 'mid' | 'high'
# ---------------------------------------------------------------------------

CONTENT_VOLATILE_HIGH = [
    ('pos', 'low', "We finally talked through the thing that's been sitting between us all week. That feeling of putting something heavy down - I'd forgotten how good it is.", ['Relationship']),
    ('pos', 'low', "My manager said she's putting my name forward for the promotion. Nothing is confirmed yet, but being seen like that felt incredible. Celebrating tonight.", ['Work']),
    ('pos', 'mid', "Great date today. We finally went to the coffee place we'd been talking about for months but never got to. They have such a good laugh.", ['Relationship']),
    ('pos', 'low', "Got the offer! Three weeks of waiting and a few sleepless nights in the middle, but it worked out.", ['Work']),
    ('pos', 'low', "Karaoke with friends until two in the morning, then slept like a rock. I needed that.", ['Friends']),
    ('pos', 'low', "A coworker complimented me out of nowhere today. Turns out the quiet things I do have been noticed. I got a little teary.", ['Work']),
    ('pos', 'low', "A close friend I hadn't seen in a year is back in town. We talked for three hours straight. Some connections just don't fade.", ['Friends']),
]
CONTENT_VOLATILE_LOW = [
    ('neg', 'high', "We argued again, and this time over something tiny. I knew it wasn't worth it and still couldn't stop. Walked home feeling like the worst version of myself.", ['Relationship', 'Emotions']),
    ('neg', 'high', "Deadline is Friday and the spec changed again. I have never wanted to quit this badly.", ['Work', 'Emotions']),
    ('neg', 'high', "They said they need some space. They swear it isn't a breakup, but I was awake the whole night.", ['Relationship', 'Emotions']),
    ('neg', 'high', "Got called out in front of the whole team today. It was my mistake, but the being-corrected-in-public part sat in my chest all day.", ['Work', 'Emotions']),
    ('neg', 'high', "My parents started in on salary and marriage again. The whole dinner table went stiff. I know they mean well.", ['Family', 'Emotions']),
    ('neg', 'mid', "Couldn't sleep again. My brain keeps replaying the argument frame by frame. I know it's useless and it keeps going anyway.", ['Emotions']),
    ('neg', 'high', "Heard secondhand what a coworker has been saying about me. Couldn't do a thing all afternoon. Pretending it's fine is exhausting.", ['Work', 'Emotions']),
]
CONTENT_VOLATILE_NEU = [
    ('neu', 'mid', "Normal day in, normal day out. Nothing really landed either way.", ['Work']),
    ('neu', 'mid', "They were busy today so we barely talked. I know it's nothing, but the quiet still felt a bit hollow.", ['Relationship']),
    ('neu', 'mid', "Cooked dinner alone with a video playing on my phone. Midweek loneliness is quieter than I expected.", []),
]

CONTENT_POSITIVE = [
    ('pos', 'low', "Up at six to run along the river. Caught the sunrise and nearly teared up. So that is what being alive feels like.", ['Exercise', 'Gratitude']),
    ('pos', 'low', "Signed up for an online psychology course. The first lesson was on self-compassion and it cracked something open. I'm finally learning to be decent to myself.", ['Learning', 'Growth']),
    ('pos', 'low', "The little piano piece I've been practising for a month finally came out clean. Small on paper, huge to me.", ['Learning', 'Growth']),
    ('pos', 'low', "Today's yoga class was a gratitude practice - thank your body for everything it did for you today. First time I've genuinely thanked myself.", ['Exercise', 'Gratitude']),
    ('pos', 'low', "A client wrote to say our proposal saved them 30% on costs. So those late nights meant something after all.", ['Growth', 'Gratitude']),
    ('pos', 'low', "Tried a new vegetarian recipe and it was surprisingly good. Eating well alone still counts as eating well.", ['Health', 'Gratitude']),
    ('pos', 'low', "Started volunteering. My first shift was just sitting and talking with the residents. Turns out giving heals more than receiving.", ['Growth', 'Gratitude']),
    ('pos', 'low', "The book I read today gave me that yes-exactly-that feeling. Words really do carry weight.", ['Learning', 'Gratitude']),
    ('pos', 'low', "Took the dog out and watched them tear across the grass. Suddenly a lot of things felt less important.", ['Gratitude']),
    ('pos', 'low', "Worked out, went grocery shopping, cooked dinner and poured a glass of wine. The simple rhythm is honestly the best one.", ['Health', 'Gratitude']),
    ('pos', 'mid', "Finished a project I'd been putting off for three months, even if it ate the whole weekend. That weight is finally off my chest.", ['Growth']),
    ('pos', 'low', "Joined a book club and shared a book with strangers for the first time. Being properly listened to is rarer than it should be.", ['Friends', 'Learning']),
    ('pos', 'low', "The barista remembered my order today. A small warmth in a big city.", ['Gratitude']),
    ('pos', 'low', "Finally did the health check I'd been avoiding. Everything came back normal. Thank you, body, for quietly doing your job.", ['Health', 'Gratitude']),
    ('pos', 'mid', "Spoke up in the meeting with what I actually thought, and they took it. Turns out my voice is worth something.", ['Growth']),
    ('pos', 'low', "Ran into an old friend and we laughed about things from ten years ago. Some people just stay with you.", ['Friends', 'Gratitude']),
    ('pos', 'low', "Saw the first blossom on the walk home and realised spring is actually here. My whole body relaxed a notch.", ['Gratitude']),
]
CONTENT_POSITIVE_NEU = [
    ('neu', 'low', "Work went smoother than expected, so I spent the spare hour wandering a bookshop. Aimless walking is underrated.", []),
    ('neu', 'mid', "It was a coworker's birthday so the office threw a small thing. A rare easy afternoon.", ['Friends']),
    ('neu', 'low', "Sat in a cafe all afternoon writing. Not much output, but a very steady mood.", []),
    ('neu', 'mid', "Today went about as expected - no surprise wins, no surprise blows. A quietly fine day.", []),
]
CONTENT_POSITIVE_LOW = [
    ('neg', 'mid', "Body is a bit worn out, probably overtrained this week. Giving myself tomorrow off.", ['Health']),
    ('neg', 'mid', "Something didn't go my way today, but I noticed it doesn't change my overall direction. It's okay.", ['Growth']),
]

CONTENT_NEGATIVE_ANXIETY = [
    ('neg', 'high', "My chest has been tight a lot lately. I'm not even thinking about anything in particular, the anxiety just won't switch off. Feels like I'm about to go off.", ['Emotions', 'Health']),
    ('neg', 'high', "My hands started shaking on the walk home - probably a panic response. Took a long stretch of slow breathing before it settled.", ['Emotions', 'Health']),
    ('neg', 'high', "Heart racing the second I woke up, before I'd done anything at all. The anxiety has moved into my body now.", ['Emotions', 'Health']),
    ('neg', 'high', "Night before the presentation and my brain went straight to the worst case. Couldn't sleep at all. What am I supposed to do tomorrow.", ['Work', 'Emotions']),
    ('neg', 'mid', "Cancelled on friends again. They'll understand, but I feel awful about it. Socialising costs more than it used to.", ['Emotions']),
    ('neg', 'high', "Waited five minutes for a coffee and felt myself boiling. My patience is running out faster than it should.", ['Emotions']),
    ('neg', 'high', "Kept checking my phone for a reply that never came and built an entire disaster out of the silence.", ['Emotions']),
]
CONTENT_NEGATIVE_BURNOUT = [
    ('neg', 'high', "Home at eleven again. Standing at the corner store buying dinner I suddenly thought, this is a bad way to live - and I don't know which part I'm allowed to change.", ['Work', 'Emotions']),
    ('neg', 'high', "Two straight months without a real day off. I answer email on weekends now. I'm a KPI machine with a pulse.", ['Work', 'Emotions']),
    ('neg', 'high', "Couldn't move a single thing forward today. It's urgent and my head is just blank. The zero-productivity panic is its own kind of awful.", ['Work', 'Emotions']),
    ('neg', 'high', "I used to like this job. Now I sigh the moment the laptop opens. Did I change, or did it.", ['Work', 'Reflection']),
    ('neg', 'mid', "Everyone else stays late, so leaving on time makes me feel like a fraud. But staying doesn't get anything done either.", ['Work', 'Emotions']),
    ('neg', 'mid', "My manager dropped another task on me last minute and my Friday plans are gone again. My life keeps getting scheduled by other people.", ['Work', 'Emotions']),
]
CONTENT_NEGATIVE_INSOMNIA = [
    ('neg', 'high', "Three in the morning and still awake, running through every wrong thing I've ever done. I know it's pointless and I can't stop.", ['Sleep', 'Emotions']),
    ('neg', 'high', "Fifth night under five hours. Ran the whole workday on coffee. I feel hollowed out.", ['Sleep', 'Health']),
    ('neg', 'mid', "Decided no phone tonight and got into bed early - then stared at the ceiling for two hours. Body exhausted, brain wide awake.", ['Sleep']),
    ('neg', 'high', "Woke up without ever actually waking up. Spent the whole day submerged in fog.", ['Sleep', 'Health']),
    ('neg', 'mid', "Stayed up again to finish the report. I knew tomorrow would hurt and I did it anyway. Me and sleep are not on good terms.", ['Sleep', 'Work']),
]
CONTENT_NEGATIVE_PERFECTIONISM = [
    ('neg', 'high', "The pitch went fine, my manager said good work, and all I could think was that I should have done better. Why am I never satisfied.", ['Work', 'Reflection']),
    ('neg', 'high', "Everyone tells me I do well and all I can see are the flaws. I can't enjoy a single thing I finish.", ['Emotions', 'Reflection']),
    ('neg', 'mid', "Eighth revision of the report. My coworker says it's already good enough. It still feels like something is missing.", ['Work', 'Reflection']),
    ('neg', 'high', "Spent the whole day berating myself over one small mistake that nobody else will remember.", ['Emotions', 'Reflection']),
]
CONTENT_NEGATIVE_DEPRESSION = [
    ('neg', 'mid', "Nothing holds my interest lately. The things I used to love feel like nothing now.", ['Emotions', 'Reflection']),
    ('neg', 'mid', "Showering felt like a major undertaking today. Sat on the edge of the bed staring at the bathroom door for half an hour.", ['Emotions', 'Health']),
    ('neg', 'high', "Like being inside very thick glass. I can see everyone out there and I can't reach any of it.", ['Emotions', 'Reflection']),
    ('neg', 'mid', "Food has no taste, exercise has no pull, and talking to friends feels like acting. Maybe it's time to get professional help.", ['Emotions', 'Health']),
    ('neg', 'mid', "Didn't leave the house again today. The world out there sounds loud and far away.", ['Emotions']),
    ('neg', 'high', "Tired all the time, and not body tired. Soul tired.", ['Emotions', 'Reflection']),
]
CONTENT_NEGATIVE_RECOVERY = [
    ('neu', 'mid', "Made myself walk for ten minutes today and came back feeling slightly better. A small step is still a step.", ['Emotions', 'Reflection']),
    ('pos', 'mid', "Called and booked a session with a counsellor for next week. That one phone call took every bit of courage I had today. But it's booked.", ['Emotions', 'Health']),
    ('neu', 'mid', "Read an article about depression and realised what I feel isn't something wrong with me, it's a state. Being understood helps more than I expected.", ['Emotions', 'Reflection']),
    ('pos', 'mid', "Woke up today without the why-bother-getting-up thought. For where I am right now, that counts as real progress.", ['Emotions', 'Reflection']),
]
# Filler neutrals for the negative profile — the zh-TW command borrows
# these from the 'balanced' pool, which has no English counterpart since
# there is no test_en account.
CONTENT_NEUTRAL_FILLER = [
    ('neu', 'mid', "Normal day at work, nothing worth reporting. Made pasta and went to bed.", ['Work']),
    ('neu', 'mid', "Finished a book on the train. No strong feelings about it, but finishing it felt fine.", []),
    ('neu', 'mid', "Walked past the breakfast place I used to go to and noticed it has new owners. Tastes about the same, feels different.", []),
    ('neu', 'mid', "Didn't get much done, didn't get nothing done. The days just go by.", ['Work']),
]

CONTENT_POOLS = {
    'volatile': {
        'pos': CONTENT_VOLATILE_HIGH,
        'neu': CONTENT_VOLATILE_NEU,
        'neg': CONTENT_VOLATILE_LOW,
    },
    'positive': {
        'pos': CONTENT_POSITIVE,
        'neu': CONTENT_POSITIVE_NEU,
        'neg': CONTENT_POSITIVE_LOW,
    },
    'negative': {
        # Negative profile pulls from 5 themed sub-pools for variety
        'pos': CONTENT_NEGATIVE_RECOVERY,
        'neu': CONTENT_NEGATIVE_RECOVERY[:2] + CONTENT_NEUTRAL_FILLER[:3],
        'neg': (
            CONTENT_NEGATIVE_ANXIETY
            + CONTENT_NEGATIVE_BURNOUT
            + CONTENT_NEGATIVE_INSOMNIA
            + CONTENT_NEGATIVE_PERFECTIONISM
            + CONTENT_NEGATIVE_DEPRESSION
        ),
    },
}

# AI feedback pools. Written by hand rather than generated: the live
# ai_engine pipeline runs every reply through OpenCC and would hand back
# Traditional Chinese for an English journal.
AI_FEEDBACK_POS = [
    "It sounds like you and yourself are on good terms today. Write it down - you'll want to read this back on a harder day.",
    "Noticing the small bright spots is what keeps people going. Hold onto this one.",
    "The small choices you made today are adding up to someone you'll be glad to be. There's no rush and nobody is timing you.",
    "Choosing to record a moment like this is its own kind of kindness. Bit by bit you're learning how to look after yourself.",
    "This was lovely to read. It's worth remembering, and worth telling someone close to you.",
]
AI_FEEDBACK_NEU = [
    "Ordinary days are part of a life too. Getting through one steadily is already worth something.",
    "Writing an observation down on a flat day takes a fine kind of attention. The patterns show up over time.",
    "Today was even-keeled, but you still stopped to record it. That habit will point you somewhere when you need it.",
    "Life moves up and down, and the flat stretches are often where the repair happens. No need to rush to a conclusion.",
]
AI_FEEDBACK_NEG = [
    "This is hard to read. Decisions made under this much pressure are rarely your best ones. Could you talk to someone tomorrow? You don't have to carry it alone.",
    "Feelings don't need a reason to be valid. Don't make yourself explain tonight - just give yourself some blank space.",
    "Writing this down while you're still uncomfortable is brave. Difficult feelings don't have to be defeated; being seen is usually enough for the tide to turn.",
    "When nothing will go right, stop and take a few slow breaths first. You have done enough. Let yourself rest tonight.",
    "Exhaustion built up over months doesn't clear in a day. Give yourself some time. Nobody is waiting on you.",
    "There's a lot of accumulated tiredness in what you wrote. If this lasts more than two weeks, talking to a professional would be a kind choice, not a drastic one.",
    "The physical side of anxiety is real - it isn't overthinking. Try slow belly breathing and let the rhythm come back down.",
    "The insomnia loop makes it easy to give up, but every night you're willing to try again counts. Tomorrow can be a little better.",
]


def pick_band(mix_pos, mix_neu, mix_neg, rng):
    """Pick 'pos'/'neu'/'neg' band by weighted dist."""
    total = mix_pos + mix_neu + mix_neg
    u = rng.uniform(0, total)
    if u < mix_pos:
        return 'pos'
    if u < mix_pos + mix_neu:
        return 'neu'
    return 'neg'


def pick_sentiment(band, baseline, rng):
    if band == 'pos':
        v = rng.uniform(0.3, 0.95)
    elif band == 'neg':
        v = rng.uniform(-0.85, -0.15)
    else:
        v = rng.uniform(-0.15, 0.25)
    return max(-1.0, min(1.0, v + baseline * 0.5))


def pick_stress(band, rng):
    if band == 'high':
        return rng.randint(6, 9)
    if band == 'low':
        return rng.randint(0, 3)
    return rng.randint(3, 6)


def pick_ai_feedback(sentiment, rng):
    if sentiment >= 0.2:
        return rng.choice(AI_FEEDBACK_POS)
    if sentiment <= -0.2:
        return rng.choice(AI_FEEDBACK_NEG)
    return rng.choice(AI_FEEDBACK_NEU)


WEATHER_DIST = (
    ['sunny'] * 45 + ['cloudy'] * 30 + ['rainy'] * 15 + ['foggy'] * 7 + ['stormy'] * 3
)


def pick_weather(rng, month):
    """Weather + temperature (Celsius), biased by month for a US West-Coast
    climate — matches ACCOUNT_TIMEZONE so the dashboard's weather-vs-mood
    correlation reads plausibly for an overseas reviewer."""
    if month in (6, 7, 8):              # summer — dry and sunny
        weather = rng.choice(['sunny'] * 55 + ['cloudy'] * 30 + ['foggy'] * 10 + ['rainy'] * 5)
        temp = rng.randint(22, 33)
    elif month in (12, 1, 2):           # winter — the wet season
        weather = rng.choice(['cloudy'] * 35 + ['rainy'] * 30 + ['sunny'] * 25 + ['foggy'] * 10)
        temp = rng.randint(9, 18)
    else:
        weather = rng.choice(WEATHER_DIST)
        temp = rng.randint(15, 26)
    return weather, temp


class Command(BaseCommand):
    help = 'Seed 3 English-only demo accounts (test1_en/test2_en/test3_en)'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Delete the User rows too (default: keep user, wipe data)')
        parser.add_argument('--seed', type=int, default=2026)
        parser.add_argument(
            '--real-feedback', action='store_true',
            help=(
                'Generate ai_feedback with the live LLM instead of the offline '
                'pools. Needs llm_server running and the GPU free. Sentiment / '
                'stress still come from the profile bands, so this costs one '
                'free-form call per note (~7-25s), not a full analyze().'
            ),
        )
        parser.add_argument(
            '--accounts', nargs='+', default=[a['username'] for a in ACCOUNTS],
            help='Subset of usernames to seed (default: all 3).',
        )

    def handle(self, *args, **opts):
        rng = random.Random(opts['seed'])
        today = timezone.now().astimezone(TZ).date()
        bio_marker = f'{DEMO_BIO_PREFIX} '
        real_feedback = opts['real_feedback']
        wanted = set(opts['accounts'])

        if real_feedback:
            # Fail before writing anything rather than 40 notes in: a dead
            # provider means every note silently falls back to the offline
            # pool, which is indistinguishable from success in the output.
            from ._llm_preflight import check_llm_reachable
            problem = check_llm_reachable()
            if problem:
                self.stdout.write(self.style.ERROR(f'ERROR: {problem}'))
                self.stdout.write(self.style.ERROR(
                    'Refusing to run --real-feedback: drop the flag to seed from '
                    'the offline pools instead.'
                ))
                return
            self.stdout.write(self.style.WARNING(
                'Generating feedback with the live LLM — expect ~7-25s per note. '
                'Keep GPU-heavy apps closed: under VRAM pressure the provider '
                'times out and every note silently drops to the offline pool.'
            ))

        seeded, failed = [], []
        for spec in ACCOUNTS:
            if spec['username'] not in wanted:
                continue
            try:
                with transaction.atomic():
                    self._seed_one_account(
                        spec, rng, today, bio_marker,
                        full_reset=opts['reset'], real_feedback=real_feedback,
                    )
                seeded.append(spec['username'])
            except Exception as e:                                        # noqa: BLE001
                failed.append(spec['username'])
                self.stdout.write(self.style.ERROR(
                    f'  ! {spec["username"]} failed: {e}'
                ))

        # Raise on any failure rather than printing a blanket success. The
        # earlier version reported "seeded" plus login details even when every
        # account had errored, so a chained run (`cmd-a; cmd-b`) carried on as
        # if the accounts existed — and the missing users only surfaced later
        # as "user does not exist" in a different command.
        if failed:
            raise CommandError(
                f'{len(failed)} of {len(failed) + len(seeded)} accounts failed: '
                f'{", ".join(failed)}. Nothing was left half-written (each account '
                f'is one transaction), but the failed accounts are NOT seeded.'
            )

        self.stdout.write(self.style.SUCCESS(
            f'\n{len(seeded)} English demo account(s) seeded: {", ".join(seeded)}'
        ))
        self.stdout.write('Login: test1_en/test1_en, test2_en/test2_en, test3_en/test3_en')

    def _seed_one_account(self, spec, rng, today, bio_marker, full_reset,
                          real_feedback=False):
        username = spec['username']
        password = spec['password']
        profile = spec['profile']
        window_start = WINDOW_START.replace(tzinfo=TZ)

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@demo.heartbox.tw',
                'bio': f'{bio_marker}{profile}',
                'email_verified': True,
                'onboarding_completed': True,
                'timezone': ACCOUNT_TIMEZONE,
                'age_band': '18_plus',
                'age_confirmed_13_plus': True,
                'terms_accepted_at': window_start,
            },
        )
        # Always reset password to documented value + bump bio marker
        user.email = f'{username}@demo.heartbox.tw'
        user.bio = f'{bio_marker}{profile}'
        user.email_verified = True
        user.onboarding_completed = True
        user.timezone = ACCOUNT_TIMEZONE
        user.set_password(password)
        user.save()

        if full_reset and not created:
            user.delete()
            self.stdout.write(self.style.WARNING(f'  reset: deleted {username} entirely'))
            # Re-create
            user = User.objects.create(
                username=username,
                email=f'{username}@demo.heartbox.tw',
                bio=f'{bio_marker}{profile}',
                email_verified=True,
                onboarding_completed=True,
                timezone=ACCOUNT_TIMEZONE,
                age_band='18_plus',
                age_confirmed_13_plus=True,
                terms_accepted_at=window_start,
            )
            user.set_password(password)
            user.save()

        # Always wipe notes / tags / streak (idempotent reseed)
        MoodNote.objects.filter(user=user).delete()
        Tag.objects.filter(user=user).delete()
        JournalStreak.objects.filter(user=user).delete()

        # Backdate user signup
        sign_dt = window_start + timedelta(
            days=rng.randint(0, 5),
            hours=rng.randint(8, 22),
            minutes=rng.randint(0, 59),
        )
        User.objects.filter(pk=user.pk).update(
            date_joined=sign_dt, created_at=sign_dt, updated_at=sign_dt,
        )

        # Tags
        tag_objs = {}
        for name, color in spec['tag_palette']:
            tag_objs[name] = Tag.objects.create(user=user, name=name, color=color)

        # Distribute notes across (sign_dt → today)
        active_days = max(1, (today - sign_dt.date()).days)
        target_notes = spec['note_count']
        # Sample days; allow some days with multiple notes
        if target_notes <= active_days:
            chosen_days = sorted(rng.sample(range(active_days), target_notes))
        else:
            chosen_days = sorted(rng.choices(range(active_days), k=target_notes))

        mix_dict = dict(spec['sentiment_mix'])
        mix_pos = mix_dict.get('pos', 33)
        mix_neu = mix_dict.get('neu', 34)
        mix_neg = mix_dict.get('neg', 33)

        pools = CONTENT_POOLS[profile]
        baseline = spec['baseline']
        user_activities = spec['activities']

        notes_created = 0
        llm_failures = 0
        for idx, day_offset in enumerate(chosen_days):
            entry_date = sign_dt.date() + timedelta(days=day_offset)
            if entry_date > today:
                continue
            band = pick_band(mix_pos, mix_neu, mix_neg, rng)
            template_band, stress_band, content, hinted_tags = rng.choice(pools[band])
            weather, temp = pick_weather(rng, entry_date.month)

            sentiment = pick_sentiment(template_band, baseline, rng)
            # Weather nudge — same slight effect the zh-TW population seed
            # applies, so the dashboard's weather correlation has signal.
            if weather == 'sunny':
                sentiment = min(1.0, sentiment + 0.05)
            elif weather in ('rainy', 'stormy'):
                sentiment = max(-1.0, sentiment - 0.04)

            n_acts = rng.randint(0, min(3, len(user_activities)))
            note_activities = rng.sample(user_activities, n_acts) if n_acts else []

            if real_feedback:
                # ai_engine routes on the score we pass, so the sub-0.4 notes
                # go through RAG exactly as a real write would.
                from api.services.ai_engine import ai_engine
                try:
                    feedback = ai_engine.generate_feedback(content, round(sentiment, 3))
                except Exception as e:                                    # noqa: BLE001
                    llm_failures += 1
                    self.stdout.write(self.style.WARNING(
                        f'    [{username}] LLM feedback failed on note '
                        f'{idx + 1}/{len(chosen_days)} ({e}); using offline pool'
                    ))
                    feedback = pick_ai_feedback(sentiment, rng)
            else:
                feedback = pick_ai_feedback(sentiment, rng)

            note = MoodNote(
                user=user,
                sentiment_score=round(sentiment, 3),
                stress_index=pick_stress(stress_band, rng),
                ai_feedback=feedback,
                metadata={
                    'weather': weather,
                    'temperature': temp,
                    'activities': note_activities,
                },
            )
            note.set_content(content)
            note.save()

            # Tags: 0-2 per note, biased toward profile palette
            relevant_tags = [tag_objs[t] for t in hinted_tags if t in tag_objs]
            if relevant_tags and rng.random() < 0.75:
                note.tags.add(rng.choice(relevant_tags))
            if tag_objs and rng.random() < 0.30:
                note.tags.add(rng.choice(list(tag_objs.values())))

            entry_dt = datetime.combine(
                entry_date, time(hour=rng.randint(8, 23), minute=rng.randint(0, 59)),
                tzinfo=TZ,
            )
            MoodNote.objects.filter(pk=note.pk).update(
                created_at=entry_dt, updated_at=entry_dt,
            )
            notes_created += 1

            if real_feedback and (idx + 1) % 5 == 0:
                self.stdout.write(
                    f'    [{username}] {idx + 1}/{len(chosen_days)} notes done '
                    f'({llm_failures} LLM failures)'
                )

        # Streak
        latest = MoodNote.objects.filter(user=user, is_deleted=False).order_by('-created_at').first()
        JournalStreak.objects.update_or_create(
            user=user,
            defaults={
                'current_streak': 1 if latest else 0,
                'longest_streak': max(1, notes_created // 7),
                'last_entry_date': latest.created_at.astimezone(TZ).date() if latest else None,
                'total_entries': notes_created,
            },
        )

        suffix = ''
        if real_feedback:
            suffix = (f', feedback=LLM ({llm_failures} fell back to pool)'
                      if llm_failures else ', feedback=LLM')
        self.stdout.write(self.style.SUCCESS(
            f'  [OK] {username} ({profile}) - {notes_created} notes, '
            f'tags={len(tag_objs)}, baseline={baseline:+.2f}{suffix}'
        ))
