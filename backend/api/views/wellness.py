"""Achievements, psychoeducation articles, courses, lessons, wellness sessions.

Extracted from views/__init__.py. Re-exported for backward compatibility.
"""

import rest_framework.pagination
from django.db.models import Count, Q
from django.utils import timezone

from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from ..models import Course, PsychoArticle, UserLessonProgress, WellnessSession
from ..serializers import (
    CourseDetailSerializer, CourseListSerializer, PsychoArticleSerializer,
    WellnessSessionSerializer,
)

from . import error_response


class AchievementsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from api.services.achievements import get_user_achievements_with_progress
        data = get_user_achievements_with_progress(request.user)
        return Response(data)


class AchievementCheckView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from api.services.achievements import check_achievements
        newly_unlocked = check_achievements(request.user)
        return Response({'newly_unlocked': newly_unlocked})


class PsychoArticleListView(generics.ListAPIView):
    """Editorial articles list — public, but anon throttled to prevent abuse."""
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = PsychoArticleSerializer

    def get_queryset(self):
        qs = PsychoArticle.objects.filter(is_published=True)
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)
        return qs


class PsychoArticleDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = PsychoArticleSerializer

    def get_queryset(self):
        return PsychoArticle.objects.filter(is_published=True)

    def retrieve(self, request, *args, **kwargs):
        response = super().retrieve(request, *args, **kwargs)
        # Auto-create progress record when article is viewed (authenticated users only)
        if request.user.is_authenticated:
            article = self.get_object()
            UserLessonProgress.objects.get_or_create(
                user=request.user, article=article,
            )
        return response


class WellnessSessionPagination(rest_framework.pagination.PageNumberPagination):
    page_size = 50


class WellnessSessionListCreateView(generics.ListCreateAPIView):
    serializer_class = WellnessSessionSerializer
    pagination_class = WellnessSessionPagination

    def get_queryset(self):
        return WellnessSession.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CourseListView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = CourseListSerializer

    def get_queryset(self):
        return Course.objects.filter(is_published=True).annotate(
            _lesson_count=Count('lessons', filter=Q(lessons__is_published=True)),
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.request.user.is_authenticated:
            completed_ids = set(
                UserLessonProgress.objects.filter(
                    user=self.request.user, completed_at__isnull=False,
                ).values_list('article_id', flat=True)
            )
        else:
            completed_ids = set()
        ctx['completed_ids'] = completed_ids
        return ctx


class CourseDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = CourseDetailSerializer

    def get_queryset(self):
        return Course.objects.filter(is_published=True).annotate(
            _lesson_count=Count('lessons', filter=Q(lessons__is_published=True)),
        )

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if self.request.user.is_authenticated:
            completed_ids = set(
                UserLessonProgress.objects.filter(
                    user=self.request.user, completed_at__isnull=False,
                ).values_list('article_id', flat=True)
            )
        else:
            completed_ids = set()
        ctx['completed_ids'] = completed_ids
        return ctx


class LessonCompleteView(APIView):
    def post(self, request, pk):
        try:
            article = PsychoArticle.objects.get(pk=pk, is_published=True)
        except PsychoArticle.DoesNotExist:
            return error_response('article_not_found', 'Article not found.', 404)

        progress, created = UserLessonProgress.objects.get_or_create(
            user=request.user, article=article,
        )
        if not progress.completed_at:
            progress.completed_at = timezone.now()
            progress.save(update_fields=['completed_at'])
        return Response({'status': 'completed', 'completed_at': progress.completed_at})
