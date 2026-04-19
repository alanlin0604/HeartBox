"""
Sleep Analysis Service

提供睡眠週期分析、品質評分、模式識別和關聯分析功能。
"""

from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

from django.db.models import Avg, Count, F, Q, StdDev
from django.utils import timezone

from ..models import DailySleep, MoodNote


def calculate_quality_score(
    sleep_hours: float,
    deep_sleep: Optional[int] = None,
    light_sleep: Optional[int] = None,
    rem_sleep: Optional[int] = None
) -> int:
    """
    計算睡眠品質分數 (0-100)

    評分標準：
    - 睡眠時數 (40%): 7-9 小時得滿分，過少或過多扣分
    - 深度睡眠 (30%): 20-25% 最佳
    - REM 睡眠 (20%): 20-25% 最佳
    - 淺睡眠 (10%): 不超過總時長 50%

    Args:
        sleep_hours: 總睡眠時數
        deep_sleep: 深度睡眠分鐘數
        light_sleep: 淺睡眠分鐘數
        rem_sleep: REM 睡眠分鐘數

    Returns:
        睡眠品質分數 (0-100)
    """
    score = 0

    # 1. 睡眠時數評分 (40 分)
    if 7 <= sleep_hours <= 9:
        score += 40
    elif 6 <= sleep_hours < 7 or 9 < sleep_hours <= 10:
        score += 30
    elif 5 <= sleep_hours < 6 or 10 < sleep_hours <= 11:
        score += 20
    else:
        score += 10

    # 2-4. 睡眠階段評分（需要 deep/light/rem 資料）
    if deep_sleep is not None and light_sleep is not None and rem_sleep is not None:
        total_min = deep_sleep + light_sleep + rem_sleep
        if total_min > 0:
            deep_pct = (deep_sleep / total_min) * 100
            rem_pct = (rem_sleep / total_min) * 100
            light_pct = (light_sleep / total_min) * 100

            # 深度睡眠評分 (30 分)
            if 20 <= deep_pct <= 25:
                score += 30
            elif 15 <= deep_pct < 20 or 25 < deep_pct <= 30:
                score += 20
            else:
                score += 10

            # REM 睡眠評分 (20 分)
            if 20 <= rem_pct <= 25:
                score += 20
            elif 15 <= rem_pct < 20 or 25 < rem_pct <= 30:
                score += 15
            else:
                score += 5

            # 淺睡眠評分 (10 分)
            if light_pct <= 50:
                score += 10
            else:
                score += 5

    return min(100, score)


def _get_hour_from_datetime(dt: datetime) -> float:
    """
    將 datetime 轉換為小時數 (0-24)，考慮跨日情況。

    例如：
    - 23:30 → 23.5
    - 01:30 → 1.5 (凌晨視為次日)

    注意：Django DateTimeField 儲存為 UTC，需轉換回本地時間
    """
    if dt is None:
        return None

    # 轉換為本地時間（台北時區）
    import pytz
    from django.conf import settings

    local_tz = pytz.timezone(settings.TIME_ZONE)
    if timezone.is_aware(dt):
        local_dt = dt.astimezone(local_tz)
    else:
        local_dt = dt

    hour = local_dt.hour + local_dt.minute / 60.0
    return hour


