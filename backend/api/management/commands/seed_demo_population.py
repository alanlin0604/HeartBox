"""Seed a realistic demo population (~260 users) for capstone-defense demos.

Generates users whose accounts look like real journal-keepers:

  - Realistic zh-TW names (surname + given name) with pinyin usernames.
  - Distributed signup dates across the project lifetime (Feb 2026 → now)
    with a growth-curve weighting (more recent users than early ones).
  - Per-user profile: power / regular / casual / dropoff cadence; a mood
    baseline; a 3-6 tag palette; weather/temperature realistic for Taipei;
    a subset of activities. Charts, insights, and aggregates therefore
    show real-looking patterns instead of uniform noise.
  - 5-50 backdated MoodNotes per user. Content rotates from an ~80-line
    pool with time-of-day and tag-aware variations so 5000+ entries don't
    feel templated.

All seeded accounts carry the marker ``bio = "[seed:<batch_id>]"`` and use
emails under ``@demo.heartbox.tw`` so a single ``--reset`` query nukes
the entire population without touching real users.

Idempotency:
  - Without flags: skip the run if a previous batch already exists.
  - ``--force`` to add another batch even when one exists.
  - ``--reset`` to wipe all prior demo-seed users first.
  - ``--count N`` to override the default 260.
  - ``--dry-run`` to print the plan without writing.

Run locally first:
    python manage.py seed_demo_population --dry-run
    python manage.py seed_demo_population

For prod (Cloud Run job pattern):
    gcloud run jobs create heartbox-seed-population \
        --image=<existing-api-image> \
        --command="python" \
        --args="manage.py,seed_demo_population"
    gcloud run jobs execute heartbox-seed-population --wait
"""
from __future__ import annotations

import random
from datetime import datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from api.models import JournalStreak, MoodNote, Tag

User = get_user_model()

SEED_EMAIL_DOMAIN = '@demo.heartbox.tw'
SEED_BIO_PREFIX = '[seed:'
DEFAULT_COUNT = 260
PROJECT_LAUNCH = datetime(2026, 2, 11)   # earliest commit
DEFAULT_PASSWORD = 'DemoPop2026!'

# ---------------------------------------------------------------------------
# Name pools — common Taiwanese surnames + given names. Combined pool
# covers male/female/unisex; pinyin romanization keyed by character.
# ---------------------------------------------------------------------------

SURNAMES = [
    ('陳', 'chen'), ('林', 'lin'), ('黃', 'huang'), ('張', 'chang'),
    ('李', 'li'), ('王', 'wang'), ('吳', 'wu'), ('劉', 'liu'),
    ('蔡', 'tsai'), ('楊', 'yang'), ('許', 'hsu'), ('鄭', 'cheng'),
    ('謝', 'hsieh'), ('郭', 'kuo'), ('洪', 'hung'), ('邱', 'chiu'),
    ('曾', 'tseng'), ('廖', 'liao'), ('賴', 'lai'), ('徐', 'hsu'),
    ('周', 'chou'), ('葉', 'yeh'), ('蘇', 'su'), ('江', 'chiang'),
    ('呂', 'lu'), ('何', 'ho'), ('羅', 'lo'), ('高', 'kao'),
    ('蕭', 'hsiao'), ('潘', 'pan'),
]

