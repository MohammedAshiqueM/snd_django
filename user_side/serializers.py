from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth.hashers import make_password
from rest_framework import serializers
from .models import (
    User, Follower, Tag, UserSkill, Blog, BlogTag, BlogVote, BlogComment, 
    Question, QuestionTag, QuestionVote, Answer, SkillSharingRequest, RequestTag,
    Schedule, Rating, Report, TimeTransaction
)

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['is_staff'] = user.is_staff
        token['is_superuser'] = user.is_superuser
        return token

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
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'profile_image', 'banner_image', 'linkedin_url', 
            'github_url', 'about', 'rating', 'time_balance', 
            'skills', 'followers', 'following', 
            'last_active'
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
    image = serializers.SerializerMethodField()
    
    class Meta:
        model = Blog
        fields = [
            'id', 'user', 'title', 'slug', 'body_content', 
            'image', 'created_at', 'updated_at', 'tags', 
            'is_published', 'view_count', 'vote_count' , 'user_vote'
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
    
    class Meta:
        model = Question
        fields = [
            'id', 'user', 'title', 'body_content', 
            'created_at', 'tags', 'view_count'
        ]
    
    def get_tags(self, obj):
        return QuestionTagSerializer(obj.tags.through.objects.filter(question=obj), many=True).data

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
    
    class Meta:
        model = SkillSharingRequest
        fields = [
            'id', 'user', 'title', 'body_content', 
            'requested_time', 'created_at', 'tags'
        ]
    
    def get_tags(self, obj):
        return RequestTagSerializer(obj.tags.through.objects.filter(request=obj), many=True).data

class RequestTagSerializer(serializers.ModelSerializer):
    tag = TagSerializer(read_only=True)
    
    class Meta:
        model = RequestTag
        fields = ['tag']

class ScheduleSerializer(serializers.ModelSerializer):
    request = SkillSharingRequestSerializer(read_only=True)
    teacher = UserSerializer(read_only=True)
    student = UserSerializer(read_only=True)
    
    class Meta:
        model = Schedule
        fields = [
            'id', 'request', 'teacher', 'student', 
            'scheduled_at', 'timezone', 'status', 'note'
        ]

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
    user = UserSerializer(read_only=True)
    related_schedule = ScheduleSerializer(read_only=True)
    
    class Meta:
        model = TimeTransaction
        fields = [
            'id', 'user', 'transaction_type', 
            'amount', 'related_schedule', 'created_at'
        ]