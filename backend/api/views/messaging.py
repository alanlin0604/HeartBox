"""Messaging — conversations, messages, and quote actions.

Extracted from views/__init__.py. Re-exported for backward compatibility.
"""

import rest_framework.pagination
from django.db.models import Prefetch, Q
from django.utils.html import strip_tags

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Conversation, CounselorProfile, Message
from ..serializers import ConversationSerializer, MessageSerializer
from ..throttles import MessageThrottle

from . import (
    MAX_MESSAGE_LENGTH, User, _push_ws_notification,
    create_notification_if_enabled, error_response,
)


class ConversationPagination(rest_framework.pagination.PageNumberPagination):
    page_size = 30


class ConversationListView(generics.ListAPIView):
    """List all conversations for the current user."""
    serializer_class = ConversationSerializer
    pagination_class = ConversationPagination

    def get_queryset(self):
        user = self.request.user
        return Conversation.objects.filter(
            Q(user=user) | Q(counselor=user)
        ).select_related(
            'user', 'counselor',
            'user__counselor_profile', 'counselor__counselor_profile',
        ).prefetch_related(
            Prefetch(
                'messages',
                queryset=Message.objects.select_related(
                    'sender', 'sender__counselor_profile',
                ).order_by('-created_at'),
            )
        )


class ConversationDeleteView(APIView):
    """Delete a conversation (only participants can delete)."""

    def delete(self, request, conv_id):
        try:
            conv = Conversation.objects.get(
                Q(id=conv_id) & (Q(user=request.user) | Q(counselor=request.user))
            )
        except Conversation.DoesNotExist:
            return error_response('conversation_not_found', 'Conversation not found.', 404)
        conv.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConversationCreateView(APIView):
    """Start a conversation with a counselor."""

    def post(self, request):
        counselor_id = request.data.get('counselor_id')
        try:
            profile = CounselorProfile.objects.get(id=counselor_id, status='approved')
        except CounselorProfile.DoesNotExist:
            return error_response('counselor_not_found', 'Counselor not found.', 404)

        conv, created = Conversation.objects.get_or_create(
            user=request.user,
            counselor=profile.user,
        )
        return Response(ConversationSerializer(conv, context={'request': request}).data,
                        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class MessageListView(APIView):
    """List messages in a conversation and send new messages."""

    def get_throttles(self):
        if self.request.method == 'POST':
            return [MessageThrottle()]
        return super().get_throttles()

    def get(self, request, conv_id):
        try:
            conv = Conversation.objects.get(
                Q(id=conv_id) & (Q(user=request.user) | Q(counselor=request.user))
            )
        except Conversation.DoesNotExist:
            return error_response('conversation_not_found', 'Conversation not found.', 404)

        # Mark unread messages as read
        conv.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)

        messages = conv.messages.select_related('sender', 'sender__counselor_profile').all()
        return Response(MessageSerializer(messages, many=True).data)

    def post(self, request, conv_id):
        try:
            conv = Conversation.objects.get(
                Q(id=conv_id) & (Q(user=request.user) | Q(counselor=request.user))
            )
        except Conversation.DoesNotExist:
            return error_response('conversation_not_found', 'Conversation not found.', 404)

        message_type = request.data.get('message_type', 'text')

        if message_type == 'quote':
            # Only approved counselors can send quotes
            if not hasattr(request.user, 'counselor_profile') or not request.user.counselor_profile.is_approved:
                return error_response('counselor_only_quotes', 'Only approved counselors can send quotes.', 403)
            description = strip_tags(request.data.get('description', '')).strip()
            if not description:
                return error_response('quote_desc_required', 'Quote description is required.')
            try:
                price = float(request.data.get('price', 0))
            except (ValueError, TypeError):
                return error_response('invalid_price', 'Invalid price.')
            if price < 0:
                return error_response('price_negative', 'Price cannot be negative.')
            currency = request.data.get('currency', 'TWD')
            metadata = {'description': description, 'price': price, 'currency': currency}
            content = f'[Quote] {description} — {currency} {price}'
            msg = Message.objects.create(
                conversation=conv, sender=request.user,
                content=content, message_type='quote', metadata=metadata,
            )
        else:
            content = strip_tags(request.data.get('content', '')).strip()
            if not content:
                return error_response('message_empty', 'Message cannot be empty.')
            if len(content) > MAX_MESSAGE_LENGTH:
                return error_response('message_too_long', f'Message cannot exceed {MAX_MESSAGE_LENGTH} characters.')
            msg = Message.objects.create(conversation=conv, sender=request.user, content=content[:MAX_MESSAGE_LENGTH])

        conv.save()  # update updated_at

        # Create notification for the other party
        recipient_id = conv.counselor_id if conv.user_id == request.user.id else conv.user_id
        notif_data = {
            'conversation_id': conv.id,
            'message_id': msg.id,
            'sender_name': request.user.username,
        }
        if message_type == 'quote':
            notif_data['message_type'] = 'quote'
        notif = create_notification_if_enabled(
            User.objects.get(pk=recipient_id), 'message',
            title='New message',
            message=msg.content[:100],
            data=notif_data,
        )

        if notif:
            _push_ws_notification(recipient_id, notif)

        return Response(MessageSerializer(msg).data, status=status.HTTP_201_CREATED)


class QuoteActionView(APIView):
    """Accept or reject a quote message."""

    def post(self, request, conv_id, msg_id):
        action = request.data.get('action')
        if action not in ('accept', 'reject'):
            return error_response('action_accept_reject', 'Action must be accept or reject.')
        try:
            conv = Conversation.objects.get(
                Q(id=conv_id) & (Q(user=request.user) | Q(counselor=request.user))
            )
        except Conversation.DoesNotExist:
            return error_response('conversation_not_found', 'Conversation not found.', 404)
        try:
            msg = conv.messages.get(id=msg_id, message_type='quote')
        except Message.DoesNotExist:
            return error_response('quote_not_found', 'Quote not found.', 404)
        # Only the non-sender can accept/reject
        if msg.sender == request.user:
            return error_response('cannot_act_own_quote', 'Cannot act on your own quote.', 403)
        msg.metadata['status'] = 'accepted' if action == 'accept' else 'rejected'
        msg.save(update_fields=['metadata'])
        return Response(MessageSerializer(msg).data)
