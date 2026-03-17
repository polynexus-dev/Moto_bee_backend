"""motobee/asgi.py — ASGI entry point (HTTP + WebSocket)"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'motobee.settings')
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.core.asgi import get_asgi_application
from .routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
