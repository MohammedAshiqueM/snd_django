from celery import shared_task
from django.core.mail import send_mass_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.apps import apps
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, autoretry_for=(Exception,), retry_backoff=True)
def send_skill_request_notifications(self, request_id):
    logger.info("Starting task: send_skill_request_notifications")
    try:
        User = get_user_model()
        SkillSharingRequest = apps.get_model('user_side', 'SkillSharingRequest')
        RequestTag = apps.get_model('user_side', 'RequestTag')
        
        request = SkillSharingRequest.objects.get(id=request_id)
        request_tags = RequestTag.objects.filter(request=request).values_list('tag_id', flat=True)
        
        matching_users = User.objects.filter(
            userskill__tag_id__in=request_tags
        ).exclude(
            id=request.user.id
        ).distinct()
        
        messages = []
        subject = f"New Skill Sharing Request: {request.title}"
        from_email = settings.DEFAULT_FROM_EMAIL
        
        for user in matching_users:
            message = f"""
            Hello {user.username},

            A new skill sharing request matches your expertise!

            Title: {request.title}
            Duration: {request.duration_minutes} minutes
            Preferred Time: {request.preferred_time}

            Description:
            {request.body_content}

            If you're interested in teaching this session, please log in to respond.

            Best regards,
            Snd Team
            """
            
            messages.append((
                subject,
                message,
                from_email,
                [user.email]
            ))
        
        if messages:
            send_mass_mail(messages, fail_silently=False)
            logger.info(f"Emails sent successfully to {len(messages)} users")
            
        return f"Sent notifications to {len(messages)} users"
        
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise