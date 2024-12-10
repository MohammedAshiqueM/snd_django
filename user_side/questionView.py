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
def  get_all_question(request):
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
    
def question_detail(request, pk):
    """
    To get a question details using slug
    """
    try:
        question = Question.objects.get(pk=pk)
        serializer = QuestionSerializer(question)
        return JsonResponse({
            'data': serializer.data
        })
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