GIVEN_NAMES = [
    # Two-character given names with rough pinyin
    ('志明', 'chihming'), ('俊宏', 'chunhung'), ('建宏', 'chienhung'),
    ('家豪', 'chiahao'), ('文雄', 'wenhsiung'), ('志偉', 'chihwei'),
    ('明哲', 'mingche'), ('政翰', 'chenghan'), ('柏翰', 'pohan'),
    ('柏宇', 'poyu'), ('冠廷', 'kuanting'), ('宇翔', 'yuhsiang'),
    ('承翰', 'chenghan'), ('凱翔', 'kaihsiang'), ('育安', 'yuan'),
    ('立祥', 'lihsiang'), ('崇文', 'chungwen'), ('俊賢', 'chunhsien'),

    ('雅婷', 'yating'), ('美玲', 'meiling'), ('淑芬', 'shufen'),
    ('怡君', 'yichun'), ('雅雯', 'yawen'), ('佳穎', 'chiaying'),
    ('佩珊', 'peishan'), ('婉君', 'wanchun'), ('心怡', 'hsinyi'),
    ('思婷', 'szuting'), ('彥婷', 'yenting'), ('靜怡', 'chingyi'),
    ('郁婷', 'yuting'), ('育琪', 'yuchi'), ('佳蓉', 'chiajung'),
    ('庭瑄', 'tinghsuan'), ('佩蓉', 'peijung'), ('巧涵', 'chiaohan'),

    # Unisex
    ('子晴', 'tzuching'), ('安琪', 'anchi'), ('柔安', 'jouan'),
    ('語璇', 'yuhsuan'), ('品妍', 'pinyen'), ('沛蓉', 'peijung'),
    ('采妮', 'tsaini'), ('俞安', 'yuan'), ('予恩', 'yuen'),
    ('恩瑜', 'enyu'), ('宇恩', 'yuen'), ('沛恩', 'peien'),
]

# Per-user content palette tag — chosen subset per user
TAG_PALETTE = [
    ('工作', '#8b5cf6'), ('家庭', '#ec4899'), ('感恩', '#f59e0b'),
    ('運動', '#10b981'), ('睡眠', '#3b82f6'), ('朋友', '#f43f5e'),
    ('學習', '#06b6d4'), ('飲食', '#f97316'), ('旅行', '#84cc16'),
    ('健康', '#14b8a6'), ('情緒', '#a855f7'), ('成長', '#eab308'),
    ('閱讀', '#0ea5e9'), ('音樂', '#d946ef'), ('反思', '#64748b'),
]

ACTIVITIES = [
    'exercise', 'social', 'work', 'reading', 'travel', 'music',
    'cooking', 'meditation', 'gaming', 'shopping', 'movie', 'nature',
]

# WMO-ish weather buckets — frequency roughly matches Taipei climate
WEATHER_DIST = (
    ['sunny'] * 35 + ['cloudy'] * 35 + ['rainy'] * 20 + ['stormy'] * 5 + ['foggy'] * 5
)

# ---------------------------------------------------------------------------
# Journal content — pool of ~80 zh-TW templates of varied tone & topic.
# Each picks a sentiment band; runtime composes with optional prefixes /
# tags for variety so 5000 entries don't all read the same.
# ---------------------------------------------------------------------------

