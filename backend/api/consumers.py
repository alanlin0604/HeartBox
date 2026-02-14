import asyncio

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import AnonymousUser

HEARTBEAT_INTERVAL = 30  # seconds


class HeartbeatMixin:
    """Mixin that sends periodic pings to keep the connection alive."""

    _heartbeat_task = None

    async def start_heartbeat(self):
        self._heartbeat_task = asyncio.ensure_future(self._heartbeat_loop())

    async def stop_heartbeat(self):
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

    async def _heartbeat_loop(self):
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await self.send_json({'type': 'ping'})
        except asyncio.CancelledError:
            pass


class AuthMixin:
    """Mixin that supports first-message JWT authentication.

    If the connection was not already authenticated via query-string,
    the first JSON message must be {"type": "auth", "token": "<JWT>"}.
    """

    async def authenticate_via_message(self, content):
        """Handle an auth message. Returns True if authenticated."""
        token = content.get('token', '')
        if not token:
            await self.send_json({'error': 'Token required'})
            await self.close()
            return False

        from .middleware import get_user_from_token
        user = await get_user_from_token(token)
        if isinstance(user, AnonymousUser) or user is None:
            await self.send_json({'error': 'Invalid token'})
            await self.close()
            return False

        self.scope['user'] = user
        return True

    def is_authenticated(self):
        user = self.scope.get('user')
        return user and not isinstance(user, AnonymousUser)


class ChatConsumer(HeartbeatMixin, AuthMixin, AsyncJsonWebsocketConsumer):
    """Real-time chat within a conversation."""

    async def connect(self):
        self.conv_id = self.scope['url_route']['kwargs']['conv_id']
        self.group_name = f'chat_{self.conv_id}'
        self._authenticated = False

        # Accept connection first (needed for first-message auth)
        await self.accept()

        user = self.scope.get('user')
        if self.is_authenticated():
            # Query-string auth — verify participant immediately
            if not await self.check_participant(user.id, self.conv_id):
                await self.send_json({'error': 'Not a participant'})
                await self.close()
                return
            self._authenticated = True
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.start_heartbeat()

    async def disconnect(self, close_code):
        await self.stop_heartbeat()
        if hasattr(self, 'group_name') and self._authenticated:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        # Handle pong responses (client keepalive)
        if content.get('type') == 'pong':
            return

        # Handle first-message auth if not yet authenticated
        if not self._authenticated:
            if content.get('type') == 'auth':
                if not await self.authenticate_via_message(content):
                    return
                # Verify participant after auth
                user = self.scope['user']
                if not await self.check_participant(user.id, self.conv_id):
                    await self.send_json({'error': 'Not a participant'})
                    await self.close()
                    return
                self._authenticated = True
                await self.channel_layer.group_add(self.group_name, self.channel_name)
                await self.start_heartbeat()
                await self.send_json({'type': 'auth_ok'})
                return
            else:
                await self.send_json({'error': 'Authentication required'})
                await self.close()
                return

        user = self.scope['user']
        from django.utils.html import strip_tags
        message_text = strip_tags(content.get('message', '')).strip()
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
            title='New message',
            message=content[:100],
            data={
                'conversation_id': conv.id,
                'message_id': msg.id,
                'sender_name': msg.sender.username,
            },
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
            'message_type': msg.message_type,
            'metadata': msg.metadata,
            'is_read': msg.is_read,
            'created_at': msg.created_at.isoformat(),
        }


class NotificationConsumer(HeartbeatMixin, AuthMixin, AsyncJsonWebsocketConsumer):
    """Per-user notification channel — receive-only."""

    async def connect(self):
        self._authenticated = False

        # Accept connection first (needed for first-message auth)
        await self.accept()

        user = self.scope.get('user')
        if self.is_authenticated():
            self._authenticated = True
            self.group_name = f'notifications_{user.id}'
            await self.channel_layer.group_add(self.group_name, self.channel_name)
            await self.start_heartbeat()

    async def disconnect(self, close_code):
        await self.stop_heartbeat()
        if hasattr(self, 'group_name') and self._authenticated:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content):
        # Handle pong responses
        if content.get('type') == 'pong':
            return

        if not self._authenticated:
            if content.get('type') == 'auth':
                if not await self.authenticate_via_message(content):
                    return
                self._authenticated = True
                user = self.scope['user']
                self.group_name = f'notifications_{user.id}'
                await self.channel_layer.group_add(self.group_name, self.channel_name)
                await self.start_heartbeat()
                await self.send_json({'type': 'auth_ok'})
                return
            else:
                await self.send_json({'error': 'Authentication required'})
                await self.close()
                return

    async def notify(self, event):
        await self.send_json(event['data'])
