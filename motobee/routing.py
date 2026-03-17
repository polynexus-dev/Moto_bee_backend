"""
motobee/routing.py — Django Channels WebSocket URL routing
"""
from django.urls import re_path
from notifications.consumers import BookingConsumer, UserNotificationConsumer

websocket_urlpatterns = [
    # Watch a specific booking (customer + owner both connect here)
    # Usage: ws://api.motobee.in/ws/booking/<uuid>/?token=<jwt>
    re_path(r'^ws/booking/(?P<booking_id>[0-9a-f-]+)/$', BookingConsumer.as_asgi()),

    # Personal notification stream
    # Usage: ws://api.motobee.in/ws/notifications/?token=<jwt>
    re_path(r'^ws/notifications/$', UserNotificationConsumer.as_asgi()),
]
