from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from .serializers import SkillSharingRequestSerializer
from rest_framework import status
from .models import Schedule, SkillSharingRequest, Tag, RequestTag, Follower, TimeTransaction
from .serializers import ScheduleSerializer
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, F
from rest_framework.response import Response
import json
from .utils import api_response
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import ValidationError
from .tasks import send_skill_request_notifications
User = get_user_model()


class Pagiator(PageNumberPagination):
    page_size = 5
    page_size_query_param = 'page_size'
    max_page_size = 50
    
       
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def skill_sharing_request_list(request):
    if request.method == 'GET':
        search_query = request.query_params.get('search', '').lower()
        category = request.query_params.get('category', None)
        status_filter = request.query_params.get('status', None)
        
        requests = SkillSharingRequest.objects.exclude(
            status=SkillSharingRequest.Status.DRAFT
        ).exclude(
            user=request.user
        ).order_by('-created_at')
        
        if search_query:
            requests = requests.filter(
                Q(title__icontains=search_query) | 
                Q(tags__name__icontains=search_query)
            ).distinct()
        
        if category and category != 'All':
            requests = requests.filter(tags__name=category).distinct()
            
        if status_filter:
            requests = requests.filter(status=status_filter)
        
        paginator = Pagiator()
        result_page = paginator.paginate_queryset(requests, request)
        serializer = SkillSharingRequestSerializer(result_page, many=True,context={'request': request} )
        return paginator.get_paginated_response(serializer.data)

    if request.method == 'POST':
        user = request.user
        data = request.data.copy()
        
        try:
            tags = json.loads(data.get("tags", []))
        except json.JSONDecodeError:
            return api_response(status.HTTP_400_BAD_REQUEST, "Invalid tags")
        
        serializer = SkillSharingRequestSerializer(data=data)
        
        try:
            if serializer.is_valid():
                # Check if user has enough available time when auto-publishing
                duration_minutes = serializer.validated_data.get('duration_minutes', 0)
                auto_publish = data.get('auto_publish', "false").lower() == "true"
                
                if auto_publish:
                    if user.available_time < duration_minutes:
                        return api_response(
                            status.HTTP_400_BAD_REQUEST,
                            "Insufficient time balance for this request"
                        )
                
                request_status = data.get('status', SkillSharingRequest.Status.DRAFT)
                
                # Start a transaction to ensure time balance and request creation are atomic
                with transaction.atomic():
                    request_obj = serializer.save(user=user, status=request_status )
                    
                    # Handle tags
                    invalid_tags = []
                    valid_tags = []
                    for tag_name in tags:
                        try:
                            tag = Tag.objects.get(name=tag_name)
                            valid_tags.append(tag)
                        except Tag.DoesNotExist:
                            invalid_tags.append(tag_name)
                            
                    if invalid_tags:
                        raise ValidationError(
                            f"Invalid tags: {', '.join(invalid_tags)}"
                        )
                    
                    for tag in valid_tags:
                        RequestTag.objects.create(request=request_obj, tag=tag)
                    
                    # Update time balance if auto-publishing
                    if auto_publish:
                        User.objects.filter(pk=user.pk).update(
                            available_time=F('available_time') - duration_minutes,
                            held_time=F('held_time') + duration_minutes
                        )
                        # Refresh user instance to get updated values
                        user.refresh_from_db()
                
                return api_response(
                    status.HTTP_201_CREATED,
                    "Request created successfully",
                    serializer.data
                )
            else:
                return api_response(
                    status.HTTP_400_BAD_REQUEST,
                    "Validation error",
                    serializer.errors
                )
        except ValidationError as e:
            return api_response(
                status.HTTP_406_NOT_ACCEPTABLE,
                str(e)
            )
        except Exception as e:
            return api_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                str(e)
            )
    
    
