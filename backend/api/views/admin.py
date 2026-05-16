"""Admin-only endpoints — stats, user management, counselor approvals, feedback.

Extracted from views/__init__.py. Re-exported for backward compatibility.
"""

import rest_framework.pagination
from django.db.models import Count, Q
from django.utils import timezone

from rest_framework import exceptions, filters, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import CounselorProfile, Feedback, MoodNote
from ..serializers import (
    AdminCounselorSerializer, AdminUserSerializer, FeedbackSerializer,
)
from ..services.audit import log_action

from . import User, error_response, logger


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class AdminStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        from datetime import timedelta
        from ..models import PublicPost, PostReport

        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        thirty_days_ago = today - timedelta(days=30)

        user_stats = User.objects.aggregate(
            total_users=Count('id'),
            today_new_users=Count('id', filter=Q(date_joined__date=today)),
            week_new_users=Count('id', filter=Q(date_joined__date__gte=week_ago)),
            active_users=Count('id', filter=Q(is_active=True)),
            verified_users=Count('id', filter=Q(email_verified=True)),
        )
        note_stats = MoodNote.objects.aggregate(
            total_notes=Count('id', filter=Q(is_deleted=False)),
            today_new_notes=Count('id', filter=Q(created_at__date=today, is_deleted=False)),
            week_new_notes=Count('id', filter=Q(created_at__date__gte=week_ago, is_deleted=False)),
        )
        counselor_stats = {
            'total_counselors': CounselorProfile.objects.filter(status='approved').count(),
            'pending_counselors': CounselorProfile.objects.filter(status='pending').count(),
        }
        community_stats = {
            'total_posts': PublicPost.objects.filter(is_active=True).count(),
            'open_reports': PostReport.objects.filter(status='open').count(),
        }

        # 30-day growth time-series (daily new users + new notes) for a sparkline.
        from django.db.models.functions import TruncDate
        daily_users = (
            User.objects
            .filter(date_joined__date__gte=thirty_days_ago)
            .annotate(d=TruncDate('date_joined'))
            .values('d')
            .annotate(c=Count('id'))
            .order_by('d')
        )
        daily_notes = (
            MoodNote.objects
            .filter(created_at__date__gte=thirty_days_ago, is_deleted=False)
            .annotate(d=TruncDate('created_at'))
            .values('d')
            .annotate(c=Count('id'))
            .order_by('d')
        )

        return Response({
            **user_stats,
            **note_stats,
            **counselor_stats,
            **community_stats,
            'growth': {
                'daily_users': [{'date': str(r['d']), 'count': r['c']} for r in daily_users],
                'daily_notes': [{'date': str(r['d']), 'count': r['c']} for r in daily_notes],
            },
        })


class AdminUserPagination(rest_framework.pagination.PageNumberPagination):
    page_size = 50


class AdminUserListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer
    pagination_class = AdminUserPagination
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email']

    def get_queryset(self):
        qs = User.objects.all().order_by('-date_joined')
        # Hide superuser accounts from non-superuser staff so they can't
        # see or attempt to modify them via the API.
        if not self.request.user.is_superuser:
            qs = qs.filter(is_superuser=False)
        return qs


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer

    def get_queryset(self):
        qs = User.objects.all()
        if not self.request.user.is_superuser:
            qs = qs.filter(is_superuser=False)
        return qs

    def perform_update(self, serializer):
        target = serializer.instance
        # Defence in depth: even though the queryset filters superusers out
        # for non-superuser staff, also block writes to superuser targets
        # unless the actor is a superuser themselves.
        if target.is_superuser and not self.request.user.is_superuser:
            raise exceptions.PermissionDenied('Cannot modify superuser accounts.')
        old_is_staff = target.is_staff
        new_is_staff = serializer.validated_data.get('is_staff', old_is_staff)
        # Prevent admin from demoting themselves
        if target.pk == self.request.user.pk and 'is_staff' in serializer.validated_data:
            if not serializer.validated_data['is_staff']:
                raise exceptions.ValidationError({'detail': 'You cannot remove your own admin privileges.'})
        serializer.save()
        # Audit privilege changes so unauthorized escalations leave a trail.
        if old_is_staff != new_is_staff:
            log_action(
                self.request.user,
                'admin.user.is_staff_change',
                request=self.request,
                target_type='User',
                target_id=target.pk,
                details={'from': old_is_staff, 'to': new_is_staff},
            )


class AdminCounselorListView(generics.ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminCounselorSerializer

    def get_queryset(self):
        qs = CounselorProfile.objects.select_related('user').all()
        s = self.request.query_params.get('status')
        if s:
            qs = qs.filter(status=s)
        return qs


class AdminCounselorActionView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, pk):
        try:
            profile = CounselorProfile.objects.get(pk=pk)
        except CounselorProfile.DoesNotExist:
            return error_response('counselor_not_found', 'Counselor not found.', 404)

        action = request.data.get('action')
        if action not in ('approve', 'reject'):
            return error_response('action_approve_reject', 'Action must be "approve" or "reject".')

        profile.status = 'approved' if action == 'approve' else 'rejected'
        profile.reviewed_at = timezone.now()
        profile.save(update_fields=['status', 'reviewed_at'])
        logger.info(
            'Admin %s %sd counselor profile %s (user: %s)',
            request.user.username, action, profile.pk, profile.user.username,
        )
        log_action(
            request.user,
            f'admin.counselor.{action}',
            request=request,
            target_type='CounselorProfile',
            target_id=profile.pk,
            details={'target_user': profile.user.username, 'new_status': profile.status},
        )
        return Response(AdminCounselorSerializer(profile).data)


class AdminFeedbackListView(generics.ListAPIView):
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Feedback.objects.select_related('user').all()


class AdminMLStatusView(APIView):
    """GET /api/admin/ml-status/ — read-only model health snapshot.

    Surfaces version, trained_at, CV metrics for each ML bundle so the
    admin can see at a glance whether models are loaded and how they
    performed. Used by the Admin > ML Monitoring tab.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from ..services.ml_predictor import get_predictor
        return Response(get_predictor().model_status())


class AdminAuditLogView(APIView):
    """GET /api/admin/audit-logs/ — recent admin + security-sensitive actions.

    Query params:
      - ?action=...   filter by action prefix (e.g. 'admin.', 'auth.', 'note')
      - ?user=...     filter by username (substring match)
      - ?limit=N      cap result count (default 200, max 500)

    Returns newest first. Read-only by design — audit trail must be append-only
    so don't expose a delete endpoint.
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        from ..models import AuditLog

        qs = AuditLog.objects.select_related('user').order_by('-created_at')

        action_prefix = (request.query_params.get('action') or '').strip()
        if action_prefix:
            qs = qs.filter(action__startswith=action_prefix)

        user_filter = (request.query_params.get('user') or '').strip()
        if user_filter:
            qs = qs.filter(user__username__icontains=user_filter)

        try:
            limit = int(request.query_params.get('limit', 200))
        except ValueError:
            limit = 200
        limit = max(1, min(limit, 500))

        rows = list(qs[:limit])
        data = [{
            'id': r.id,
            'action': r.action,
            'user': r.user.username if r.user else None,
            'target_type': r.target_type,
            'target_id': r.target_id,
            'ip_address': r.ip_address,
            'details': r.details or {},
            'created_at': r.created_at,
        } for r in rows]
        return Response({'count': len(data), 'results': data})
