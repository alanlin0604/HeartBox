"""Seed the demo@heartbox.tw account used by Google Play reviewers.

Idempotent: runs against the DB pointed to by DATABASE_URL. Use --reset to wipe
and re-seed the demo user's content; otherwise only fills gaps.

    python manage.py seed_demo_account              # create or top up
    python manage.py seed_demo_account --reset      # wipe content and re-seed
"""

from datetime import date, datetime, time, timedelta
import random

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from api.models import (
    AIChatMessage, AIChatSession,
    HealthMetric, JournalStreak, MoodNote, Tag,
)

User = get_user_model()

DEMO_USERNAME = 'demo'
DEMO_EMAIL = 'demo@heartbox.tw'
DEMO_PASSWORD = 'DemoPass2026'
DEMO_DAYS = 14

TAG_PALETTE = [
    ('工作', '#8b5cf6'),
    ('家庭', '#ec4899'),
    ('感恩', '#f59e0b'),
    ('運動', '#10b981'),
    ('睡眠', '#3b82f6'),
]

# 14 entries — varied tone, realistic length, zh-TW. (sentiment, stress, tags, content, ai_feedback)
JOURNAL_ENTRIES = [
    (0.7, 2, ['感恩'],
     '今天去爬象山，山頂的風很涼，把整個禮拜累積的疲倦都吹走了。原來偶爾離開螢幕、走進自然，比任何休息都有效。',
     '看到你願意主動安排這樣的時間照顧自己，真的很棒。記得這份輕盈感，下次累的時候，給自己一個重新出發的機會。'),
    (-0.3, 6, ['工作'],
     '會議從早上十點開到下午兩點半，期間還被插了三通電話。回到座位才發現原本要交的東西完全沒動。整個下午都在補進度，腦袋脹脹的。',
     '長時間高密度的會議真的會耗光專注力。如果可能，試著把不同類型的工作分到不同時段，給大腦切換的緩衝。'),
    (0.4, 3, ['家庭'],
     '晚上和媽媽通電話聊了快一小時，聊她最近在學的太極拳。她說一開始覺得自己學不會，但教練說「沒有人天生會」。聽起來像在對我說。',
     '家人不經意說的一句話有時候比專業建議還有力量。把這句「沒有人天生會」記下來，下次卡住時可以提醒自己。'),
    (0.0, 5, ['工作'],
     '今天沒什麼特別的事，就是普通地上班、普通地下班。這種日子有時候反而最讓人困惑——說不上好，也說不上壞。',
     '平淡的日子也是生活的一部分。不是每一天都需要有意義，能夠安穩地度過，本身已經值得肯定。'),
    (0.6, 2, ['運動', '感恩'],
     '報名了線上瑜伽課，第一堂結束後身體有種久違的放鬆感。教練說「呼吸進到哪裡，意識就到哪裡」，我做了好幾次深呼吸才真的感受到。',
     '把身體和心理放在一起照顧是很聰明的選擇。瑜伽帶來的放鬆會慢慢累積，幾週後你會發現自己的睡眠和情緒都變穩。'),
    (-0.5, 7, ['工作'],
     '專案 deadline 提前了兩週，組員又有人請假。今晚加班到十一點才回家，吃了便利商店的飯糰。坐在沙發上覺得自己快撐不住了。',
     '聽到這樣的描述很心疼。請記得：高壓狀態下做出的決定通常不是最好的決定。明天能不能找主管聊聊資源調整？你不需要一個人扛。'),
    (0.3, 4, ['睡眠'],
     '昨晚提前一個小時上床，把手機放在客廳。今天起床的感覺差很多，整個人比較清醒，連咖啡都覺得不太需要。',
     '把手機和睡眠隔開是個很有效的習慣。如果可以的話，試著把這個小改變固定下來，一週後再來看看身體的回應。'),
    (0.5, 3, ['家庭', '感恩'],
     '週末和姊姊吃飯，她分享最近想轉換跑道的猶豫。我發現自己能夠認真聽，而不是急著給建議。或許這就是一種成熟。',
     '能夠單純地聽，不急著解決，是很珍貴的能力。對別人是支持，對自己是練習耐心。你做得很好。'),
    (-0.2, 5, [],
     '不知道為什麼今天一直覺得有點悶。沒發生什麼特別的事，但情緒就是低低的。也許是天氣，也許是身體在提醒我什麼。',
     '情緒沒有理由也是合理的。今晚不要勉強自己解釋為什麼，給自己一個放空的時間就好。明天再看看身體想說什麼。'),
    (0.8, 1, ['感恩', '運動'],
     '參加了公司的健康日活動，跟同事一起打了兩小時羽球。汗流浹背但心情超好，發現好久沒有這樣大笑了。',
     '身體運動帶來的多巴胺加上社交連結，是最自然的抗壓組合。這份愉快可以記在心裡，工作累的時候拿出來提醒自己。'),
    (0.1, 5, ['工作', '睡眠'],
     '半夜兩點才睡著，腦袋一直在想下週的簡報該怎麼開場。早上鬧鐘響的時候，覺得自己還沒準備好面對今天。',
     '睡前思緒停不下來時，可以試著把擔心的事情寫下來，告訴自己「明天再處理」。這種「外化」的動作有時候比強迫入睡更有效。'),
    (0.4, 3, ['家庭'],
     '晚上煮了義大利麵給自己吃，配一杯紅酒，看了一部老電影。一個人的晚上也可以這樣過。',
     '能夠享受一個人的時間是很重要的能力。儀式感不需要有別人在場才成立，你已經把今晚過得很好。'),
    (0.6, 2, ['感恩'],
     '今天收到客戶的感謝信，說我們上週交付的成果幫他們解決了一個拖了半年的問題。原來那些加班的夜晚是有意義的。',
     '辛苦付出的回報不一定即時，但它會以你想不到的方式回來。記得這份被看見的感覺。'),
    (0.5, 3, ['運動', '感恩'],
     '今天早上散步去買咖啡，路上看到第一朵盛開的杜鵑。突然覺得春天真的來了，連帶整個人也輕鬆了一些。',
     '能夠注意到季節的細節是很可貴的。城市再忙，也別讓自己錯過這些小小的提醒——時間在走，你也在前進。'),
]

