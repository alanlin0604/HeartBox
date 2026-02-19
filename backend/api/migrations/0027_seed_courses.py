# Data migration: Create 4 courses and assign articles to them

from django.db import migrations


def seed_courses(apps, schema_editor):
    Course = apps.get_model('api', 'Course')
    PsychoArticle = apps.get_model('api', 'PsychoArticle')

    # Create 4 courses
    courses_data = [
        {
            'title_zh': 'CBT 基礎入門',
            'title_en': 'CBT Fundamentals',
            'title_ja': 'CBT基礎入門',
            'description_zh': '學習認知行為治療的核心概念，掌握改變思維模式的技巧。',
            'description_en': 'Learn core CBT concepts and master techniques to change thinking patterns.',
            'description_ja': '認知行動療法の核心的な概念を学び、思考パターンを変える技術を習得します。',
            'category': 'cbt',
            'icon_emoji': '\U0001f9e0',
            'order': 1,
        },
        {
            'title_zh': '壓力緩解工具箱',
            'title_en': 'Stress Relief Toolbox',
            'title_ja': 'ストレス解消ツールボックス',
            'description_zh': '實用的壓力管理技巧，從呼吸法到漸進式肌肉放鬆。',
            'description_en': 'Practical stress management techniques, from breathing to progressive muscle relaxation.',
            'description_ja': '呼吸法から漸進的筋弛緩法まで、実用的なストレス管理テクニック。',
            'category': 'stress',
            'icon_emoji': '\U0001f33f',
            'order': 2,
        },
        {
            'title_zh': '情緒智慧',
            'title_en': 'Emotional Intelligence',
            'title_ja': '感情的知性',
            'description_zh': '認識、理解並管理自己的情緒，建立更健康的人際關係。',
            'description_en': 'Recognize, understand and manage your emotions for healthier relationships.',
            'description_ja': '自分の感情を認識し、理解し、管理して、より健康的な人間関係を築きます。',
            'category': 'emotion',
            'icon_emoji': '\u2764\ufe0f',
            'order': 3,
        },
        {
            'title_zh': '正念與身心健康',
            'title_en': 'Mindfulness & Wellbeing',
            'title_ja': 'マインドフルネスとウェルビーイング',
            'description_zh': '透過正念冥想、自我慈悲和感恩練習，提升身心健康。',
            'description_en': 'Enhance wellbeing through mindfulness meditation, self-compassion and gratitude practices.',
            'description_ja': 'マインドフルネス瞑想、セルフコンパッション、感謝の実践でウェルビーイングを向上。',
            'category': 'mindfulness',
            'icon_emoji': '\U0001f9d8',
            'order': 4,
        },
    ]

    created_courses = []
    for data in courses_data:
        course = Course.objects.create(**data)
        created_courses.append(course)

    # Map articles to courses by title_en
    # Course 1: CBT Fundamentals
    cbt_articles = [
        ('Introduction to Cognitive Distortions', 1),
        ('How to Reframe Negative Thoughts', 2),
        ('Behavioral Activation for Depression', 3),
    ]

    # Course 2: Stress Relief Toolbox
    stress_articles = [
        ('4-7-8 Breathing Technique', 1),
        ('5-4-3-2-1 Grounding Exercise', 2),
        ('Progressive Muscle Relaxation', 3),
        ('Stress Management Strategies', 4),
        ('Building Psychological Resilience', 5),
    ]

    # Course 3: Emotional Intelligence
    emotion_articles = [
        ('Emotion Identification and Acceptance', 1),
        ('Understanding Anxiety', 2),
        ('Anger Management Techniques', 3),
        ('Social Connection and Mental Health', 4),
    ]

    # Course 4: Mindfulness & Wellbeing
    mindfulness_articles = [
        ('Introduction to Mindfulness Meditation', 1),
        ('Self-Compassion Practice', 2),
        ('The Science of Gratitude Journaling', 3),
        ('Sleep Hygiene Guide', 4),
    ]

    course_map = [
        (created_courses[0], cbt_articles),
        (created_courses[1], stress_articles),
        (created_courses[2], emotion_articles),
        (created_courses[3], mindfulness_articles),
    ]

    for course, articles in course_map:
        for title_en, lesson_order in articles:
            try:
                article = PsychoArticle.objects.get(title_en=title_en)
                article.course = course
                article.lesson_order = lesson_order
                article.save()
            except PsychoArticle.DoesNotExist:
                pass  # Article not found, skip


def reverse_seed(apps, schema_editor):
    Course = apps.get_model('api', 'Course')
    PsychoArticle = apps.get_model('api', 'PsychoArticle')
    PsychoArticle.objects.filter(course__isnull=False).update(course=None, lesson_order=0)
    Course.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0026_wellness_course_progress'),
    ]

    operations = [
        migrations.RunPython(seed_courses, reverse_seed),
    ]
