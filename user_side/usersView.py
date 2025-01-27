from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from django.views.decorators.csrf import csrf_exempt
from .models import (
    Follower, Tag, UserSkill, Blog, BlogTag, BlogVote, BlogComment, 
    Question, QuestionTag, QuestionVote, Answer, SkillSharingRequest, RequestTag,
    Schedule, Rating, Report, TimeTransaction, Message, OnlineUser, Notification
)
from .serializers import (
    MyTokenObtainPairSerializer,TagSerializer,BlogSerializer,UserSerializer,
    RatingSerializer,ReportSerializer,BlogTagSerializer,BlogVoteSerializer,
    FollowerSerializer,QuestionSerializer,ScheduleSerializer,UserSkillSerializer,
    RequestTagSerializer,BlogCommentSerializer,QuestionTagSerializer,QuestionVoteSerializer,
    AnswerSerializer,SkillSharingRequest,TimeTransactionSerializer,SkillSharingRequestSerializer,NotificationSerializer
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
from django.utils import timezone
from datetime import timedelta
from django.db.models import (
    Q, F, Max, Count, OuterRef, Subquery, 
    CharField, DateTimeField, IntegerField
)
from django.db.models.functions import Coalesce
from urllib.parse import parse_qs
from django.core.exceptions import PermissionDenied
from . utils import validate_access_token
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
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def all_users(request):
    """
    List users with chat history, sorted by last message time
    """
    try:
        current_user = request.user
        if not current_user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)

        # Handle both ASGI and REST framework requests
        if hasattr(request, 'query_params'):
            # REST framework request
            search_query = request.query_params.get('search', '')
            page = int(request.query_params.get('page', 1))
        else:
            # ASGI request
            query_string = request.scope.get('query_string', b'').decode()
            query_params = parse_qs(query_string)
            search_query = query_params.get('search', [''])[0]
            page = int(query_params.get('page', ['1'])[0])

        # Get the latest message for each conversation
        latest_messages = Message.objects.filter(
            Q(sender=OuterRef('id'), receiver=current_user) |
            Q(sender=current_user, receiver=OuterRef('id'))
        ).order_by('-timestamp')

        # Base query for users
        users = User.objects.filter(
            is_superuser=False
        ).exclude(
            id=current_user.id
        ).annotate(
            last_message=Subquery(
                latest_messages.values('content')[:1],
                output_field=CharField()
            ),
            last_message_time=Subquery(
                latest_messages.values('timestamp')[:1],
                output_field=DateTimeField()
            ),
            last_message_sender_id=Subquery(
                latest_messages.values('sender_id')[:1],
                output_field=IntegerField()
            ),
            last_message_receiver_id=Subquery(
                latest_messages.values('receiver_id')[:1],
                output_field=IntegerField()
            ),
            unread_count=Count(
                'received_messages',
                filter=Q(
                    received_messages__is_read=False,
                    received_messages__sender=current_user
                )
            )
        )

        # Apply search filter if provided
        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )

        # Get users with messages first
        users_with_messages = users.filter(
            Q(sent_messages__receiver=current_user) |
            Q(received_messages__sender=current_user)
        ).distinct().order_by('-last_message_time')

        # Then get users without messages
        users_without_messages = users.exclude(
            Q(sent_messages__receiver=current_user) |
            Q(received_messages__sender=current_user)
        ).order_by('username')

        # Combine both querysets
        all_users = list(users_with_messages) + list(users_without_messages)

        # Implement pagination
        page_size = 20
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated_users = all_users[start_idx:end_idx]
        has_more = len(all_users) > end_idx

        # Serialize the data
        serializer = UserSerializer(paginated_users, many=True, context={'request': request})
        
        return Response({
            "data": serializer.data,
            "has_more": has_more
        })

    except Exception as e:
        return Response({"error": str(e)}, status=500)


@permission_classes([IsAuthenticated])
def websocket_handshake(request, user_id,target_id):
    token = request.COOKIES.get("access_token")
    if not token:
        return JsonResponse({"error": "Access token not found"}, status=401)
    try:
        validate_access_token(token) 
    except PermissionDenied:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)

    websocket_url = f"ws://127.0.0.1:8000/ws/chat/{user_id}/{target_id}/?token={token}"
    return JsonResponse({"websocket_url": websocket_url})