# Format: (sentiment_band, stress_band, content_template, tag_hints)
# Bands: 'pos', 'neu', 'neg' → sentiment range; 'low', 'mid', 'high' → stress
CONTENT_POOL = [
    # ---- 正向 (positive) ----
    ('pos', 'low', '今天去爬山，山頂的風很涼，整個禮拜的疲倦都被吹走了。原來離開螢幕走進自然，比什麼休息都有效。', ['運動', '感恩']),
    ('pos', 'low', '早上跟久沒見的朋友吃早午餐，聊到大學那些蠢事還是會大笑。有些關係不用刻意維持也會自然延續。', ['朋友', '感恩']),
    ('pos', 'low', '收到客戶的感謝信，說我們上週交付的成果幫他們解決了一個拖了半年的問題。原來那些加班的夜晚是有意義的。', ['工作', '感恩']),
    ('pos', 'low', '參加公司健康日，跟同事打了兩小時羽球。汗流浹背但心情超好，發現好久沒這樣大笑了。', ['運動', '朋友']),
    ('pos', 'low', '今天早上散步去買咖啡，路上看到第一朵盛開的杜鵑。突然覺得春天真的來了。', ['感恩']),
    ('pos', 'low', '報名了線上瑜伽課，第一堂結束後身體有種久違的放鬆感。教練說「呼吸進到哪裡，意識就到哪裡」。', ['運動', '健康']),
    ('pos', 'low', '晚上和媽媽通電話聊了一小時，她在學太極拳。她說「沒有人天生會」，聽起來像在對我說。', ['家庭']),
    ('pos', 'low', '今天提早完成手上的事，難得有空閒去附近書店逛了一個下午。沒目的的時間真的很珍貴。', ['閱讀', '感恩']),
    ('pos', 'low', '加入了讀書會，第一次跟陌生人討論一本書。被別人的觀點打開新世界的感覺很棒。', ['學習', '朋友']),
    ('pos', 'low', '把房間整理了一個下午，把不用的東西捐出去。空間整理完心情也跟著輕鬆。', ['反思', '成長']),
    ('pos', 'low', '今晚煮了義大利麵給自己吃，配一杯紅酒，看了一部老電影。一個人的晚上也可以這樣過。', ['飲食', '感恩']),
    ('pos', 'mid', '簡報終於結束了，主管當場給了好評。準備了三個禮拜的東西沒白費，今晚要好好睡一覺。', ['工作', '睡眠']),
    ('pos', 'low', '帶爸媽去吃了他們唸了很久的那家餐廳。看到他們吃得開心，比自己吃還滿足。', ['家庭', '感恩']),
    ('pos', 'low', '今天運動完去買菜，回家做了一頓晚餐。簡單的生活節奏其實最舒服。', ['運動', '飲食']),
    ('pos', 'low', '報名了陶藝課，第一堂手忙腳亂但很療癒。專心捏一個東西的感覺，跟工作完全不同。', ['學習', '成長']),
    ('pos', 'mid', '今天第一次主動向同事道謝，他幫了我一個小忙。原本覺得小事，但說出口後氣氛變得很好。', ['工作', '反思']),
    ('pos', 'low', '週末去看了一場戶外音樂會，躺在草地上聽現場樂團。城市裡也能找到這樣的時刻。', ['音樂', '感恩']),
    ('pos', 'low', '今天的會議意外地短，多出的時間我去附近的公園走走。陽光剛好，整個人很放鬆。', ['工作', '感恩']),
    ('pos', 'mid', '練習了一個月的鋼琴小曲今天終於彈順了。看似微不足道的進步，但對自己很重要。', ['學習', '成長']),

    # ---- 中性 (neutral) ----
    ('neu', 'mid', '今天沒什麼特別的事，就是普通地上班、普通地下班。這種日子有時候反而最讓人困惑。', ['工作']),
    ('neu', 'mid', '下班後直接回家，沒做晚餐就點了外送。電視開著但沒在看，就這樣到睡覺。', ['睡眠']),
    ('neu', 'mid', '在咖啡廳坐了一整個下午，本來想寫東西但什麼也沒寫出來。腦袋空空的也許就是該空空的。', ['反思']),
    ('neu', 'mid', '今天的進度沒有很多，但也沒有特別少。就是這樣的一天。', ['工作']),
    ('neu', 'mid', '路上突然想起以前的事，發了一下呆。沒什麼結論，但腦袋好像被整理過一遍。', ['反思']),
    ('neu', 'mid', '今晚的天氣有點悶，本來想出門散步又懶得動。最後就在沙發上滑了一陣子手機。', []),
    ('neu', 'low', '同事生日，公司有訂蛋糕。沒什麼特別感覺，但這種小儀式還是讓辦公室有點溫度。', ['工作']),
    ('neu', 'mid', '看了一篇關於睡眠的文章，發現自己長期都睡不好。可能該認真調整一下。', ['睡眠', '健康']),
    ('neu', 'mid', '收到大學同學的訊息，聊了一下彼此的近況。發現大家都在各自的軌道上前進，有點感慨。', ['朋友', '反思']),
    ('neu', 'mid', '在通勤的捷運上看完一本書，闔上的瞬間有種完成感。但走出車站後又被現實淹沒。', ['閱讀']),
    ('neu', 'mid', '今天午餐吃得很簡單，下班後沒什麼力氣，回家就洗澡睡了。', ['飲食']),
    ('neu', 'low', '想了一下這個禮拜過得怎樣，發現不錯也不壞。也許這就是日子。', ['反思']),
    ('neu', 'mid', '今天比預期更早完成手上的東西，多出的時間反而不知道做什麼。', ['工作']),

    # ---- 負向 (negative) ----
    ('neg', 'high', '專案 deadline 提前兩週，組員又有人請假。今晚加班到十一點才回家，吃了便利商店的飯糰。', ['工作']),
    ('neg', 'high', '半夜兩點才睡著，腦袋一直在想下週的簡報該怎麼開場。早上鬧鐘響的時候，覺得自己還沒準備好面對今天。', ['工作', '睡眠']),
    ('neg', 'mid', '不知道為什麼今天一直覺得有點悶。沒發生什麼特別的事，但情緒就是低低的。', ['情緒']),
    ('neg', 'high', '今天被主管在會議上指出一個錯誤，雖然就事論事，但整個下午心情都沒辦法平復。', ['工作', '情緒']),
    ('neg', 'mid', '跟朋友吵了一架，事後想想其實是小事，但話已經說出口，要怎麼回去都覺得卡住。', ['朋友', '情緒']),
    ('neg', 'high', '會議從早上十點開到下午兩點半，期間還被插了三通電話。回到座位才發現原本要交的東西完全沒動。', ['工作']),
    ('neg', 'mid', '今晚失眠到天亮，翻來覆去地想以前發生的事。明知道沒意義，但腦袋停不下來。', ['睡眠']),
    ('neg', 'mid', '今天家裡又因為小事吵起來。已經習慣了，但每次發生還是會耗掉一整天的能量。', ['家庭', '情緒']),
    ('neg', 'high', '感覺最近什麼都做不好。明明每天都很努力，但結果就是不如預期。開始懷疑是不是自己的問題。', ['情緒', '反思']),
    ('neg', 'mid', '雨下了一整天，連去買午餐都覺得麻煩。在家工作其實很方便，但有時候會覺得自己被困住了。', []),
    ('neg', 'mid', '今天讀了一篇文章說「30 歲還沒存到 OO 萬的人」之類的標題，看完心情變很糟。', ['反思', '情緒']),
    ('neg', 'high', '今天突然覺得很累，不是身體累，是那種「不知道在為什麼努力」的累。', ['情緒', '反思']),
    ('neg', 'mid', '想找朋友聊天但又怕打擾人家。最後還是把訊息打了又刪。', ['朋友', '情緒']),
    ('neg', 'high', '工作上的事一直堆積，每天都覺得只是在處理「最緊急」的，根本沒空想「重要」的。', ['工作']),
    ('neg', 'mid', '今天嘗試早睡，但躺在床上滑手機滑到一點半。明知道不對但停不下來。', ['睡眠']),

    # ---- 混合 / 反思類 ----
    ('neu', 'mid', '今天去做了一年一次的健康檢查，結果都正常，但醫生提醒我要多運動。又是一個熟悉的提醒。', ['健康', '反思']),
    ('pos', 'mid', '把長期拖著沒做的事情解決了一件，雖然花了整個週末，但心裡那塊石頭終於放下。', ['成長', '反思']),
    ('neu', 'low', '今天沒做什麼大事，但走在路上突然有種感覺：原來日子就是這樣一天一天累積起來的。', ['反思']),
    ('pos', 'low', '帶寵物去散步，看牠在草地上奔跑的樣子，突然覺得很多事都沒那麼重要。', ['感恩']),
    ('neg', 'mid', '最近常常想到以前不該說的話，明知道過了就過了，但腦袋還是會自己跑回去。', ['反思']),
    ('pos', 'low', '今天試了一個新的早餐店，老闆人很好還記得我說過的話。城市裡的小溫暖。', ['飲食', '感恩']),
    ('neu', 'mid', '一個人吃晚餐的時候會想很多事，但今晚什麼都不想，只是好好把飯吃完。', ['飲食', '反思']),
    ('pos', 'mid', '今天主動約了一個很久沒聯絡的朋友，雖然有點緊張但對方很開心。下次別再讓自己後悔了。', ['朋友', '成長']),
]

