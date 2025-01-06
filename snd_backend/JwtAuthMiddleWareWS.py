import os
import logging
from http.cookies import SimpleCookie
from jwt import decode, ExpiredSignatureError, InvalidTokenError

# Ensure DJANGO_SETTINGS_MODULE is set
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "snd_backend.settings")

from django.conf import settings
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model

logger = logging.getLogger(__name__)

# Dynamically fetch the User model
User = get_user_model()

# @database_sync_to_async
# def get_user_from_jwt(token):
#     try:
#         decoded = decode(token, settings.SECRET_KEY, algorithms=["HS256"])
#         user_id = decoded.get("user_id")
#         return User.objects.get(id=user_id)
#     except User.DoesNotExist:
#         logger.warning("User does not exist for the given token.")
#         return AnonymousUser()
#     except ExpiredSignatureError:
#         logger.warning("Token has expired.")
#         return AnonymousUser()
#     except InvalidTokenError:
#         logger.warning("Invalid token.")
#         return AnonymousUser()
#     except Exception as e:
#         logger.error(f"Unexpected error while decoding token: {e}")
#         return AnonymousUser()

# class JWTAuthMiddleware:
#     def __init__(self, inner):
#         self.inner = inner

#     def __call__(self, scope):
#         return JWTAuthMiddlewareInstance(scope, self.inner)

# class JWTAuthMiddlewareInstance:
#     def __init__(self, scope, inner):
#         self.scope = scope
#         self.inner = inner

#     async def __call__(self, receive, send):
#         headers = dict(self.scope.get("headers", []))
#         token = None

#         if b"cookie" in headers:
#             cookies_str = headers[b"cookie"].decode("utf-8")
#             cookie = SimpleCookie()
#             cookie.load(cookies_str)
#             token = cookie.get("access_token").value if "access_token" in cookie else None

#         if token:
#             self.scope["user"] = await get_user_from_jwt(token)
#         else:
#             self.scope["user"] = AnonymousUser()

#         logger.debug(f"User set in scope: {self.scope.get('user')}")
#         inner = self.inner(self.scope)
#         return await inner(receive, send)

from urllib.parse import parse_qs
from jwt import decode, exceptions as jwt_exceptions
from django.conf import settings
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from user_side.models import User  # Adjust this path

class JWTAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        headers = dict(scope["headers"])
        cookies = headers.get(b"cookie", b"").decode()
        token = None

        for cookie in cookies.split("; "):
            if cookie.startswith("access_token="):
                token = cookie.split("=")[1]
                break

        if token:
            try:
                payload = decode(token, settings.SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get("user_id")
                scope["user"] = await self.get_user(user_id)
            except (jwt_exceptions.ExpiredSignatureError, jwt_exceptions.InvalidTokenError):
                scope["user"] = None
        else:
            scope["user"] = None

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
