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

from . import User, error_response, logger


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and request.user.is_staff


class AdminStatsView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        today = timezone.now().date()
        user_stats = User.objects.aggregate(
            total_users=Count('id'),
            today_new_users=Count('id', filter=Q(date_joined__date=today)),
            active_users=Count('id', filter=Q(is_active=True)),
        )
        note_stats = MoodNote.objects.aggregate(
            total_notes=Count('id', filter=Q(is_deleted=False)),
            today_new_notes=Count('id', filter=Q(created_at__date=today, is_deleted=False)),
        )
        pending_counselors = CounselorProfile.objects.filter(status='pending').count()
        return Response({
            **user_stats,
            **note_stats,
            'pending_counselors': pending_counselors,
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
        return User.objects.all().order_by('-date_joined')


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = AdminUserSerializer
    queryset = User.objects.all()

    def perform_update(self, serializer):
        target = serializer.instance
        # Prevent admin from demoting themselves
        if target.pk == self.request.user.pk and 'is_staff' in serializer.validated_data:
            if not serializer.validated_data['is_staff']:
                raise exceptions.ValidationError({'detail': 'You cannot remove your own admin privileges.'})
        serializer.save()


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
        return Response(AdminCounselorSerializer(profile).data)


class AdminFeedbackListView(generics.ListAPIView):
    serializer_class = FeedbackSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_queryset(self):
        return Feedback.objects.select_related('user').all()
