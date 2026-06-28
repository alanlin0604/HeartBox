"""Seed realistic user feedback for the admin "使用回饋" tab.

Pulls ~45 random seed users (those created by seed_demo_population) and
attaches one feedback entry each with a backdated created_at inside the
April-June user-testing window. Rating distribution is intentionally
positive-leaning (avg ~4.2) so the admin overview looks like a healthy
product — most users had a good experience, a few were lukewarm, one or
two had a bad day. Avoids the "all 5★" pattern that screams seed data.

Identifies seeded feedback by the bound user (their bio starts with the
seed marker), so the cleanup query is a simple JOIN. No marker bytes
needed on the Feedback row itself.

Usage:
    python manage.py seed_demo_feedback
    python manage.py seed_demo_feedback --reset    # wipe seed-user feedback
    python manage.py seed_demo_feedback --count 60 # override default 45
"""
from __future__ import annotations

import random
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from api.models import Feedback

User = get_user_model()

SEED_BIO_PREFIX = '[seed:'
DEFAULT_COUNT = 45
# Window matches seed_demo_population — April through today
WINDOW_START = datetime(2026, 4, 15)

# Rating distribution: weighted toward 4-5 to look like a healthy app.
RATING_WEIGHTS = [
    (5, 45),
    (4, 35),
    (3, 13),
    (2,  5),
    (1,  2),
]

# Content pool — keyed by rating band so 5★ gets a glowing comment and
# 1★ gets a constructive complaint. Variety within each band so 45
# entries don't repeat.
CONTENT_5 = [
    '介面真的很舒服，特別是日記寫完會給溫暖的回饋，感覺真的有人在聽。',
    '已經用兩個多月了，每天睡前寫一篇變成新習慣。原本很怕看自己的情緒，現在反而會主動寫。',
    '心情趨勢圖讓我發現自己每個月底狀態都會掉，意識到後現在會提早安排放鬆，超有用！',
    '推薦給朋友後她也愛上了。比市面上其他日記 app 更有「被理解」的感覺。',
    '個人化洞察那塊很神奇，居然真的抓到我下雨天容易憂鬱的規律，建議也都很實在。',
    'AI 回饋很有溫度，不是那種制式罐頭話，會看完心裡覺得暖暖的。',
    '介面乾淨，速度快，功能該有的都有。我在 App Store 找好久才找到這款。',
    '寫到第三十篇的時候解鎖了一個成就，那一刻真的有被肯定的感覺，繼續寫的動力。',
    '當作情緒筆記用很方便，標籤分類做得好直觀。',
    '隱私做得很到位，看到日記是加密儲存就很安心，會願意寫得更深一點。',
    '今日個人化建議結合了天氣讓我有點驚喜，沒想到 app 會這樣關心使用者。',
    '冥想跟睡眠追蹤一起看的時候，第一次明白為什麼自己這幾週特別焦躁。感謝這款 app。',
    '當諮商前的暖身工具用很合適，去諮商時可以直接把這幾週的紀錄翻給諮商師看。',
    '我自己是憂鬱症患者，這款 app 比市售大牌好用，重點是中文很自然不會卡。',
]
CONTENT_4 = [
    '整體很不錯，唯一想要的是希望可以 Android 也有原生版（目前用網頁也還行）。',
    '功能很完整，剛開始有點不知道從哪寫起，建議可以增加新手導覽。',
    '圖表蠻好看的，但希望可以匯出 PDF 給諮商師看。',
    '愛這款，唯一覺得可惜的是離線時某些功能不能用。',
    '寫日記寫得很順，AI 回饋偶爾會重複句型，但整體仍然加分。',
    '介面美感很棒，比同類 app 都好看。再增加一些自訂主題會更完美。',
    '推薦給好幾位朋友，大家都覺得「終於有一款不是冷冰冰的情緒紀錄 app」。',
    '使用感很好，希望可以增加家人共享情緒摘要的功能（在家人同意的前提下）。',
    '蠻喜歡的，會持續用下去。如果可以加個語音輸入會更方便。',
    '功能蠻齊全，標籤想要可以再多一些預設選項。',
    '每天記錄已經養成習慣，希望以後可以做月份/年度的回顧報告。',
    '介面流暢、加密我也很放心，整體很好用。',
]
CONTENT_3 = [
    '功能還可以，但偶爾載入會卡一下。希望可以再優化速度。',
    '介面美但功能對我來說有點太多，希望有「簡單模式」。',
    '日記 AI 分析有時候不太準，但其他功能還不錯。',
    '蠻好用的，但每天的提示問題重複率有點高。',
    '一般般，期待之後有更多個人化內容。',
    '功能 OK，希望增加多語界面（雖然知道已經有英日，但希望更多）。',
]
CONTENT_2 = [
    '想用但介面有點複雜，新手不友善，需要花時間摸索。',
    'AI 回饋有時候會偏離主題，希望可以更精準。',
]
CONTENT_1 = [
    '剛開始用，遇到網頁打不開的問題，希望可以儘快修復。',
]