@api_view(['GET', 'PUT', 'DELETE', 'PATCH'])
@permission_classes([IsAuthenticated])
def skill_sharing_request_detail(request, pk):
    import logging
    logger = logging.getLogger(__name__)
    
    skill_request = get_object_or_404(SkillSharingRequest, pk=pk)
    print(">>>>>", skill_request.id)

    # Handle GET request
    if request.method == 'GET':
        serializer = SkillSharingRequestSerializer(skill_request, context={'request': request})
        is_following = Follower.objects.filter(
            follower=request.user,
            following=skill_request.user
        ).exists()
        data = serializer.data
        data['is_following'] = is_following
        return JsonResponse(data)

    # Handle PUT/PATCH requests
    if request.method in ['PUT', 'PATCH']:
        try:
            data = JSONParser().parse(request)
            print(f"Received data: {data}")
            
            original_status = skill_request.status
            
            if 'status' in data:
                new_status = data['status']
                print(f"Status change requested: {original_status} -> {new_status}")
                
                if new_status == 'PE' and original_status == 'DR':
                    # try:
                        # from redis import Redis
                        # redis_client = Redis(host='localhost', port=6379, db=0, socket_connect_timeout=5)
                        # redis_client.ping()
                        
                        # print("Redis connection successful")
                        
                        send_skill_request_notifications.delay(skill_request.id)
                        # print(f"Task sent with id: {task_result.id}")
                        
                    # except Exception as e:
                    #     print(f"Redis/Celery error: {str(e)}")
                    #     logger.error(f"Redis Connection Failed: {e}", exc_info=True)
            serializer = SkillSharingRequestSerializer(
                skill_request,
                data=data,
                partial=request.method == 'PATCH'
            )
            
            if serializer.is_valid():
                updated_request = serializer.save()
                
                if data.get('status') == 'PE' and original_status == 'DR':
                    try:
                        updated_request.user.hold_time(updated_request.duration_minutes)
                    except Exception as e:
                        print(f"Error updating time balance: {str(e)}")
                
                return JsonResponse(serializer.data)
            return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Handle DELETE request
    if request.method == 'DELETE':
        skill_request.delete()
        return JsonResponse({'message': 'Request deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

    # Default response if none of the methods match (shouldn't happen with @api_view decorator)
    return JsonResponse({'error': 'Method not allowed'}, status=status.HTTP_405_METHOD_NOT_ALLOWED)
from redis import Redis
@api_view(['GET'])
@permission_classes([IsAuthenticated])   
def my_skill_request(request):
        """
        To get requests of the requested user(current user)
        """
        # try:
        #     # Explicit Redis connection test
        #     client = Redis(host='localhost', port=6379)
        #     client.ping()
        #     print("connected................................",client.ping())
        # except Exception as e:
        #     print(f"Redis Connection Error: {e}")
        #     # Handle connection failure gracefully
        #     return Response({'error': 'Redis unavailable'}, status=503)
        # send_skill_request_notifications.delay(34)
        search_query = request.query_params.get('search', '').lower()
        category = request.query_params.get('category', None)
        requests = SkillSharingRequest.objects.filter(user__username=request.user).order_by('-created_at')

        if search_query:
            requests = requests.filter(
                Q(title__icontains=search_query) | Q(tags__name__icontains=search_query)
            ).distinct()

        if category and category != 'All':
            requests = requests.filter(tags__name=category).distinct()

        paginator = Pagiator()
        result_page = paginator.paginate_queryset(requests, request)
        serializer = SkillSharingRequestSerializer(result_page, many=True)
        return paginator.get_paginated_response(serializer.data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def propose_list(request):
    if request.method == 'GET':
        schedules = Schedule.objects.all()
        serializer = ScheduleSerializer(schedules, many=True)
        return JsonResponse(serializer.data, safe=False)

    if request.method == 'POST':
        data = JSONParser().parse(request)
        print("Received data:", data) 
        skill_request = get_object_or_404(SkillSharingRequest, id=data.get('request'))

        # Validate request status
        if skill_request.status != SkillSharingRequest.Status.PENDING:
            return JsonResponse(
                {'error': 'Can only propose schedules for pending requests.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Prevent the request creator from proposing schedules
        if skill_request.user == request.user:
            return JsonResponse(
                {'error': 'You cannot propose a schedule for your own request.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Prevent duplicate schedule proposals
        if Schedule.objects.filter(
            request=skill_request,
            teacher=request.user
        ).exists():
            return JsonResponse(
                {'error': 'You have already proposed a schedule for this request.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ScheduleSerializer(data=data)
        if serializer.is_valid():
            try:
                schedule = serializer.save(
                    teacher=request.user,
                    student=skill_request.user,
                    status=Schedule.Status.PROPOSED,
                    request=skill_request
                )
                return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return JsonResponse({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def propose_detail(request, pk):
    schedule = get_object_or_404(Schedule, pk=pk)

    if request.method == 'GET':
        serializer = ScheduleSerializer(schedule)
        return JsonResponse(serializer.data)

    if request.method == 'PATCH':
        if schedule.student != request.user:
            return JsonResponse(
                {'error': 'You can only update schedules for your requests.'},
                status=status.HTTP_403_FORBIDDEN
            )

        data = JSONParser().parse(request)
        new_status = data.get('status')

        try:
            if new_status == Schedule.Status.ACCEPTED:
                schedule.accept()
            elif new_status == Schedule.Status.COMPLETED:
                schedule.complete()
            elif new_status == Schedule.Status.REJECTED:
                schedule.reject()
            elif new_status == Schedule.Status.CANCELLED:
                # Add cancellation logic if needed
                pass
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ScheduleSerializer(schedule)
        return JsonResponse(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def request_proposes(request, request_id):
    """Get all schedules for a specific request"""
    skill_request = get_object_or_404(SkillSharingRequest, pk=request_id)
    print("skill request...",skill_request)
    # Only allow the request owner to see the schedules
    if skill_request.user != request.user:
        return JsonResponse(
            {'error': 'You can only view schedules for your own requests.'},
            status=status.HTTP_403_FORBIDDEN
        )
        
    schedules = Schedule.objects.filter(request=skill_request)
    serializer = ScheduleSerializer(schedules, many=True)
    print("schedules",serializer)
    return JsonResponse(serializer.data, safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def send_proposes(request):
    """
    To get proposed of the requested user(current user) sended
    """
    search_query = request.query_params.get('search', '').lower()
    category = request.query_params.get('category', None)
    requests = Schedule.objects.filter(teacher=request.user).order_by('-created_at')
    if search_query:
        requests = requests.filter(
            Q(request__title__icontains=search_query) | Q(request__tags__name__icontains=search_query)
        ).distinct()

    if category and category != 'All':
        requests = requests.filter(request__tags__name=category).distinct()

    paginator = Pagiator()
    result_page = paginator.paginate_queryset(requests, request)
    serializer = ScheduleSerializer(result_page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def receved_proposes(request):
    """
    To get proposed of the requested user(current user) sended
    """
    search_query = request.query_params.get('search', '').lower()
    category = request.query_params.get('category', None)
    requests = Schedule.objects.filter(student=request.user).order_by('-created_at')

    if search_query:
        requests = requests.filter(
            Q(request__title__icontains=search_query) | Q(request__tags__name__icontains=search_query)
        ).distinct()

    if category and category != 'All':
        requests = requests.filter(request__tags__name=category).distinct()

    paginator = Pagiator()
    result_page = paginator.paginate_queryset(requests, request)
    serializer = ScheduleSerializer(result_page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teaching_schedules(request):
    """
    Get schedules where the current user is the teacher
    """
    paginator = Pagiator()
    
    # Get query parameters
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    
    # Base queryset
    schedules = Schedule.objects.filter(
    teacher=request.user, status=Schedule.Status.ACCEPTED
    ).select_related('request', 'teacher', 'student')

    
    # Apply filters
    if search:
        schedules = schedules.filter(
            Q(request__title__icontains=search) |
            Q(request__description__icontains=search)
        )
    
    if category:
        schedules = schedules.filter(request__tags__name=category)
    
    # Order by created date
    schedules = schedules.order_by('-created_at')
    
    # Paginate results
    result_page = paginator.paginate_queryset(schedules, request)
    serializer = ScheduleSerializer(result_page, many=True)
    
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def learning_schedules(request):
    """
    Get schedules where the current user is the student
    """
    paginator = Pagiator()
    
    # Get query parameters
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    
    # Base queryset
    schedules = Schedule.objects.filter(
    student=request.user, status=Schedule.Status.ACCEPTED
    ).select_related('request', 'teacher', 'student')
    
    # Apply filters
    if search:
        schedules = schedules.filter(
            Q(request__title__icontains=search) |
            Q(request__description__icontains=search)
        )
    
    if category:
        schedules = schedules.filter(request__tags__name=category)
    
    # Order by created date
    schedules = schedules.order_by('-created_at')
    
    # Paginate results
    result_page = paginator.paginate_queryset(schedules, request)
    serializer = ScheduleSerializer(result_page, many=True)
    
    return paginator.get_paginated_response(serializer.data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def session_details(request, pk):
    try:
        # Use get() instead of filter() to retrieve a single object
        schedule = Schedule.objects.select_related(
            'request',
            'teacher',
            'student'
        ).get(pk=pk)
        
        serializer = ScheduleSerializer(schedule)
        return Response(serializer.data)
        
    except Schedule.DoesNotExist:
        return Response(
            {"error": "Schedule not found"}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {"error": str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@transaction.atomic
@permission_classes([IsAuthenticated])
def transfer_time(request):
    """
    Transfer time from student to teacher based on the actual meeting duration.
    """
    try:
        # Extract data from the request
            schedule_id = request.data.get('meeting_id')
            elapsed_minutes = request.data.get('elapsedMinutes')
            
            if not schedule_id or not elapsed_minutes:
                raise ValidationError("Invalid schedule ID or elapsed time.")
            
            elapsed_minutes = int(elapsed_minutes)
            if elapsed_minutes <= 0:
                raise ValidationError("Elapsed time must be greater than zero.")
            
            # Fetch the schedule and related users
            schedule = Schedule.objects.select_related('student', 'teacher').get(id=schedule_id)
            student = schedule.student
            teacher = schedule.teacher
            
            # Ensure the schedule is in the correct state
            if schedule.status != Schedule.Status.ACCEPTED:
                raise ValidationError("Time can only be transferred for accepted schedules.")
            
            # Calculate the time to transfer (not exceeding the scheduled duration)
            scheduled_duration = schedule.request.duration_minutes
            transfer_minutes = min(elapsed_minutes, scheduled_duration)
            
            # Validate student's held time
            if student.held_time < transfer_minutes:
                raise ValidationError("Student does not have enough held time for transfer.")
            
            # Perform the time transfer
            student.held_time -= transfer_minutes
            teacher.available_time += transfer_minutes
            
            # Save the updated user balances
            student.save()
            teacher.save()
            
            # Create a time transaction record
            TimeTransaction.objects.create(
                from_user=student,
                to_user=teacher,
                amount=transfer_minutes,
                schedule=schedule,
            )
            
            # Update the schedule status to completed
            schedule.status = Schedule.Status.COMPLETED
            schedule.save()
            
            return Response({
                'status': 'success',
                'message': f'Transferred {transfer_minutes} minutes from student to teacher.',
                'student_held_time': student.held_time,
                'teacher_available_time': teacher.available_time
            })
        
    except Schedule.DoesNotExist:
        return Response({'status': 'error', 'message': 'Schedule not found.'}, status=404)
    except ValidationError as e:
        return Response({'status': 'error', 'message': str(e)}, status=400)
    except Exception as e:
        return Response({'status': 'error', 'message': f'An error occurred: {str(e)}'}, status=500)