def identify_sleep_pattern(
    bedtime: Optional[datetime],
    wake_time: Optional[datetime],
    user,
    days: int = 7
) -> str:
    """
    識別睡眠模式

    基於最近 N 天的平均入睡和起床時間判斷：
    - early_bird: 平均 bedtime < 23:00, wake_time < 7:00
    - night_owl: 平均 bedtime > 00:30, wake_time > 8:00
    - irregular: 標準差過大（作息不規律）
    - insufficient_data: 資料不足

    Args:
        bedtime: 當前入睡時間
        wake_time: 當前起床時間
        user: 使用者
        days: 分析天數

    Returns:
        睡眠模式字串
    """
    # 查詢最近 N 天的睡眠記錄
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    recent_sleeps = DailySleep.objects.filter(
        user=user,
        date__gte=start_date,
        bedtime__isnull=False,
        wake_time__isnull=False
    ).order_by('-date')

    if recent_sleeps.count() < 3:
        return 'insufficient_data'

    # 計算平均入睡和起床時間（小時）
    bedtimes = []
    wake_times = []

    for sleep in recent_sleeps:
        bedtime_hour = _get_hour_from_datetime(sleep.bedtime)
        wake_time_hour = _get_hour_from_datetime(sleep.wake_time)

        # 將午夜後的入睡時間（0-6點）視為 24+hour（例如凌晨1點=25）
        if bedtime_hour is not None:
            if 0 <= bedtime_hour < 6:
                bedtime_hour += 24
            bedtimes.append(bedtime_hour)

        if wake_time_hour is not None:
            wake_times.append(wake_time_hour)

    if not bedtimes or not wake_times:
        return 'insufficient_data'

    avg_bedtime = sum(bedtimes) / len(bedtimes)
    avg_wake = sum(wake_times) / len(wake_times)

    # 計算標準差（作息規律性）
    if len(bedtimes) > 1:
        bedtime_variance = sum((x - avg_bedtime) ** 2 for x in bedtimes) / len(bedtimes)
        bedtime_std = bedtime_variance ** 0.5

        # 如果入睡時間標準差 > 2 小時，視為不規律
        if bedtime_std > 2.0:
            return 'irregular'

    # 將 24+ 小時轉回 0-24 範圍（例如 25 → 1）
    avg_bedtime_normalized = avg_bedtime if avg_bedtime < 24 else avg_bedtime - 24

    # 判斷模式
    # early_bird: 平均 bedtime < 23:00 (23), wake_time < 7:00 (7)
    if avg_bedtime_normalized < 23 and avg_wake < 7:
        return 'early_bird'

    # night_owl: 平均 bedtime > 00:30 (24.5), wake_time > 8:00 (8)
    if avg_bedtime > 24.5 and avg_wake > 8:
        return 'night_owl'

    # 其他情況視為一般
    return 'regular'


def analyze_sleep_mood_correlation(user, days: int = 30) -> Dict:
    """
    分析睡眠與情緒的關聯

    計算：
    - 睡眠充足日（>=7h）的平均情緒分數
    - 睡眠不足日（<7h）的平均情緒分數
    - 差異值

    Args:
        user: 使用者
        days: 分析天數

    Returns:
        關聯分析結果字典
    """
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    # 獲取睡眠記錄
    sleep_records = DailySleep.objects.filter(
        user=user,
        date__gte=start_date
    ).values('date', 'sleep_hours')

    sleep_dict = {s['date']: s['sleep_hours'] for s in sleep_records}

    # 獲取情緒記錄（使用 sentiment_score）
    mood_records = MoodNote.objects.filter(
        user=user,
        created_at__date__gte=start_date,
        sentiment_score__isnull=False,
        is_deleted=False
    ).values('created_at__date', 'sentiment_score')

    # 計算每日平均情緒
    mood_by_date = {}
    for record in mood_records:
        date = record['created_at__date']
        score = record['sentiment_score']
        if date not in mood_by_date:
            mood_by_date[date] = []
        mood_by_date[date].append(score)

    # 分類：睡眠充足 vs 睡眠不足
    sufficient_moods = []
    insufficient_moods = []

    for date, sleep_hours in sleep_dict.items():
        if date in mood_by_date:
            avg_mood = sum(mood_by_date[date]) / len(mood_by_date[date])
            # 將 sentiment_score (-1 到 1) 轉換為 0-10 分數
            mood_score = (avg_mood + 1) * 5  # -1→0, 0→5, 1→10

            if sleep_hours >= 7:
                sufficient_moods.append(mood_score)
            else:
                insufficient_moods.append(mood_score)

    # 計算平均值
    sufficient_avg = sum(sufficient_moods) / len(sufficient_moods) if sufficient_moods else None
    insufficient_avg = sum(insufficient_moods) / len(insufficient_moods) if insufficient_moods else None

    # 計算差異和相關性
    correlation = 'neutral'
    mood_difference = None

    if sufficient_avg is not None and insufficient_avg is not None:
        mood_difference = sufficient_avg - insufficient_avg

        if mood_difference > 0.5:
            correlation = 'positive'  # 睡眠充足→情緒較好
        elif mood_difference < -0.5:
            correlation = 'negative'  # 睡眠充足→情緒較差（不太可能）

    return {
        'sufficient_sleep_avg_mood': round(sufficient_avg, 1) if sufficient_avg else None,
        'insufficient_sleep_avg_mood': round(insufficient_avg, 1) if insufficient_avg else None,
        'mood_difference': round(mood_difference, 1) if mood_difference else None,
        'correlation': correlation,
        'sample_size': len(sufficient_moods) + len(insufficient_moods)
    }


