"""WSGI config — used by gunicorn for HTTP-only deploys (no WebSocket)."""
import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'motobee.settings')
application = get_wsgi_application()