# AI feedback pool — friendly paraphrases keyed loosely to sentiment
AI_FEEDBACK_POS = [
    '聽到你願意主動安排這樣的時間照顧自己，真的很棒。記得這份輕盈感，下次累的時候，給自己一個重新出發的機會。',
    '能注意到生活的小小光亮，是讓人持續走下去的力量。把這份感受記下來，當作之後可以回頭看的禮物。',
    '看得出你今天和自己的關係很好。這種狀態值得被珍惜，也很值得分享給身邊的人。',
    '能夠把這樣的時刻寫下來，本身就是一種溫柔。慢慢地，你會發現自己更懂得照顧自己。',
    '一個能感受到滿足的日子，背後通常都有許多細心的選擇。為今天的你拍拍手吧。',
]
AI_FEEDBACK_NEU = [
    '平淡的日子也是生活的一部分。不是每一天都需要有意義，能夠安穩地度過，本身已經值得肯定。',
    '能夠在不太有起伏的日子裡寫下自己的觀察，是很細膩的覺察。慢慢累積，你會發現規律。',
    '今天的狀態雖然平和，但你願意停下來記錄，這份習慣會在需要的時候給你方向。',
    '日子起起伏伏是正常的，平淡的時刻其實也是修復期。不用急著找到結論。',
]
AI_FEEDBACK_NEG = [
    '聽到這樣的描述很心疼。請記得：高壓狀態下做出的決定通常不是最好的決定。明天能不能找人聊聊資源調整？你不需要一個人扛。',
    '情緒沒有理由也是合理的。今晚不要勉強自己解釋為什麼，給自己一個放空的時間就好。明天再看看身體想說什麼。',
    '能夠在不舒服的時刻還寫下感受，是很勇敢的事。負面情緒不需要被消滅，被看見就會慢慢退潮。',
    '當什麼都做不順的時候，先停下來呼吸幾次。你已經做得夠多了，今晚允許自己休息。',
    '長時間累積的疲倦不是一天能解決的。給自己一些時間，慢慢來，沒有人在等你。',
]

