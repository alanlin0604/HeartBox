"""
測試睡眠分析功能

執行方式：
cd backend
venv/Scripts/python.exe test_sleep_analysis.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moodnotes_pro.settings')
django.setup()

from datetime import datetime, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from api.models import DailySleep, MoodNote
from api.services.sleep_analysis import (
    calculate_quality_score,
    identify_sleep_pattern,
    analyze_sleep_mood_correlation,
    analyze_sleep_stress_correlation,
    get_sleep_statistics,
    identify_sleep_issues,
    generate_sleep_recommendations,
)

User = get_user_model()


def test_calculate_quality_score():
    """測試品質分數計算"""
    print("\n===== 測試品質分數計算 =====")

    # 完美睡眠（7.5h，深度睡眠22%，REM 22%）
    score1 = calculate_quality_score(7.5, 100, 150, 100)  # 總350分鐘
    print(f"完美睡眠分數: {score1}/100")

    # 睡眠不足
    score2 = calculate_quality_score(5.5, None, None, None)
    print(f"睡眠不足分數: {score2}/100")

    # 睡眠過多
    score3 = calculate_quality_score(11, None, None, None)
    print(f"睡眠過多分數: {score3}/100")

    assert 80 <= score1 <= 100, "完美睡眠分數應該很高"
    assert score2 < 50, "睡眠不足分數應該較低"
    print("[PASS] 品質分數計算測試通過")


def test_identify_sleep_pattern():
    """測試睡眠模式識別"""
    print("\n===== 測試睡眠模式識別 =====")

    # 獲取或建立測試使用者
    user, _ = User.objects.get_or_create(username='test_sleep_user', email='test@example.com')

    # 清理舊資料
    DailySleep.objects.filter(user=user).delete()

    # 建立早睡早起的記錄（10點睡，6點起）
    import pytz
    taipei_tz = pytz.timezone('Asia/Taipei')

    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        bedtime = taipei_tz.localize(datetime.combine(date, datetime.strptime("22:00", "%H:%M").time()))
        wake_time = taipei_tz.localize(datetime.combine(date + timedelta(days=1), datetime.strptime("06:00", "%H:%M").time()))

        DailySleep.objects.create(
            user=user,
            date=date,
            sleep_hours=8.0,
            sleep_quality=4,
            bedtime=bedtime,
            wake_time=wake_time
        )

    pattern = identify_sleep_pattern(bedtime, wake_time, user, days=7)
    print(f"早睡早起模式: {pattern}")

    # Debug: 檢查最近的睡眠記錄
    recent = DailySleep.objects.filter(user=user).order_by('-date')[:3]
    for s in recent:
        print(f"  - Date: {s.date}, Bedtime: {s.bedtime}, Wake: {s.wake_time}")

    assert pattern == 'early_bird', f"應識別為 early_bird，但得到 {pattern}"

    # 清理並建立晚睡晚起的記錄（1點睡，9點起）
    DailySleep.objects.filter(user=user).delete()

    for i in range(7):
        date = timezone.now().date() - timedelta(days=i)
        bedtime = taipei_tz.localize(datetime.combine(date + timedelta(days=1), datetime.strptime("01:00", "%H:%M").time()))
        wake_time = taipei_tz.localize(datetime.combine(date + timedelta(days=1), datetime.strptime("09:00", "%H:%M").time()))

        DailySleep.objects.create(
            user=user,
            date=date,
            sleep_hours=8.0,
            sleep_quality=4,
            bedtime=bedtime,
            wake_time=wake_time
        )

    pattern = identify_sleep_pattern(bedtime, wake_time, user, days=7)
    print(f"晚睡晚起模式: {pattern}")
    assert pattern == 'night_owl', f"應識別為 night_owl，但得到 {pattern}"

    print("[PASS] 睡眠模式識別測試通過")


def test_sleep_statistics():
    """測試睡眠統計"""
    print("\n===== 測試睡眠統計 =====")

    user, _ = User.objects.get_or_create(username='test_sleep_user', email='test@example.com')
    DailySleep.objects.filter(user=user).delete()

    # 建立30天的睡眠記錄（平均6.5小時，略有不足）
    import pytz
    taipei_tz = pytz.timezone('Asia/Taipei')

    for i in range(30):
        date = timezone.now().date() - timedelta(days=i)
        sleep_hours = 6.5 + (i % 3) * 0.5  # 6.5, 7, 7.5 循環

        bedtime = taipei_tz.localize(datetime.combine(date, datetime.strptime("23:00", "%H:%M").time()))
        wake_time = taipei_tz.localize(datetime.combine(date + timedelta(days=1), datetime.strptime("07:00", "%H:%M").time()))

        DailySleep.objects.create(
            user=user,
            date=date,
            sleep_hours=sleep_hours,
            sleep_quality=3,
            bedtime=bedtime,
            wake_time=wake_time,
            deep_sleep_minutes=80,
            light_sleep_minutes=180,
            rem_sleep_minutes=80
        )

    stats = get_sleep_statistics(user, days=30)
    print(f"統計資料: {stats}")

    assert stats['total_records'] == 30
    assert stats['avg_sleep_hours'] is not None
    assert stats['sleep_debt'] is not None

    print("[PASS] 睡眠統計測試通過")


def test_sleep_issues():
    """測試睡眠問題識別"""
    print("\n===== 測試睡眠問題識別 =====")

    user, _ = User.objects.get_or_create(username='test_sleep_user', email='test@example.com')
    DailySleep.objects.filter(user=user).delete()

    # 建立睡眠不足的記錄（連續14天都只睡5小時）
    for i in range(14):
        date = timezone.now().date() - timedelta(days=i)
        DailySleep.objects.create(
            user=user,
            date=date,
            sleep_hours=5.0,
            sleep_quality=2
        )

    issues = identify_sleep_issues(user, days=14)
    print(f"識別的問題: {issues}")

    assert issues['has_issues'] is True
    assert len(issues['issues']) > 0

    # 檢查是否識別到失眠或睡眠不足
    issue_types = {issue['type'] for issue in issues['issues']}
    assert 'insomnia' in issue_types or 'insufficient_sleep' in issue_types

    print("[PASS] 睡眠問題識別測試通過")


def test_recommendations():
    """測試建議生成"""
    print("\n===== 測試建議生成 =====")

    user, _ = User.objects.get_or_create(username='test_sleep_user', email='test@example.com')
    DailySleep.objects.filter(user=user).delete()

    # 建立不規律的睡眠記錄
    for i in range(14):
        date = timezone.now().date() - timedelta(days=i)
        sleep_hours = 6.0 if i % 2 == 0 else 8.5  # 不規律

        DailySleep.objects.create(
            user=user,
            date=date,
            sleep_hours=sleep_hours,
            sleep_quality=3
        )

    recommendations = generate_sleep_recommendations(user, days=14)
    print(f"建議數量: {len(recommendations)}")
    print("建議內容:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")

    assert len(recommendations) > 0
    assert len(recommendations) <= 5  # 最多5條

    print("[PASS] 建議生成測試通過")


def test_mood_correlation():
    """測試睡眠與情緒關聯"""
    print("\n===== 測試睡眠與情緒關聯 =====")

    user, _ = User.objects.get_or_create(username='test_sleep_user', email='test@example.com')
    DailySleep.objects.filter(user=user).delete()
    MoodNote.objects.filter(user=user).delete()

    # 建立睡眠記錄 + 對應的情緒記錄
    for i in range(20):
        date = timezone.now().date() - timedelta(days=i)

        # 前10天睡眠充足（>=7h），後10天睡眠不足（<7h）
        if i < 10:
            sleep_hours = 8.0
            sentiment = 0.6  # 正面情緒
        else:
            sleep_hours = 5.5
            sentiment = -0.2  # 負面情緒

        DailySleep.objects.create(
            user=user,
            date=date,
            sleep_hours=sleep_hours,
            sleep_quality=4 if i < 10 else 2
        )

        # 建立對應日期的情緒記錄
        note = MoodNote.objects.create(
            user=user,
            encrypted_content='test',
            sentiment_score=sentiment,
            created_at=timezone.make_aware(datetime.combine(date, datetime.strptime("12:00", "%H:%M").time()))
        )

    correlation = analyze_sleep_mood_correlation(user, days=30)
    print(f"睡眠情緒關聯: {correlation}")

    assert correlation['correlation'] in ['positive', 'negative', 'neutral']
    assert correlation['sample_size'] > 0

    print("[PASS] 睡眠情緒關聯測試通過")


def main():
    """執行所有測試"""
    print("=" * 60)
    print("開始測試睡眠分析功能")
    print("=" * 60)

    try:
        test_calculate_quality_score()
        test_identify_sleep_pattern()
        test_sleep_statistics()
        test_sleep_issues()
        test_recommendations()
        test_mood_correlation()

        print("\n" + "=" * 60)
        print("[PASS] 所有測試通過！")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n[FAIL] 測試失敗: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FAIL] 測試錯誤: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
