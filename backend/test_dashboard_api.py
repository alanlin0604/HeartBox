"""
Simple script to test dashboard API endpoints.
Run: python test_dashboard_api.py
"""
import os
import sys
import django

# Setup Django
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from api.models import DashboardLayout, UserMetric, JournalStreak, MoodNote
from api.services.dashboard_service import (
    get_default_layout,
    get_widget_data,
    update_metric_current_value
)

User = get_user_model()

def test_dashboard_service():
    """Test dashboard service functions."""
    print("=" * 60)
    print("Testing Dashboard Service Functions")
    print("=" * 60)

    # Get or create test user
    user, created = User.objects.get_or_create(
        username='test_dashboard_user',
        defaults={
            'email': 'test@dashboard.com',
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"✓ Created test user: {user.username}")
    else:
        print(f"✓ Using existing test user: {user.username}")

    # Test 1: Get default layout
    print("\n1. Testing get_default_layout()...")
    default_layout = get_default_layout()
    assert 'widgets' in default_layout
    assert len(default_layout['widgets']) == 6
    print(f"   ✓ Default layout has {len(default_layout['widgets'])} widgets")

    # Test 2: Create DashboardLayout
    print("\n2. Testing DashboardLayout model...")
    layout, created = DashboardLayout.objects.update_or_create(
        user=user,
        defaults={'layout_config': default_layout}
    )
    print(f"   ✓ DashboardLayout {'created' if created else 'updated'} for {user.username}")

    # Test 3: Create UserMetric
    print("\n3. Testing UserMetric model...")
    metric, created = UserMetric.objects.update_or_create(
        user=user,
        metric_type='daily_entries',
        defaults={
            'target_value': 7.0,
            'current_value': 0.0
        }
    )
    print(f"   ✓ UserMetric {'created' if created else 'updated'}: {metric.metric_type}")

    # Test 4: Update metric current value
    print("\n4. Testing update_metric_current_value()...")
    current_value = update_metric_current_value(user, 'daily_entries')
    print(f"   ✓ Current value for daily_entries: {current_value}")

    # Test 5: Get widget data - streak
    print("\n5. Testing get_widget_data('streak')...")
    streak_data = get_widget_data(user, 'streak')
    assert 'current_streak' in streak_data
    assert 'longest_streak' in streak_data
    assert 'total_entries' in streak_data
    print(f"   ✓ Streak data: {streak_data}")

    # Test 6: Get widget data - mood_trends
    print("\n6. Testing get_widget_data('mood_trends')...")
    mood_data = get_widget_data(user, 'mood_trends')
    assert 'dates' in mood_data
    assert 'mood_scores' in mood_data
    assert len(mood_data['dates']) == 7
    print(f"   ✓ Mood trends data: {len(mood_data['dates'])} days")

    # Test 7: Get widget data - habit_checkin
    print("\n7. Testing get_widget_data('habit_checkin')...")
    habit_data = get_widget_data(user, 'habit_checkin')
    assert 'habits' in habit_data
    assert 'completed_count' in habit_data
    assert 'total_count' in habit_data
    print(f"   ✓ Habit check-in data: {habit_data['completed_count']}/{habit_data['total_count']} completed")

    # Test 8: Get widget data - on_this_day
    print("\n8. Testing get_widget_data('on_this_day')...")
    memory_data = get_widget_data(user, 'on_this_day')
    assert 'memories' in memory_data
    assert 'count' in memory_data
    print(f"   ✓ On this day: {memory_data['count']} memories found")

    # Test 9: Get widget data - ai_suggestions
    print("\n9. Testing get_widget_data('ai_suggestions')...")
    ai_data = get_widget_data(user, 'ai_suggestions')
    assert 'suggestions' in ai_data
    assert 'count' in ai_data
    print(f"   ✓ AI suggestions: {ai_data['count']} suggestions")

    # Test 10: Get widget data - sleep_stats
    print("\n10. Testing get_widget_data('sleep_stats')...")
    sleep_data = get_widget_data(user, 'sleep_stats')
    assert 'dates' in sleep_data
    assert 'hours' in sleep_data
    print(f"   ✓ Sleep stats: {sleep_data['record_count']} records")

    print("\n" + "=" * 60)
    print("All tests passed! ✓")
    print("=" * 60)


def test_models():
    """Test model creation and validation."""
    print("\n" + "=" * 60)
    print("Testing Dashboard Models")
    print("=" * 60)

    user = User.objects.filter(username='test_dashboard_user').first()
    if not user:
        print("✗ Test user not found. Run test_dashboard_service() first.")
        return

    # Test DashboardLayout
    print("\n1. Testing DashboardLayout model...")
    layout = DashboardLayout.objects.filter(user=user).first()
    if layout:
        print(f"   ✓ Layout exists for {user.username}")
        print(f"   - Widgets count: {len(layout.layout_config.get('widgets', []))}")
        print(f"   - Last updated: {layout.updated_at}")
    else:
        print("   ✗ No layout found")

    # Test UserMetric
    print("\n2. Testing UserMetric model...")
    metrics = UserMetric.objects.filter(user=user)
    print(f"   ✓ Found {metrics.count()} metrics")
    for metric in metrics:
        progress = (metric.current_value / metric.target_value * 100) if metric.target_value > 0 else 0
        print(f"   - {metric.metric_type}: {metric.current_value}/{metric.target_value} ({progress:.1f}%)")

    print("\n" + "=" * 60)
    print("Model tests completed! ✓")
    print("=" * 60)


if __name__ == '__main__':
    try:
        test_dashboard_service()
        test_models()
    except Exception as e:
        print(f"\n✗ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
