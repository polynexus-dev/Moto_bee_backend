"""
notifications/tasks.py
──────────────────────
Push notification sender for MOTOBEE.

Called after every booking status change (from bookings/views.py).

Flow per event:
  1. Look up the customer's FCM tokens from the FCMToken table
  2. Send Firebase push notification via notifications/fcm.py
  3. Save a Notification record to DB (for in-app bell icon)
  4. Broadcast the booking update over WebSocket

All push notifications go ONLY to the customer.
  - new_booking  → triggered by customer action, still notifies customer
                   (confirmation that booking was submitted)
  - accepted     → garage owner action → notify customer
  - rejected     → garage owner action → notify customer
  - in_progress  → garage owner action → notify customer
  - completed    → garage owner action → notify customer
  - cancelled    → customer action, no push needed (they did it themselves)
"""
import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from . import fcm as fcm_service

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Notification templates
# Every entry has customer_title / customer_body because ALL pushes go to
# the customer.  The cancelled event has no push (customer triggered it).
# ─────────────────────────────────────────────────────────────────────────────

NOTIFICATION_TEMPLATES = {
    'new_booking': {
        'customer_title': '📋 Booking Submitted',
        'customer_body':  'Your booking at {garage} for {date} at {time} is pending confirmation.',
    },
    'accepted': {
        'customer_title': '✅ Booking Confirmed!',
        'customer_body':  'Your booking at {garage} on {date} at {time} is confirmed.',
    },
    'rejected': {
        'customer_title': '❌ Booking Declined',
        'customer_body':  'Your booking at {garage} was declined.{note}',
    },
    'in_progress': {
        'customer_title': '🔧 Service Started',
        'customer_body':  'Your vehicle is now being serviced at {garage}.',
    },
    'completed': {
        'customer_title': '🎉 Vehicle Ready!',
        'customer_body':  'Your vehicle service at {garage} is complete. Ready for pickup!',
    },
    # 'cancelled' intentionally omitted — no push sent when customer cancels
}


def _build_context(booking) -> dict:
    """Build the template interpolation context from a booking instance."""
    rejection_note = booking.rejection_note.strip() if booking.rejection_note else ''
    return {
        'garage':  booking.garage.name,
        'date':    str(booking.date),
        'time':    booking.time,
        'vehicle': booking.vehicle_type,
        # Prefix with a space so the body reads naturally when note is present
        'note':    f' Reason: {rejection_note}' if rejection_note else '',
    }


def _get_fcm_tokens(user) -> list[str]:
    """
    Return all active FCM tokens for a user.
    Tokens are stored in the FCMToken table (one row per device).
    """
    from .models import FCMToken
    return list(FCMToken.objects.filter(user=user).values_list('token', flat=True))


def _send_fcm_push(tokens: list[str], title: str, body: str, data: dict) -> None:
    """
    Dispatch to single or multicast FCM send depending on token count.
    Logs errors but never raises — a failed push must not break the booking flow.
    """
    if not tokens:
        logger.info('[FCM] No tokens for user — skipping push.')
        return

    try:
        if len(tokens) == 1:
            fcm_service.send_to_device(tokens[0], title, body, data)
        else:
            fcm_service.send_to_multiple_devices(tokens, title, body, data)
    except Exception as exc:
        logger.error('[FCM] Push failed: %s', exc)


def _save_notification(user, booking, event_type: str, title: str, body: str) -> None:
    """Persist a Notification row for the in-app notification centre."""
    from .models import Notification
    try:
        Notification.objects.create(
            recipient=user,
            booking=booking,
            notification_type=event_type,
            title=title,
            body=body,
        )
    except Exception as exc:
        logger.error('[FCM] DB save failed: %s', exc)


def _broadcast_ws(booking, event_type: str, recipient) -> None:
    """
    Broadcast a booking update to two WebSocket groups:
      booking_{booking_id}  — any client watching this specific booking
      user_{uid}            — the recipient's personal notification channel
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        return

    from bookings.serializers import BookingSerializer

    payload = {
        'type':           'booking.update',
        'event':          event_type,
        'booking_id':     str(booking.id),
        'booking_status': booking.status,
        'booking':        BookingSerializer(booking).data,
    }

    try:
        async_to_sync(channel_layer.group_send)(
            f'booking_{booking.id}',
            {'type': 'booking_update', 'data': payload},
        )
        async_to_sync(channel_layer.group_send)(
            f'user_{recipient.uid}',
            {'type': 'booking_update', 'data': payload},
        )
    except Exception as exc:
        logger.error('[FCM] WebSocket broadcast failed: %s', exc)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point — called from bookings/views.py
# ─────────────────────────────────────────────────────────────────────────────

def send_booking_notification(booking, event_type: str) -> None:
    """
    Main entry point called from booking action views.

    All push notifications are sent only to the customer.
    The 'cancelled' event skips the push (customer triggered it themselves)
    but still saves a DB record and broadcasts via WebSocket.

    Args:
        booking:    Booking model instance (must have .customer, .garage loaded)
        event_type: One of new_booking / accepted / rejected / in_progress /
                    completed / cancelled
    """
    template = NOTIFICATION_TEMPLATES.get(event_type)
    customer = booking.customer
    ctx = _build_context(booking)

    fcm_data = {
        'booking_id': str(booking.id),
        'event':      event_type,
        'screen':     'bookings',
    }

    if template:
        title = template['customer_title']
        body  = template['customer_body'].format(**ctx)

        # 1. Send FCM push to all customer devices
        tokens = _get_fcm_tokens(customer)
        _send_fcm_push(tokens, title, body, fcm_data)

        # 2. Save in-app notification record
        _save_notification(customer, booking, event_type, title, body)
    else:
        # 'cancelled' or any unknown event — no push, still save a minimal record
        logger.info('[FCM] No push template for event "%s" — skipping push.', event_type)
        _save_notification(
            customer, booking, event_type,
            title='Booking Update',
            body=f'Your booking status changed to {booking.status}.',
        )

    # 3. WebSocket broadcast (always, regardless of push)
    _broadcast_ws(booking, event_type, customer)