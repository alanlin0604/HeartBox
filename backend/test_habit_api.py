"""
Habit Tracker API Test Script
"""

import os
import sys
import django

# Fix Windows console encoding
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moodnotes_pro.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from api.models import Habit, HabitLog, MoodNote
from datetime import timedelta

User = get_user_model()


def test_habit_tracker():
    print("\n=== 習慣追蹤器 API 測試 ===\n")

    # 1. 建立測試用戶
    user, created = User.objects.get_or_create(
        username='test_habit_user',
        defaults={'email': 'test_habit@example.com'}
    )
    if created:
        user.set_password('testpass123')
        user.save()
    print(f"✓ 測試用戶: {user.username}")

    # 2. 建立習慣
    habit1 = Habit.objects.create(
        user=user,
        name='每日運動',
        description='每天至少運動30分鐘',
        category='健康',
        color='#22c55e',
        icon='dumbbell',
        target_frequency='daily',
        target_count=1
    )
    print(f"✓ 建立習慣: {habit1.name}")

    habit2 = Habit.objects.create(
        user=user,
        name='閱讀',
        description='每週閱讀3次',
        category='學習',
        color='#3b82f6',
        icon='book',
        target_frequency='weekly',
        target_count=3
    )
    print(f"✓ 建立習慣: {habit2.name}")

    # 3. 建立打卡記錄
    today = timezone.now().date()
    for i in range(7):
        date = today - timedelta(days=i)
        HabitLog.objects.get_or_create(
            habit=habit1,
            user=user,
            date=date,
            defaults={'note': f'第 {7-i} 天完成'}
        )
    print(f"✓ 建立打卡記錄: 連續7天")

    # 4. 測試 Serializer - 計算連續天數
    from api.serializers import HabitSerializer
    from rest_framework.request import Request
    from rest_framework.test import APIRequestFactory

    factory = APIRequestFactory()
    request = factory.get('/')
    request.user = user

    serializer = HabitSerializer(habit1, context={'request': request})
    data = serializer.data

    print(f"\n--- Habit Serializer 測試 ---")
    print(f"習慣名稱: {data['name']}")
    print(f"連續天數: {data['streak']} 天")
    print(f"完成率 (30天): {data['completion_rate']}%")

    # 5. 建立一些情緒記錄來測試關聯分析
    print(f"\n--- 建立情緒記錄 ---")
    for i in range(7):
        date = today - timedelta(days=i)
        note = MoodNote.objects.create(
            user=user,
            encrypted_content='test',
            sentiment_score=0.8,  # 打卡日的情緒較好
        )
        note.created_at = timezone.make_aware(
            timezone.datetime.combine(date, timezone.datetime.min.time())
        )
        note.save(update_fields=['created_at'])
    print(f"✓ 建立情緒記錄: 7天 (打卡日)")

    # 非打卡日的情緒記錄
    for i in range(8, 15):
        date = today - timedelta(days=i)
        note = MoodNote.objects.create(
            user=user,
            encrypted_content='test',
            sentiment_score=0.3,  # 未打卡日的情緒較差
        )
        note.created_at = timezone.make_aware(
            timezone.datetime.combine(date, timezone.datetime.min.time())
        )
        note.save(update_fields=['created_at'])
    print(f"✓ 建立情緒記錄: 7天 (未打卡日)")

    # 6. 測試情緒關聯分析
    print(f"\n--- 習慣與情緒關聯分析 ---")
    from django.db.models import Avg

    end_date = today
    start_date = today - timedelta(days=30)

    completed_dates = HabitLog.objects.filter(
        habit=habit1,
        date__gte=start_date,
        date__lte=end_date
    ).values_list('date', flat=True)

    completed_mood = MoodNote.objects.filter(
        user=user,
        created_at__date__in=completed_dates
    ).aggregate(avg=Avg('sentiment_score'))

    not_completed_mood = MoodNote.objects.filter(
        user=user,
        created_at__date__gte=start_date,
        created_at__date__lte=end_date
    ).exclude(
        created_at__date__in=completed_dates
    ).aggregate(avg=Avg('sentiment_score'))

    print(f"打卡日平均情緒: {completed_mood['avg']:.2f}")
    print(f"未打卡日平均情緒: {not_completed_mood['avg']:.2f}")
    print(f"情緒差異: {(completed_mood['avg'] - not_completed_mood['avg']):.2f}")

    # 7. 測試 Calendar API
    print(f"\n--- Calendar API 測試 ---")
    logs = HabitLog.objects.filter(
        habit=habit1,
        date__gte=start_date,
        date__lte=end_date
    ).values('date')

    completed_dates_list = [log['date'].isoformat() for log in logs]
    print(f"打卡日期列表: {completed_dates_list[:5]}...")

    # 8. 統計資訊
    print(f"\n=== 統計資訊 ===")
    print(f"總習慣數: {Habit.objects.filter(user=user).count()}")
    print(f"活躍習慣數: {Habit.objects.filter(user=user, is_active=True).count()}")
    print(f"總打卡記錄: {HabitLog.objects.filter(user=user).count()}")
    print(f"今日打卡數: {HabitLog.objects.filter(user=user, date=today).count()}")

    print("\n✓ 所有測試完成！\n")


if __name__ == '__main__':
    test_habit_tracker()
