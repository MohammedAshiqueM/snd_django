import os
import logging
from http.cookies import SimpleCookie
from jwt import decode, ExpiredSignatureError, InvalidTokenError
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.conf import settings
from datetime import datetime

# Ensure DJANGO_SETTINGS_MODULE is set
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "snd_backend.settings")

logger = logging.getLogger(__name__)
User = get_user_model()

class JWTAuthMiddleware(BaseMiddleware):
    def __init__(self, inner):
        super().__init__(inner)
        self.online_users = {}  # Store online users and their connection counts

    async def __call__(self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        cookies = headers.get(b"cookie", b"").decode("utf-8", errors="ignore")
        token = self.get_token_from_cookies(cookies)
        
        # Store the previous user for comparison
        previous_user = scope.get("user", AnonymousUser())
        authenticated_user = None
        
        if token:
            authenticated_user = await self.authenticate_user(token)
        
        # Update user in scope and handle online status
        if authenticated_user and authenticated_user != previous_user:
            scope["user"] = authenticated_user
            await self.handle_user_connected(authenticated_user)
        elif previous_user.is_authenticated and not authenticated_user:
            scope["user"] = AnonymousUser()
            await self.handle_user_disconnected(previous_user)
        
        # Store the disconnect handler in scope for cleanup
        if authenticated_user:
            scope["disconnect_handler"] = lambda: self.handle_user_disconnected(authenticated_user)
        
        return await super().__call__(scope, receive, send)

    @staticmethod
    def get_token_from_cookies(cookies):
        """Extract token from the cookies string."""
        try:
            cookie = SimpleCookie()
            cookie.load(cookies)
            return cookie.get("access_token").value
        except (AttributeError, KeyError):
            return None

    async def authenticate_user(self, token):
        """Authenticate user using the JWT token."""
        try:
            payload = decode(token, settings.SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")
            if user_id:
                return await self.get_user(user_id)
        except ExpiredSignatureError:
            logger.warning("Token has expired")
        except InvalidTokenError:
            logger.warning("Invalid token")
        except Exception as e:
            logger.error(f"Error decoding token: {e}")
        return None

    @database_sync_to_async
    def get_user(self, user_id):
        """Fetch the user from the database."""
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            logger.warning(f"User with ID {user_id} does not exist")
            return None

    @database_sync_to_async
    def handle_user_connected(self, user):
        """Handle user connection and update online status."""
        from user_side.models import OnlineUser  # Import here to avoid circular imports
        
        try:
            # Increment connection count
            self.online_users[user.id] = self.online_users.get(user.id, 0) + 1
            
            # Update online status only if this is the first connection
            if self.online_users[user.id] == 1:
                OnlineUser.objects.update_or_create(
                    user=user,
                    defaults={
                        'is_online': True,
                        'last_seen': datetime.now()
                    }
                )
                user_logged_in.send(sender=user.__class__, request=None, user=user)
                logger.info(f"User {user.id} is now online")
        except Exception as e:
            logger.error(f"Error handling user connection: {e}")

    @database_sync_to_async
    def handle_user_disconnected(self, user):
        """Handle user disconnection and update online status."""
        from user_side.models import OnlineUser  # Import here to avoid circular imports
        
        try:
            # Decrement connection count
            self.online_users[user.id] = max(0, self.online_users.get(user.id, 1) - 1)
            
            # Update online status only if this was the last connection
            if self.online_users[user.id] == 0:
                OnlineUser.objects.update_or_create(
                    user=user,
                    defaults={
                        'is_online': False,
                        'last_seen': datetime.now()
                    }
                )
                user_logged_out.send(sender=user.__class__, request=None, user=user)
                logger.info(f"User {user.id} is now offline")
        except Exception as e:
            logger.error(f"Error handling user disconnection: {e}")