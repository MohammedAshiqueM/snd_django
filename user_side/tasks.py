from celery import shared_task
from django.core.mail import send_mass_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.apps import apps
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_skill_request_notifications(request_id):
    """
    Send email notifications to users with matching skills
    for a new skill sharing request
    """
    print("inside the send skill request")
    try:
        User = get_user_model()
        SkillSharingRequest = apps.get_model('user_side', 'SkillSharingRequest')
        RequestTag = apps.get_model('user_side', 'RequestTag')
        
        # Log the start of task
        logger.info(f"Starting email notifications for request {request_id}")
        
        request = SkillSharingRequest.objects.get(id=request_id)
        request_tags = RequestTag.objects.filter(request=request).values_list('tag_id', flat=True)
        
        matching_users = User.objects.filter(
            userskill__tag_id__in=request_tags
        ).exclude(
            id=request.user.id
        ).distinct()
        
        logger.info(f"Found {matching_users.count()} matching users")
        
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
            Your Platform Team
            """
            
            messages.append((
                subject,
                message,
                from_email,
                [user.email]
            ))
        
        if messages:
            logger.info(f"Attempting to send {len(messages)} emails")
            send_mass_mail(messages, fail_silently=False)
            logger.info("Emails sent successfully")
            
        return f"Sent notifications to {len(messages)} users"
        
    except Exception as e:
        logger.error(f"Error in send_skill_request_notifications: {str(e)}", exc_info=True)
        raise  # Re-raise the exception so Celery knows the task failed