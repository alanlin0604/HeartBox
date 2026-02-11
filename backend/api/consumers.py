from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser


class ChatConsumer(AsyncJsonWebsocketConsumer):
    """Real-time chat within a conversation."""

    async def connect(self):
        self.conv_id = self.scope['url_route']['kwargs']['conv_id']
        self.group_name = f'chat_{self.conv_id}'
        user = self.scope.get('user')

        if isinstance(user, AnonymousUser) or user is None:
            await self.close()
            return

        # Verify user is a participant of this conversation
        is_participant = await self.check_participant(user.id, self.conv_id)
        if not is_participant:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        user = self.scope['user']
        message_text = content.get('message', '').strip()
        if not message_text:
            return
        if len(message_text) > 5000:
            message_text = message_text[:5000]

        msg_data = await self.save_message(user.id, self.conv_id, message_text)
        await self.channel_layer.group_send(self.group_name, {
            'type': 'chat.message',
            'data': msg_data,
        })

    async def chat_message(self, event):
        await self.send_json(event['data'])

    @database_sync_to_async
    def check_participant(self, user_id, conv_id):
        from django.db.models import Q
        from .models import Conversation
        return Conversation.objects.filter(
            Q(id=conv_id) & (Q(user_id=user_id) | Q(counselor_id=user_id))
        ).exists()

    @database_sync_to_async
    def save_message(self, user_id, conv_id, content):
        from .models import Conversation, Message, Notification
        conv = Conversation.objects.get(id=conv_id)
        msg = Message.objects.create(conversation=conv, sender_id=user_id, content=content)
        conv.save()  # update updated_at

        # Determine the recipient and create a notification
        recipient_id = conv.counselor_id if conv.user_id == user_id else conv.user_id
        notification = Notification.objects.create(
            user_id=recipient_id,
            type='message',
            title='新訊息',
            message=content[:100],
            data={'conversation_id': conv.id, 'message_id': msg.id},
        )

        # Push notification via channel layer (fire-and-forget from sync context)
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'notifications_{recipient_id}',
            {
                'type': 'notify',
                'data': {
                    'id': notification.id,
                    'type': notification.type,
                    'title': notification.title,
                    'message': notification.message,
                    'data': notification.data,
                    'is_read': False,
                    'created_at': notification.created_at.isoformat(),
                },
            },
        )

        return {
            'id': msg.id,
            'sender': user_id,
            'sender_name': msg.sender.username,
            'sender_avatar': msg.sender.avatar.url if getattr(msg.sender, 'avatar', None) else None,
            'content': msg.content,
            'is_read': msg.is_read,
            'created_at': msg.created_at.isoformat(),
        }


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """Per-user notification channel — receive-only."""

    async def connect(self):
        user = self.scope.get('user')
        if isinstance(user, AnonymousUser) or user is None:
            await self.close()
            return

        self.group_name = f'notifications_{user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notify(self, event):
        await self.send_json(event['data'])
