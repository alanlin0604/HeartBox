# Data migration: update existing article sources to clinical guidelines
# and add 8 new articles based on WHO, APA, NICE, NIMH, NHS sources.

from django.db import migrations

# Update existing article sources to reference clinical guidelines
UPDATED_SOURCES = {
    'Introduction to Cognitive Distortions': (
        'Burns, D. D. (1980). Feeling Good: The New Mood Therapy. '
        'American Psychological Association (APA). '
        'https://www.apa.org/ptsd-guideline/patients-and-families/cognitive-behavioral'
    ),
    'How to Reframe Negative Thoughts': (
        'Beck, J. S. (2011). Cognitive Behavior Therapy: Basics and Beyond. '
        'National Institute for Health and Care Excellence (NICE) CG90. '
        'https://www.nice.org.uk/guidance/cg90'
    ),
    '4-7-8 Breathing Technique': (
        'Weil, A. (2015). Breathing: The Master Key to Self Healing. '
        'Harvard Health Publishing. '
        'https://www.health.harvard.edu/mind-and-mood/relaxation-techniques-breath-control-helps-quell-errant-stress-response'
    ),
    'Emotion Identification and Acceptance': (
        'Gross, J. J. (2014). Handbook of Emotion Regulation. '
        'National Institute of Mental Health (NIMH). '
        'https://www.nimh.nih.gov/health/topics/caring-for-your-mental-health'
    ),
    'Introduction to Mindfulness Meditation': (
        'Kabat-Zinn, J. (1990). Full Catastrophe Living. '
        'National Institute for Health and Care Excellence (NICE) NG225. '
        'https://www.nice.org.uk/guidance/ng225'
    ),
    'Stress Management Strategies': (
        'Lazarus, R. S., & Folkman, S. (1984). Stress, Appraisal, and Coping. '
        'World Health Organization (WHO). '
        'https://www.who.int/news-room/questions-and-answers/item/stress'
    ),
}

