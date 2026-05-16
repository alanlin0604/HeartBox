"""Dashboard layout, custom user metrics, notifications, subscription, push.

Extracted from views/__init__.py. Re-exported for backward compatibility.

Note: ``send_push_notification`` lives here because PushSubscriptionView and
push delivery share the same model. ``api.tasks`` imports it via
``from api.views import send_push_notification`` — the re-export at the
bottom of views/__init__.py preserves that path.
"""

import os

import rest_framework.pagination
from django.conf import settings

from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_control

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from ..models import (
    DashboardLayout, Notification, NotificationPreference, PushSubscription,
    SubscriptionPlan, UserMetric, UserSubscription,
)
from ..serializers import (
    DashboardLayoutSerializer, NotificationPreferenceSerializer,
    NotificationSerializer, SubscriptionPlanSerializer, UserMetricSerializer,
    UserSubscriptionSerializer,
)

from . import error_response, logger


class DashboardLayoutView(APIView):
    """
    GET: Retrieve user's dashboard layout (or default if not set)
    PUT: Update user's dashboard layout
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get dashboard layout for current user."""
        try:
            layout = DashboardLayout.objects.get(user=request.user)
            serializer = DashboardLayoutSerializer(layout)
            return Response(serializer.data)
        except DashboardLayout.DoesNotExist:
            # Return default layout if user hasn't customized yet
            from ..services.dashboard_service import get_default_layout
            default_layout = get_default_layout()
            return Response({
                'layout_config': default_layout,
                'updated_at': None
            })

    def put(self, request):
        """Update or create dashboard layout for current user."""
        try:
            layout = DashboardLayout.objects.get(user=request.user)
            serializer = DashboardLayoutSerializer(layout, data=request.data, partial=True)
        except DashboardLayout.DoesNotExist:
            serializer = DashboardLayoutSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DashboardLayoutResetView(APIView):
    """POST: Reset dashboard layout to default."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Reset dashboard layout to default configuration."""
        from ..services.dashboard_service import get_default_layout

        default_layout = get_default_layout()

        layout, created = DashboardLayout.objects.update_or_create(
            user=request.user,
            defaults={'layout_config': default_layout}
        )

        serializer = DashboardLayoutSerializer(layout)
        return Response({
            'message': 'Dashboard layout reset to default',
            'data': serializer.data
        })


