# snd_backend/asgi.py
import os
import django

# Set the Django settings module path BEFORE importing anything that depends on Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'snd_backend.settings')
django.setup()  # This is crucial - it configures Django before we proceed

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from .JwtAuthMiddleWareWS import JWTAuthMiddleware
from channels.auth import AuthMiddlewareStack

# Import your websocket URL patterns after Django is configured
from user_side.routing import websocket_urlpatterns  # Adjust this import based on where your websocket_urlpatterns is defined

# Configure the ASGI application
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        JWTAuthMiddleware(
            URLRouter(
                websocket_urlpatterns
            )
        )
    ),
})