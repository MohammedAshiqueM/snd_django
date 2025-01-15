from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import (
    User, Follower, Tag, UserSkill, Blog, BlogTag, BlogVote, BlogComment, 
    Question, QuestionTag, QuestionVote, Answer, SkillSharingRequest, RequestTag,
    Schedule, Rating, Report, TimeTransaction, Message, OnlineUser, Notification
)
from enum import Enum
from django.db.models import Q
from django.utils import timezone

class UserRole(Enum):
    ADMIN = "admin"
    STAFF = "staff"
    USER = "user"

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['email'] = user.email
        token['username'] = user.username
        
        # Define role based on user permissions
        if user.is_superuser:
            role = UserRole.ADMIN.value
        elif user.is_staff:
            role = UserRole.STAFF.value
        else:
            role = UserRole.USER.value
            
        token['role'] = role
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        
        # Define role using the same logic as above
        if user.is_superuser:
            role = UserRole.ADMIN.value
        elif user.is_staff:
            role = UserRole.STAFF.value
        else:
            role = UserRole.USER.value
            
        data['user'] = {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'role': role
        }
        
        return data


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'about', 'created_at']

class UserSkillSerializer(serializers.ModelSerializer):
    tag = TagSerializer(read_only=True)
    
    class Meta:
        model = UserSkill
        fields = ['tag']

class UserSerializer(serializers.ModelSerializer):
    skills = serializers.SlugRelatedField(
        many=True, queryset=Tag.objects.all(), slug_field='name'
    )
    followers = serializers.IntegerField(source='follower_count', read_only=True)
    following = serializers.IntegerField(source='following_count', read_only=True)
    role = serializers.SerializerMethodField()
    last_message = serializers.CharField(read_only=True)
    last_message_time = serializers.DateTimeField(read_only=True)
    last_message_sender_id = serializers.IntegerField(read_only=True)
    unread_count = serializers.IntegerField(read_only=True)
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'profile_image', 'banner_image', 'linkedin_url', 
            'github_url', 'about', 'rating', 'time_balance', 
            'skills', 'followers', 'following', 
            'last_active','role','is_blocked',
            'last_message', 'last_message_time', 
            'last_message_sender_id', 'unread_count'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
        }
    
    # def get_skills(self, obj):
    #     # Return the names of the skills instead of IDs
    #     return [tag.name for tag in obj.skills.all()]
    def get_skills(self, obj):
        return UserSkillSerializer(obj.skills.through.objects.filter(user=obj), many=True).data
    
    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data.get('password'))
        return super().create(validated_data)
 
    def update(self, instance, validated_data):
        print(f"Validated data received for update: {validated_data}")
        skills = validated_data.pop("skills", [])
        print(f"Skills extracted for update: {skills}")

        instance.skills.set(skills)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def get_role(self, obj):
        return "admin" if obj.is_staff or obj.is_superuser else "user"
    
    def get_message_data(self, obj):
        # Get the most recent message for this user (either sent or received)
        last_message = Message.objects.filter(
            Q(sender=obj) | Q(receiver=obj)
        ).order_by('-timestamp').first()

        if last_message:
            return {
                'last_message': last_message.content,
                'last_message_time': last_message.timestamp,
                'last_message_sender_id': last_message.sender_id,
            }
        return {
            'last_message': None,
            'last_message_time': None,
            'last_message_sender_id': None,
        }

    def get_unread_count(self, obj):
        return Message.objects.filter(
            receiver=obj,
            is_read=False
        ).count()

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        message_data = self.get_message_data(instance)
        
        representation['last_message'] = message_data['last_message']
        representation['last_message_time'] = message_data['last_message_time']
        representation['last_message_sender_id'] = message_data['last_message_sender_id']
        representation['unread_count'] = self.get_unread_count(instance)
        
        return representation
class FollowerSerializer(serializers.ModelSerializer):
    follower = UserSerializer(read_only=True)
    following = UserSerializer(read_only=True)
    
    class Meta:
        model = Follower
        fields = ['follower', 'following', 'followed_at']

class BlogTagSerializer(serializers.ModelSerializer):
    tag = TagSerializer(read_only=True)
    
    class Meta:
        model = BlogTag
        fields = ['tag']

class BlogSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    vote_count = serializers.IntegerField(read_only=True)
    user_vote = serializers.SerializerMethodField()
    image = serializers.ImageField(required=False)
    comment_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Blog
        fields = [
            'id', 'user', 'title', 'slug', 'body_content', 
            'image', 'created_at', 'updated_at', 'tags', 
            'is_published', 'view_count', 'vote_count' , 'user_vote', 'comment_count'
        ]
    
    def get_tags(self, obj):
        return BlogTagSerializer(obj.tags.through.objects.filter(blog=obj), many=True).data
    
    def get_user_vote(self, obj):
        """Get the logged-in user's vote for the blog."""
        request = self.context.get('request', None)
        if request and request.user.is_authenticated:
            vote = obj.blogvote_set.filter(user=request.user).first()
            if vote:
                return 'upvote' if vote.vote else 'downvote'
        return None
    
    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image:
            image_url = obj.image.url
            if request:
                absolute_url = request.build_absolute_uri(image_url)
                print(f"Absolute URL: {absolute_url}")  # Debugging
                return absolute_url
            print(f"Relative URL: {image_url}")  # Debugging
            return image_url
        print("No image found.")  # Debugging
        return None

    def get_comment_count(self, obj):
        return obj.blogcomment_set.count()

class BlogVoteSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    blog = BlogSerializer(read_only=True)
    
    class Meta:
        model = BlogVote
        fields = ['user', 'blog', 'vote']

class BlogCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    blog = BlogSerializer(read_only=True)
    
    class Meta:
        model = BlogComment
        fields = ['id', 'blog', 'user', 'content', 'created_at']

class QuestionTagSerializer(serializers.ModelSerializer):
    tag = TagSerializer(read_only=True)
    
    class Meta:
        model = QuestionTag
        fields = ['tag']

class QuestionSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    answered = serializers.SerializerMethodField()
    answers_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = [
            'id', 'user', 'title', 'body_content', 
            'created_at', 'tags', 'view_count', 'answered', 'answers_count', 'vote_count'
        ]
    
    def get_tags(self, obj):
        return QuestionTagSerializer(obj.tags.through.objects.filter(question=obj), many=True).data

    def get_answered(self, obj):
        return obj.answer_set.exists()
    
    def get_answers_count(self, obj):
        return obj.answer_set.count()
    
class QuestionVoteSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    question = QuestionSerializer(read_only=True)
    
    class Meta:
        model = QuestionVote
        fields = ['user', 'question', 'vote']

class AnswerSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    question = QuestionSerializer(read_only=True)
    
    class Meta:
        model = Answer
        fields = ['id', 'question', 'user', 'content', 'created_at']
        
class SkillSharingRequestSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    tags = serializers.SerializerMethodField()
    preferred_time = serializers.DateTimeField(required=True)
    duration_minutes = serializers.IntegerField(required=True)
    # status = serializers.CharField(read_only=True)
    
    class Meta:
        model = SkillSharingRequest
        fields = [
            'id', 'user', 'title', 'body_content', 
            'duration_minutes', 'preferred_time', 'created_at',
            'updated_at', 'status', 'tags'
        ]
    def get_tags(self, obj):
        return RequestTagSerializer(obj.tags.through.objects.filter(request=obj), many=True).data

    def validate_preferred_time(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Preferred time must be in the future")
        return value

    def validate_duration_minutes(self, value):
        if value <= 0:
            raise serializers.ValidationError("Duration must be greater than 0 minutes")
        return value
    
class RequestTagSerializer(serializers.ModelSerializer):
    tag = TagSerializer(read_only=True)
    
    class Meta:
        model = RequestTag
        fields = ['tag']

class ScheduleSerializer(serializers.ModelSerializer):
    request = SkillSharingRequestSerializer(read_only=True)
    teacher = UserSerializer(read_only=True)
    student = UserSerializer(read_only=True)
    status = serializers.CharField(read_only=True)
    
    class Meta:
        model = Schedule
        fields = [
            'id', 'request', 'teacher', 'student', 
            'scheduled_time', 'timezone', 'status', 'note'
        ]

    def validate_scheduled_time(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("Schedule time must be in the future")
        return value

class RatingSerializer(serializers.ModelSerializer):
    teacher = UserSerializer(read_only=True)
    student = UserSerializer(read_only=True)
    
    class Meta:
        model = Rating
        fields = ['teacher', 'student', 'rating', 'created_at']

class ReportSerializer(serializers.ModelSerializer):
    reported_user = UserSerializer(read_only=True)
    reported_by = UserSerializer(read_only=True)
    
    class Meta:
        model = Report
        fields = ['reported_user', 'reported_by', 'note', 'created_at']

class TimeTransactionSerializer(serializers.ModelSerializer):
    from_user = UserSerializer(read_only=True)
    to_user = UserSerializer(read_only=True)
    schedule = ScheduleSerializer(read_only=True)
    request = SkillSharingRequestSerializer(read_only=True)
    
    class Meta:
        model = TimeTransaction
        fields = [
            'id', 'from_user', 'to_user', 'amount',
            'schedule', 'request', 'created_at'
        ]
        
class NotificationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    created_at_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Notification
        fields = ['id', 'user', 'message', 'type', 'is_read', 'created_at', 'created_at_formatted']
        read_only_fields = ['created_at']

    def get_created_at_formatted(self, obj):
        return obj.created_at.strftime("%Y-%m-%d %H:%M:%S")

    def update(self, instance, validated_data):
        instance.is_read = validated_data.get('is_read', instance.is_read)
        instance.save()
        return instance