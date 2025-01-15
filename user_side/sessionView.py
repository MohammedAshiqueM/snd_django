from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from .serializers import SkillSharingRequestSerializer
from rest_framework import status
from .models import Schedule, SkillSharingRequest, Tag, RequestTag, Follower
from .serializers import ScheduleSerializer
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from rest_framework.response import Response
import json
from .utils import api_response
from django.core.exceptions import ValidationError

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
        
        requests = SkillSharingRequest.objects.exclude(status=SkillSharingRequest.Status.DRAFT).order_by('-created_at')

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
        serializer = SkillSharingRequestSerializer(result_page, many=True)
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
                # Set initial status based on auto_publish
                initial_status = (
                    SkillSharingRequest.Status.PENDING 
                    if data.get('auto_publish', False) 
                    else SkillSharingRequest.Status.DRAFT
                )
                
                request_obj = serializer.save(user=user, status=initial_status)
                
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
                    request_obj.delete()
                    return api_response(
                        status.HTTP_406_NOT_ACCEPTABLE,
                        f"Invalid tags: {', '.join(invalid_tags)}"
                    )
                    
                for tag in valid_tags:
                    RequestTag.objects.create(request=request_obj, tag=tag)
                
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
        except Exception as e:
            return api_response(
                status.HTTP_500_INTERNAL_SERVER_ERROR,
                str(e)
            )
    
    
@api_view(['GET', 'PUT', 'DELETE', 'PATCH'])
@permission_classes([IsAuthenticated])
def skill_sharing_request_detail(request, pk):
    skill_request = get_object_or_404(SkillSharingRequest, pk=pk)

    if request.method == 'GET':
        serializer = SkillSharingRequestSerializer(skill_request)
        is_following = Follower.objects.filter(
            follower=request.user, 
            following=skill_request.user
        ).exists()
        data = serializer.data
        data['is_following'] = is_following
        return JsonResponse(data)

    if request.method in ['PUT', 'PATCH']:
        if skill_request.user != request.user:
            return JsonResponse(
                {'error': 'You can only edit your own requests.'},
                status=status.HTTP_403_FORBIDDEN
            )

        data = JSONParser().parse(request)
        
        # Validate status changes
        if 'status' in data:
            new_status = data['status']
            current_status = skill_request.status
            
            # Validate status transitions
            if new_status == 'CA':  # Cancel request
                if current_status not in ['DR', 'PE']:
                    return JsonResponse(
                        {'error': 'Can only cancel draft or pending requests'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            elif new_status == 'PE':  # Publish request
                if current_status != 'DR':
                    return JsonResponse(
                        {'error': 'Can only publish draft requests'},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        serializer = SkillSharingRequestSerializer(
            skill_request,
            data=data,
            partial=request.method == 'PATCH'
        )
        
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
@api_view(['GET'])
@permission_classes([IsAuthenticated])   
def my_skill_request(request):
        """
        To get requests of the requested user(current user)
        """
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
def schedule_list(request):
    if request.method == 'GET':
        schedules = Schedule.objects.all()
        serializer = ScheduleSerializer(schedules, many=True)
        return JsonResponse(serializer.data, safe=False)

    if request.method == 'POST':
        data = JSONParser().parse(request)
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
                    status=Schedule.Status.PROPOSED
                )
                return JsonResponse(serializer.data, status=status.HTTP_201_CREATED)
            except ValidationError as e:
                return JsonResponse({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def schedule_detail(request, pk):
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
            elif new_status == Schedule.Status.CANCELLED:
                # Add cancellation logic if needed
                pass
        except ValidationError as e:
            return JsonResponse({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ScheduleSerializer(schedule)
        return JsonResponse(serializer.data)