# Per-user profile types — affects cadence + average mood
PROFILE_TYPES = [
    # (name, weight, notes_per_day, mood_baseline_range, dropoff_after_days)
    ('power',   15, 1.5,  (0.1, 0.5),  None),
    ('regular', 35, 0.5,  (-0.1, 0.4), None),
    ('casual',  35, 0.2,  (-0.2, 0.3), None),
    ('dropoff', 15, 0.4,  (-0.3, 0.1), 14),   # writes for 14d then stops
]

WEEKDAY_PREFIXES = ['今天', '今晚', '早上', '中午過後', '下班後', '剛剛', '吃完晚餐後']


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def pick_sentiment(band: str, profile_baseline: float, rng: random.Random) -> float:
    """Sentiment in (-1, 1) drawn from the band, shifted by the user's baseline."""
    if band == 'pos':
        v = rng.uniform(0.3, 0.95)
    elif band == 'neg':
        v = rng.uniform(-0.85, -0.15)
    else:
        v = rng.uniform(-0.15, 0.25)
    # Shift by user's mood baseline but clamp inside [-1, 1]
    return max(-1.0, min(1.0, v + profile_baseline * 0.5))


def pick_stress(band: str, rng: random.Random) -> int:
    if band == 'high':
        return rng.randint(6, 9)
    if band == 'low':
        return rng.randint(0, 3)
    return rng.randint(3, 6)


def pick_ai_feedback(sentiment: float, rng: random.Random) -> str:
    if sentiment >= 0.2:
        return rng.choice(AI_FEEDBACK_POS)
    if sentiment <= -0.2:
        return rng.choice(AI_FEEDBACK_NEG)
    return rng.choice(AI_FEEDBACK_NEU)


