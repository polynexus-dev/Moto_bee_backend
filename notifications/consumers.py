"""
notifications/consumers.py — Django Channels WebSocket consumers
────────────────────────────────────────────────────────────────

Two consumers:

1. BookingConsumer
   ws://api.motobee.in/ws/booking/{booking_id}/
   → Clients (customer OR owner) connect to watch a specific booking's
     status in real-time (live status bar in app).

2. UserNotificationConsumer
   ws://api.motobee.in/ws/notifications/
   → Each user connects once and receives ALL their notifications
     (new bookings for owners, status updates for customers).

Authentication is done via JWT token passed as a query param:
   ?token=<access_token>
"""
import json
import logging
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

logger = logging.getLogger(__name__)
User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_str: str):
    """Validate JWT and return User or None."""
    try:
        token = AccessToken(token_str)
        user_id = token['user_id']
        return User.objects.get(id=user_id)
    except (InvalidToken, TokenError, User.DoesNotExist):
        return None


class BookingConsumer(AsyncWebsocketConsumer):
    """
    Connect to a specific booking's real-time updates.

    URL: /ws/booking/<booking_id>/
    Group: booking_<booking_id>

    Messages received by client:
    {
        "type": "booking_update",
        "event": "accepted" | "rejected" | "in_progress" | "completed",
        "booking_id": "uuid",
        "booking_status": "accepted",
        "booking": { ...full booking object... }
    }
    """

    async def connect(self):
        self.booking_id = self.scope['url_route']['kwargs']['booking_id']
        self.group_name = f"booking_{self.booking_id}"

        # Authenticate via token query param
        query_string = self.scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token_str = params.get('token', [None])[0]

        if not token_str:
            await self.close(code=4001)
            return

        user = await get_user_from_token(token_str)
        if not user:
            await self.close(code=4001)
            return

        self.user = user

        # Verify user is allowed to watch this booking
        allowed = await self._is_allowed(self.booking_id, user)
        if not allowed:
            await self.close(code=4003)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"WS BookingConsumer: {user.email} joined {self.group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Clients don't send messages to this consumer — read-only
        pass

    async def booking_update(self, event):
        """Called by channel layer when a booking status changes."""
        await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def _is_allowed(self, booking_id, user):
        from bookings.models import Booking
        try:
            booking = Booking.objects.select_related('customer', 'garage__owner').get(pk=booking_id)
            return booking.customer == user or booking.garage.owner == user
        except Booking.DoesNotExist:
            return False


class UserNotificationConsumer(AsyncWebsocketConsumer):
    """
    Personal notification stream for a user.

    URL: /ws/notifications/
    Group: user_<uid>

    Receives all booking events related to this user.
    Also used by owners to get new booking pings without polling.
    """

    async def connect(self):
        query_string = self.scope.get('query_string', b'').decode()
        params = parse_qs(query_string)
        token_str = params.get('token', [None])[0]

        if not token_str:
            await self.close(code=4001)
            return

        user = await get_user_from_token(token_str)
        if not user:
            await self.close(code=4001)
            return

        self.user = user
        self.group_name = f"user_{user.uid}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"WS UserNotificationConsumer: {user.email} connected to {self.group_name}")

        # Send unread count on connect
        unread = await self._get_unread_count(user)
        await self.send(text_data=json.dumps({
            'type': 'connected',
            'unread_count': unread,
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle mark-as-read commands from client."""
        try:
            data = json.loads(text_data)
            if data.get('action') == 'mark_read':
                notification_id = data.get('notification_id')
                if notification_id:
                    await self._mark_read(notification_id, self.user)
                    await self.send(text_data=json.dumps({
                        'type': 'marked_read',
                        'notification_id': notification_id,
                    }))
        except json.JSONDecodeError:
            pass

    async def booking_update(self, event):
        """Called by channel layer when any of user's bookings change."""
        await self.send(text_data=json.dumps(event['data']))

    @database_sync_to_async
    def _get_unread_count(self, user):
        from notifications.models import Notification
        return Notification.objects.filter(recipient=user, is_read=False).count()

    @database_sync_to_async
    def _mark_read(self, notification_id, user):
        from notifications.models import Notification
        Notification.objects.filter(id=notification_id, recipient=user).update(is_read=True)
