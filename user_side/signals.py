from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from datetime import datetime
from .models import OnlineUser
import logging

logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def handle_user_logged_in(sender, user, request, **kwargs):
    """Update user's online status when they log in via any method"""
    try:
        OnlineUser.objects.update_or_create(
            user=user,
            defaults={
                'is_online': True,
                'last_seen': datetime.now(),
                'connection_count': 1  # Initialize connection count
            }
        )
        logger.info(f"User {user.id} logged in and marked as online")
    except Exception as e:
        logger.error(f"Error updating online status on login: {e}")

@receiver(user_logged_out)
def handle_user_logged_out(sender, user, request, **kwargs):
    """Update user's online status when they log out"""
    try:
        online_user = OnlineUser.objects.filter(user=user).first()
        if online_user and online_user.connection_count <= 1:
            online_user.is_online = False
            online_user.last_seen = datetime.now()
            online_user.connection_count = 0
            online_user.save()
        elif online_user:
            online_user.connection_count = max(0, online_user.connection_count - 1)
            online_user.save()
        logger.info(f"User {user.id} logged out and marked as offline")
    except Exception as e:
        logger.error(f"Error updating online status on logout: {e}")