@permission_classes([IsAuthenticated])
def notification_handshake(request, user_id):
  
    token = request.COOKIES.get("access_token")
    if not token:
        return JsonResponse({"error": "Access token not found"}, status=401)
    try:
        validate_access_token(token)
    except PermissionDenied:
        return JsonResponse({"error": "Invalid or expired token"}, status=401)
    # Dynamically generate the WebSocket URL
    websocket_url = f"ws://127.0.0.1:8000/ws/notifications/{user_id}/?token={token}"
    return JsonResponse({"websocket_url": websocket_url})


@api_view(['POST'])
def mark_messages_as_read(request, contact_id):
    Message.objects.filter(
        sender_id=contact_id,
        receiver=request.user,
        is_read=False
    ).update(is_read=True)
    return Response({'status': 'success'})


@api_view(['GET'])
def get_online_status(request):
    online_users = OnlineUser.objects.filter(
        is_online=True, 
        connection_count__gt=0
    ).values_list('user_id', flat=True)
    return Response({'online_users': list(online_users)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_notifications(request):
    """
    List all notifications for the authenticated user.
    """
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unread_notification_count(request):
    """
    Get the count of unread notifications for the authenticated user.
    """
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return Response({'count': count})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    """
    Mark a specific notification as read.
    """
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
    except Notification.DoesNotExist:
        return Response({'error': 'Notification not found'}, status=status.HTTP_404_NOT_FOUND)

    notification.is_read = True
    notification.save()
    return Response({'status': 'success'})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_meeting(request, schedule_id):
    try:
        schedule = Schedule.objects.get(
            id=schedule_id,
            status=Schedule.Status.ACCEPTED
        )
        
        # Verify user is participant
        if request.user not in [schedule.teacher, schedule.student]:
            return Response(
                {"error": "Not authorized for this meeting"}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        # Check meeting time (5 min before to 30 min after)
        now = timezone.now()
        if not (schedule.scheduled_time - timedelta(minutes=5) <= now <= 
                schedule.scheduled_time + timedelta(minutes=30)):
            return Response(
                {"error": "Meeting is not active at this time"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        return Response({
            "meeting_id": str(schedule.id),
            "role": "teacher" if request.user == schedule.teacher else "student"
        })
        
    except Schedule.DoesNotExist:
        return Response(
            {"error": "Meeting not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def verify_meeting(request, schedule_id):
    user_id = request.user.id
    token = request.COOKIES.get("access_token")
    if not token:
        return JsonResponse({"error": "Access token not found"}, status=401)
    try:
        schedule = Schedule.objects.get(
            id=schedule_id,
            status=Schedule.Status.ACCEPTED
        )
        
        if request.user not in [schedule.teacher, schedule.student]:
            return Response(
                {"error": "Not authorized"}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        websocket_url = f"ws://127.0.0.1:8000/ws/video/{schedule_id}/{user_id}/?token={token}"
        
        return Response({
            "valid": True,
            "role": "teacher" if request.user == schedule.teacher else "student",
            "websocket_url": websocket_url
        })
        
    except Schedule.DoesNotExist:
        return Response(
            {"error": "Invalid meeting"}, 
            status=status.HTTP_404_NOT_FOUND
        )
        
@api_view(['GET'])
@permission_classes([IsAuthenticated])        
def time_transactions(request):
    # Fetch transactions for the current user (both sent and received)
        sent_transactions = TimeTransaction.objects.filter(from_user=request.user)
        received_transactions = TimeTransaction.objects.filter(to_user=request.user)
        
        # Combine and order transactions by most recent
        transactions = (sent_transactions | received_transactions).order_by('-created_at')
        
        # Serialize the transactions
        serializer = TimeTransactionSerializer(transactions, many=True)
        
        # Prepare response with time balance information
        response_data = {
            'transactions': serializer.data,
            'time_balance': {
                'total_time': request.user.total_time,
                'available_time': request.user.available_time,
                'held_time': request.user.held_time
            }
        }
        
        return Response(response_data)