# 8 new articles based on authoritative international sources
NEW_ARTICLES = [
    {
        'title_zh': '漸進式肌肉放鬆法',
        'title_en': 'Progressive Muscle Relaxation',
        'title_ja': '漸進的筋弛緩法',
        'content_zh': (
            '漸進式肌肉放鬆法（PMR）是由 Edmund Jacobson 博士於 1930 年代開發的技巧，被美國心理學會（APA）推薦用於管理焦慮和壓力。\n\n'
            '## 原理\n\n'
            '當我們感到焦慮時，肌肉會不自覺地緊繃。PMR 透過有意識地繃緊再放鬆各肌肉群，幫助大腦學會辨識並釋放身體緊張。\n\n'
            '## 練習步驟（約 15 分鐘）\n\n'
            '找一個安靜的地方坐下或躺下，閉上眼睛。\n\n'
            '**1. 雙手**\n緊握拳頭 5 秒 → 放鬆 15 秒，感受鬆弛感。\n\n'
            '**2. 前臂**\n彎曲手腕向上 5 秒 → 放鬆 15 秒。\n\n'
            '**3. 上臂**\n彎曲手臂繃緊二頭肌 5 秒 → 放鬆 15 秒。\n\n'
            '**4. 肩膀**\n聳肩靠近耳朵 5 秒 → 放鬆 15 秒。\n\n'
            '**5. 臉部**\n皺眉、緊閉眼睛、咬緊牙齒 5 秒 → 放鬆 15 秒。\n\n'
            '**6. 腹部**\n繃緊腹肌 5 秒 → 放鬆 15 秒。\n\n'
            '**7. 大腿**\n繃緊大腿肌肉 5 秒 → 放鬆 15 秒。\n\n'
            '**8. 小腿和腳**\n腳趾向上勾 5 秒 → 放鬆 15 秒。\n\n'
            '## 注意事項\n\n'
            '- 繃緊時不要過度用力\n'
            '- 專注在緊繃和放鬆之間的對比感\n'
            '- 如有肌肉損傷，跳過該部位\n'
            '- 建議每天練習一次，持續兩週即可感受到效果'
        ),
        'content_en': (
            'Progressive Muscle Relaxation (PMR) was developed by Dr. Edmund Jacobson in the 1930s and is recommended by the American Psychological Association (APA) for managing anxiety and stress.\n\n'
            '## How It Works\n\n'
            'When we feel anxious, our muscles tense involuntarily. PMR helps the brain learn to recognize and release physical tension by deliberately tensing and then relaxing each muscle group.\n\n'
            '## Practice Steps (about 15 minutes)\n\n'
            'Find a quiet place to sit or lie down. Close your eyes.\n\n'
            '**1. Hands**\nClench your fists for 5 seconds → Relax for 15 seconds, notice the release.\n\n'
            '**2. Forearms**\nBend wrists upward for 5 seconds → Relax for 15 seconds.\n\n'
            '**3. Upper arms**\nFlex biceps for 5 seconds → Relax for 15 seconds.\n\n'
            '**4. Shoulders**\nShrug shoulders toward ears for 5 seconds → Relax for 15 seconds.\n\n'
            '**5. Face**\nFurrow brow, squeeze eyes shut, clench jaw for 5 seconds → Relax for 15 seconds.\n\n'
            '**6. Abdomen**\nTighten stomach muscles for 5 seconds → Relax for 15 seconds.\n\n'
            '**7. Thighs**\nTense thigh muscles for 5 seconds → Relax for 15 seconds.\n\n'
            '**8. Calves and feet**\nPull toes upward for 5 seconds → Relax for 15 seconds.\n\n'
            '## Important Notes\n\n'
            '- Do not tense too hard\n'
            '- Focus on the contrast between tension and relaxation\n'
            '- Skip any area with muscle injury\n'
            '- Practice daily for two weeks to notice improvement'
        ),
        'content_ja': (
            '漸進的筋弛緩法（PMR）は1930年代にエドマンド・ジェイコブソン博士が開発した技法で、アメリカ心理学会（APA）が不安やストレスの管理に推奨しています。\n\n'
            '## 原理\n\n'
            '不安を感じると筋肉は無意識に緊張します。PMRは意図的に各筋肉群を緊張させてから弛緩させることで、身体の緊張を認識し解放することを脳に教えます。\n\n'
            '## 練習ステップ（約15分）\n\n'
            '静かな場所で座るか横になり、目を閉じます。\n\n'
            '**1. 手**\n拳を5秒間握る → 15秒間弛緩し、解放を感じる。\n\n'
            '**2. 前腕**\n手首を上に曲げて5秒間 → 15秒間弛緩。\n\n'
            '**3. 上腕**\n上腕二頭筋を5秒間曲げる → 15秒間弛緩。\n\n'
            '**4. 肩**\n肩を耳に向けて5秒間すくめる → 15秒間弛緩。\n\n'
            '**5. 顔**\n眉をひそめ、目をきつく閉じ、歯を食いしばって5秒間 → 15秒間弛緩。\n\n'
            '**6. 腹部**\n腹筋を5秒間締める → 15秒間弛緩。\n\n'
            '**7. 太もも**\n太ももの筋肉を5秒間緊張 → 15秒間弛緩。\n\n'
            '**8. ふくらはぎと足**\nつま先を上に引いて5秒間 → 15秒間弛緩。\n\n'
            '## 注意点\n\n'
            '- 強く緊張させすぎない\n'
            '- 緊張と弛緩のコントラストに集中する\n'
            '- 筋肉に怪我がある部位はスキップする\n'
            '- 2週間毎日練習すると効果を実感できます'
        ),
        'category': 'stress',
        'reading_time': 5,
        'order': 9,
        'source': (
            'American Psychological Association (APA). Relaxation Techniques. '
            'https://www.apa.org/topics/stress/relaxation-techniques'
        ),
    },
    {
        'title_zh': '行為活化：用行動改善情緒',
        'title_en': 'Behavioral Activation for Depression',
        'title_ja': '行動活性化：行動で気分を改善する',
        'content_zh': (
            '行為活化（BA）是一種基於實證的心理治療技巧，由英國國家健康與照護卓越研究院（NICE）推薦為憂鬱症的一線治療方法。\n\n'
            '## 核心原理\n\n'
            '憂鬱時我們傾向減少活動 → 缺乏正向體驗 → 情緒更低落 → 更不想活動。行為活化打破這個惡性循環，透過增加有意義的活動來改善情緒。\n\n'
            '## 實踐步驟\n\n'
            '**1. 活動監控**\n記錄一週內的活動和對應心情（0-10 分），找出哪些活動讓你感覺好。\n\n'
            '**2. 活動排程**\n每天安排至少一個讓你有成就感或愉悅感的活動，從小事開始。\n\n'
            '**3. 分級任務**\n把大任務拆成小步驟，降低開始的門檻。例如「整理房間」→「先整理桌面」。\n\n'
            '**4. 價值導向**\n選擇與個人價值觀一致的活動（如家庭、健康、創造力）。\n\n'
            '## 適合的活動範例\n\n'
            '- 散步 15 分鐘\n'
            '- 打電話給朋友\n'
            '- 烹飪一道簡單的菜\n'
            '- 聽喜歡的音樂\n'
            '- 整理一個小空間\n\n'
            '## 重要提醒\n\n'
            '不需要等到「有動力」才行動——先行動，動力會跟著來。'
        ),
        'content_en': (
            'Behavioral Activation (BA) is an evidence-based psychotherapy technique recommended by the National Institute for Health and Care Excellence (NICE) as a first-line treatment for depression.\n\n'
            '## Core Principle\n\n'
            'When depressed, we tend to reduce activity → fewer positive experiences → lower mood → even less activity. BA breaks this vicious cycle by increasing meaningful activities to improve mood.\n\n'
            '## Practice Steps\n\n'
            '**1. Activity Monitoring**\nTrack your activities and corresponding mood (0-10) for a week to identify which activities make you feel better.\n\n'
            '**2. Activity Scheduling**\nSchedule at least one activity each day that gives you a sense of achievement or pleasure, starting small.\n\n'
            '**3. Graded Tasks**\nBreak large tasks into smaller steps to lower the barrier. e.g., "Clean the room" → "Start with the desk."\n\n'
            '**4. Values-Based**\nChoose activities aligned with your personal values (family, health, creativity).\n\n'
            '## Activity Examples\n\n'
            '- Walk for 15 minutes\n'
            '- Call a friend\n'
            '- Cook a simple meal\n'
            '- Listen to music you enjoy\n'
            '- Tidy up a small space\n\n'
            '## Key Reminder\n\n'
            'You don\'t need to wait for motivation to act — action comes first, motivation follows.'
        ),
        'content_ja': (
            '行動活性化（BA）はエビデンスに基づく心理療法技法で、英国国立医療技術評価機構（NICE）がうつ病の第一選択治療として推奨しています。\n\n'
            '## 核心原理\n\n'
            'うつ状態では活動を減らしがち → ポジティブな体験が減る → 気分がさらに低下 → さらに活動しなくなる。BAはこの悪循環を断ち切り、意味のある活動を増やして気分を改善します。\n\n'
            '## 実践ステップ\n\n'
            '**1. 活動モニタリング**\n1週間の活動と対応する気分（0-10）を記録し、どの活動が気分を良くするか特定する。\n\n'
            '**2. 活動スケジューリング**\n毎日少なくとも1つ、達成感や喜びを与える活動を計画する。小さなことから始める。\n\n'
            '**3. 段階的タスク**\n大きなタスクを小さなステップに分割してハードルを下げる。例：「部屋を片付ける」→「まず机の上から」。\n\n'
            '**4. 価値観に基づく**\n個人の価値観に沿った活動を選ぶ（家族、健康、創造性）。\n\n'
            '## 活動の例\n\n'
            '- 15分間散歩する\n'
            '- 友人に電話する\n'
            '- 簡単な料理を作る\n'
            '- 好きな音楽を聴く\n'
            '- 小さなスペースを片付ける\n\n'
            '## 重要なポイント\n\n'
            'やる気が出るのを待つ必要はありません——まず行動すれば、やる気は後からついてきます。'
        ),
        'category': 'cbt',
        'reading_time': 5,
        'order': 10,
        'source': (
            'National Institute for Health and Care Excellence (NICE). '
            'Depression in adults: treatment and management (NG222). '
            'https://www.nice.org.uk/guidance/ng222'
        ),
    },
    {
        'title_zh': '認識焦慮：了解你的身心反應',
        'title_en': 'Understanding Anxiety',
        'title_ja': '不安を理解する：心身の反応を知る',
        'content_zh': (
            '焦慮是人類正常的情緒反應，但當它過度或持續時，可能影響日常生活。根據世界衛生組織（WHO），全球約有 3.01 億人患有焦慮症。\n\n'
            '## 焦慮的身體症狀\n\n'
            '- 心跳加速\n'
            '- 呼吸急促\n'
            '- 肌肉緊繃\n'
            '- 手心出汗\n'
            '- 腸胃不適\n'
            '- 難以入睡\n\n'
            '## 焦慮的心理症狀\n\n'
            '- 持續擔心\n'
            '- 注意力難以集中\n'
            '- 易怒\n'
            '- 感覺失控\n'
            '- 迴避行為\n\n'
            '## 什麼時候需要尋求幫助\n\n'
            '根據美國國家心理衛生研究院（NIMH），如果以下情況持續超過 6 個月，建議尋求專業協助：\n\n'
            '- 焦慮感無法控制\n'
            '- 嚴重影響工作或人際關係\n'
            '- 開始迴避日常活動\n'
            '- 伴隨恐慌發作\n\n'
            '## 自我幫助策略\n\n'
            '1. 規律運動（每週 150 分鐘中等強度活動）\n'
            '2. 限制咖啡因和酒精攝取\n'
            '3. 練習放鬆技巧（深呼吸、正念）\n'
            '4. 維持規律作息\n'
            '5. 與信任的人談論你的感受'
        ),
        'content_en': (
            'Anxiety is a normal human emotional response, but when excessive or persistent, it can affect daily life. According to the World Health Organization (WHO), approximately 301 million people worldwide have anxiety disorders.\n\n'
            '## Physical Symptoms of Anxiety\n\n'
            '- Rapid heartbeat\n'
            '- Shortness of breath\n'
            '- Muscle tension\n'
            '- Sweaty palms\n'
            '- Stomach discomfort\n'
            '- Difficulty sleeping\n\n'
            '## Psychological Symptoms\n\n'
            '- Persistent worry\n'
            '- Difficulty concentrating\n'
            '- Irritability\n'
            '- Feeling out of control\n'
            '- Avoidance behavior\n\n'
            '## When to Seek Help\n\n'
            'According to the National Institute of Mental Health (NIMH), seek professional help if the following persist for more than 6 months:\n\n'
            '- Anxiety feels uncontrollable\n'
            '- It significantly affects work or relationships\n'
            '- You start avoiding daily activities\n'
            '- You experience panic attacks\n\n'
            '## Self-Help Strategies\n\n'
            '1. Regular exercise (150 minutes of moderate activity per week)\n'
            '2. Limit caffeine and alcohol intake\n'
            '3. Practice relaxation techniques (deep breathing, mindfulness)\n'
            '4. Maintain a regular sleep schedule\n'
            '5. Talk to someone you trust about your feelings'
        ),
        'content_ja': (
            '不安は人間の正常な感情反応ですが、過度に続くと日常生活に影響を与えることがあります。世界保健機関（WHO）によると、世界で約3億100万人が不安障害を抱えています。\n\n'
            '## 不安の身体症状\n\n'
            '- 心拍数の増加\n'
            '- 息切れ\n'
            '- 筋肉の緊張\n'
            '- 手のひらの発汗\n'
            '- 胃腸の不快感\n'
            '- 入眠困難\n\n'
            '## 心理的症状\n\n'
            '- 持続的な心配\n'
            '- 集中力の低下\n'
            '- イライラ\n'
            '- コントロールを失う感覚\n'
            '- 回避行動\n\n'
            '## 助けを求めるべきとき\n\n'
            '米国国立精神衛生研究所（NIMH）によると、以下が6ヶ月以上続く場合は専門的な助けを求めましょう：\n\n'
            '- 不安がコントロールできない\n'
            '- 仕事や人間関係に大きく影響\n'
            '- 日常活動を避け始める\n'
            '- パニック発作を経験\n\n'
            '## セルフヘルプ戦略\n\n'
            '1. 定期的な運動（週150分の中程度の活動）\n'
            '2. カフェインとアルコールの摂取を制限\n'
            '3. リラクゼーション技法の練習（深呼吸、マインドフルネス）\n'
            '4. 規則正しい睡眠スケジュールの維持\n'
            '5. 信頼できる人に気持ちを話す'
        ),
        'category': 'emotion',
        'reading_time': 5,
        'order': 11,
        'source': (
            'World Health Organization (WHO). Anxiety disorders. '
            'https://www.who.int/news-room/fact-sheets/detail/anxiety-disorders '
            '| National Institute of Mental Health (NIMH). '
            'https://www.nimh.nih.gov/health/topics/anxiety-disorders'
        ),
    },
    {
        'title_zh': '自我慈悲練習',
        'title_en': 'Self-Compassion Practice',
        'title_ja': 'セルフ・コンパッション実践',
        'content_zh': (
            '自我慈悲是由 Kristin Neff 博士提出的概念，獲得美國心理學會（APA）的研究支持。它是指用對待好朋友的方式來對待自己。\n\n'
            '## 自我慈悲的三個核心元素\n\n'
            '**1. 自我善待（而非自我批評）**\n當遭遇困難時，用溫和和理解代替嚴厲的自我批判。\n\n'
            '**2. 共同人性（而非孤立感）**\n認識到痛苦和不完美是所有人共有的體驗，你並不孤單。\n\n'
            '**3. 正念覺察（而非過度認同）**\n以平衡的方式觀察負面情緒，既不壓抑也不放大。\n\n'
            '## 自我慈悲暫停練習\n\n'
            '當你感到痛苦時，試試以下三步驟：\n\n'
            '1. **覺察：**「這是一個痛苦的時刻。」（正念）\n'
            '2. **連結：**「痛苦是人生的一部分，很多人也有同樣的感受。」（共同人性）\n'
            '3. **善待：**把手放在心口，對自己說：「願我對自己仁慈。」（自我善待）\n\n'
            '## 研究證實的好處\n\n'
            '- 減少焦慮和憂鬱症狀\n'
            '- 提升情緒復原力\n'
            '- 增強動機和自我成長\n'
            '- 改善人際關係品質'
        ),
        'content_en': (
            'Self-compassion is a concept developed by Dr. Kristin Neff, supported by research from the American Psychological Association (APA). It means treating yourself with the same kindness you would offer a good friend.\n\n'
            '## Three Core Elements of Self-Compassion\n\n'
            '**1. Self-Kindness (vs. Self-Criticism)**\nWhen facing difficulty, respond with warmth and understanding rather than harsh self-judgment.\n\n'
            '**2. Common Humanity (vs. Isolation)**\nRecognize that suffering and imperfection are shared human experiences — you are not alone.\n\n'
            '**3. Mindful Awareness (vs. Over-Identification)**\nObserve negative emotions in a balanced way, neither suppressing nor amplifying them.\n\n'
            '## Self-Compassion Break Exercise\n\n'
            'When you are suffering, try these three steps:\n\n'
            '1. **Acknowledge:** "This is a moment of suffering." (Mindfulness)\n'
            '2. **Connect:** "Suffering is part of life. Many people feel this way too." (Common Humanity)\n'
            '3. **Kindness:** Place your hand on your heart and say: "May I be kind to myself." (Self-Kindness)\n\n'
            '## Research-Backed Benefits\n\n'
            '- Reduced anxiety and depression symptoms\n'
            '- Greater emotional resilience\n'
            '- Enhanced motivation and personal growth\n'
            '- Improved relationship quality'
        ),
        'content_ja': (
            'セルフ・コンパッションはクリスティン・ネフ博士が提唱した概念で、アメリカ心理学会（APA）の研究により支持されています。良い友人に接するように自分自身に接することを意味します。\n\n'
            '## セルフ・コンパッションの3つの核心要素\n\n'
            '**1. 自分への優しさ（自己批判ではなく）**\n困難に直面したとき、厳しい自己判断の代わりに温かさと理解で対応する。\n\n'
            '**2. 共通の人間性（孤立感ではなく）**\n苦しみや不完全さは全ての人に共通する体験であり、あなたは一人ではないと認識する。\n\n'
            '**3. マインドフルな気づき（過剰な同一化ではなく）**\n否定的な感情をバランスよく観察し、抑圧も増幅もしない。\n\n'
            '## セルフ・コンパッション・ブレイク\n\n'
            '苦しいとき、次の3ステップを試しましょう：\n\n'
            '1. **気づき：**「これは苦しい瞬間だ。」（マインドフルネス）\n'
            '2. **つながり：**「苦しみは人生の一部。多くの人も同じように感じている。」（共通の人間性）\n'
            '3. **優しさ：** 手を胸に当てて言う：「自分に優しくしよう。」（自分への優しさ）\n\n'
            '## 研究で証明された効果\n\n'
            '- 不安やうつ症状の軽減\n'
            '- 感情的レジリエンスの向上\n'
            '- モチベーションと自己成長の強化\n'
            '- 人間関係の質の改善'
        ),
        'category': 'mindfulness',
        'reading_time': 5,
        'order': 12,
        'source': (
            'Neff, K. D. (2011). Self-Compassion. William Morrow. '
            'American Psychological Association (APA). '
            'https://www.apa.org/monitor/2023/11/self-compassion-benefits'
        ),
    },
    {
        'title_zh': '感恩日記的科學基礎',
        'title_en': 'The Science of Gratitude Journaling',
        'title_ja': '感謝日記の科学的根拠',
        'content_zh': (
            '感恩日記是經過大量研究驗證的正向心理學工具。加州大學戴維斯分校 Robert Emmons 教授的研究表明，定期記錄感恩之事可顯著改善心理健康。\n\n'
            '## 研究發現\n\n'
            '- 每週寫感恩日記的人，整體幸福感提升 25%\n'
            '- 減少焦慮和憂鬱症狀\n'
            '- 改善睡眠品質\n'
            '- 增強免疫系統功能\n'
            '- 提升人際關係滿意度\n\n'
            '## 如何寫感恩日記\n\n'
            '**每天或每週記錄 3-5 件你感到感恩的事。**\n\n'
            '**1. 具體化**\n不要只寫「感恩家人」，而是「今天媽媽特地煮了我喜歡的湯」。\n\n'
            '**2. 專注在人而非物品**\n對人的感恩比對物質的感恩更能提升幸福感。\n\n'
            '**3. 關注驚喜和意外**\n意想不到的好事特別能激發感恩之情。\n\n'
            '**4. 探索深度**\n深入思考「為什麼」這件事讓你感恩，而不只是列出事項。\n\n'
            '## 練習提示\n\n'
            '- 嘗試在每天固定時間寫（如睡前）\n'
            '- 不需要寫很多——質比量重要\n'
            '- 感覺困難時，從最簡單的事開始（如乾淨的水、安全的住所）'
        ),
        'content_en': (
            'Gratitude journaling is a well-researched positive psychology tool. Professor Robert Emmons at UC Davis has shown that regularly recording things you\'re grateful for significantly improves mental health.\n\n'
            '## Research Findings\n\n'
            '- People who write gratitude journals weekly report 25% higher well-being\n'
            '- Reduced anxiety and depression symptoms\n'
            '- Improved sleep quality\n'
            '- Enhanced immune system function\n'
            '- Greater relationship satisfaction\n\n'
            '## How to Write a Gratitude Journal\n\n'
            '**Record 3-5 things you\'re grateful for daily or weekly.**\n\n'
            '**1. Be Specific**\nDon\'t just write "grateful for family." Instead: "Mom made my favorite soup today."\n\n'
            '**2. Focus on People, Not Things**\nGratitude toward people boosts well-being more than gratitude for material items.\n\n'
            '**3. Notice Surprises**\nUnexpected positive events especially spark gratitude.\n\n'
            '**4. Explore Depth**\nThink about "why" something makes you grateful, not just list items.\n\n'
            '## Practice Tips\n\n'
            '- Try writing at a fixed time each day (e.g., before bed)\n'
            '- You don\'t need to write a lot — quality over quantity\n'
            '- When it feels hard, start with the simplest things (clean water, safe shelter)'
        ),
        'content_ja': (
            '感謝日記は多くの研究で検証されたポジティブ心理学のツールです。カリフォルニア大学デービス校のロバート・エモンズ教授の研究により、感謝していることを定期的に記録することが精神的健康を大幅に改善することが示されています。\n\n'
            '## 研究結果\n\n'
            '- 毎週感謝日記を書く人は幸福感が25%向上\n'
            '- 不安やうつ症状の軽減\n'
            '- 睡眠の質の改善\n'
            '- 免疫システム機能の強化\n'
            '- 人間関係の満足度の向上\n\n'
            '## 感謝日記の書き方\n\n'
            '**毎日または毎週、感謝していることを3〜5つ記録する。**\n\n'
            '**1. 具体的に**\n「家族に感謝」ではなく「今日お母さんが好きなスープを作ってくれた」と書く。\n\n'
            '**2. モノより人に焦点を**\n人への感謝は物質への感謝より幸福感を高めます。\n\n'
            '**3. 驚きに注目**\n予想外のポジティブな出来事は特に感謝の気持ちを刺激します。\n\n'
            '**4. 深さを探求**\n項目をリストアップするだけでなく、「なぜ」感謝しているのか考える。\n\n'
            '## 練習のコツ\n\n'
            '- 毎日決まった時間に書く（例：就寝前）\n'
            '- たくさん書く必要はない — 量より質\n'
            '- 難しく感じるときは、最もシンプルなことから始める（きれいな水、安全な住まい）'
        ),
        'category': 'mindfulness',
        'reading_time': 5,
        'order': 13,
        'source': (
            'Emmons, R. A., & McCullough, M. E. (2003). Counting blessings versus burdens. '
            'Journal of Personality and Social Psychology, 84(2), 377-389. '
            'Greater Good Science Center, UC Berkeley. '
            'https://greatergood.berkeley.edu/topic/gratitude/definition'
        ),
    },
    {
        'title_zh': '憤怒管理技巧',
        'title_en': 'Anger Management Techniques',
        'title_ja': 'アンガーマネジメント技法',
        'content_zh': (
            '憤怒是一種正常的人類情緒，但如果管理不當，可能影響健康和人際關係。美國心理學會（APA）提供以下實證策略來有效管理憤怒。\n\n'
            '## 即時緩解技巧\n\n'
            '**1. 暫停法**\n感到憤怒時，先暫停 10 秒再回應。默數到 10 或離開現場冷靜。\n\n'
            '**2. 深呼吸**\n緩慢深呼吸可以降低生理激動。嘗試方框呼吸：吸 4 秒、屏 4 秒、呼 4 秒、等 4 秒。\n\n'
            '**3. 身體活動**\n快走、跑步或任何有氧運動可以幫助釋放累積的緊張能量。\n\n'
            '## 長期管理策略\n\n'
            '**1. 辨識觸發因素**\n記錄什麼情境、人或想法容易觸發你的憤怒。\n\n'
            '**2. 用「我」的語句表達**\n不要說「你總是...」，改說「當...的時候，我感到...」。\n\n'
            '**3. 認知重構**\n檢視你的想法是否合理。問自己：「事實是什麼？」「有沒有其他解釋？」\n\n'
            '**4. 問題解決**\n如果憤怒來自合理的問題，把注意力放在尋找解決方案上。\n\n'
            '## 什麼時候尋求幫助\n\n'
            '- 憤怒導致暴力行為\n'
            '- 影響工作或人際關係\n'
            '- 頻率或強度持續增加\n'
            '- 伴隨酒精或藥物使用'
        ),
        'content_en': (
            'Anger is a normal human emotion, but when poorly managed, it can affect health and relationships. The American Psychological Association (APA) provides these evidence-based strategies for effective anger management.\n\n'
            '## Immediate Relief Techniques\n\n'
            '**1. Time-Out**\nWhen feeling angry, pause for 10 seconds before responding. Count to 10 or leave the situation to cool down.\n\n'
            '**2. Deep Breathing**\nSlow, deep breathing reduces physiological arousal. Try box breathing: inhale 4s, hold 4s, exhale 4s, wait 4s.\n\n'
            '**3. Physical Activity**\nBrisk walking, running, or any aerobic exercise helps release built-up tension.\n\n'
            '## Long-Term Management Strategies\n\n'
            '**1. Identify Triggers**\nNote which situations, people, or thoughts tend to trigger your anger.\n\n'
            '**2. Use "I" Statements**\nInstead of "You always...", say "When... happens, I feel..."\n\n'
            '**3. Cognitive Restructuring**\nExamine whether your thoughts are reasonable. Ask: "What are the facts?" "Is there another explanation?"\n\n'
            '**4. Problem-Solving**\nIf anger stems from a legitimate problem, focus on finding solutions.\n\n'
            '## When to Seek Help\n\n'
            '- Anger leads to violent behavior\n'
            '- It affects work or relationships\n'
            '- Frequency or intensity keeps increasing\n'
            '- It co-occurs with alcohol or substance use'
        ),
        'content_ja': (
            '怒りは正常な人間の感情ですが、うまく管理できないと健康や人間関係に影響を与えます。アメリカ心理学会（APA）は効果的なアンガーマネジメントのためにこれらのエビデンスに基づく戦略を提供しています。\n\n'
            '## 即時緩和テクニック\n\n'
            '**1. タイムアウト**\n怒りを感じたら、反応する前に10秒間一時停止する。10まで数えるか、その場を離れてクールダウンする。\n\n'
            '**2. 深呼吸**\nゆっくりとした深呼吸は生理的な興奮を低下させます。ボックス呼吸を試しましょう：4秒吸う、4秒止める、4秒吐く、4秒待つ。\n\n'
            '**3. 身体活動**\n早歩き、ランニング、または有酸素運動は蓄積された緊張を解放するのに役立ちます。\n\n'
            '## 長期的な管理戦略\n\n'
            '**1. トリガーの特定**\nどの状況、人、考えが怒りを引き起こしやすいか記録する。\n\n'
            '**2.「私」メッセージを使う**\n「あなたはいつも...」ではなく「...のとき、私は...と感じる」と言う。\n\n'
            '**3. 認知的再構成**\n自分の考えが合理的かどうか検証する。「事実は何か？」「他の説明はあるか？」と自問する。\n\n'
            '**4. 問題解決**\n怒りが正当な問題から来ている場合は、解決策を見つけることに焦点を当てる。\n\n'
            '## 助けを求めるべきとき\n\n'
            '- 怒りが暴力的な行動につながる\n'
            '- 仕事や人間関係に影響する\n'
            '- 頻度や強度が増し続けている\n'
            '- アルコールや薬物使用を伴う'
        ),
        'category': 'emotion',
        'reading_time': 5,
        'order': 14,
        'source': (
            'American Psychological Association (APA). Controlling anger before it controls you. '
            'https://www.apa.org/topics/anger/control'
        ),
    },
    {
        'title_zh': '社交連結與心理健康',
        'title_en': 'Social Connection and Mental Health',
        'title_ja': '社会的つながりとメンタルヘルス',
        'content_zh': (
            '世界衛生組織（WHO）將社交孤立列為影響健康的重要因素。研究顯示，良好的社交連結對心理健康有深遠的正面影響。\n\n'
            '## 社交連結的好處\n\n'
            '- 降低焦慮和憂鬱風險\n'
            '- 增強壓力應對能力\n'
            '- 提升自我價值感\n'
            '- 改善認知功能\n'
            '- 延長壽命（效果等同於戒菸）\n\n'
            '## 如何建立有意義的連結\n\n'
            '**1. 品質重於數量**\n幾段深入的關係比眾多表面關係更有益。\n\n'
            '**2. 主動聯繫**\n不要等別人先聯絡你。今天就傳個訊息或打個電話。\n\n'
            '**3. 全心投入**\n見面時放下手機，給予對方完整的注意力。\n\n'
            '**4. 加入社群**\n參加興趣小組、志工活動或社區組織。\n\n'
            '**5. 接受脆弱**\n願意分享真實的感受，而不只是表面的寒暄。\n\n'
            '## 當社交感到困難時\n\n'
            '如果你正經歷社交焦慮或孤獨感：\n'
            '- 從小步驟開始（微笑、打招呼）\n'
            '- 考慮線上社群作為起步\n'
            '- 練習自我慈悲\n'
            '- 如有需要，尋求專業支持'
        ),
        'content_en': (
            'The World Health Organization (WHO) lists social isolation as a significant health risk factor. Research shows that strong social connections have profound positive effects on mental health.\n\n'
            '## Benefits of Social Connection\n\n'
            '- Lower risk of anxiety and depression\n'
            '- Enhanced stress coping ability\n'
            '- Greater sense of self-worth\n'
            '- Improved cognitive function\n'
            '- Increased longevity (effect comparable to quitting smoking)\n\n'
            '## How to Build Meaningful Connections\n\n'
            '**1. Quality Over Quantity**\nA few deep relationships are more beneficial than many superficial ones.\n\n'
            '**2. Reach Out First**\nDon\'t wait for others to contact you. Send a message or make a call today.\n\n'
            '**3. Be Fully Present**\nPut away your phone when meeting someone and give them your full attention.\n\n'
            '**4. Join Communities**\nParticipate in interest groups, volunteer work, or community organizations.\n\n'
            '**5. Embrace Vulnerability**\nBe willing to share genuine feelings, not just surface-level pleasantries.\n\n'
            '## When Socializing Feels Hard\n\n'
            'If you\'re experiencing social anxiety or loneliness:\n'
            '- Start small (smile, say hello)\n'
            '- Consider online communities as a starting point\n'
            '- Practice self-compassion\n'
            '- Seek professional support if needed'
        ),
        'content_ja': (
            '世界保健機関（WHO）は社会的孤立を健康に影響する重要なリスク要因として挙げています。研究により、良好な社会的つながりが精神的健康に深い良い影響を与えることが示されています。\n\n'
            '## 社会的つながりの利点\n\n'
            '- 不安やうつのリスク低下\n'
            '- ストレス対処能力の強化\n'
            '- 自己価値感の向上\n'
            '- 認知機能の改善\n'
            '- 寿命の延長（禁煙に匹敵する効果）\n\n'
            '## 意味のあるつながりの構築方法\n\n'
            '**1. 量より質**\n少数の深い関係は多くの表面的な関係より有益です。\n\n'
            '**2. 自分から連絡する**\n他の人が連絡してくるのを待たない。今日メッセージを送るか電話をしましょう。\n\n'
            '**3. 完全に集中する**\n会うときはスマホを置いて、相手に完全な注意を向ける。\n\n'
            '**4. コミュニティに参加**\n趣味のグループ、ボランティア活動、地域組織に参加する。\n\n'
            '**5. 脆弱性を受け入れる**\n表面的な挨拶だけでなく、本当の気持ちを共有する意思を持つ。\n\n'
            '## 社交が難しいと感じるとき\n\n'
            '社交不安や孤独を感じている場合：\n'
            '- 小さなステップから始める（微笑む、挨拶する）\n'
            '- オンラインコミュニティを出発点として検討\n'
            '- セルフ・コンパッションを実践\n'
            '- 必要に応じて専門的なサポートを求める'
        ),
        'category': 'emotion',
        'reading_time': 5,
        'order': 15,
        'source': (
            'World Health Organization (WHO). Social isolation and loneliness. '
            'https://www.who.int/teams/social-determinants-of-health/demographic-change-and-healthy-ageing/social-isolation-and-loneliness '
            '| Holt-Lunstad, J. et al. (2010). Social Relationships and Mortality Risk. PLoS Medicine.'
        ),
    },
    {
        'title_zh': '建立心理韌性',
        'title_en': 'Building Psychological Resilience',
        'title_ja': '心理的レジリエンスの構築',
        'content_zh': (
            '心理韌性是指面對逆境、壓力或創傷時，能夠適應和恢復的能力。美國心理學會（APA）指出，韌性是可以學習和培養的。\n\n'
            '## APA 建議的韌性建構策略\n\n'
            '**1. 建立連結**\n維持與家人、朋友和社群的關係，在困難時接受支持。\n\n'
            '**2. 培養健康**\n照顧身體需求：充足睡眠、營養飲食、規律運動、避免不良習慣。\n\n'
            '**3. 找到目標**\n幫助他人、設定小目標、尋找每天的意義。\n\n'
            '**4. 接受改變**\n接受無法改變的事實，把注意力放在你能控制的部分。\n\n'
            '**5. 採取行動**\n面對問題而非逃避。即使是微小的行動也能帶來控制感。\n\n'
            '**6. 自我發現**\n從困難經歷中學習，重新認識自己的力量和能力。\n\n'
            '**7. 培養正向思維**\n練習感恩、保持希望、用長遠的角度看待困難。\n\n'
            '**8. 保持觀點**\n避免把事情災難化。問自己：「五年後這件事還重要嗎？」\n\n'
            '## 韌性不代表\n\n'
            '- 不代表不會感到痛苦\n'
            '- 不代表要獨自面對一切\n'
            '- 不代表每次都能快速恢復\n'
            '- 韌性是一個持續的過程，不是一種固定特質'
        ),
        'content_en': (
            'Psychological resilience is the ability to adapt and recover when facing adversity, stress, or trauma. The American Psychological Association (APA) emphasizes that resilience can be learned and developed.\n\n'
            '## APA-Recommended Resilience-Building Strategies\n\n'
            '**1. Build Connections**\nMaintain relationships with family, friends, and community. Accept support during difficult times.\n\n'
            '**2. Foster Wellness**\nTake care of physical needs: adequate sleep, nutritious diet, regular exercise, avoid harmful habits.\n\n'
            '**3. Find Purpose**\nHelp others, set small goals, seek meaning in each day.\n\n'
            '**4. Embrace Change**\nAccept what cannot be changed. Focus on what you can control.\n\n'
            '**5. Take Action**\nFace problems rather than avoiding them. Even small actions can restore a sense of control.\n\n'
            '**6. Self-Discovery**\nLearn from difficult experiences. Recognize your own strength and capabilities.\n\n'
            '**7. Nurture Positive Thinking**\nPractice gratitude, maintain hope, view difficulties from a long-term perspective.\n\n'
            '**8. Keep Perspective**\nAvoid catastrophizing. Ask yourself: "Will this matter in five years?"\n\n'
            '## Resilience Does NOT Mean\n\n'
            '- You won\'t feel pain\n'
            '- You have to face everything alone\n'
            '- You\'ll always recover quickly\n'
            '- It\'s an ongoing process, not a fixed trait'
        ),
        'content_ja': (
            '心理的レジリエンスとは、逆境、ストレス、トラウマに直面したときに適応し回復する能力です。アメリカ心理学会（APA）は、レジリエンスは学び、育てることができると強調しています。\n\n'
            '## APA推奨のレジリエンス構築戦略\n\n'
            '**1. つながりを構築する**\n家族、友人、コミュニティとの関係を維持する。困難なときにサポートを受け入れる。\n\n'
            '**2. 健康を育む**\n身体的ニーズのケア：十分な睡眠、栄養のある食事、定期的な運動、有害な習慣を避ける。\n\n'
            '**3. 目的を見つける**\n他者を助け、小さな目標を設定し、毎日の意味を探す。\n\n'
            '**4. 変化を受け入れる**\n変えられないことを受け入れる。コントロールできることに集中する。\n\n'
            '**5. 行動を起こす**\n問題を避けずに直面する。小さな行動でもコントロール感を取り戻せる。\n\n'
            '**6. 自己発見**\n困難な経験から学ぶ。自分の強さと能力を再認識する。\n\n'
            '**7. ポジティブ思考を育む**\n感謝を実践し、希望を持ち、長期的な視点で困難を見る。\n\n'
            '**8. 視野を保つ**\n破局的に考えることを避ける。「5年後もこれは重要か？」と自問する。\n\n'
            '## レジリエンスは以下を意味しない\n\n'
            '- 痛みを感じないこと\n'
            '- すべてを一人で乗り越えること\n'
            '- 常に素早く回復すること\n'
            '- 継続的なプロセスであり、固定された特性ではない'
        ),
        'category': 'stress',
        'reading_time': 5,
        'order': 16,
        'source': (
            'American Psychological Association (APA). Building your resilience. '
            'https://www.apa.org/topics/resilience/building-your-resilience'
        ),
    },
]


def update_sources_and_add_articles(apps, schema_editor):
    PsychoArticle = apps.get_model('api', 'PsychoArticle')

    # Update existing article sources
    for title_en, source in UPDATED_SOURCES.items():
        PsychoArticle.objects.filter(title_en=title_en).update(source=source)

    # Add new articles
    for article in NEW_ARTICLES:
        PsychoArticle.objects.get_or_create(
            title_en=article['title_en'],
            defaults=article,
        )


def revert(apps, schema_editor):
    PsychoArticle = apps.get_model('api', 'PsychoArticle')
    # Delete new articles
    PsychoArticle.objects.filter(
        title_en__in=[a['title_en'] for a in NEW_ARTICLES]
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0024_alter_auditlog_action'),
    ]

    operations = [
        migrations.RunPython(update_sources_and_add_articles, revert),
    ]