def analyze_sleep_stress_correlation(user, days: int = 30) -> Dict:
    """
    分析睡眠與壓力的關聯

    類似情緒分析，但使用 stress_index

    Args:
        user: 使用者
        days: 分析天數

    Returns:
        關聯分析結果字典
    """
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    # 獲取睡眠記錄
    sleep_records = DailySleep.objects.filter(
        user=user,
        date__gte=start_date
    ).values('date', 'sleep_hours')

    sleep_dict = {s['date']: s['sleep_hours'] for s in sleep_records}

    # 獲取壓力記錄（使用 stress_index）
    stress_records = MoodNote.objects.filter(
        user=user,
        created_at__date__gte=start_date,
        stress_index__isnull=False,
        is_deleted=False
    ).values('created_at__date', 'stress_index')

    # 計算每日平均壓力
    stress_by_date = {}
    for record in stress_records:
        date = record['created_at__date']
        stress = record['stress_index']
        if date not in stress_by_date:
            stress_by_date[date] = []
        stress_by_date[date].append(stress)

    # 分類：睡眠充足 vs 睡眠不足
    sufficient_stress = []
    insufficient_stress = []

    for date, sleep_hours in sleep_dict.items():
        if date in stress_by_date:
            avg_stress = sum(stress_by_date[date]) / len(stress_by_date[date])

            if sleep_hours >= 7:
                sufficient_stress.append(avg_stress)
            else:
                insufficient_stress.append(avg_stress)

    # 計算平均值
    sufficient_avg = sum(sufficient_stress) / len(sufficient_stress) if sufficient_stress else None
    insufficient_avg = sum(insufficient_stress) / len(insufficient_stress) if insufficient_stress else None

    # 計算差異和相關性
    correlation = 'neutral'
    stress_difference = None

    if sufficient_avg is not None and insufficient_avg is not None:
        stress_difference = insufficient_avg - sufficient_avg

        if stress_difference > 0.5:
            correlation = 'negative'  # 睡眠不足→壓力較高（負相關）
        elif stress_difference < -0.5:
            correlation = 'positive'  # 睡眠不足→壓力較低（不太可能）

    return {
        'sufficient_sleep_avg_stress': round(sufficient_avg, 1) if sufficient_avg else None,
        'insufficient_sleep_avg_stress': round(insufficient_avg, 1) if insufficient_avg else None,
        'stress_difference': round(stress_difference, 1) if stress_difference else None,
        'correlation': correlation,
        'sample_size': len(sufficient_stress) + len(insufficient_stress)
    }


def get_sleep_statistics(user, days: int = 30) -> Dict:
    """
    取得睡眠統計資料

    Args:
        user: 使用者
        days: 分析天數

    Returns:
        睡眠統計字典
    """
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    sleeps = DailySleep.objects.filter(
        user=user,
        date__gte=start_date
    )

    total_records = sleeps.count()

    if total_records == 0:
        return {
            'avg_sleep_hours': None,
            'avg_quality_score': None,
            'most_common_pattern': None,
            'total_records': 0,
            'sleep_debt': None
        }

    # 計算平均睡眠時數
    avg_hours = sleeps.aggregate(Avg('sleep_hours'))['sleep_hours__avg']

    # 計算平均品質分數
    quality_scores = []

    for sleep in sleeps:
        score = calculate_quality_score(
            sleep.sleep_hours,
            sleep.deep_sleep_minutes,
            sleep.light_sleep_minutes,
            sleep.rem_sleep_minutes
        )
        quality_scores.append(score)

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None

    # 計算睡眠模式（使用最近的睡眠記錄分析）
    most_common_pattern = None
    if total_records >= 7:
        # 取得最近的睡眠記錄來判斷當前模式
        latest_sleep = sleeps.filter(bedtime__isnull=False, wake_time__isnull=False).first()
        if latest_sleep:
            most_common_pattern = identify_sleep_pattern(
                latest_sleep.bedtime,
                latest_sleep.wake_time,
                user,
                days=min(days, 14)  # 最多分析14天
            )

    # 計算睡眠債（相對於建議的7小時）
    sleep_debt = None
    if avg_hours is not None:
        sleep_debt = (avg_hours - 7) * days  # 正數=多睡，負數=欠睡

    return {
        'avg_sleep_hours': round(avg_hours, 1) if avg_hours is not None else None,
        'avg_quality_score': round(avg_quality) if avg_quality is not None else None,
        'most_common_pattern': most_common_pattern,
        'total_records': total_records,
        'sleep_debt': round(sleep_debt, 1) if sleep_debt is not None else None
    }


