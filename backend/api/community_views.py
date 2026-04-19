"""
Community Views - Anonymous post sharing and support reactions
Simplified version without content moderation or reporting.
"""
import logging

from django.db import transaction
from django.db.models import Count, Q, Prefetch
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import PublicPost, PostReaction
from .serializers import (
    PublicPostSerializer,
    PublicPostCreateSerializer,
    PostReactionSerializer,
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
        """Create a new anonymous post."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create post
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