def pick_weather(rng: random.Random, month: int) -> tuple[str, int]:
    """Weather + temperature, biased by month (TW climate)."""
    if month in (6, 7, 8):              # summer
        weather = rng.choice(['sunny'] * 35 + ['cloudy'] * 25 + ['rainy'] * 25 + ['stormy'] * 15)
        temp = rng.randint(26, 34)
    elif month in (12, 1, 2):           # winter
        weather = rng.choice(['cloudy'] * 35 + ['sunny'] * 25 + ['rainy'] * 25 + ['foggy'] * 15)
        temp = rng.randint(12, 20)
    else:                                # spring/autumn
        weather = rng.choice(WEATHER_DIST)
        temp = rng.randint(18, 27)
    return weather, temp


def generate_username(used: set, rng: random.Random) -> tuple[str, str]:
    """Return (chinese_name, username). Username = pinyin + 2-digit suffix."""
    for _ in range(20):
        sur_zh, sur_py = rng.choice(SURNAMES)
        given_zh, given_py = rng.choice(GIVEN_NAMES)
        suffix = rng.randint(1, 99)
        username = f'{sur_py}_{given_py}{suffix}'.lower()
        if username not in used and len(username) <= 30:
            used.add(username)
            return f'{sur_zh}{given_zh}', username
    # Fall back to numeric uniqueness — extremely rare
    n = rng.randint(1000, 9999)
    fallback = f'user_{n}'
    while fallback in used:
        n += 1
        fallback = f'user_{n}'
    used.add(fallback)
    return fallback, fallback


def stagger_signup_dates(count: int, rng: random.Random, now: datetime) -> list[datetime]:
    """Growth-curve weighted signup dates from PROJECT_LAUNCH to now.

    All returned datetimes are timezone-aware (Asia/Taipei) so they can be
    written directly to TIME_ZONE-aware DB columns without naive-datetime
    warnings.
    """
    span_days = (now.date() - PROJECT_LAUNCH.date()).days
    dates = []
    for _ in range(count):
        # Beta-like weighting: more recent users than early — alpha=2, beta=4 cumulative
        u = rng.random()
        # Bias toward later (1.0 = today)
        biased = u ** 0.5
        day_offset = int(biased * span_days)
        sign_date = PROJECT_LAUNCH + timedelta(days=day_offset)
        sign_date = sign_date.replace(
            hour=rng.randint(8, 22),
            minute=rng.randint(0, 59),
        )
        dates.append(timezone.make_aware(sign_date))
    dates.sort()
    return dates


