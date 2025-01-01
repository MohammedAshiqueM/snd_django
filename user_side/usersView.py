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
    To list users with search and category filter
    """
    search_query = request.query_params.get('search', '').lower()
    category = request.query_params.get('category', None)
    users = User.objects.filter(is_superuser=False)

    if search_query:
        users = users.filter(
            Q(username__icontains=search_query) | 
            Q(email__icontains=search_query) | 
            Q(first_name__icontains=search_query) | 
            Q(last_name__icontains=search_query) |
            Q(userskill__tag__name__icontains=search_query)
        ).distinct()

    if category and category != 'All':
        users = users.filter(userskill__tag__name=category).distinct()

    paginator = UserPagination()
    result_page = paginator.paginate_queryset(users, request)
    serializer = UserSerializer(result_page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_details(request,pk):
    """
    To give details of a perticular user
    """
    user = User.objects.get(pk=pk)
    follow_status = Follower.objects.filter(
        follower=request.user, 
        following=user
    ).exists()
            
    serializer = UserSerializer(user)
    data = serializer.data
    data['isFollowing'] = follow_status
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def report_user(request,pk):
    """
    To reporting another user by request.user
    """
    try:
        reported_user = User.objects.get(pk=pk)
    except User.DoesNotExist:
        return Response({"error": "Reported user does not exist."}, status=status.HTTP_404_NOT_FOUND)
    
    note = request.data.get('note')

    if not reported_user or not note:
        return Response(
            {"error": "Both 'reported_user_id' and 'note' are required."},
            status=status.HTTP_400_BAD_REQUEST
        )

    if reported_user == request.user:
        return Response({"error": "You cannot report yourself."}, status=status.HTTP_400_BAD_REQUEST)

    report = Report.objects.create(
        reported_user=reported_user,
        reported_by=request.user,
        note=note
    )

    serializer = ReportSerializer(report)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def follow_unfollow(request,pk):
    """
    To follow and unfollow user
    """
    try:
        target_user = User.objects.get(pk=pk)
        if target_user == request.user:
            return Response({"error": "You cannot follow yourself."}, status=status.HTTP_400_BAD_REQUEST)

        follow_relation, created = Follower.objects.get_or_create(
            follower=request.user,
            following=target_user
        )

        if not created:
            follow_relation.delete()
            return Response({"message": "Unfollowed successfully."}, status=status.HTTP_200_OK)

        return Response({"message": "Followed successfully."}, status=status.HTTP_201_CREATED)

    except User.DoesNotExist:
        return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)