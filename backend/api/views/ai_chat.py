"""AI chat session and message endpoints.

Extracted from views/__init__.py to keep AI-chat-specific logic in its own
module. Re-exported via views/__init__.py for backward compatibility.
"""

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import AIChatMessage, AIChatSession
from ..serializers import AIChatMessageSerializer, AIChatSessionSerializer
from ..throttles import AIChatThrottle

# Import shared helpers from the package init. This is safe because __init__.py
# defines them at module level before any submodule import would re-trigger it.
from . import error_response, MAX_AI_CHAT_MESSAGE_LENGTH


class AIChatSessionListCreateView(APIView):
    """List all active sessions or create a new one."""

    def get(self, request):
        from django.db.models import Count, Subquery, OuterRef
        from django.db.models.functions import Substr
        last_msg_subquery = (
            AIChatMessage.objects.filter(session=OuterRef('pk'))
            .order_by('-created_at')
            .values('content')[:1]
        )
        sessions = (
            AIChatSession.objects.filter(user=request.user, is_active=True)
            .annotate(
                _message_count=Count('messages'),
                _last_message_preview=Substr(Subquery(last_msg_subquery), 1, 80),
            )
        )
        return Response(AIChatSessionSerializer(sessions, many=True).data)

    def post(self, request):
        session = AIChatSession.objects.create(user=request.user)
        return Response(AIChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)


class AIChatSessionDetailView(APIView):
    """Get session detail with messages, or soft-delete session."""

    def get(self, request, session_id):
        try:
            session = AIChatSession.objects.get(id=session_id, user=request.user, is_active=True)
        except AIChatSession.DoesNotExist:
            return error_response('session_not_found', 'Session not found.', 404)

        messages = session.messages.all()
        before = request.query_params.get('before')
        if before:
            messages = messages.filter(id__lt=before)
        total = messages.count()
        page = messages.order_by('-created_at')[:50]
        msg_list = list(reversed(page))
        return Response({
            **AIChatSessionSerializer(session).data,
            'messages': AIChatMessageSerializer(msg_list, many=True).data,
            'has_more': total > len(msg_list),
        })

    def patch(self, request, session_id):
        try:
            session = AIChatSession.objects.get(id=session_id, user=request.user, is_active=True)
        except AIChatSession.DoesNotExist:
            return error_response('session_not_found', 'Session not found.', 404)

        update_fields = []
        if 'title' in request.data:
            session.title = str(request.data['title'])[:100]
            update_fields.append('title')
        if 'is_pinned' in request.data:
            session.is_pinned = bool(request.data['is_pinned'])
            update_fields.append('is_pinned')

        if update_fields:
            session.save(update_fields=update_fields)
        return Response(AIChatSessionSerializer(session).data)

    def delete(self, request, session_id):
        try:
            session = AIChatSession.objects.get(id=session_id, user=request.user, is_active=True)
        except AIChatSession.DoesNotExist:
            return error_response('session_not_found', 'Session not found.', 404)

        session.is_active = False
        session.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class AIChatSendMessageView(APIView):
    """Send a message in an AI chat session."""
    throttle_classes = [AIChatThrottle]

    def post(self, request, session_id):
        try:
            session = AIChatSession.objects.get(id=session_id, user=request.user, is_active=True)
        except AIChatSession.DoesNotExist:
            return error_response('session_not_found', 'Session not found.', 404)

        content = (request.data.get('content') or '').strip()
        if not content:
            return error_response('message_empty', 'Message cannot be empty.')
        if len(content) > MAX_AI_CHAT_MESSAGE_LENGTH:
            return error_response('message_too_long', f'Message cannot exceed {MAX_AI_CHAT_MESSAGE_LENGTH} characters.')

        from ..services.ai_chat import analyze_user_message, generate_ai_response, _get_lang
        sentiment = analyze_user_message(content)

        user_msg = AIChatMessage.objects.create(
            session=session,
            role='user',
            content=content,
            sentiment_score=sentiment['sentiment_score'],
            stress_index=sentiment['stress_index'],
        )

        if session.messages.count() == 1:
            session.title = content[:50]
            session.save(update_fields=['title', 'updated_at'])
        else:
            session.save(update_fields=['updated_at'])

        lang = _get_lang(request.headers.get('Accept-Language', ''))
        all_messages = list(session.messages.all())
        ai_content = generate_ai_response(all_messages, lang)

        ai_msg = AIChatMessage.objects.create(
            session=session,
            role='assistant',
            content=ai_content,
        )

        return Response({
            'user_message': AIChatMessageSerializer(user_msg).data,
            'ai_message': AIChatMessageSerializer(ai_msg).data,
        }, status=status.HTTP_201_CREATED)