def identify_sleep_issues(user, days: int = 14) -> Dict:
    """
    識別睡眠問題

    檢查：
    - 失眠：連續多日睡眠時數 < 6h
    - 睡眠不足：平均睡眠 < 7h
    - 作息不規律：bedtime 標準差過大
    - 睡眠品質差：平均 quality_score < 60

    Args:
        user: 使用者
        days: 分析天數

    Returns:
        睡眠問題字典
    """
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=days)

    sleeps = DailySleep.objects.filter(
        user=user,
        date__gte=start_date
    ).order_by('-date')

    if sleeps.count() < 3:
        return {
            'has_issues': False,
            'issues': []
        }

    issues = []

    # 1. 檢查失眠（連續3天睡眠<6h）
    consecutive_low = 0
    for sleep in sleeps:
        if sleep.sleep_hours < 6:
            consecutive_low += 1
            if consecutive_low >= 3:
                issues.append({
                    'type': 'insomnia',
                    'severity': 'severe',
                    'description': f'連續 {consecutive_low} 天睡眠不足 6 小時'
                })
                break
        else:
            consecutive_low = 0

    # 2. 檢查平均睡眠不足
    avg_hours = sleeps.aggregate(Avg('sleep_hours'))['sleep_hours__avg']
    if avg_hours and avg_hours < 7:
        severity = 'severe' if avg_hours < 6 else 'moderate'
        issues.append({
            'type': 'insufficient_sleep',
            'severity': severity,
            'description': f'平均睡眠時間僅 {avg_hours:.1f} 小時'
        })

    # 3. 檢查作息不規律
    bedtimes = []
    for sleep in sleeps:
        if sleep.bedtime:
            hour = _get_hour_from_datetime(sleep.bedtime)
            if hour is not None:
                if 0 <= hour < 6:
                    hour += 24
                bedtimes.append(hour)

    if len(bedtimes) > 2:
        avg_bedtime = sum(bedtimes) / len(bedtimes)
        variance = sum((x - avg_bedtime) ** 2 for x in bedtimes) / len(bedtimes)
        std = variance ** 0.5

        if std > 2.0:
            issues.append({
                'type': 'irregular_schedule',
                'severity': 'moderate',
                'description': f'入睡時間變化大（標準差 {std:.1f} 小時）'
            })

    # 4. 檢查睡眠品質差
    quality_scores = []
    for sleep in sleeps:
        score = calculate_quality_score(
            sleep.sleep_hours,
            sleep.deep_sleep_minutes,
            sleep.light_sleep_minutes,
            sleep.rem_sleep_minutes
        )
        quality_scores.append(score)

    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else None
    if avg_quality and avg_quality < 60:
        severity = 'severe' if avg_quality < 40 else 'moderate'
        issues.append({
            'type': 'poor_quality',
            'severity': severity,
            'description': f'平均睡眠品質分數僅 {avg_quality:.0f} 分'
        })

    return {
        'has_issues': len(issues) > 0,
        'issues': issues
    }


def generate_sleep_recommendations(user, days: int = 14) -> List[str]:
    """
    生成個人化睡眠建議

    基於：
    - 識別的睡眠問題
    - 睡眠模式
    - 睡眠品質分數

    Args:
        user: 使用者
        days: 分析天數

    Returns:
        建議列表
    """
    recommendations = []

    # 獲取睡眠問題
    issues_data = identify_sleep_issues(user, days)
    issues = issues_data.get('issues', [])

    # 獲取統計資料
    stats = get_sleep_statistics(user, days)

    # 根據問題類型給建議
    issue_types = {issue['type'] for issue in issues}

    if 'insomnia' in issue_types or 'insufficient_sleep' in issue_types:
        recommendations.extend([
            '嘗試每天固定時間上床睡覺，建立規律作息',
            '睡前 1-2 小時避免使用電子產品（藍光會影響褪黑激素分泌）',
            '確保臥室環境舒適（溫度約 18-22°C，保持安靜與黑暗）'
        ])

    if 'irregular_schedule' in issue_types:
        recommendations.extend([
            '建立固定的睡眠時間表，包括週末',
            '白天多接觸自然光，幫助調節生理時鐘'
        ])

    if 'poor_quality' in issue_types:
        recommendations.extend([
            '睡前進行輕度運動或冥想，幫助放鬆身心',
            '避免睡前攝取咖啡因（至少睡前 6 小時）和酒精',
            '考慮增加深度睡眠：規律運動、減少壓力'
        ])

    # 根據睡眠模式給建議
    if stats['most_common_pattern'] == 'night_owl':
        recommendations.append('如果是夜貓子，嘗試逐步提前 15-30 分鐘入睡時間')

    # 根據睡眠債給建議
    if stats['sleep_debt'] is not None and stats['sleep_debt'] < -7:  # 欠睡超過7小時
        recommendations.append('建議週末適度補眠，但不要超過平時起床時間 2 小時')

    # 如果沒有問題，給予鼓勵
    if not issues:
        recommendations.append('您的睡眠狀況良好！繼續保持規律作息')

    # 限制建議數量（最多5條）
    return recommendations[:5]
