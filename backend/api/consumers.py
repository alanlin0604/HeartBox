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
        if msg_data is None:
            # Either the conversation vanished or the DB write failed.
            # Tell only the sender so they can retry; don't broadcast garbage.
            await self.send_json({'error': 'Message could not be saved'})
            return
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
        """Persist a chat message + recipient notification atomically.

        Returns the serialized message on success, None if the conversation
        was deleted between accept() and now (handled gracefully — caller
        sees no exception thrown across the WS).

        The DB writes (message + notification) run in a single transaction
        so a failure midway can't leave a recipient with a notification
        that points at a never-saved message id. The downstream channel-
        layer broadcast is intentionally OUTSIDE the transaction — Redis /
        in-memory broadcast failures shouldn't roll back the persisted
        message; the recipient still gets it via NotificationListView.
        """
        from django.db import transaction
        from .models import Conversation, Message, Notification

        try:
            with transaction.atomic():
                try:
                    conv = Conversation.objects.select_related().get(id=conv_id)
                except Conversation.DoesNotExist:
                    return None
                msg = Message.objects.create(
                    conversation=conv, sender_id=user_id, content=content,
                )
                conv.save()  # bump updated_at

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
        except Exception:
            # Surface to logs but don't tear down the WS — caller decides.
            import logging
            logging.getLogger(__name__).exception(
                'save_message DB write failed; user=%s conv=%s', user_id, conv_id,
            )
            return None

        # Best-effort notification fan-out — separate from the persisted writes.
        try:
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
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                'channel-layer notify fan-out failed for recipient=%s', recipient_id,
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