CONTENT_BY_RATING = {
    5: CONTENT_5,
    4: CONTENT_4,
    3: CONTENT_3,
    2: CONTENT_2,
    1: CONTENT_1,
}


def pick_rating(rng: random.Random) -> int:
    population = [r for r, _ in RATING_WEIGHTS]
    weights = [w for _, w in RATING_WEIGHTS]
    return rng.choices(population, weights=weights, k=1)[0]


def random_dt_in_window(rng: random.Random, sign_dt_min: datetime, now: datetime) -> datetime:
    """Pick a datetime between the user's signup and now (within window).

    All datetimes are normalised to aware (TIME_ZONE) before comparison
    so we don't trip Django's naive/aware comparison error.
    """
    aware_window_start = timezone.make_aware(WINDOW_START) if timezone.is_naive(WINDOW_START) else WINDOW_START
    if timezone.is_naive(sign_dt_min):
        sign_dt_min = timezone.make_aware(sign_dt_min)
    start = max(sign_dt_min, aware_window_start)
    if start > now:
        start = now - timedelta(days=3)
    span = max(60, int((now - start).total_seconds()))
    offset = rng.randint(60, span)
    return now - timedelta(seconds=offset)


class Command(BaseCommand):
    help = 'Seed realistic positive-leaning feedback for the admin tab'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=DEFAULT_COUNT)
        parser.add_argument('--reset', action='store_true',
                            help='Wipe all feedback from seed users first')
        parser.add_argument('--seed', type=int, default=2026)

    def handle(self, *args, **opts):
        rng = random.Random(opts['seed'])
        now = timezone.now()
        count = opts['count']

        if opts['reset']:
            n = Feedback.objects.filter(user__bio__startswith=SEED_BIO_PREFIX).count()
            Feedback.objects.filter(user__bio__startswith=SEED_BIO_PREFIX).delete()
            self.stdout.write(self.style.WARNING(f'  reset: removed {n} seed-user feedback rows'))

        existing = Feedback.objects.filter(user__bio__startswith=SEED_BIO_PREFIX).count()
        if existing >= count:
            self.stdout.write(f'Already have {existing} seed feedback rows (target {count}); nothing to do.')
            return

        # Pick users who don't already have a feedback (idempotency safety)
        candidates = list(User.objects.filter(
            bio__startswith=SEED_BIO_PREFIX,
            feedbacks__isnull=True,
        ).order_by('?')[:count - existing])

        if not candidates:
            self.stdout.write(self.style.ERROR('No eligible seed users without existing feedback.'))
            return

        created = 0
        for u in candidates:
            rating = pick_rating(rng)
            content = rng.choice(CONTENT_BY_RATING[rating])
            sign_dt = u.date_joined if u.date_joined else WINDOW_START
            if timezone.is_naive(sign_dt):
                sign_dt = timezone.make_aware(sign_dt)
            dt = random_dt_in_window(rng, sign_dt, now)

            fb = Feedback.objects.create(user=u, rating=rating, content=content)
            Feedback.objects.filter(pk=fb.pk).update(created_at=dt)
            created += 1

        # Stats
        all_seed = Feedback.objects.filter(user__bio__startswith=SEED_BIO_PREFIX)
        avg = sum(f.rating for f in all_seed) / max(1, all_seed.count())
        dist = {r: all_seed.filter(rating=r).count() for r in (5, 4, 3, 2, 1)}
        self.stdout.write(self.style.SUCCESS(
            f'Created {created} feedback rows. '
            f'Total seed feedback: {all_seed.count()} | avg {avg:.2f}★ | '
            f'dist: 5★={dist[5]} 4★={dist[4]} 3★={dist[3]} 2★={dist[2]} 1★={dist[1]}'
        ))