def make_content(
    template: str,
    rng: random.Random,
    weather: str,
    month: int,
) -> str:
    """Add small prefix / weather mention variations to vary 5000 entries."""
    prefix = ''
    if rng.random() < 0.25:
        prefix = rng.choice(WEEKDAY_PREFIXES) + '，'
    # ~15% append a small weather aside
    weather_mention = ''
    if rng.random() < 0.12:
        if weather == 'sunny':
            weather_mention = '陽光剛好。'
        elif weather == 'rainy':
            weather_mention = '外面在下雨。'
        elif weather == 'stormy':
            weather_mention = '外面打雷打得厲害。'
        elif weather == 'cloudy':
            weather_mention = '天有點陰陰的。'
    # Compose
    body = template
    if prefix:
        # Replace leading "今天" / "今晚" / "早上" duplicates with prefix
        for kw in ('今天', '今晚', '早上'):
            if body.startswith(kw):
                body = body[len(kw):]
                if body.startswith('，'):
                    body = body[1:]
                break
        body = prefix + body
    if weather_mention:
        body = body + ' ' + weather_mention
    return body


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = 'Seed a realistic demo population of ~260 zh-TW users for defense'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=DEFAULT_COUNT)
        parser.add_argument('--reset', action='store_true',
                            help='Wipe all prior demo-seed users + their data first')
        parser.add_argument('--force', action='store_true',
                            help='Add another batch even if a prior one exists')
        parser.add_argument('--dry-run', action='store_true',
                            help='Print summary without writing anything')
        parser.add_argument('--seed', type=int, default=42,
                            help='RNG seed for reproducibility (default 42)')

    def handle(self, *args, **opts):
        count = opts['count']
        rng = random.Random(opts['seed'])
        now = timezone.now()
        batch_id = now.strftime('%Y%m%d')
        marker = f'{SEED_BIO_PREFIX}{batch_id}]'

        if opts['reset']:
            self._reset_all_seed_users()

        existing = User.objects.filter(bio__startswith=SEED_BIO_PREFIX).count()
        if existing > 0 and not opts['force'] and not opts['reset']:
            self.stdout.write(self.style.WARNING(
                f'Found {existing} existing seed users. Use --force to add a new batch '
                f'or --reset to wipe and re-seed.'
            ))
            return

        used_usernames = set(User.objects.values_list('username', flat=True))
        signup_dates = stagger_signup_dates(count, rng, now)

        plan = []
        for sign_dt in signup_dates:
            zh_name, username = generate_username(used_usernames, rng)
            profile_name, _, notes_per_day, baseline_range, dropoff = self._weighted_pick(
                PROFILE_TYPES, rng,
            )
            baseline = rng.uniform(*baseline_range)
            account_age_days = (now.date() - sign_dt.date()).days
            active_days = min(account_age_days, dropoff) if dropoff else account_age_days
            est_notes = max(1, int(active_days * notes_per_day * rng.uniform(0.6, 1.2)))
            est_notes = min(est_notes, 80)   # cap so dropoff/casual don't explode
            plan.append({
                'zh_name': zh_name, 'username': username, 'sign_dt': sign_dt,
                'profile': profile_name, 'baseline': baseline,
                'active_days': active_days, 'est_notes': est_notes,
            })

        total_notes = sum(p['est_notes'] for p in plan)
        self.stdout.write(self.style.SUCCESS(
            f'Plan: {count} users, ~{total_notes} notes, batch={batch_id}, '
            f'profiles: '
            f'{sum(1 for p in plan if p["profile"] == "power")}P/'
            f'{sum(1 for p in plan if p["profile"] == "regular")}R/'
            f'{sum(1 for p in plan if p["profile"] == "casual")}C/'
            f'{sum(1 for p in plan if p["profile"] == "dropoff")}D'
        ))

        if opts['dry_run']:
            self.stdout.write('Dry run — exiting without writes.')
            return

        users_done = 0
        notes_done = 0
        for p in plan:
            try:
                with transaction.atomic():
                    n_notes = self._create_user_with_notes(p, marker, rng, now)
                users_done += 1
                notes_done += n_notes
                if users_done % 20 == 0:
                    self.stdout.write(
                        f'  ...{users_done}/{count} users, {notes_done} notes'
                    )
            except Exception as e:                                        # noqa: BLE001
                self.stdout.write(self.style.ERROR(
                    f'  ! {p["username"]} failed: {e}'
                ))

        self.stdout.write(self.style.SUCCESS(
            f'Done. {users_done} users, {notes_done} notes. '
            f'Cleanup: python manage.py seed_demo_population --reset'
        ))

    # ------------------------------------------------------------------
    # User + notes
    # ------------------------------------------------------------------

    def _create_user_with_notes(self, plan, marker, rng, now):
        username = plan['username']
        email = f'{username}{SEED_EMAIL_DOMAIN}'
        sign_dt = plan['sign_dt']
        baseline = plan['baseline']

        user = User(
            username=username, email=email,
            bio=f'{marker} {plan["zh_name"]}',
            email_verified=True, onboarding_completed=True,
            timezone='Asia/Taipei', age_band='18_plus',
            age_confirmed_13_plus=True,
            terms_accepted_at=sign_dt,
        )
        user.set_password(DEFAULT_PASSWORD)
        user.save()
        # Backdate created_at
        User.objects.filter(pk=user.pk).update(
            created_at=sign_dt, updated_at=sign_dt,
        )

        # Tag palette for this user (4-7 tags)
        n_tags = rng.randint(4, 7)
        chosen_tags = rng.sample(TAG_PALETTE, n_tags)
        tag_objs = {}
        for name, color in chosen_tags:
            tag = Tag.objects.create(user=user, name=name, color=color)
            tag_objs[name] = tag

        # Activity palette for this user (3-6 activities)
        n_acts = rng.randint(3, 6)
        user_activities = rng.sample(ACTIVITIES, n_acts)

        # Generate notes across active period
        n_notes_target = plan['est_notes']
        active_days = max(1, plan['active_days'])
        # Notes get distributed across days; some days double-up, some skip
        chosen_days = sorted(rng.sample(
            range(active_days), min(n_notes_target, active_days),
        )) if n_notes_target <= active_days else (
            sorted(rng.choices(range(active_days), k=n_notes_target))
        )

        notes_created = 0
        for day_offset in chosen_days:
            entry_date = sign_dt.date() + timedelta(days=day_offset)
            if entry_date > now.date():
                continue   # don't write future-dated notes
            template_band, stress_band, content, hinted_tags = rng.choice(CONTENT_POOL)
            sentiment = pick_sentiment(template_band, baseline, rng)
            stress = pick_stress(stress_band, rng)
            weather, temp = pick_weather(rng, entry_date.month)
            # Apply weather effect on sentiment (slight; weather → mood
            # correlation surfaces in analytics)
            if weather == 'sunny':
                sentiment = min(1.0, sentiment + 0.05)
            elif weather == 'rainy':
                sentiment = max(-1.0, sentiment - 0.04)

            # Activities for this note: subset of user's palette
            note_activities = rng.sample(
                user_activities,
                rng.randint(0, min(3, len(user_activities))),
            )
            content_final = make_content(content, rng, weather, entry_date.month)

            note = MoodNote(
                user=user,
                sentiment_score=round(sentiment, 3),
                stress_index=stress,
                ai_feedback=pick_ai_feedback(sentiment, rng),
                metadata={
                    'weather': weather,
                    'temperature': temp,
                    'activities': note_activities,
                },
            )
            note.set_content(content_final)
            note.save()

            # Attach 0-2 tags
            relevant_tags = [tag_objs[t] for t in hinted_tags if t in tag_objs]
            if relevant_tags and rng.random() < 0.7:
                note.tags.add(rng.choice(relevant_tags))
            if tag_objs and rng.random() < 0.3:
                note.tags.add(rng.choice(list(tag_objs.values())))

            # Backdate to a realistic evening time
            entry_dt = timezone.make_aware(datetime.combine(
                entry_date, time(hour=rng.randint(8, 23), minute=rng.randint(0, 59)),
            ))
            MoodNote.objects.filter(pk=note.pk).update(
                created_at=entry_dt, updated_at=entry_dt,
            )
            notes_created += 1

        # Journal streak from latest activity
        if notes_created > 0:
            latest = MoodNote.objects.filter(user=user, is_deleted=False).order_by('-created_at').first()
            JournalStreak.objects.update_or_create(
                user=user,
                defaults={
                    'current_streak': 1 if latest else 0,
                    'longest_streak': max(1, notes_created // 7),
                    'last_entry_date': latest.created_at.date() if latest else None,
                    'total_entries': notes_created,
                },
            )

        return notes_created

    # ------------------------------------------------------------------

    def _reset_all_seed_users(self):
        qs = User.objects.filter(bio__startswith=SEED_BIO_PREFIX)
        count = qs.count()
        if count == 0:
            self.stdout.write('  reset: no prior seed users found.')
            return
        # Cascade through MoodNote / Tag / JournalStreak via FK on_delete=CASCADE
        deleted = qs.delete()
        self.stdout.write(self.style.WARNING(
            f'  reset: removed {count} seed users (cascade: {deleted})'
        ))

    @staticmethod
    def _weighted_pick(items_with_weight, rng):
        weights = [item[1] for item in items_with_weight]
        return rng.choices(items_with_weight, weights=weights, k=1)[0]
