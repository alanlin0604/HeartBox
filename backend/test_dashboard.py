"""
Test dashboard functionality using Django shell.
Run: python manage.py shell < test_dashboard.py
"""
from django.contrib.auth import get_user_model
from api.models import DashboardLayout, UserMetric
from api.services.dashboard_service import get_default_layout, get_widget_data

User = get_user_model()

print("=" * 60)
print("Dashboard API Test")
print("=" * 60)

# Get or create test user
user, created = User.objects.get_or_create(
    username='test_dashboard',
    defaults={'email': 'test@dashboard.com'}
)
if created:
    user.set_password('test123')
    user.save()
    print(f"\n✓ Created test user: {user.username}")
else:
    print(f"\n✓ Using existing user: {user.username}")

# Test 1: Default layout
print("\n1. Testing get_default_layout()...")
default_layout = get_default_layout()
print(f"   ✓ Default layout has {len(default_layout['widgets'])} widgets")

# Test 2: Create DashboardLayout
print("\n2. Creating DashboardLayout...")
layout, created = DashboardLayout.objects.update_or_create(
    user=user,
    defaults={'layout_config': default_layout}
)
print(f"   ✓ Layout {'created' if created else 'updated'}")

# Test 3: Create UserMetric
print("\n3. Creating UserMetric...")
metric, created = UserMetric.objects.update_or_create(
    user=user,
    metric_type='daily_entries',
    defaults={'target_value': 7.0, 'current_value': 0.0}
)
print(f"   ✓ Metric {'created' if created else 'updated'}: {metric.metric_type}")

# Test 4: Get widget data
print("\n4. Testing widget data...")
widgets = ['streak', 'mood_trends', 'habit_checkin']
for widget_id in widgets:
    data = get_widget_data(user, widget_id)
    print(f"   ✓ {widget_id}: {list(data.keys())}")

print("\n" + "=" * 60)
print("All tests passed! ✓")
print("=" * 60)
