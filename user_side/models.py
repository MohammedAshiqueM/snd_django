from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
    FileExtensionValidator,
    RegexValidator,
)
from django.utils import timezone
from django.utils.text import slugify
import os
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.core.exceptions import ValidationError
import uuid
from django.utils.timezone import now, timedelta
from django.db import transaction

def validate_image_size(image):
    """Validate that image file size is under 5MB"""
    file_size = image.size
    limit_mb = 5
    if file_size > limit_mb * 1024 * 1024:
        raise ValidationError(f"Maximum file size is {limit_mb}MB")


def user_profile_image_path(instance, filename):
    """Path to upload profile images: profile_images/uuid.extension"""
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4()}.{ext}'
    return os.path.join('profile_images', filename)


def user_banner_image_path(instance, filename):
    """Path to upload banner images: banner_images/uuid.extension"""
    ext = filename.split('.')[-1]
    filename = f'{uuid.uuid4()}_banner.{ext}'
    return os.path.join('banner_images', filename)


def blog_image_path(instance, filename):
    """Path to upload blog images with slugified title"""
    ext = filename.split('.')[-1]
    slug = slugify(instance.title)
    filename = f'{slug}_{timezone.now().timestamp()}.{ext}'
    return os.path.join('blog_images', str(instance.user.id), filename)

class User(AbstractUser):
    profile_image = models.ImageField(
        upload_to=user_profile_image_path,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']),
            validate_image_size
        ],
        null=True,
        blank=True,
        help_text="Profile image of the user (max 5MB)"
    )
    banner_image = models.ImageField(
        upload_to=user_banner_image_path,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']),
            validate_image_size
        ],
        null=True,
        blank=True,
        help_text="Banner image for the user profile page (max 5MB)"
    )
    linkedin_url = models.URLField(
        max_length=200,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^https:\/\/(www\.)?linkedin\.com\/.*$',
                message='Enter a valid LinkedIn URL (e.g., https://www.linkedin.com/in/username)'
            )
        ],
        help_text="Your LinkedIn profile URL"
    )
    github_url = models.URLField(
        max_length=200,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^https:\/\/(www\.)?github\.com\/.*$',
                message='Enter a valid GitHub URL (e.g., https://github.com/username)'
            )
        ],
        help_text="Your GitHub profile URL"
    )
    about = models.TextField(
        blank=True,
        help_text="Tell us about yourself"
    )
    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        null=True,
        blank=True,
        help_text="User rating (0-5)"
    )
    time_balance = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        help_text="User's remaining time balance in minutes"
    )
    available_time = models.PositiveIntegerField(
        default=0,
        help_text="User's available time balance in minutes"
    )
    held_time = models.PositiveIntegerField(
        default=0,
        help_text="User's time currently on hold for pending requests"
    )
    followers = models.ManyToManyField(
        'self',
        through='Follower',
        symmetrical=False,
        related_name='following'
    )
    skills = models.ManyToManyField('Tag', through='UserSkill')
    last_active = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time the user was active"
    )
    otp_code = models.CharField(
        max_length=5,
        blank=True,
        null=True,
        help_text="Temporary OTP for email verification"
    )
    otp_created_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Timestamp of when the OTP was created"
    )
    reset_token = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Token for password reset"
    )
    reset_token_expiration = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Expiration time for the reset token"
    )
    is_blocked = models.BooleanField(
        default=False,
        help_text="Indicates if the user is blocked by an admin"
    )

    class Meta:
        db_table = 'user'
        indexes = [
            models.Index(fields=['email'], name='user_email_idx'),
            models.Index(fields=['username'], name='user_username_idx'),
            models.Index(fields=['rating'], name='user_rating_idx'),
            models.Index(fields=['last_active'], name='user_last_active_idx'),
        ]
        
    def save(self, *args, **kwargs):
        """Resize and optimize profile and banner images before saving."""
        if self.profile_image and hasattr(self.profile_image, 'file'):
            self.profile_image = self._resize_image(
                self.profile_image,
                size=(300, 300),
                crop=True
            )
        if self.banner_image and hasattr(self.banner_image, 'file'):
            self.banner_image = self._resize_image(
                self.banner_image,
                size=(1200, 400),
                crop=False
            )
        super().save(*args, **kwargs)

    def _resize_image(self, image_field, size, crop=False):
        """Helper to resize and optimize images"""
        img = Image.open(image_field)
        
        # Convert to RGB if necessary
        if img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
            
        if crop:
            # Calculate dimensions to crop to desired aspect ratio
            target_ratio = size[0] / size[1]
            img_ratio = img.width / img.height
            
            if img_ratio > target_ratio:
                # Image is wider than needed
                new_width = int(img.height * target_ratio)
                left = (img.width - new_width) // 2
                img = img.crop((left, 0, left + new_width, img.height))
            elif img_ratio < target_ratio:
                # Image is taller than needed
                new_height = int(img.width / target_ratio)
                top = (img.height - new_height) // 2
                img = img.crop((0, top, img.width, top + new_height))
        
        img = img.resize(size, Image.LANCZOS)
        
        output = BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        return InMemoryUploadedFile(
            output,
            'ImageField',
            f"{os.path.splitext(image_field.name)[0]}.jpg",
            'image/jpeg',
            output.getbuffer().nbytes,
            None
        )
        
    def is_otp_valid(self):
        """Check if the OTP is still valid on time."""
        if self.otp_created_at:
            return now() < self.otp_created_at + timedelta(minutes=5)
        return False
    
    def generate_reset_token(self):
        """Generate a unique reset token and set expiration."""
        self.reset_token = str(uuid.uuid4())  # Generate a unique token
        self.reset_token_expiration = now() + timedelta(hours=1)  # Set 1-hour validity
        self.save()

    def is_reset_token_valid(self, token):
        """Check if the provided reset token is valid."""
        return (
            self.reset_token == token and
            self.reset_token_expiration and
            now() < self.reset_token_expiration
        )
        
    @property
    def follower_count(self):
        """Get the number of followers"""
        return self.followers.count()

    @property
    def following_count(self):
        """Get the number of users being followed"""
        return self.following.count()
    @property
    def total_time(self):
        """Total time balance including held time"""
        return self.available_time + self.held_time

    def has_sufficient_time(self, minutes):
        """Check if user has enough available time"""
        return self.available_time >= minutes

    def hold_time(self, minutes):
        """Put time on hold for a request"""
        if not self.has_sufficient_time(minutes):
            raise ValidationError(
                f"Insufficient time balance. Need {minutes} minutes but only have {self.available_time} available."
            )
        self.available_time -= minutes
        self.held_time += minutes
        self.save()

    def release_held_time(self, minutes):
        """Release held time back to available"""
        self.held_time -= minutes
        self.available_time += minutes
        self.save()

    def transfer_time(self, recipient, minutes):
        """Transfer time to another user"""
        if self.held_time < minutes:
            raise ValidationError("Insufficient held time for transfer")
        
        self.held_time -= minutes
        recipient.available_time += minutes
        
        self.save()
        recipient.save()
