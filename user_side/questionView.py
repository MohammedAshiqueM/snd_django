from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.views.decorators.csrf import csrf_exempt
from .models import (
    Follower, Tag, UserSkill, Blog, BlogTag, BlogVote, BlogComment, 
    Question, QuestionTag, QuestionVote, Answer, SkillSharingRequest, RequestTag,
    Schedule, Rating, Report, TimeTransaction
)
from .serializers import (
    MyTokenObtainPairSerializer,TagSerializer,BlogSerializer,UserSerializer,
    RatingSerializer,ReportSerializer,BlogTagSerializer,BlogVoteSerializer,
    FollowerSerializer,QuestionSerializer,ScheduleSerializer,UserSkillSerializer,
    RequestTagSerializer,BlogCommentSerializer,QuestionTagSerializer,QuestionVoteSerializer,
    AnswerSerializer,SkillSharingRequest,TimeTransactionSerializer,SkillSharingRequestSerializer
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

User = get_user_model()

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def question_creation(request):
    """
    To create questions
    """
    user = request.user
    data = request.data.copy()
    
    try:
        tags = json.loads(data.get("tags",[]))
    except json.JSONDecodeError:
        return api_response(
            status.HTTP_400_BAD_REQUEST,
            "Invalid tags"
        )
        
    serializer = QuestionSerializer(data=data)
    
    try:
        if serializer.is_valid():
            question = serializer.save(user=user)
            
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
                    f"Invalid tags: {', '.join(invalid_tags)}"
                )
                
            for tag in valid_tags:
                QuestionTag.objects.create(question=question, tag=tag)
                
            return api_response(status.HTTP_201_CREATED,"Question created successfully",serializer.data)
        else:
            return api_response(status.HTTP_400_BAD_REQUEST,"Unexpected error",serializer.errors)
    except Exception as e:
        return api_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            str(e)
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_all_question(request):
    """
    To get all questions with search and category filter
    """
    search_query = request.query_params.get('search', None)
    category = request.query_params.get('category',None)
    page = request.query_params.get('page', 1)
    limit = request.query_params.get('limit', 5)
    
    try:
        page = int(page)
        limit = int(limit)
    except ValueError:
        page = 1
        limit = 5
        
    questions = Question.objects.all()
    
    if search_query:
        questions = questions.filter(
            Q(title__icontains=search_query) | Q(tags__name__icontains=search_query)
        ).distinct()
        
    if category and category != 'All' :
        questions = questions.filter(tags__name=category)
        
    total_questions = questions.count()
    total_pages = math.ceil(total_questions / limit)
    
    start = (page - 1)*limit
    end = start + limit
    
    paginated_questions = questions[start:end]
    
    serilaizer = QuestionSerializer(paginated_questions, many=True)
    
    return Response({
        'data':serilaizer.data,
        'total_pages':total_pages,
        'current_page':page,
        'total_questions':total_questions
    })
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def question_detail(request, pk):
    # print("Starting question_detail")
    # print("User authenticated:", request.user.is_authenticated)
    
    try:
        question = Question.objects.get(pk=pk)
        print(question.id)
        
        with transaction.atomic():
            question.view_count = models.F('view_count') + 1
            question.save(update_fields=['view_count'])
        
        question.refresh_from_db()
        serializer = QuestionSerializer(question)
        data = serializer.data
        
        # print("Checking for vote")
        # print("User:", request.user.id)
        existing_vote = QuestionVote.objects.filter(
            user=request.user,
            question=question
        ).values('vote').first()
        # print("Vote query result:", existing_vote)
        
        user_vote = None
        if existing_vote:
            user_vote = 'upvote' if existing_vote['vote'] else 'downvote'
        
        is_following = Follower.objects.filter(
                follower=request.user, 
                following=question.user 
            ).exists()
            
        data['user_vote'] = user_vote
        data['is_following'] = is_following
        
        return JsonResponse({'data': data})
        
    except Question.DoesNotExist:
        raise Http404("Question not found")
        
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_answer(request, pk):
    """
    Adds answer to the question
    """
    try:
        question = Question.objects.get(pk=pk)
    except Question.DoesNotExist:
        return api_response(status.HTTP_404_NOT_FOUND,"Question not found",)
    
    serializer = AnswerSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user, question=question)
        return api_response(status.HTTP_201_CREATED,"answer added successfully",serializer.data,)
    return api_response(status.HTTP_400_BAD_REQUEST,"Error occur while adding answer",serializer.errors)

@api_view(['GET'])
def get_answers(request, pk):
    """
    To get all the answer of question
    """
    try:
        question = Question.objects.get(pk=pk)
    except Question.DoesNotExist:
        return api_response(status.HTTP_404_NOT_FOUND,"Question not found")

    answer = Answer.objects.filter(question=question).order_by('-created_at')
    serializer = BlogCommentSerializer(answer, many=True)
    return api_response(status.HTTP_200_OK,"success",serializer.data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def question_vote(request, pk):
    try:
        user = request.user
        question = Question.objects.get(pk=pk)
        vote_type = request.data.get('vote')

        if not vote_type or vote_type not in ['upvote', 'downvote']:
            return Response({"error": "Invalid vote type"}, status=status.HTTP_400_BAD_REQUEST)

        existing_vote = QuestionVote.objects.filter(user=user, question=question).first()

        if existing_vote:
            if (vote_type == 'upvote' and existing_vote.vote) or (vote_type == 'downvote' and not existing_vote.vote):
                existing_vote.delete()
            else:
                existing_vote.vote = vote_type == 'upvote'
                existing_vote.save()
        else:
            QuestionVote.objects.create(
                user=user,
                question=question,
                vote=vote_type == 'upvote'
            )

        vote_count = question.vote_count
        return Response({"vote_count": vote_count}, status=status.HTTP_200_OK)

    except Question.DoesNotExist:
        return Response({"error": "Question not found"}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)