class UserMetricListView(APIView):
    """
    GET: List all custom metrics for the user
    POST: Create a new custom metric
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Get all custom metrics for current user."""
        metrics = UserMetric.objects.filter(user=request.user)
        serializer = UserMetricSerializer(metrics, many=True)

        return Response({
            'metrics': serializer.data
        })

    def post(self, request):
        """Create a new custom metric."""
        serializer = UserMetricSerializer(data=request.data)

        if serializer.is_valid():
            try:
                # Calculate initial current_value
                from ..services.dashboard_service import update_metric_current_value
                metric_type = serializer.validated_data['metric_type']
                current_value = update_metric_current_value(request.user, metric_type)

                # Save with calculated current_value
                metric = serializer.save(
                    user=request.user,
                    current_value=current_value
                )

                response_serializer = UserMetricSerializer(metric)
                return Response(response_serializer.data, status=status.HTTP_201_CREATED)

            except Exception as e:
                # Handle unique_together constraint violation
                if 'unique' in str(e).lower():
                    return Response(
                        {'error': 'You already have a metric of this type'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                raise

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserMetricDetailView(APIView):
    """
    PATCH: Update a specific metric
    DELETE: Delete a specific metric
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, request, pk):
        """Get metric and verify ownership."""
        try:
            return UserMetric.objects.get(pk=pk, user=request.user)
        except UserMetric.DoesNotExist:
            return None

    def patch(self, request, pk):
        """Update a custom metric (target_value or is_active)."""
        metric = self.get_object(request, pk)
        if not metric:
            return Response(
                {'error': 'Metric not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = UserMetricSerializer(metric, data=request.data, partial=True)

        if serializer.is_valid():
            # Recalculate current_value if needed
            from ..services.dashboard_service import update_metric_current_value
            current_value = update_metric_current_value(request.user, metric.metric_type)

            serializer.save(current_value=current_value)
            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        """Delete a custom metric."""
        metric = self.get_object(request, pk)
        if not metric:
            return Response(
                {'error': 'Metric not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        metric.delete()
        return Response(
            {'message': 'Metric deleted successfully'},
            status=status.HTTP_204_NO_CONTENT
        )


class DashboardWidgetDataView(APIView):
    """GET: Fetch data for a specific widget."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, widget_id):
        """Get data for a specific widget."""
        from ..services.dashboard_service import get_widget_data

        # Validate widget_id
        valid_widgets = [
            'streak', 'mood_trends', 'on_this_day',
            'habit_checkin', 'ai_suggestions', 'sleep_stats'
        ]

        if widget_id not in valid_widgets:
            return Response(
                {'error': f'Invalid widget_id. Must be one of: {", ".join(valid_widgets)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            data = get_widget_data(request.user, widget_id)
            return Response(data)
        except Exception as e:
            logger.error(f'Error fetching widget data for {widget_id}: {str(e)}')
            return Response(
                {'error': 'Failed to fetch widget data'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UserMetricRefreshView(APIView):
    """POST: Refresh current_value for all active metrics."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """Refresh current values for all user's active metrics."""
        from ..services.dashboard_service import update_metric_current_value

        metrics = UserMetric.objects.filter(user=request.user, is_active=True)
        updated_count = 0

        for metric in metrics:
            try:
                current_value = update_metric_current_value(request.user, metric.metric_type)
                metric.current_value = current_value
                metric.save()
                updated_count += 1
            except Exception as e:
                logger.error(f'Error updating metric {metric.id}: {str(e)}')

        return Response({
            'message': f'Refreshed {updated_count} metrics',
            'updated_count': updated_count
        })


class NotificationPagination(rest_framework.pagination.PageNumberPagination):
    page_size = 50


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    pagination_class = NotificationPagination

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')


class NotificationReadView(APIView):
    def post(self, request):
        ids = request.data.get('ids', [])
        if ids:
            Notification.objects.filter(user=request.user, id__in=ids).update(is_read=True)
        else:
            Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({'status': 'ok'})


@method_decorator(
    cache_control(public=True, max_age=600, s_maxage=1800),  # 10min browser, 30min CF
    name='dispatch',
)
class SubscriptionPlanListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = SubscriptionPlanSerializer
    queryset = SubscriptionPlan.objects.filter(is_active=True)


class MySubscriptionView(APIView):
    def get(self, request):
        try:
            sub = request.user.subscription
            return Response(UserSubscriptionSerializer(sub).data)
        except UserSubscription.DoesNotExist:
            return Response({'plan': None, 'status': 'none'})

    def post(self, request):
        plan_id = request.data.get('plan')
        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return error_response('plan_not_found', 'Plan not found.', 404)

        sub, created = UserSubscription.objects.update_or_create(
            user=request.user,
            defaults={'plan': plan, 'status': 'active'},
        )
        return Response(UserSubscriptionSerializer(sub).data)


class RequireTier(permissions.BasePermission):
    """Usage: permission_classes = [RequireTier.of('pro')]"""
    tier_required = 'free'

    @classmethod
    def of(cls, tier):
        return type(f'RequireTier_{tier}', (cls,), {'tier_required': tier})

    TIER_LEVELS = {'free': 0, 'pro': 1, 'counselor': 2}

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            user_tier = request.user.subscription.plan.tier
        except (UserSubscription.DoesNotExist, AttributeError):
            user_tier = 'free'
        return self.TIER_LEVELS.get(user_tier, 0) >= self.TIER_LEVELS.get(self.tier_required, 0)


class NotificationPreferenceView(APIView):
    def get(self, request):
        prefs = NotificationPreference.objects.filter(user=request.user)
        return Response(NotificationPreferenceSerializer(prefs, many=True).data)

    def patch(self, request):
        results = []
        for item in request.data if isinstance(request.data, list) else [request.data]:
            ntype = item.get('notification_type')
            enabled = item.get('enabled', True)
            if ntype:
                pref, _ = NotificationPreference.objects.update_or_create(
                    user=request.user,
                    notification_type=ntype,
                    defaults={'enabled': enabled},
                )
                results.append(NotificationPreferenceSerializer(pref).data)
        return Response(results)


class PushSubscriptionView(APIView):
    def post(self, request):
        endpoint = request.data.get('endpoint', '')
        keys = request.data.get('keys', {})
        p256dh = keys.get('p256dh', '')
        auth = keys.get('auth', '')

        if not endpoint or not p256dh or not auth:
            return error_response('push_missing_data', 'Missing push subscription data.', 400)

        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={'user': request.user, 'p256dh': p256dh, 'auth': auth},
        )
        return Response({'detail': 'Push subscription registered'})

    def delete(self, request):
        endpoint = request.data.get('endpoint', '')
        PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        return Response({'detail': 'Push subscription removed'})


def send_push_notification(user, title, body, url='/'):
    """Send web push notification to all user's subscriptions."""
    import json
    try:
        from pywebpush import webpush
    except ImportError:
        return

    vapid_private_key = os.environ.get('VAPID_PRIVATE_KEY', '')
    vapid_claims = {'sub': f'mailto:{settings.DEFAULT_FROM_EMAIL}'}

    if not vapid_private_key:
        return

    subscriptions = PushSubscription.objects.filter(user=user)
    payload = json.dumps({'title': title, 'body': body, 'url': url})

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
                },
                data=payload,
                vapid_private_key=vapid_private_key,
                vapid_claims=vapid_claims,
            )
        except Exception:
            logger.exception('Web push failed for subscription %s, removing', sub.endpoint[:50])
            sub.delete()  # Remove invalid subscriptions