class Follower(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_followers')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_following')
    followed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'followers'
        unique_together = ('follower', 'following')

class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    about = models.TextField(
        blank=True,
        help_text="Discription about the tags"
    )
    class Meta:
        db_table = 'tags'

class UserSkill(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        db_table = 'user_skills'
        unique_together = ('user', 'tag')
        
class Blog(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blogs'
    )
    title = models.CharField(
        max_length=50,
        help_text="Blog post title"
    )
    slug = models.SlugField(
        max_length=60,
        unique=True,
        blank=True,
        help_text="URL-friendly version of the title"
    )
    body_content = models.TextField(
        help_text="Main content of the blog post"
    )
    image = models.ImageField(
        upload_to=blog_image_path,
        validators=[
            FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png']),
            validate_image_size
        ],
        null=True,
        blank=True,
        help_text="Featured image for the blog post (max 5MB)"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(Tag, through='BlogTag')
    is_published = models.BooleanField(
        default=True,
        help_text="Whether the blog post is publicly visible"
    )
    view_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of times this post has been viewed"
    )

    class Meta:
        db_table = 'blogs'
        indexes = [
            models.Index(fields=['created_at'], name='blog_date_idx'),
            models.Index(fields=['user'], name='blog_user_idx'),
            models.Index(fields=['slug'], name='blog_slug_idx'),
            models.Index(fields=['is_published'], name='blog_published_idx'),
        ]
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        # Generate slug if it doesn't exist
        if not self.slug:
            self.slug = slugify(self.title)
            
            # Ensure unique slug
            original_slug = self.slug
            counter = 1
            while Blog.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        # Resize blog image if present
        if self.image and hasattr(self.image, 'file'):
            self.image = User._resize_image(
                self,
                self.image,
                size=(800, 600),
                crop=False
            )
            
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def vote_count(self):
        """Get the total number of votes (positive - negative)"""
        return self.blogvote_set.filter(vote=True).count() - \
               self.blogvote_set.filter(vote=False).count()
               

class BlogTag(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        db_table = 'blog_tags'
        unique_together = ('blog', 'tag')

class BlogVote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    vote = models.BooleanField()

    class Meta:
        db_table = 'blog_votes'
        unique_together = ('user', 'blog')

class BlogComment(models.Model):
    blog = models.ForeignKey(Blog, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'blog_comments'

class Question(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    body_content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    tags = models.ManyToManyField(Tag, through='QuestionTag')
    view_count = models.PositiveIntegerField(default=0)
    class Meta:
        db_table = 'questions'
        
    @property
    def vote_count(self):
        """Get the total number of votes (positive - negative)"""
        return self.questionvote_set.filter(vote=True).count() - \
               self.questionvote_set.filter(vote=False).count()

class QuestionTag(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        db_table = 'question_tags'
        unique_together = ('question', 'tag')

class QuestionVote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    vote = models.BooleanField()

    class Meta:
        db_table = 'question_vote'
        unique_together = ('user', 'question')

class Answer(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'answer'
 
def default_preferred_time():
    return timezone.now() + timedelta(days=1)       
class SkillSharingRequest(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DR', 'Draft'
        PENDING = 'PE', 'Pending'  # Time held, looking for teacher
        SCHEDULED = 'SC', 'Scheduled'  # Has accepted schedule
        COMPLETED = 'CO', 'Completed'
        CANCELLED = 'CA', 'Cancelled'

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='learning_requests'
    )
    title = models.CharField(max_length=100)
    body_content = models.TextField()
    duration_minutes = models.PositiveIntegerField(
        default=5,
        help_text="Requested session duration in minutes"
    )
    preferred_time = models.DateTimeField(
        default=default_preferred_time,
        help_text="Preferred time for the session"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(
        max_length=2,
        choices=Status.choices,
        default=Status.DRAFT
    )
    tags = models.ManyToManyField(Tag, through='RequestTag')

    class Meta:
        db_table = 'skill_sharing_requests'
        indexes = [
            models.Index(fields=['status'], name='request_status_idx'),
            models.Index(fields=['preferred_time'], name='request_time_idx'),
            models.Index(fields=['created_at'], name='request_created_idx'),
        ]

    def clean(self):
        if self.preferred_time <= timezone.now():
            raise ValidationError("Preferred time must be in the future")
        
        if self.duration_minutes <= 0:
            raise ValidationError("Duration must be greater than 0 minutes")

    @transaction.atomic
    def publish(self):
        """Publish request and hold time"""
        if self.status != self.Status.DRAFT:
            raise ValidationError("Only draft requests can be published")
            
        # Check and hold time
        self.user.hold_time(self.duration_minutes)
        self.status = self.Status.PENDING
        self.save()

    @transaction.atomic
    def cancel(self):
        """Cancel request and release held time"""
        if self.status not in [self.Status.DRAFT, self.Status.PENDING]:
            raise ValidationError("Only draft or pending requests can be cancelled")
            
        if self.status == self.Status.PENDING:
            self.user.release_held_time(self.duration_minutes)
            
        self.status = self.Status.CANCELLED
        self.save()

class RequestTag(models.Model):
    request = models.ForeignKey(SkillSharingRequest, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)

    class Meta:
        db_table = 'request_tags'
        unique_together = ('request', 'tag')

class Schedule(models.Model):
    class Status(models.TextChoices):
        PROPOSED = 'PR', 'Proposed'
        ACCEPTED = 'AC', 'Accepted'
        REJECTED = 'RE', 'Rejected'
        COMPLETED = 'CO', 'Completed'
        CANCELLED = 'CA', 'Cancelled'

    request = models.ForeignKey(SkillSharingRequest, on_delete=models.CASCADE)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teaching_schedules')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='learning_schedules')
    scheduled_time = models.DateTimeField()
    timezone = models.CharField(max_length=50)
    status = models.CharField(max_length=2, choices=Status.choices, default=Status.PROPOSED)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = 'schedules'
        unique_together = ('request', 'teacher')
        
    def clean(self):
        if self.scheduled_time <= timezone.now():
            raise ValidationError("Schedule time must be in the future")
            
        if self.teacher == self.request.user:
            raise ValidationError("Teacher cannot be the same as student")

    @transaction.atomic
    def accept(self):
        """Accept the proposed schedule"""
        if self.status != self.Status.PROPOSED:
            raise ValidationError("Only proposed schedules can be accepted")
            
        # Reject other proposals
        Schedule.objects.filter(
            request=self.request,
            status=self.Status.PROPOSED
        ).exclude(id=self.id).update(status=self.Status.REJECTED)
        
        self.status = self.Status.ACCEPTED
        self.request.status = SkillSharingRequest.Status.SCHEDULED
        
        self.save()
        self.request.save()

    @transaction.atomic
    def complete(self):
        """Mark schedule as completed and transfer time"""
        if self.status != self.Status.ACCEPTED:
            raise ValidationError("Only accepted schedules can be completed")
            
        # Transfer held time from student to teacher
        self.request.user.transfer_time(
            self.teacher,
            self.request.duration_minutes
        )
        
        self.status = self.Status.COMPLETED
        self.completed_at = timezone.now()
        self.request.status = SkillSharingRequest.Status.COMPLETED
        
        self.save()
        self.request.save()
        
        # Create transaction records
        TimeTransaction.objects.create(
            from_user=self.request.user,
            to_user=self.teacher,
            amount=self.request.duration_minutes,
            schedule=self,
            request=self.request
        )
    
    @transaction.atomic
    def reject(self):
        """Accept the proposed schedule"""
        if self.status != self.Status.PROPOSED:
            raise ValidationError("Only proposed schedules can be accepted")
            
        # Reject other proposals
        Schedule.objects.filter(
            request=self.request,
            status=self.Status.REJECTED
        ).exclude(id=self.id).update(status=self.Status.REJECTED)
        
        self.status = self.Status.REJECTED
        
        self.save()
        self.request.save()

        
class Rating(models.Model):
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name='teacher_ratings')
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name='student_ratings')
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'ratings'

class Report(models.Model):
    reported_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_received')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports_made')
    note = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'reports'

class TimeTransaction(models.Model):
    class TransactionType(models.TextChoices):
        CREDIT = 'CR', 'Credit'
        DEBIT = 'DE', 'Debit'

    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='time_sent',
        default=1
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='time_received',
        default=2
    )
    amount = models.PositiveIntegerField()
    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'time_transactions'
              
class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']
    
    @classmethod
    def mark_messages_as_read(cls, sender_id, receiver_id):
        cls.objects.filter(
            sender_id=sender_id,
            receiver_id=receiver_id,
            is_read=False
        ).update(is_read=True)
        
    
class OnlineUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(auto_now=True)
    connection_count = models.IntegerField(default=0) 
    
    def __str__(self):
        return f"{self.user.username} - {'Online' if self.is_online else 'Offline'}"
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications', null=True)
    message = models.TextField()
    type = models.CharField(max_length=50)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
class TimePlan(models.Model):
    name = models.CharField(max_length=100)
    minutes = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        help_text="Number of minutes in the plan"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1)],
        help_text="Price in INR"
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'time_plans'
        ordering = ['price']

class TimeOrder(models.Model):
    class OrderStatus(models.TextChoices):
        PENDING = 'PE', 'Pending'
        SUCCESSFUL = 'SU', 'Successful'
        FAILED = 'FA', 'Failed'

    user = models.ForeignKey('User', on_delete=models.CASCADE)
    plan = models.ForeignKey(TimePlan, on_delete=models.PROTECT)
    order_id = models.CharField(max_length=100, unique=True)
    razorpay_order_id = models.CharField(max_length=100, unique=True)
    razorpay_payment_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_signature = models.CharField(max_length=200, null=True, blank=True)
    status = models.CharField(
        max_length=2,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'time_orders'