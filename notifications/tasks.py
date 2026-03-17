"""
notifications/tasks.py
─────────────────────
Push notification sender for MOTOBEE.

Called after every booking status change.
Sends Expo push notification + stores in DB + broadcasts via WebSocket.
"""
import logging
import urllib.request
import json

from django.conf import settings
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

NOTIFICATION_TEMPLATES = {
    'new_booking': {
        'owner_title': '🔔 New Booking Request',
        'owner_body': '{customer} wants to book {time} on {date} for {vehicle}.',
        'customer_title': '📋 Booking Submitted',
        'customer_body': 'Your booking at {garage} for {date} {time} is pending confirmation.',
    },
    'accepted': {
        'customer_title': '✅ Booking Confirmed!',
        'customer_body': 'Your booking at {garage} on {date} at {time} is confirmed.',
    },
    'rejected': {
        'customer_title': '❌ Booking Declined',
        'customer_body': 'Your booking at {garage} was declined. {note}',
    },
    'in_progress': {
        'customer_title': '🔧 Service Started',
        'customer_body': 'Your vehicle is now being serviced at {garage}.',
    },
    'completed': {
        'customer_title': '🎉 Vehicle Ready!',
        'customer_body': 'Your vehicle service at {garage} is complete. Ready for pickup!',
    },
    'cancelled': {
        'owner_title': '🚫 Booking Cancelled',
        'owner_body': '{customer} cancelled their booking for {date} at {time}.',
    },
}


def build_context(booking):
    return {
        'customer': booking.customer.get_full_name() or booking.customer.email,
        'garage': booking.garage.name,
        'date': str(booking.date),
        'time': booking.time,
        'vehicle': booking.vehicle_type,
        'note': f"Reason: {booking.rejection_note}" if booking.rejection_note else '',
    }


def send_booking_notification(booking, event_type: str):
    """
    Main entry point called from booking views.
    1. Saves a Notification record to DB
    2. Sends Expo push notification if token present
    3. Broadcasts booking update via WebSocket channel group
    """
    from notifications.models import Notification

    templates = NOTIFICATION_TEMPLATES.get(event_type, {})
    ctx = build_context(booking)

    recipients = []

    # Determine recipients based on event
    if event_type == 'new_booking':
        # Notify the garage owner
        owner = booking.garage.owner
        title = templates.get('owner_title', '').format(**ctx)
        body = templates.get('owner_body', '').format(**ctx)
        recipients.append((owner, title, body))
        # Also notify customer confirmation
        c_title = templates.get('customer_title', '').format(**ctx)
        c_body = templates.get('customer_body', '').format(**ctx)
        recipients.append((booking.customer, c_title, c_body))
    elif event_type == 'cancelled':
        owner = booking.garage.owner
        title = templates.get('owner_title', '').format(**ctx)
        body = templates.get('owner_body', '').format(**ctx)
        recipients.append((owner, title, body))
    else:
        # All other events notify the customer
        c_title = templates.get('customer_title', '').format(**ctx)
        c_body = templates.get('customer_body', '').format(**ctx)
        recipients.append((booking.customer, c_title, c_body))

    for user, title, body in recipients:
        # 1. Save to DB
        try:
            Notification.objects.create(
                recipient=user,
                booking=booking,
                notification_type=event_type,
                title=title,
                body=body,
            )
        except Exception as e:
            logger.error(f"Failed to save notification: {e}")

        # 2. Send Expo push if token exists
        if user.expo_push_token:
            _send_expo_push(user.expo_push_token, title, body, {
                'booking_id': str(booking.id),
                'event': event_type,
            })

        # 3. WebSocket broadcast
        _broadcast_ws(booking, event_type, user)


def _send_expo_push(token: str, title: str, body: str, data: dict):
    """Send a push notification via Expo's push API."""
    payload = json.dumps({
        'to': token,
        'title': title,
        'body': body,
        'data': data,
        'sound': 'default',
    }).encode('utf-8')

    req = urllib.request.Request(
        settings.EXPO_PUSH_URL,
        data=payload,
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            logger.info(f"Expo push sent to {token[:20]}... status={response.status}")
    except Exception as e:
        logger.error(f"Expo push failed: {e}")


def _broadcast_ws(booking, event_type: str, recipient):
    """
    Broadcast booking update to two WebSocket groups:
    - booking_{booking_id}  → any client watching this specific booking
    - user_{user_uid}       → the recipient's personal channel
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    from bookings.serializers import BookingSerializer
    payload = {
        'type': 'booking.update',
        'event': event_type,
        'booking_id': str(booking.id),
        'booking_status': booking.status,
        'booking': BookingSerializer(booking).data,
    }

    try:
        async_to_sync(channel_layer.group_send)(
            f"booking_{booking.id}", {'type': 'booking_update', 'data': payload}
        )
        async_to_sync(channel_layer.group_send)(
            f"user_{recipient.uid}", {'type': 'booking_update', 'data': payload}
        )
    except Exception as e:
        logger.error(f"WebSocket broadcast failed: {e}")
