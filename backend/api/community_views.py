"""Community Views — anonymous post sharing, support reactions, and the
moderation pieces (report flow + admin review) that gate this from going
public. The moderation policy itself lives in
``api/services/content_moderation.py``."""
import logging

from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from .models import Notification, PostReaction, PostReport, PublicPost
from .serializers import (
    PostReactionSerializer,
    PublicPostCreateSerializer,
    PublicPostSerializer,
)
from .services.content_moderation import (
    maybe_autohide_post, screen_content,
)

logger = logging.getLogger(__name__)


class CommunityPostPagination(PageNumberPagination):
    """Pagination for community posts."""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50


class PublicPostViewSet(viewsets.ModelViewSet):
    """
    ViewSet for anonymous community posts.

    List: GET /api/community/posts/ - List all active public posts
    Create: POST /api/community/posts/ - Create a new anonymous post
    Retrieve: GET /api/community/posts/{id}/ - Get single post
    Delete: DELETE /api/community/posts/{id}/ - Delete own post
    React: POST /api/community/posts/{id}/react/ - Give reaction
    My Posts: GET /api/community/posts/my_posts/ - List user's own posts
    """
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = CommunityPostPagination

    def get_queryset(self):
        """Get active posts with optimized queries."""
        return PublicPost.objects.filter(
            is_active=True
        ).select_related('user').prefetch_related(
            'reactions'
        ).order_by('-created_at')

    def get_serializer_class(self):
        """Use different serializers for create vs read."""
        if self.action == 'create':
            return PublicPostCreateSerializer
        return PublicPostSerializer

    def create(self, request, *args, **kwargs):
        """Create a new anonymous post.

        Runs the content through ``screen_content`` first so blatant abuse /
        ad spam is rejected at write time with a 400 carrying a machine-
        readable ``code`` the frontend can map to a localized message.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        allowed, reason = screen_content(serializer.validated_data.get('content', ''))
        if not allowed:
            code_map = {
                'empty':            'community.content_empty',
                'too_short':        'community.content_too_short',
                'too_long':         'community.content_too_long',
                'blocked_keyword':  'community.content_blocked',
            }
            return Response(
                {'detail': reason, 'code': code_map.get(reason, 'community.content_rejected')},
                status=status.HTTP_400_BAD_REQUEST,
            )

        post = serializer.save(user=request.user)

        # Optionally analyze sentiment (if AI service available)
        try:
            from .services.ai_service import analyze_sentiment
            sentiment = analyze_sentiment(post.content)
            if sentiment:
                post.sentiment_score = sentiment.get('score')
                post.category = sentiment.get('category', '')
                post.save(update_fields=['sentiment_score', 'category'])
        except Exception as e:
            logger.warning(f'Failed to analyze post sentiment: {e}')

        # Return created post with full serializer
        return Response(
            PublicPostSerializer(post, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        """Delete own post (soft delete by setting is_active=False)."""
        post = self.get_object()

        # Only owner can delete
        if post.user != request.user:
            return Response(
                {'detail': 'You can only delete your own posts.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Soft delete
        post.is_active = False
        post.save(update_fields=['is_active'])

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        """
        Give a reaction to a post.

        Body: {"reaction_type": "hug" | "support" | "heart"}
        - If reaction exists, remove it (toggle)
        - If reaction doesn't exist, add it
        """
        post = self.get_object()
        reaction_type = request.data.get('reaction_type')

        if not reaction_type or reaction_type not in ['hug', 'support', 'heart']:
            return Response(
                {'detail': 'Invalid reaction_type. Must be: hug, support, or heart.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Toggle reaction (remove if exists, add if not)
        existing = PostReaction.objects.filter(
            post=post,
            user=request.user,
            reaction_type=reaction_type
        ).first()

        if existing:
            # Remove reaction
            existing.delete()
            action_type = 'removed'
        else:
            # Add reaction
            PostReaction.objects.create(
                post=post,
                user=request.user,
                reaction_type=reaction_type
            )
            action_type = 'added'

            # Notify the post author when someone (other than themselves) reacts.
            # Stays anonymous — we don't reveal who reacted, just that someone
            # did, to keep the community pseudo-anonymous.
            if post.user_id != request.user.id:
                emoji = {'hug': '🤗', 'support': '💪', 'heart': '❤️'}.get(reaction_type, '✨')
                preview = post.content[:30] + ('…' if len(post.content) > 30 else '')
                try:
                    Notification.objects.create(
                        user=post.user,
                        type='post_reaction',
                        title=f'有人{emoji}你的貼文',
                        message=f'「{preview}」收到了一個 {reaction_type} 反應',
                        data={'post_id': post.id, 'reaction_type': reaction_type},
                    )
                except Exception:
                    logger.warning('Failed to create reaction notification for post %d', post.id)

        # Return updated post
        return Response({
            'action': action_type,
            'post': PublicPostSerializer(post, context={'request': request}).data
        })

    @action(detail=False, methods=['get'])
    def my_posts(self, request):
        """List current user's own posts (including inactive)."""
        posts = PublicPost.objects.filter(
            user=request.user
        ).prefetch_related('reactions').order_by('-created_at')

        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = PublicPostSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = PublicPostSerializer(posts, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def report(self, request, pk=None):
        """File a report against a post.

        Body: ``{"reason": "<one of REASON_CHOICES>", "note": "<optional>"}``

        - Reporter can only report a given post once (DB-level unique).
        - Reporter cannot report their own post.
        - Once REPORT_AUTOHIDE_THRESHOLD distinct reporters file a report,
          the post is automatically hidden pending admin review.
        """
        post = self.get_object()
        if post.user_id == request.user.id:
            return Response(
                {'detail': 'You cannot report your own post.', 'code': 'community.cannot_report_own'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        reason = request.data.get('reason')
        valid_reasons = {choice[0] for choice in PostReport.REASON_CHOICES}
        if reason not in valid_reasons:
            return Response(
                {'detail': f'reason must be one of {sorted(valid_reasons)}',
                 'code': 'community.invalid_reason'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        note = (request.data.get('note') or '').strip()[:500]

        report, created = PostReport.objects.get_or_create(
            post=post, reporter=request.user,
            defaults={'reason': reason, 'note': note},
        )
        if not created:
            return Response(
                {'detail': 'You have already reported this post.', 'code': 'community.already_reported'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        autohid = maybe_autohide_post(post)
        return Response({
            'reported': True,
            'auto_hidden': autohid,
            'report_id': report.id,
        }, status=status.HTTP_201_CREATED)


# --- Admin moderation surface ---

class IsStaffUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class ReportListView(APIView):
    """GET /api/community/reports/?status=open  — staff-only.
    Returns the queue of open reports, newest first, for manual review."""
    permission_classes = [IsStaffUser]

    def get(self, request):
        status_filter = request.query_params.get('status', 'open')
        valid_statuses = {choice[0] for choice in PostReport.STATUS_CHOICES}
        if status_filter and status_filter not in valid_statuses:
            return Response({'detail': 'invalid status filter'}, status=400)

        qs = PostReport.objects.select_related('post', 'post__user', 'reporter')
        if status_filter:
            qs = qs.filter(status=status_filter)
        qs = qs.order_by('-created_at')[:200]

        data = [{
            'id': r.id,
            'reason': r.reason,
            'note': r.note,
            'status': r.status,
            'reporter': r.reporter.username,
            'created_at': r.created_at,
            'post': {
                'id': r.post_id,
                'content': r.post.content,
                'author': r.post.user.username,
                'is_active': r.post.is_active,
                'created_at': r.post.created_at,
                'open_report_count': r.post.reports.filter(status='open').count(),
            },
        } for r in qs]
        return Response(data)


class ModeratePostView(APIView):
    """POST /api/community/posts/<pk>/moderate/ — staff-only.
    Body: ``{"action": "remove" | "keep" | "dismiss"}``.

    - ``remove`` hides the post (is_active=False) and marks all open reports
      as ``reviewed_removed``.
    - ``keep`` leaves the post visible (or unhides it if it was auto-hidden)
      and marks reports ``reviewed_kept``.
    - ``dismiss`` marks reports ``dismissed`` without touching the post.
    """
    permission_classes = [IsStaffUser]

    def post(self, request, pk):
        try:
            post = PublicPost.objects.get(pk=pk)
        except PublicPost.DoesNotExist:
            return Response({'detail': 'Post not found.'}, status=404)

        action_kind = request.data.get('action')
        if action_kind not in ('remove', 'keep', 'dismiss'):
            return Response({'detail': 'action must be remove / keep / dismiss'}, status=400)

        now = timezone.now()
        new_status = {
            'remove':  'reviewed_removed',
            'keep':    'reviewed_kept',
            'dismiss': 'dismissed',
        }[action_kind]

        if action_kind == 'remove':
            post.is_active = False
            post.save(update_fields=['is_active'])
        elif action_kind == 'keep' and not post.is_active:
            post.is_active = True
            post.save(update_fields=['is_active'])

        affected = post.reports.filter(status='open').update(
            status=new_status, reviewed_by=request.user, reviewed_at=now,
        )
        return Response({
            'action': action_kind,
            'is_active': post.is_active,
            'reports_resolved': affected,
        })


# drf_spectacular schema policy — see backend/api/views/__init__.py for rationale.
_UNDOCUMENTED_VIEWS = ['ReportListView', 'ModeratePostView']
for _name in _UNDOCUMENTED_VIEWS:
    _cls = globals().get(_name)
    if _cls is not None:
        _cls.schema = None
