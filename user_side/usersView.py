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
from rest_framework.pagination import PageNumberPagination

User = get_user_model()

class UserPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_users(request):
    """
    To list users
    """
    search_query = request.query_params.get('search', '').lower()
    category = request.query_params.get('category', '').lower()
    users = User.objects.all()

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query) | 
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) |
            Q(skills__tag__name__icontains=search_query) 
        )

    paginator = UserPagination()
    result_page = paginator.paginate_queryset(users, request)
    serializer = UserSerializer(result_page, many=True)
    return paginator.get_paginated_response(serializer.data)