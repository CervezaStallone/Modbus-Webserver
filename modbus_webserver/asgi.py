"""
ASGI config for modbus_webserver project.
Configures both HTTP and WebSocket protocols.
"""

import os

from django.core.asgi import get_asgi_application

# Set Django settings before importing Channels
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "modbus_webserver.settings")

# Initialize Django ASGI application early to populate AppRegistry
django_asgi_app = get_asgi_application()

from channels.auth import AuthMiddlewareStack

# Import after Django setup
from channels.routing import ProtocolTypeRouter, URLRouter

from modbus_app import routing

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(routing.websocket_urlpatterns)),
    }
)
