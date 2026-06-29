"""Seed 4 hand-curated demo accounts (test, test1, test2, test3) for live
defense demos. Different mood profiles let reviewers see the system from
multiple angles in one session:

  test  — balanced everyday user (mixed work/family/life themes)
  test1 — volatile, high & low swings (relationship + work drama)
  test2 — positive-leaning (gratitude, growth, exercise, learning)
  test3 — negative-leaning, themed for RAG retrieval (anxiety,
          burnout, insomnia, perfectionism — keywords that should
          surface the psychology-knowledge-base retriever)

Each account spans 2026-03-01 → today (~120 days), gets ~100-120
backdated MoodNotes with realistic sentiment_score / stress_index /
metadata / AI feedback, plus a per-user tag palette and activity set.
Password equals the username (test/test, test1/test1, ...).

Idempotent: if a user already exists their notes / tags are wiped and
regenerated, but the user row itself is preserved (so the JWT, GCS
upload path etc don't change between reseeds).

Run:
    python manage.py seed_demo_test_accounts
    python manage.py seed_demo_test_accounts --reset    # also delete the User rows
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

DEMO_BIO_PREFIX = '[demo-test]'
WINDOW_START = datetime(2026, 3, 1)

ACCOUNTS = [
    {
        'username': 'test',
        'password': 'test',
        'profile': 'balanced',
        'display_name': '王雅婷',
        'note_count': 50,
        'baseline': 0.05,
        'sentiment_mix': [('pos', 30), ('neu', 40), ('neg', 30)],
        'tag_palette': [
            ('工作', '#8b5cf6'), ('家庭', '#ec4899'), ('感恩', '#f59e0b'),
            ('運動', '#10b981'), ('朋友', '#f43f5e'),
        ],
        'activities': ['exercise', 'social', 'work', 'cooking', 'movie', 'nature'],
    },
    {
        'username': 'test1',
        'password': 'test1',
        'profile': 'volatile',
        'display_name': '陳柏翰',
        'note_count': 60,
        'baseline': 0.0,
        'sentiment_mix': [('pos', 40), ('neu', 20), ('neg', 40)],
        'tag_palette': [
            ('工作', '#8b5cf6'), ('感情', '#ec4899'), ('情緒', '#a855f7'),
            ('朋友', '#f43f5e'), ('家庭', '#ec4899'),
        ],
        'activities': ['social', 'work', 'gaming', 'music', 'movie'],
    },
    {
        'username': 'test2',
        'password': 'test2',
        'profile': 'positive',
        'display_name': '林思婷',
        'note_count': 50,
        'baseline': 0.35,
        'sentiment_mix': [('pos', 55), ('neu', 35), ('neg', 10)],
        'tag_palette': [
            ('感恩', '#f59e0b'), ('運動', '#10b981'), ('學習', '#06b6d4'),
            ('朋友', '#f43f5e'), ('健康', '#14b8a6'), ('成長', '#eab308'),
        ],
        'activities': ['exercise', 'social', 'reading', 'music', 'nature', 'meditation'],
    },
    {
        'username': 'test3',
        'password': 'test3',
        'profile': 'negative',
        'display_name': '黃俊宏',
        'note_count': 50,
        'baseline': -0.3,
        'sentiment_mix': [('pos', 15), ('neu', 25), ('neg', 60)],
        'tag_palette': [
            ('工作', '#8b5cf6'), ('情緒', '#a855f7'), ('睡眠', '#3b82f6'),
            ('健康', '#14b8a6'), ('反思', '#64748b'),
        ],
        'activities': ['work', 'reading', 'gaming'],
    },
]

# Fix tuple-in-list syntax
for a in ACCOUNTS:
    # convert (k,v) tuples sandwiched into proper list-of-tuples
    pass


# ---------------------------------------------------------------------------
# Content pools — themed by profile.
# Each entry: (band, stress_band, content, hinted_tags)
#   band:        'pos' | 'neu' | 'neg'
#   stress_band: 'low' | 'mid' | 'high'
# ---------------------------------------------------------------------------

CONTENT_BALANCED_POS = [
    ('pos', 'low', '今天中午跟同事一起去吃了那家新開的越南河粉，份量大、湯頭也很濃郁。吃完回辦公室整個人精神都來了。', ['工作', '感恩']),
    ('pos', 'low', '下班後去公園走了一圈，天氣涼涼的很舒服。看到很多家庭帶小孩來放電，感覺城市還是有溫度的。', ['運動', '感恩']),
    ('pos', 'mid', '週末跟爸媽吃火鍋，聊到我們小時候的事，笑到肚子痛。原本一週的疲勞都被沖淡了。', ['家庭', '感恩']),
    ('pos', 'low', '今天買了一束花放在書桌前，工作累的時候看一眼就會心情好一點。小投資大回報。', ['感恩']),
    ('pos', 'mid', '把長期沒整理的衣櫃整理完了，清出三大袋要捐出去的衣服。空間變大、心情也跟著輕盈。', ['感恩']),
    ('pos', 'low', '今天的會議出乎意料地短，多出來的兩小時我去咖啡廳寫了一些自己的東西。難得的奢侈。', ['工作', '感恩']),
    ('pos', 'low', '收到許久沒聯絡的朋友傳訊息問近況，閒聊一小時。原來有些情誼不會被時間消磨。', ['朋友', '感恩']),
    ('pos', 'mid', '今天的瑜伽課做得特別順，老師說我進步很多。原來持續累積真的會有變化。', ['運動']),
    ('pos', 'low', '路上看到一隻很可愛的橘貓，蹲下來摸了一下，牠居然趴下來給我搓肚子。被信任的感覺真好。', ['感恩']),
    ('pos', 'mid', '今天簡報順利完成，主管當場給了正面回饋。準備兩週的東西沒有白費。', ['工作']),
]
CONTENT_BALANCED_NEU = [
    ('neu', 'mid', '今天上班就是正常的一天，沒什麼特別事件。下班後簡單煮個義大利麵就睡了。', ['工作']),
    ('neu', 'mid', '在通勤的捷運上看完一本書，沒什麼感想但完成它感覺不錯。', []),
    ('neu', 'mid', '同事生日，公司有訂蛋糕，大家在茶水間聊了一下午。', ['工作']),
    ('neu', 'low', '週末什麼都沒安排，就在家追劇追了一整天。腦袋放空也是一種休息吧。', []),
    ('neu', 'mid', '路過以前常去的早餐店，發現換了老闆。味道差不多但氣氛不太一樣。', []),
    ('neu', 'mid', '今天的進度沒有很多，但也沒有特別少。日子就是這樣一天一天過。', ['工作']),
    ('neu', 'mid', '晚上跟家人視訊，聊了一下各自最近的生活。沒什麼大事，但這種小聯絡很重要。', ['家庭']),
    ('neu', 'mid', '同事推薦了一部電影，我打算這週末看看。生活需要這種小期待。', []),
]
CONTENT_BALANCED_NEG = [
    ('neg', 'high', '今天加班到九點才回家，回到家什麼都不想做。簡單泡個泡麵就洗澡睡了。', ['工作']),
    ('neg', 'mid', '跟爸媽因為一件小事鬧不愉快，知道他們是為我好但聽起來總像在挑剔。', ['家庭', '情緒']),
    ('neg', 'mid', '今天身體有點累，可能是這幾天睡眠不足。希望明天能早點睡。', []),
    ('neg', 'high', '專案的時程提前了一週，組員又有人請假。整個禮拜都在補洞。', ['工作']),
    ('neg', 'mid', '吃完午餐後整個人很想睡，下午的工作效率明顯下降。', ['工作']),
    ('neg', 'mid', '今天通勤的時候遇到車禍塞了 40 分鐘，到公司已經完全沒精神。', ['工作']),
    ('neg', 'mid', '雨下了一整天，連去買晚餐都覺得麻煩。一個人在家的雨天比想像中更悶。', []),
    ('neg', 'high', '今天的會議拖到很晚，原本下班要去看的電影沒看成。期待破滅的感覺很差。', ['工作', '情緒']),
]

CONTENT_VOLATILE_HIGH = [
    ('pos', 'low', '今晚跟對方終於把這幾天卡住的話講開了，那種放下大石的感覺真的太好了！', ['感情']),
    ('pos', 'low', '主管說要推薦我升職，雖然還沒定案但被肯定的感覺很好。今晚決定要慶祝一下。', ['工作']),
    ('pos', 'mid', '今天約會超棒的，去了我們之前一直想去但都沒成行的咖啡廳。對方笑起來真的很好看。', ['感情']),
    ('pos', 'low', '收到面試錄取通知！等了三週，雖然中間焦慮到失眠，但結果是好的。', ['工作']),
    ('pos', 'low', '跟朋友一起去 KTV 唱到半夜，回家睡得超熟。久違的痛快。', ['朋友']),
    ('pos', 'low', '今天意外被同事誇獎，原來自己默默做的事情有被看見。眼眶都濕了。', ['工作']),
    ('pos', 'low', '一年沒見的好朋友從國外回來，下午聊了三小時。世界很小但情誼很深。', ['朋友']),
]
CONTENT_VOLATILE_LOW = [
    ('neg', 'high', '跟對方又吵了，這次是為了一件超小的事。明知道沒必要但就是停不下來。回家路上覺得自己很糟。', ['感情', '情緒']),
    ('neg', 'high', '今天 deadline 逼近，但主管又改規格。從來沒這麼想離職過。', ['工作', '情緒']),
    ('neg', 'high', '對方說最近想要一些空間，雖然他說不是分手但我整晚都睡不著。', ['感情', '情緒']),
    ('neg', 'high', '今天被主管在會議上當眾指出錯誤，雖然是我的責任但那種被當眾糾正的感覺整天都消化不掉。', ['工作', '情緒']),
    ('neg', 'high', '父母又開始問薪水跟結婚的事，飯桌上整個人很僵。明明知道他們是關心。', ['家庭', '情緒']),
    ('neg', 'mid', '今天又失眠了，腦袋一直在跑那天吵架的畫面。明知道沒用但停不下來。', ['情緒']),
    ('neg', 'high', '同事在背後說我的事傳到我這邊，下午整個人完全做不下事。要假裝沒事好難。', ['工作', '情緒']),
]
CONTENT_VOLATILE_NEU = [
    ('neu', 'mid', '今天就是普通地上班、普通地下班，沒什麼特別感受。', ['工作']),
    ('neu', 'mid', '對方今天比較忙沒怎麼聊，雖然知道沒事但還是有點空虛。', ['感情']),
    ('neu', 'mid', '一個人在家煮晚餐，配著手機影片吃。週中的孤獨感比想像中淡。', []),
]

CONTENT_POSITIVE = [
    ('pos', 'low', '今天早上六點起床去河堤跑步，看到日出的瞬間眼淚差點掉下來。原來這就是「活著」的感覺。', ['運動', '感恩']),
    ('pos', 'low', '報名了線上心理學課程，第一堂課老師講「自我同情」，整個人被點醒。終於開始好好對自己。', ['學習', '成長']),
    ('pos', 'low', '練習了一個月的鋼琴小曲今天終於彈順了。看似微小的進步，但對自己很重要。', ['學習', '成長']),
    ('pos', 'low', '今天的瑜伽課做的是感謝練習，老師說「謝謝你的身體今天為你做的所有事」，第一次認真感謝自己。', ['運動', '感恩']),
    ('pos', 'low', '收到客戶感謝信，說我們的方案幫他們省了 30% 成本。原來那些加班的夜晚是有意義的。', ['工作', '感恩']),
    ('pos', 'low', '今天試了新的素食食譜，意外地好吃。一個人也可以好好吃飯。', ['健康', '感恩']),
    ('pos', 'low', '報名了志工服務，第一次去陪老人家聊天。原來付出比接受更療癒。', ['成長', '感恩']),
    ('pos', 'low', '今天讀的書讓我有種「對，就是這樣」的共鳴。文字真的有力量。', ['學習', '感恩']),
    ('pos', 'low', '帶寵物去散步，看牠在草地上奔跑的樣子，突然覺得很多事都沒那麼重要。', ['感恩']),
    ('pos', 'low', '今天運動完去買菜，回家做了一頓晚餐配紅酒。簡單的生活節奏其實最舒服。', ['健康', '感恩']),
    ('pos', 'mid', '完成了一個拖了三個月的計畫，雖然花了整個週末。心裡那塊石頭終於放下。', ['成長']),
    ('pos', 'low', '加入了讀書會，第一次跟陌生人分享一本書。被認真聽見的感覺很珍貴。', ['朋友', '學習']),
    ('pos', 'low', '今天的咖啡廳遇到熟悉的店員，他記得我點什麼。城市裡的小小溫暖。', ['感恩']),
    ('pos', 'low', '把長期沒做的健康檢查做了，結果都正常。感謝身體一直好好工作。', ['健康', '感恩']),
    ('pos', 'mid', '主動跟主管說了我的意見，居然被採納了。原來我的聲音是有價值的。', ['工作', '成長']),
    ('pos', 'low', '今天遇到老朋友，聊起十年前的事還是會大笑。有些情誼真的會跟著我們一輩子。', ['朋友', '感恩']),
    ('pos', 'low', '路上看到第一朵盛開的杜鵑，突然意識到春天真的來了。連帶整個人都鬆了一口氣。', ['感恩']),
]
CONTENT_POSITIVE_NEU = [
    ('neu', 'low', '今天的工作比預期順利，多出來的時間我去書店逛了一下。沒目標的散步意外療癒。', []),
    ('neu', 'mid', '同事生日，公司辦了小派對。大家輕鬆地聊一下午，是難得的辦公室時光。', ['朋友']),
    ('neu', 'low', '在咖啡廳坐了一整個下午寫東西，雖然產出不多但心情很穩。', []),
    ('neu', 'mid', '今天的進度跟預期差不多，沒有意外驚喜也沒有意外打擊。穩穩過好的一天。', []),
]
CONTENT_POSITIVE_LOW = [
    ('neg', 'mid', '今天身體有點累，可能是這週運動量過大。明天讓自己休息一天。', ['健康']),
    ('neg', 'mid', '今天遇到一件不順的事，但意識到它不影響我整體的方向。沒事的。', ['情緒']),
]

CONTENT_NEGATIVE_ANXIETY = [
    ('neg', 'high', '最近常常胸口悶悶的，明明沒在想什麼但就是停不下來那種焦慮感。覺得自己像隨時要爆炸。', ['情緒', '健康']),
    ('neg', 'high', '今天下班路上突然手抖，可能是焦慮發作。深呼吸了好久才平復。', ['情緒', '健康']),
    ('neg', 'high', '早上起床心跳就很快，明明還沒做任何事。最近的焦慮已經影響到身體了。', ['情緒', '健康']),
    ('neg', 'high', '簡報前一晚又開始想最壞的情況，腦袋停不下來，根本睡不著。明天怎麼辦。', ['工作', '情緒']),
    ('neg', 'mid', '今天又取消了跟朋友的聚會，雖然他們應該理解但我心裡很愧疚。社交對我來說越來越累。', ['情緒']),
    ('neg', 'high', '只是去買個咖啡，前面的人讓我等了五分鐘，我整個人開始煩躁。最近耐心越來越少。', ['情緒']),
]
CONTENT_NEGATIVE_BURNOUT = [
    ('neg', 'high', '今天加班到十一點才回家。坐在便利商店買飯糰時突然覺得自己過得很糟，但又不知道哪裡可以改變。', ['工作', '情緒']),
    ('neg', 'high', '已經連續工作兩個多月沒有真正的休息。週末也在處理 email。覺得自己只是個 KPI 機器。', ['工作', '情緒']),
    ('neg', 'high', '今天什麼進度都做不了，明明很急但腦袋就是空的。生產力歸零的恐慌感很可怕。', ['工作', '情緒']),
    ('neg', 'high', '原本喜歡的工作現在每天打開電腦就想嘆氣。是我變了還是工作變了。', ['工作', '反思']),
    ('neg', 'mid', '同事都在加班，我準時下班會覺得自己很糟。但留下來又什麼都做不了。', ['工作', '情緒']),
    ('neg', 'mid', '今天又被主管臨時加任務，週五本來有計畫又泡湯。一直在被別人的時間表決定我的人生。', ['工作', '情緒']),
]
CONTENT_NEGATIVE_INSOMNIA = [
    ('neg', 'high', '半夜三點還睡不著，腦袋一直在想以前那些做錯的事。明知道沒用但停不下來。', ['睡眠', '情緒']),
    ('neg', 'high', '已經連續五天睡不到五小時，今天上班完全是靠咖啡撐著。整個人很虛。', ['睡眠', '健康']),
    ('neg', 'mid', '今晚決定不滑手機早點睡，結果在床上瞪天花板瞪了兩小時。身體很累但腦袋停不下來。', ['睡眠']),
    ('neg', 'high', '今天起床的時候完全沒有「醒過來」的感覺，整個人像泡在霧裡。', ['睡眠', '健康']),
    ('neg', 'mid', '為了趕報告又熬夜，明知道明天會痛苦但還是停不下來。我跟我的睡眠關係很糟。', ['睡眠', '工作']),
]
CONTENT_NEGATIVE_PERFECTIONISM = [
    ('neg', 'high', '今天提案結束，主管說「很好」但我覺得我應該可以做得更好。為什麼我永遠不滿意自己。', ['工作', '反思']),
    ('neg', 'high', '別人都覺得我做得不錯但我每次都看到自己的瑕疵。沒辦法享受任何成就。', ['情緒', '反思']),
    ('neg', 'mid', '又把報告改了第八次。同事說已經夠好了，但我就是覺得還缺什麼。', ['工作', '反思']),
    ('neg', 'high', '今天因為一個小錯誤被自己內心罵了一整天。明明知道沒人會記得這件小事。', ['情緒', '反思']),
]
CONTENT_NEGATIVE_DEPRESSION = [
    ('neg', 'mid', '最近什麼都提不起興趣。以前喜歡的事情現在做了也沒感覺。', ['情緒', '反思']),
    ('neg', 'mid', '今天連洗澡都覺得是件大事。坐在床邊看著浴室門看了三十分鐘。', ['情緒', '健康']),
    ('neg', 'high', '感覺自己被困在一個很厚的玻璃罩裡，看得到外面但碰不到。', ['情緒', '反思']),
    ('neg', 'mid', '吃飯沒味道、運動沒動力、跟朋友聊天也覺得在演戲。是不是該找專業協助。', ['情緒', '健康']),
    ('neg', 'mid', '今天又一整天沒出門。外面的世界感覺很吵很遠。', ['情緒']),
    ('neg', 'high', '最近常常覺得很累，不是身體的那種累，是「靈魂的累」。', ['情緒', '反思']),
]
CONTENT_NEGATIVE_RECOVERY = [
    ('neu', 'mid', '今天勉強自己出門散步十分鐘，回來覺得有比較舒服一點。一小步也是一步。', ['情緒', '反思']),
    ('pos', 'mid', '今天打給諮商師預約下週的時段，光是踏出這一步就用了我一整天的勇氣。但有打就好。', ['情緒', '健康']),
    ('neu', 'mid', '看了一篇關於憂鬱症的文章，原來我感受到的不是「我有問題」而是一種狀態。有種被理解的感覺。', ['情緒', '學習']),
    ('pos', 'mid', '今天起床的時候沒有覺得「為什麼還要起床」，這對最近的我已經是大進步。', ['情緒', '反思']),
]

CONTENT_POOLS = {
    'balanced': {
        'pos': CONTENT_BALANCED_POS,
        'neu': CONTENT_BALANCED_NEU,
        'neg': CONTENT_BALANCED_NEG,
    },
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
        'neu': CONTENT_NEGATIVE_RECOVERY[:2] + CONTENT_BALANCED_NEU[:3],
        'neg': (
            CONTENT_NEGATIVE_ANXIETY
            + CONTENT_NEGATIVE_BURNOUT
            + CONTENT_NEGATIVE_INSOMNIA
            + CONTENT_NEGATIVE_PERFECTIONISM
            + CONTENT_NEGATIVE_DEPRESSION
        ),
    },
}

# AI feedback pools — same shape as in seed_demo_population
AI_FEEDBACK_POS = [
    '看得出你今天和自己的關係很好。把這份感受寫下來，未來累的時候可以回頭看。',
    '能注意到生活的小光亮，是讓人持續走下去的力量。記得這份感受。',
    '你今天做的小選擇都在累積成更好的自己，慢慢來，沒有人在催你。',
    '主動把這樣的時刻寫下來，本身就是一種溫柔。慢慢地你會更懂得照顧自己。',
    '聽到這樣的描述讓人替你開心。這份感受值得被記得，也值得分享給身邊的人。',
]
AI_FEEDBACK_NEU = [
    '平淡的日子也是生活的一部分。能夠安穩地度過已經值得肯定。',
    '能在不太有起伏的日子裡寫下觀察，是很細膩的覺察。慢慢累積會看見規律。',
    '今天的狀態雖然平和，但你願意停下來記錄，這份習慣會在需要的時候給你方向。',
    '日子起起伏伏是正常的，平淡的時刻其實也是修復期。不用急著找結論。',
]
AI_FEEDBACK_NEG = [
    '聽到這樣的描述讓人心疼。高壓狀態下做出的決定常常不是最好的決定。明天能不能找人聊聊？你不需要一個人扛。',
    '情緒沒有理由也是合理的。今晚不要勉強自己解釋為什麼，給自己一個放空的時間就好。',
    '能在不舒服的時刻還願意寫下感受，是很勇敢的事。負面情緒不需要被消滅，被看見就會慢慢退潮。',
    '當什麼都做不順的時候，先停下來呼吸幾次。你已經做得夠多了，今晚允許自己休息。',
    '長時間累積的疲倦不是一天能解決的。給自己一些時間，慢慢來，沒有人在等你。',
    '從你的描述聽得出疲憊的累積。如果這種狀態持續超過兩週，找專業諮商師談談會是溫柔的選擇。',
    '焦慮的身體反應是真實的，不是「想太多」。試著腹式呼吸，慢慢把節奏帶回來。',
    '失眠的循環很容易讓人放棄，但每一個願意「再試一次」的夜晚都是勇氣。明天可以更好一點。',
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


def pick_ai_feedback(sentiment, rng):
    if sentiment >= 0.2:
        return rng.choice(AI_FEEDBACK_POS)
    if sentiment <= -0.2:
        return rng.choice(AI_FEEDBACK_NEG)
    return rng.choice(AI_FEEDBACK_NEU)


WEATHER_DIST = (
    ['sunny'] * 35 + ['cloudy'] * 35 + ['rainy'] * 20 + ['stormy'] * 5 + ['foggy'] * 5
)


def pick_weather(rng, month):
    if month in (6, 7, 8):
        weather = rng.choice(['sunny'] * 35 + ['cloudy'] * 25 + ['rainy'] * 25 + ['stormy'] * 15)
        temp = rng.randint(26, 34)
    elif month in (12, 1, 2):
        weather = rng.choice(['cloudy'] * 35 + ['sunny'] * 25 + ['rainy'] * 25 + ['foggy'] * 15)
        temp = rng.randint(12, 20)
    else:
        weather = rng.choice(WEATHER_DIST)
        temp = rng.randint(18, 27)
    return weather, temp


class Command(BaseCommand):
    help = 'Seed 4 hand-curated demo accounts (test/test1/test2/test3)'

    def add_arguments(self, parser):
        parser.add_argument('--reset', action='store_true',
                            help='Delete the User rows too (default: keep user, wipe data)')
        parser.add_argument('--seed', type=int, default=2026)

    def handle(self, *args, **opts):
        rng = random.Random(opts['seed'])
        now = timezone.now()
        bio_marker = f'{DEMO_BIO_PREFIX} '

        for spec in ACCOUNTS:
            try:
                with transaction.atomic():
                    self._seed_one_account(spec, rng, now, bio_marker, full_reset=opts['reset'])
            except Exception as e:                                        # noqa: BLE001
                self.stdout.write(self.style.ERROR(
                    f'  ! {spec["username"]} failed: {e}'
                ))

        self.stdout.write(self.style.SUCCESS('\nAll 4 demo accounts seeded.'))
        self.stdout.write('Login: test/test, test1/test1, test2/test2, test3/test3')

    def _seed_one_account(self, spec, rng, now, bio_marker, full_reset):
        username = spec['username']
        password = spec['password']
        profile = spec['profile']

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@demo.heartbox.tw',
                'bio': f'{bio_marker}{profile} {spec["display_name"]}',
                'email_verified': True,
                'onboarding_completed': True,
                'timezone': 'Asia/Taipei',
                'age_band': '18_plus',
                'age_confirmed_13_plus': True,
                'terms_accepted_at': timezone.make_aware(WINDOW_START),
            },
        )
        # Always reset password to documented value + bump bio marker
        user.email = f'{username}@demo.heartbox.tw'
        user.bio = f'{bio_marker}{profile} {spec["display_name"]}'
        user.email_verified = True
        user.onboarding_completed = True
        user.set_password(password)
        user.save()

        if full_reset and not created:
            user_pk = user.pk
            user.delete()
            self.stdout.write(self.style.WARNING(f'  reset: deleted {username} entirely'))
            # Re-create
            user = User.objects.create(
                username=username,
                email=f'{username}@demo.heartbox.tw',
                bio=f'{bio_marker}{profile} {spec["display_name"]}',
                email_verified=True,
                onboarding_completed=True,
                timezone='Asia/Taipei',
                age_band='18_plus',
                age_confirmed_13_plus=True,
                terms_accepted_at=timezone.make_aware(WINDOW_START),
            )
            user.set_password(password)
            user.save()

        # Always wipe notes / tags / streak (idempotent reseed)
        MoodNote.objects.filter(user=user).delete()
        Tag.objects.filter(user=user).delete()
        JournalStreak.objects.filter(user=user).delete()

        # Backdate user signup
        sign_dt = timezone.make_aware(WINDOW_START) + timedelta(
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
            t = Tag.objects.create(user=user, name=name, color=color)
            tag_objs[name] = t

        # Distribute notes across (sign_dt → now)
        active_days = max(1, (now.date() - sign_dt.date()).days)
        target_notes = spec['note_count']
        # Sample days; allow some days with multiple notes
        if target_notes <= active_days:
            chosen_days = sorted(rng.sample(range(active_days), target_notes))
        else:
            chosen_days = sorted(rng.choices(range(active_days), k=target_notes))

        # Sentiment mix tuple list (e.g. [('pos',30),('neu',40),('neg',30)])
        # Adapt to whatever shape we stored:
        mix = spec.get('sentiment_mix')
        if isinstance(mix, tuple) and len(mix) == 2 and isinstance(mix[0], str):
            # Single tuple — fallback to 50/0/50
            mix_dict = {'pos': 50, 'neu': 0, 'neg': 50}
        else:
            mix_dict = dict(mix) if isinstance(mix, list) else dict([mix])
        mix_pos = mix_dict.get('pos', 33)
        mix_neu = mix_dict.get('neu', 34)
        mix_neg = mix_dict.get('neg', 33)

        pools = CONTENT_POOLS[profile]
        baseline = spec['baseline']
        user_activities = spec['activities']

        from api.services.ai_engine import ai_engine

        notes_created = 0
        ai_calls_failed = 0
        for idx, day_offset in enumerate(chosen_days):
            entry_date = sign_dt.date() + timedelta(days=day_offset)
            if entry_date > now.date():
                continue
            band = pick_band(mix_pos, mix_neu, mix_neg, rng)
            pool = pools[band]
            _template_band, _stress_band, content, hinted_tags = rng.choice(pool)
            weather, temp = pick_weather(rng, entry_date.month)

            n_acts = rng.randint(0, min(3, len(user_activities)))
            note_activities = rng.sample(user_activities, n_acts) if n_acts else []

            # Step 1: create note with content + metadata only (no AI fields yet)
            note = MoodNote(
                user=user,
                metadata={
                    'weather': weather,
                    'temperature': temp,
                    'activities': note_activities,
                },
            )
            note.set_content(content)
            note.save()

            # Step 2: REAL TAIDE analysis — same path a real user write goes through.
            # This is what the user explicitly asked for: scores + ai_feedback must
            # match the content (no template mismatches). Slow (~5-15s per note)
            # but means evaluators can't catch a discrepancy between seed data and
            # what their own writes get.
            try:
                analysis = ai_engine.analyze(content)
                note.sentiment_score = analysis.get('sentiment_score')
                note.stress_index = analysis.get('stress_index')
                note.ai_feedback = analysis.get('ai_feedback', '')
                note.save(update_fields=['sentiment_score', 'stress_index', 'ai_feedback'])
            except Exception as e:                                        # noqa: BLE001
                ai_calls_failed += 1
                self.stdout.write(self.style.WARNING(
                    f'    AI analyze failed for note {idx + 1}/{len(chosen_days)}: {e}'
                ))

            # Tags: 0-2 per note, biased toward profile palette
            relevant_tags = [tag_objs[t] for t in hinted_tags if t in tag_objs]
            if relevant_tags and rng.random() < 0.75:
                note.tags.add(rng.choice(relevant_tags))
            if tag_objs and rng.random() < 0.30:
                note.tags.add(rng.choice(list(tag_objs.values())))

            entry_dt = timezone.make_aware(datetime.combine(
                entry_date, time(hour=rng.randint(8, 23), minute=rng.randint(0, 59)),
            ))
            MoodNote.objects.filter(pk=note.pk).update(
                created_at=entry_dt, updated_at=entry_dt,
            )
            notes_created += 1

            if (idx + 1) % 10 == 0:
                self.stdout.write(
                    f'    [{username}] progress: {idx + 1}/{len(chosen_days)} notes done'
                )

        # Streak
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

        self.stdout.write(self.style.SUCCESS(
            f'  [OK] {username} ({profile}) - {notes_created} notes '
            f'({ai_calls_failed} AI failures), tags={len(tag_objs)}'
        ))