# Quick mock chat — varied tone, demonstrates emotion analysis features.
CHAT_MESSAGES = [
    ('user', '最近常常覺得很疲憊，工作沒做完就回家了，回家也不想動。', None, 6),
    ('assistant', '聽起來你正承受不少壓力。當「沒做完」的感覺持續累積，疲倦會變成全身性的，不只是身體。可以試著辨認這份疲倦的來源——是任務量、是責任感、還是對自己的標準？這三種需要的修復方式不太一樣。', None, None),
    ('user', '應該是責任感吧。覺得不做完對不起團隊。', None, 5),
    ('assistant', '責任感是好事，但「對不起團隊」這個句子值得停下來看一下。你的角色是把該做的事盡力做好，不是承擔所有人的進度。如果今晚把工作放下、好好休息一晚，明天的你會比今晚硬撐的你更能照顧團隊。', None, None),
    ('user', '聽起來有點道理。我可能太把自己當救火隊了。', 0.2, 4),
    ('assistant', '能夠這樣覺察自己已經是改變的開始。下次感覺要超載時，可以問自己：「這真的是我的火，還是別人的？」幫自己把界線畫清楚，疲憊會慢慢退潮。', None, None),
]


class Command(BaseCommand):
    help = 'Create or refresh the demo@heartbox.tw account used by Play reviewers'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Wipe demo user content (notes, health, chat) before seeding',
        )

    def handle(self, *args, **options):
        user, created = User.objects.get_or_create(
            username=DEMO_USERNAME,
            defaults={
                'email': DEMO_EMAIL,
                'bio': 'Demo account for Google Play review',
                'email_verified': True,
                'onboarding_completed': True,
                'timezone': 'Asia/Taipei',
            },
        )
        # Always reset the password so the documented one works even if rotated.
        user.email = DEMO_EMAIL
        user.email_verified = True
        user.onboarding_completed = True
        user.set_password(DEMO_PASSWORD)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created user {DEMO_USERNAME} ({DEMO_EMAIL})'))
        else:
            self.stdout.write(f'User {DEMO_USERNAME} exists — password reset to documented value')

        if options['reset']:
            n_notes, _ = MoodNote.objects.filter(user=user).delete()
            n_health, _ = HealthMetric.objects.filter(user=user).delete()
            n_sessions, _ = AIChatSession.objects.filter(user=user).delete()
            n_tags, _ = Tag.objects.filter(user=user).delete()
            self.stdout.write(f'  reset: {n_notes} notes, {n_health} health, {n_sessions} chat sessions, {n_tags} tags')

        # --- Tags ---
        tag_objs = {}
        for name, color in TAG_PALETTE:
            t, _ = Tag.objects.get_or_create(user=user, name=name, defaults={'color': color})
            tag_objs[name] = t

        # --- Mood notes (one per day, walking back from today) ---
        today = timezone.localdate()
        random.seed(42)  # reproducible content
        notes_created = 0
        for i, (sentiment, stress, tag_names, content, ai_feedback) in enumerate(JOURNAL_ENTRIES):
            entry_date = today - timedelta(days=i)
            # Skip if a note already exists for that day (idempotency without --reset)
            if MoodNote.objects.filter(user=user, created_at__date=entry_date, is_deleted=False).exists():
                continue
            note = MoodNote(
                user=user,
                sentiment_score=sentiment,
                stress_index=stress,
                ai_feedback=ai_feedback,
                is_pinned=(i == 0 and sentiment > 0.6),  # pin a recent positive entry
                metadata={'weather': random.choice(['sunny', 'cloudy', 'rainy']),
                          'temperature': random.randint(18, 28)},
            )
            note.set_content(content)
            note.save()
            # Backdate created_at for the dashboard trend chart
            entry_dt = timezone.make_aware(datetime.combine(entry_date, time(hour=21, minute=random.randint(0, 59))))
            MoodNote.objects.filter(pk=note.pk).update(created_at=entry_dt, updated_at=entry_dt)
            for name in tag_names:
                note.tags.add(tag_objs[name])
            notes_created += 1
        self.stdout.write(f'  notes: +{notes_created} (total {MoodNote.objects.filter(user=user, is_deleted=False).count()})')

        # --- Health metrics (per day, per type) ---
        health_created = 0
        for i in range(DEMO_DAYS):
            d = today - timedelta(days=i)
            base_steps = random.randint(5500, 11500)
            samples = [
                ('steps', base_steps),
                ('heart_rate', round(random.uniform(64, 78), 1)),
                ('hrv', round(random.uniform(35, 55), 1)),
                ('active_calories', round(base_steps * random.uniform(0.035, 0.045), 1)),
                ('exercise_minutes', random.choice([15, 20, 25, 30, 35, 45, 55])),
            ]
            for metric_type, value in samples:
                _, was_created = HealthMetric.objects.update_or_create(
                    user=user, date=d, metric_type=metric_type,
                    defaults={'value': value, 'source': 'demo-seed'},
                )
                if was_created:
                    health_created += 1
        self.stdout.write(f'  health: +{health_created} metrics ({HealthMetric.objects.filter(user=user).count()} total)')

        # --- Journal streak ---
        streak, _ = JournalStreak.objects.update_or_create(
            user=user,
            defaults={
                'current_streak': DEMO_DAYS,
                'longest_streak': DEMO_DAYS,
                'last_entry_date': today,
                'total_entries': MoodNote.objects.filter(user=user, is_deleted=False).count(),
            },
        )
        self.stdout.write(f'  streak: {streak.current_streak} days')

        # --- AI chat session ---
        if not AIChatSession.objects.filter(user=user).exists():
            session = AIChatSession.objects.create(
                user=user, title='關於工作疲憊', is_active=True, is_pinned=True,
            )
            for role, content, sentiment, stress in CHAT_MESSAGES:
                AIChatMessage.objects.create(
                    session=session, role=role, content=content,
                    sentiment_score=sentiment, stress_index=stress,
                )
            self.stdout.write(f'  chat: 1 session, {len(CHAT_MESSAGES)} messages')
        else:
            self.stdout.write('  chat: already present (use --reset to refresh)')

        self.stdout.write(self.style.SUCCESS(
            f'\nDemo account ready:\n  username: {DEMO_USERNAME}\n  email: {DEMO_EMAIL}\n  password: {DEMO_PASSWORD}'
        ))
