# Data migration: Create "Breathing & Meditation" course with 3 trilingual articles

from django.db import migrations


def seed_breathing_course(apps, schema_editor):
    Course = apps.get_model('api', 'Course')
    PsychoArticle = apps.get_model('api', 'PsychoArticle')

    # Create the course
    course = Course.objects.create(
        title_zh='呼吸與冥想',
        title_en='Breathing & Meditation',
        title_ja='呼吸と瞑想',
        description_zh='了解呼吸法與冥想的科學原理，學習如何建立每日練習習慣。',
        description_en='Understand the science behind breathing techniques and meditation, and learn to build a daily practice.',
        description_ja='呼吸法と瞑想の科学的原理を理解し、毎日の練習習慣を築く方法を学びます。',
        category='mindfulness',
        icon_emoji='\U0001f32c\ufe0f',
        order=5,
    )

    # Article 1: Science of Breathing
    a1 = PsychoArticle.objects.create(
        title_zh='呼吸法的科學原理',
        title_en='The Science of Breathing Techniques',
        title_ja='呼吸法の科学的原理',
        content_zh=(
            '## 為什麼呼吸法有效？\n\n'
            '呼吸是少數既受自主神經控制，又能被意識主動調節的生理功能。'
            '當我們刻意放慢呼吸節奏時，迷走神經會向大腦發送「安全」訊號，'
            '啟動副交感神經系統，降低心率和血壓。\n\n'
            '## 三種呼吸法的生理差異\n\n'
            '### 4-7-8 呼吸法\n'
            '由 Andrew Weil 醫師推廣。吸氣 4 秒、屏住 7 秒、呼氣 8 秒。'
            '延長的呼氣階段能最大化副交感神經激活，特別適合放鬆入睡。'
            '研究顯示，持續練習可在 4-6 週內顯著改善入睡時間。\n\n'
            '### 方框呼吸（Box Breathing）\n'
            '美國海豹突擊隊使用的壓力管理技巧。'
            '吸氣、屏住、呼氣、屏住各 4 秒，形成「方框」節奏。'
            '均等的節奏能快速恢復專注力，適合高壓環境下使用。\n\n'
            '### 深呼吸（腹式呼吸）\n'
            '吸氣 4 秒、屏住 2 秒、呼氣 6 秒。'
            '強調橫膈膜的深層擴張，能有效降低皮質醇水平，緩解焦慮與緊張。\n\n'
            '## 科學研究支持\n\n'
            '2023 年史丹佛大學研究發現，每天僅 5 分鐘的結構化呼吸練習，'
            '就能顯著降低皮質醇水平並改善情緒。'
            '另一項發表於《Cell Reports Medicine》的研究表明，'
            '控制呼吸比被動冥想更能有效減少焦慮。\n\n'
            '## 開始練習\n\n'
            '選擇一種呼吸法，每天練習 3-5 分鐘。'
            '建議在安靜的環境中坐下或躺下，閉上眼睛，專注於呼吸的節奏。'
        ),
        content_en=(
            '## Why Do Breathing Techniques Work?\n\n'
            'Breathing is one of the few physiological functions controlled by the autonomic nervous system '
            'that can also be consciously regulated. When we deliberately slow our breathing, the vagus nerve '
            'sends a "safety" signal to the brain, activating the parasympathetic nervous system, '
            'lowering heart rate and blood pressure.\n\n'
            '## Physiological Differences of Three Techniques\n\n'
            '### 4-7-8 Breathing\n'
            'Popularized by Dr. Andrew Weil. Inhale for 4 seconds, hold for 7 seconds, exhale for 8 seconds. '
            'The extended exhale phase maximizes parasympathetic activation, making it ideal for relaxation and sleep. '
            'Studies show consistent practice can significantly improve sleep onset time within 4-6 weeks.\n\n'
            '### Box Breathing\n'
            'A stress management technique used by U.S. Navy SEALs. '
            'Inhale, hold, exhale, and hold for 4 seconds each, forming a "box" rhythm. '
            'The balanced rhythm quickly restores focus, ideal for high-pressure situations.\n\n'
            '### Deep Breathing (Diaphragmatic)\n'
            'Inhale for 4 seconds, hold for 2 seconds, exhale for 6 seconds. '
            'Emphasizes deep diaphragm expansion, effectively lowering cortisol levels to relieve anxiety and tension.\n\n'
            '## Scientific Evidence\n\n'
            'A 2023 Stanford University study found that just 5 minutes of structured breathing exercises daily '
            'can significantly reduce cortisol levels and improve mood. '
            'Another study published in Cell Reports Medicine showed that '
            'controlled breathing is more effective at reducing anxiety than passive meditation.\n\n'
            '## Start Practicing\n\n'
            'Choose a breathing technique and practice 3-5 minutes daily. '
            'Sit or lie down in a quiet environment, close your eyes, and focus on the rhythm of your breath.'
        ),
        content_ja=(
            '## なぜ呼吸法は効果があるのか？\n\n'
            '呼吸は、自律神経系によって制御されながらも、意識的に調節できる数少ない生理機能の一つです。'
            '意図的に呼吸を遅くすると、迷走神経が脳に「安全」の信号を送り、'
            '副交感神経系を活性化させ、心拍数と血圧を低下させます。\n\n'
            '## 3つの呼吸法の生理学的違い\n\n'
            '### 4-7-8 呼吸法\n'
            'Andrew Weil医師が推奨。4秒吸って、7秒止めて、8秒かけて吐きます。'
            '長い呼気が副交感神経の活性化を最大化し、リラックスと睡眠に最適です。'
            '研究によると、継続的な練習で4〜6週間以内に入眠時間が大幅に改善されます。\n\n'
            '### ボックス呼吸\n'
            '米国海軍特殊部隊が使用するストレス管理テクニック。'
            '吸う・止める・吐く・止めるを各4秒ずつ、「ボックス」のリズムで行います。'
            '均等なリズムが集中力を素早く回復させ、高圧環境に適しています。\n\n'
            '### 深呼吸（腹式呼吸）\n'
            '4秒吸って、2秒止めて、6秒かけて吐きます。'
            '横隔膜の深い拡張を重視し、コルチゾールレベルを効果的に低下させ、不安と緊張を和らげます。\n\n'
            '## 科学的エビデンス\n\n'
            '2023年のスタンフォード大学の研究では、1日わずか5分の構造化された呼吸エクササイズで、'
            'コルチゾールレベルが有意に低下し、気分が改善されることが分かりました。'
            'Cell Reports Medicineに掲載された別の研究では、'
            'コントロールされた呼吸は受動的な瞑想よりも不安の軽減に効果的であることが示されています。\n\n'
            '## 練習を始めましょう\n\n'
            '呼吸法を一つ選び、毎日3〜5分練習してください。'
            '静かな環境で座るか横になり、目を閉じて呼吸のリズムに集中しましょう。'
        ),
        category='mindfulness',
        reading_time=6,
        source='Stanford University / Cell Reports Medicine',
        course=course,
        lesson_order=1,
    )

    # Article 2: Science and Benefits of Meditation
    a2 = PsychoArticle.objects.create(
        title_zh='冥想的科學與益處',
        title_en='The Science and Benefits of Meditation',
        title_ja='瞑想の科学と効果',
        content_zh=(
            '## 什麼是冥想？\n\n'
            '冥想是一種訓練注意力和覺察力的心智練習。'
            '它不是「放空大腦」，而是學習觀察自己的思緒而不被捲入其中。\n\n'
            '## 冥想的主要類型\n\n'
            '### 正念冥想（Mindfulness）\n'
            '專注於當下的體驗，不評判地觀察呼吸、身體感受和思緒。'
            '這是最被廣泛研究的冥想形式。\n\n'
            '### 專注冥想（Focused Attention）\n'
            '將注意力集中在單一對象上，如呼吸、聲音或視覺焦點。'
            '當注意力漂移時，溫柔地將它帶回。\n\n'
            '### 身體掃描（Body Scan）\n'
            '從頭到腳逐步關注身體各部位的感受，'
            '幫助釋放身體緊張並增進身心連結。\n\n'
            '## 科學研究發現\n\n'
            '### 神經可塑性\n'
            '持續冥想練習會改變大腦結構。'
            '研究顯示 8 週的正念練習可以增厚前額葉皮層（決策和情緒調節區域），'
            '並縮小杏仁核（恐懼和壓力反應中心）。\n\n'
            '### 焦慮減少\n'
            '一項涵蓋 1,200 多名參與者的統合分析顯示，'
            '冥想練習能顯著降低焦慮症狀，效果與認知行為治療相當。\n\n'
            '### 注意力提升\n'
            '僅 4 天的冥想訓練就能改善注意力持續時間和工作記憶，'
            '這對日常工作和學習有直接益處。\n\n'
            '## 初學者建議\n\n'
            '從每天 5 分鐘開始。找一個安靜的地方坐下，'
            '閉上眼睛，將注意力放在呼吸上。'
            '當思緒漂移時（這是正常的），只需注意到它，然後溫柔地回到呼吸上。'
        ),
        content_en=(
            '## What Is Meditation?\n\n'
            'Meditation is a mental practice that trains attention and awareness. '
            "It's not about \"emptying your mind\" but learning to observe your thoughts without getting caught up in them.\n\n"
            '## Main Types of Meditation\n\n'
            '### Mindfulness Meditation\n'
            'Focus on present-moment experience, observing breath, bodily sensations, and thoughts without judgment. '
            'This is the most widely researched form of meditation.\n\n'
            '### Focused Attention Meditation\n'
            'Concentrate attention on a single object such as breath, sound, or a visual focus point. '
            'When attention drifts, gently bring it back.\n\n'
            '### Body Scan\n'
            'Progressively attend to sensations in each part of the body from head to toe, '
            'helping release physical tension and improve mind-body connection.\n\n'
            '## Scientific Findings\n\n'
            '### Neuroplasticity\n'
            'Consistent meditation practice changes brain structure. '
            'Research shows 8 weeks of mindfulness practice can thicken the prefrontal cortex '
            '(decision-making and emotional regulation) and shrink the amygdala (fear and stress response center).\n\n'
            '### Anxiety Reduction\n'
            'A meta-analysis of over 1,200 participants showed that '
            'meditation practice significantly reduces anxiety symptoms, with effects comparable to cognitive behavioral therapy.\n\n'
            '### Improved Attention\n'
            'Just 4 days of meditation training can improve sustained attention and working memory, '
            'directly benefiting daily work and learning.\n\n'
            '## Tips for Beginners\n\n'
            'Start with 5 minutes a day. Find a quiet place to sit, '
            'close your eyes, and focus on your breathing. '
            "When your mind wanders (this is normal), simply notice it and gently return to your breath."
        ),
        content_ja=(
            '## 瞑想とは？\n\n'
            '瞑想は、注意力と気づきを訓練する心の練習です。'
            '「頭を空にする」ことではなく、自分の思考に巻き込まれずに観察することを学ぶことです。\n\n'
            '## 瞑想の主な種類\n\n'
            '### マインドフルネス瞑想\n'
            '今この瞬間の体験に集中し、呼吸、身体の感覚、思考を判断せずに観察します。'
            'これは最も広く研究されている瞑想の形式です。\n\n'
            '### 集中瞑想\n'
            '呼吸、音、または視覚的な焦点など、単一の対象に注意を集中させます。'
            '注意がそれたら、優しく戻します。\n\n'
            '### ボディスキャン\n'
            '頭からつま先まで、体の各部位の感覚に順番に注意を向けます。'
            '身体の緊張を解放し、心身のつながりを高めるのに役立ちます。\n\n'
            '## 科学的な発見\n\n'
            '### 神経可塑性\n'
            '継続的な瞑想練習は脳の構造を変えます。'
            '研究によると、8週間のマインドフルネス練習で前頭前皮質（意思決定と感情調節の領域）が厚くなり、'
            '扁桃体（恐怖とストレス反応の中枢）が縮小します。\n\n'
            '### 不安の軽減\n'
            '1,200人以上の参加者を対象としたメタ分析では、'
            '瞑想練習が不安症状を有意に軽減し、その効果は認知行動療法に匹敵することが示されました。\n\n'
            '### 注意力の向上\n'
            'わずか4日間の瞑想トレーニングで持続的注意力とワーキングメモリが改善され、'
            '日常の仕事や学習に直接的な恩恵をもたらします。\n\n'
            '## 初心者へのアドバイス\n\n'
            '1日5分から始めましょう。静かな場所を見つけて座り、'
            '目を閉じて呼吸に集中してください。'
            '心がさまよったら（これは普通のことです）、それに気づいて、優しく呼吸に戻りましょう。'
        ),
        category='mindfulness',
        reading_time=7,
        source='JAMA Internal Medicine / Psychological Bulletin',
        course=course,
        lesson_order=2,
    )

    # Article 3: Building a Daily Practice
    a3 = PsychoArticle.objects.create(
        title_zh='建立每日呼吸與冥想習慣',
        title_en='Building a Daily Breathing & Meditation Habit',
        title_ja='毎日の呼吸と瞑想の習慣を築く',
        content_zh=(
            '## 為什麼需要「習慣化」？\n\n'
            '研究顯示，冥想和呼吸練習的益處來自持續性，而非單次練習的長度。'
            '每天 3 分鐘持續一個月，比偶爾做 30 分鐘更有效。\n\n'
            '## 從小處開始\n\n'
            '### 2-3 分鐘法則\n'
            '不要一開始就設定 20 分鐘的目標。從 2-3 分鐘開始，'
            '讓大腦習慣「這是一件輕鬆的事」。'
            '當你連續做了一週，自然會想延長時間。\n\n'
            '### 習慣疊加法（Habit Stacking）\n'
            '將呼吸練習「綁定」在已有的習慣之後：\n'
            '- 早上刷牙後 → 做 3 分鐘呼吸練習\n'
            '- 午餐前 → 做 1 分鐘方框呼吸\n'
            '- 睡前放下手機後 → 做 4-7-8 呼吸法\n\n'
            '把新習慣連結到舊習慣，成功率會大幅提升。\n\n'
            '## 環境設置\n\n'
            '### 創造你的練習空間\n'
            '不需要專門的冥想室。只需要一個固定的位置：\n'
            '- 一張舒適的椅子或一個靠墊\n'
            '- 減少視覺干擾（面向牆壁或窗戶）\n'
            '- 可選：輕柔的環境音（白噪音、自然聲音）\n\n'
            '### 設定提醒\n'
            '使用 HeartBox 的呼吸與冥想功能來追蹤練習紀錄，'
            '看到自己的練習歷史會增強持續的動力。\n\n'
            '## 常見障礙與克服\n\n'
            '### 「我的心思總是在飄」\n'
            '這是完全正常的！冥想不是消除念頭，'
            '而是練習「注意到念頭飄走，然後帶回來」這個動作。'
            '每次帶回注意力，就像做一次心智的仰臥起坐。\n\n'
            '### 「我沒有時間」\n'
            '如果你有時間滑 3 分鐘手機，你就有時間做呼吸練習。'
            '試試在等電梯、搭公車或午休時做幾個深呼吸。\n\n'
            '### 「我覺得沒有效果」\n'
            '呼吸練習的效果是漸進的，通常需要 2-4 週才能感受到明顯改變。'
            '記錄你的練習次數和時長，一個月後回顧會看到進步。\n\n'
            '## 30 天挑戰\n\n'
            '試試看連續 30 天，每天至少做一次呼吸或冥想練習。'
            '不需要很長，2 分鐘就夠了。重點是「每天都做」。'
            '你可以在 HeartBox 的練習紀錄中追蹤你的進度！'
        ),
        content_en=(
            '## Why "Make It a Habit"?\n\n'
            'Research shows that the benefits of meditation and breathing exercises come from consistency, '
            'not the length of individual sessions. '
            '3 minutes daily for a month is more effective than an occasional 30-minute session.\n\n'
            '## Start Small\n\n'
            '### The 2-3 Minute Rule\n'
            "Don't set a 20-minute goal right away. Start with 2-3 minutes, "
            'letting your brain learn that "this is easy." '
            "After a week of consistency, you'll naturally want to extend the time.\n\n"
            '### Habit Stacking\n'
            'Attach your breathing practice to an existing habit:\n'
            '- After brushing teeth in the morning → 3-minute breathing exercise\n'
            '- Before lunch → 1-minute box breathing\n'
            '- After putting phone down before bed → 4-7-8 breathing\n\n'
            'Linking new habits to old ones dramatically increases success rates.\n\n'
            '## Environment Setup\n\n'
            '### Create Your Practice Space\n'
            "You don't need a dedicated meditation room. Just a consistent spot:\n"
            '- A comfortable chair or cushion\n'
            '- Reduced visual distractions (face a wall or window)\n'
            '- Optional: gentle ambient sounds (white noise, nature sounds)\n\n'
            '### Set Reminders\n'
            "Use HeartBox's breathing and meditation features to track your sessions. "
            'Seeing your practice history builds motivation to keep going.\n\n'
            '## Common Obstacles & Solutions\n\n'
            '### "My mind keeps wandering"\n'
            "This is completely normal! Meditation isn't about eliminating thoughts — "
            'it\'s about practicing the action of "noticing thoughts drift, then bringing attention back." '
            "Each time you bring your attention back, it's like doing a mental sit-up.\n\n"
            '### "I don\'t have time"\n'
            'If you have time to scroll your phone for 3 minutes, you have time to breathe. '
            'Try a few deep breaths while waiting for an elevator, riding a bus, or during a break.\n\n'
            '### "I don\'t feel any effect"\n'
            'The effects of breathing practice are gradual, typically taking 2-4 weeks to notice. '
            'Track your practice frequency and duration — review after a month to see your progress.\n\n'
            '## 30-Day Challenge\n\n'
            'Try doing at least one breathing or meditation session every day for 30 consecutive days. '
            "It doesn't need to be long — 2 minutes is enough. The key is \"doing it every day.\" "
            'Track your progress in HeartBox\'s session history!'
        ),
        content_ja=(
            '## なぜ「習慣化」が必要？\n\n'
            '研究によると、瞑想と呼吸エクササイズの効果は一回のセッションの長さではなく、'
            '継続性から生まれます。'
            '毎日3分を1ヶ月続ける方が、たまに30分やるよりも効果的です。\n\n'
            '## 小さく始める\n\n'
            '### 2〜3分ルール\n'
            '最初から20分の目標を設定しないでください。2〜3分から始めて、'
            '脳に「これは簡単なこと」と学ばせましょう。'
            '1週間続けると、自然と時間を延ばしたくなります。\n\n'
            '### 習慣スタッキング\n'
            '呼吸練習を既存の習慣に紐付けましょう：\n'
            '- 朝の歯磨き後 → 3分の呼吸エクササイズ\n'
            '- 昼食前 → 1分のボックス呼吸\n'
            '- 就寝前にスマホを置いた後 → 4-7-8呼吸法\n\n'
            '新しい習慣を古い習慣にリンクさせると、成功率が大幅に上がります。\n\n'
            '## 環境づくり\n\n'
            '### 練習スペースを作る\n'
            '専用の瞑想室は必要ありません。固定の場所があれば十分です：\n'
            '- 快適な椅子またはクッション\n'
            '- 視覚的な気を散らすものを減らす（壁や窓に向かう）\n'
            '- オプション：穏やかな環境音（ホワイトノイズ、自然音）\n\n'
            '### リマインダーを設定\n'
            'HeartBoxの呼吸と瞑想機能を使ってセッションを記録しましょう。'
            '練習履歴を見ることで、続けるモチベーションが高まります。\n\n'
            '## よくある障害と克服法\n\n'
            '### 「心がさまよってしまう」\n'
            'これは完全に普通のことです！瞑想は思考をなくすことではなく、'
            '「思考がさまよったことに気づいて、注意を戻す」という動作を練習することです。'
            '注意を戻すたびに、メンタルの腹筋運動をしているようなものです。\n\n'
            '### 「時間がない」\n'
            'スマホを3分スクロールする時間があるなら、呼吸する時間もあります。'
            'エレベーター待ち、バスに乗っている時、休憩中に深呼吸を試してみてください。\n\n'
            '### 「効果を感じない」\n'
            '呼吸練習の効果は徐々に現れ、通常2〜4週間かかります。'
            '練習の頻度と時間を記録し、1ヶ月後に振り返ると進歩が見えるでしょう。\n\n'
            '## 30日チャレンジ\n\n'
            '30日間連続で、毎日少なくとも1回の呼吸または瞑想セッションを試してみてください。'
            '長くなくて大丈夫です — 2分で十分です。大切なのは「毎日やること」。'
            'HeartBoxのセッション履歴で進捗を追跡しましょう！'
        ),
        category='mindfulness',
        reading_time=5,
        source='Atomic Habits / HeartBox',
        course=course,
        lesson_order=3,
    )


def reverse_seed(apps, schema_editor):
    Course = apps.get_model('api', 'Course')
    PsychoArticle = apps.get_model('api', 'PsychoArticle')
    # Remove articles and course
    PsychoArticle.objects.filter(
        title_en__in=[
            'The Science of Breathing Techniques',
            'The Science and Benefits of Meditation',
            'Building a Daily Breathing & Meditation Habit',
        ]
    ).delete()
    Course.objects.filter(title_en='Breathing & Meditation').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0027_seed_courses'),
    ]

    operations = [
        migrations.RunPython(seed_breathing_course, reverse_seed),
    ]
