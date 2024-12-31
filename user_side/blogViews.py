from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.views.decorators.csrf import csrf_exempt
from .models import (
    Follower, Tag, UserSkill, Blog, BlogTag, BlogVote, BlogComment, 
    Question, QuestionTag, QuestionVote, SkillSharingRequest, RequestTag,
    Schedule, Rating, Report, TimeTransaction
)
from .serializers import (
    MyTokenObtainPairSerializer,TagSerializer,BlogSerializer,UserSerializer,
    RatingSerializer,ReportSerializer,BlogTagSerializer,BlogVoteSerializer,
    FollowerSerializer,QuestionSerializer,ScheduleSerializer,UserSkillSerializer,
    RequestTagSerializer,BlogCommentSerializer,QuestionTagSerializer,QuestionVoteSerializer,
    SkillSharingRequest,TimeTransactionSerializer,SkillSharingRequestSerializer
    )
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse
import json
from .utils import api_response
from django.db.models import Q
from django.db import transaction, models
import math
from django.http import JsonResponse, Http404
from django.db.models import Count,F

User = get_user_model()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def blog_creation(request):
    """
    To create blog 
    """
    user = request.user
    data = request.data.copy()
    
    image = request.FILES.get('image')
    if image:
        if image.size > 5 * 1024 * 1024:  # 5MB
            return api_response(
                status.HTTP_400_BAD_REQUEST,
                "Image size should be less than 5MB",
            )
        
        allowed_types = ['image/jpeg', 'image/png', 'image/jpg']
        if image.content_type not in allowed_types:
            return api_response(
                status.HTTP_400_BAD_REQUEST,
                f"Invalid image type, {image.content_type} is not allowed. (Allowed types are : JPEG, PNG, JPG)",
            )
        
        data['image'] = image
    else:
        data.pop('image', None)

    try:
        tags = json.loads(data.get('tags', '[]'))
    except json.JSONDecodeError:
        return api_response(
            status.HTTP_400_BAD_REQUEST,
            "Invalid tags format",
        )

    serializer = BlogSerializer(data=data)
    
    try:
        if serializer.is_valid():
            blog = serializer.save(user=user)
            
            invalid_tags = []
            valid_tags = []
            for tag_name in tags:
                try:
                    tag = Tag.objects.get(name=tag_name)
                    valid_tags.append(tag)
                except Tag.DoesNotExist:
                    invalid_tags.append(tag_name)
            
            if invalid_tags:
                return api_response(
                    status.HTTP_406_NOT_ACCEPTABLE,
                    f"Invalid tags: {', '.join(invalid_tags)}",
                )
            
            for tag in valid_tags:
                BlogTag.objects.create(blog=blog, tag=tag)
            
            return api_response(status.HTTP_201_CREATED,"Blog created successfully",serializer.data,)
        else:
            return api_response(status.HTTP_400_BAD_REQUEST,"Unexpected error",serializer.errors,)
    except Exception as e:
        return api_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            str(e),
        )
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_blogs(request):
    """
    To get all blogs with search and category filter
    """
    search_query = request.query_params.get('search', None)
    category = request.query_params.get('category', None)
    page = request.query_params.get('page', 1)
    limit = request.query_params.get('limit', 5)
    
    try:
        page = int(page)
        limit = int(limit)
    except ValueError:
        page = 1
        limit = 5
    
    # print(f"Search Query: {search_query}, Category: {category}")
    # print(f"page: {page}, limit: {limit}")
    
    blogs = Blog.objects.all()
    
    if search_query:
        blogs = blogs.filter(
            Q(title__icontains=search_query) | Q(tags__name__icontains=search_query)
        ).distinct()
    
    if category and category != 'All':
        blogs = blogs.filter(tags__name=category)
    
    total_blogs = blogs.count()
    total_pages = math.ceil(total_blogs / limit)
    
    start = (page - 1) * limit
    end = start + limit
    
    paginated_blogs = blogs[start:end]
    
    serializer = BlogSerializer(paginated_blogs, many=True)
    
    return Response({
        'data': serializer.data,
        'total_pages': total_pages,
        'current_page': page,
        'total_blogs': total_blogs
    })
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def blog_detail(request, slug):
    """
    To get a blog details using slug
    """
    try:
        blog = Blog.objects.get(slug=slug)
        
        with transaction.atomic():
            blog.view_count = models.F('view_count') + 1
            blog.save(update_fields=['view_count'])
        
        blog.refresh_from_db()
        
        serializer = BlogSerializer(blog)
        
        data = serializer.data
        
        user_vote = None
        if request.user.is_authenticated:
            existing_vote = BlogVote.objects.filter(
                user=request.user, 
                blog=blog
            ).first()
            
            if existing_vote:
                user_vote = 'upvote' if existing_vote.vote else 'downvote'

            # blog_author = blog.user 
            # is_following = blog_author.followers.filter(id=request.user.id).exists()
            is_following = Follower.objects.filter(
                follower=request.user, 
                following=blog.user 
            ).exists()
            
        data['user_vote'] = user_vote
        data['is_following'] = is_following
        
        return JsonResponse({
            'data': data
        })
        
    except Blog.DoesNotExist:
        raise Http404("Blog not found")
    
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_comment(request, slug):
    """
    Adds comment to the blog
    """
    try:
        blog = Blog.objects.get(slug=slug)
    except Blog.DoesNotExist:
        return api_response(status.HTTP_404_NOT_FOUND,"Blog not found",)
    
    serializer = BlogCommentSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user, blog=blog)
        return api_response(status.HTTP_201_CREATED,"comment added successfully",serializer.data,)
    return api_response(status.HTTP_400_BAD_REQUEST,"Error occur while adding comment",serializer.errors)

@api_view(['GET'])
def get_comments(request, slug):
    """
    To get all the comments of a blog
    """
    try:
        blog = Blog.objects.get(slug=slug)
    except Blog.DoesNotExist:
        return api_response(status.HTTP_404_NOT_FOUND,"Blog not found")

    comments = BlogComment.objects.filter(blog=blog).order_by('-created_at')
    serializer = BlogCommentSerializer(comments, many=True)
    return api_response(status.HTTP_200_OK,"success",serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vote_blog(request, slug):
    try:
        user = request.user
        blog = Blog.objects.get(slug=slug)
        vote_type = request.data.get('vote')

        if not vote_type or vote_type not in ['upvote', 'downvote']:
            return Response({"error": "Invalid vote type"}, status=status.HTTP_400_BAD_REQUEST)

        existing_vote = BlogVote.objects.filter(user=user, blog=blog).first()

        if existing_vote:
            if (vote_type == 'upvote' and existing_vote.vote) or (vote_type == 'downvote' and not existing_vote.vote):
                existing_vote.delete()
            else:
                existing_vote.vote = vote_type == 'upvote'
                existing_vote.save()
        else:
            BlogVote.objects.create(
                user=user,
                blog=blog,
                vote=vote_type == 'upvote'
            )

        vote_count = blog.vote_count
        return Response({"vote_count": vote_count}, status=status.HTTP_200_OK)

    except Blog.DoesNotExist:
        return Response({"error": "Blog not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
