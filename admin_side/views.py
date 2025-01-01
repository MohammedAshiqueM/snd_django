from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated,IsAdminUser,BasePermission
from rest_framework import status
from user_side.utils import api_response
from rest_framework.views import APIView
from rest_framework.response import Response
from user_side.models import (
    Follower, Tag, UserSkill, Blog, BlogTag, BlogVote, BlogComment, 
    Question, QuestionTag, QuestionVote, SkillSharingRequest, RequestTag,
    Schedule, Rating, Report, TimeTransaction
)
from user_side.serializers import (
    MyTokenObtainPairSerializer,TagSerializer,BlogSerializer,UserSerializer,
    RatingSerializer,ReportSerializer,BlogTagSerializer,BlogVoteSerializer,
    FollowerSerializer,QuestionSerializer,ScheduleSerializer,UserSkillSerializer,
    RequestTagSerializer,BlogCommentSerializer,QuestionTagSerializer,QuestionVoteSerializer,
    SkillSharingRequest,TimeTransactionSerializer,SkillSharingRequestSerializer
    )
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

User = get_user_model()

class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)
    
@api_view(['GET'])
# @permission_classes([IsSuperUser])
@permission_classes([IsAuthenticated])
def AdminAuthCheck(request):
    print("inside///////////////")
    try:
        # print("Received Cookies:", request.COOKIES)
        # print("Received Headers:", request.headers)
        # print("Authenticated User:", request.user)
        
        return api_response(
            status.HTTP_200_OK,
            "Authenticated User",
            {"isAuthorized": True}
        )
    except Exception as e:
        # print(f"Error in AuthCheck: {e}")
        return api_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Autherization check failed check failed",
            {"error": str(e)}
        )
        
class ReportPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50

from django.db.models import Count

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_reports(request):
    """
    To list the reports
    """
    search_query = request.query_params.get('search', '').lower()
    
    # Annotate the number of times each user is reported
    reports = Report.objects.values(
        'reported_user__id',
        'reported_user__username',
        'reported_user__email',
        'reported_user__is_blocked'
    ).annotate(
        report_count=Count('id')
    )

    # Apply search filter
    if search_query:
        reports = reports.filter(
            Q(reported_user__username__icontains=search_query) | 
            Q(reported_user__email__icontains=search_query)
        )

    # Order by the report count in descending order
    reports = reports.order_by('-report_count')

    # Paginate results
    paginator = ReportPagination()
    result_page = paginator.paginate_queryset(reports, request)

    return paginator.get_paginated_response({
        'total_count': reports.count(),
        'results': list(result_page)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def report_details(request, pk):
    """
    Fetch detailed reports for a specific reported user.
    """
    # Get the user being reported
    reported_user = get_object_or_404(User, id=pk)
    
    # Fetch all reports against this user
    reports = Report.objects.filter(reported_user=reported_user).select_related('reported_by')
    
    # Serialize data
    serializer = ReportSerializer(reports, many=True)
    
    return Response({
        "reported_user": {
            "id": reported_user.id,
            "username": reported_user.username,
            "email": reported_user.email,
            "status":reported_user.is_blocked
        },
        "reports": serializer.data
    })


@api_view(['POST'])
@permission_classes([IsSuperUser])
def block_unblock(request, pk):
    if not request.user.is_superuser:
        return JsonResponse({'error': 'Permission denied'}, status=403)

    user = get_object_or_404(User, id=pk)
    user.is_blocked = not user.is_blocked
    user.save()

    return JsonResponse({
        'message': f"User {'blocked' if user.is_blocked else 'unblocked'} successfully",
        'status': 'blocked' if user.is_blocked else 'active'
    })
    
    
class UserPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 50
     
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tags_list(request):
    """
    To get all tags
    """
    search_query = request.query_params.get('search', None)
    tags = Tag.objects.all()
    
    if search_query:
        tags = tags.filter(name__icontains=search_query)
    
    paginator = UserPagination()
    result_page = paginator.paginate_queryset(tags, request)
    serializer = TagSerializer(result_page, many=True)
    return paginator.get_paginated_response(serializer.data)

@api_view(['POST'])
@permission_classes([IsSuperUser])
def add_tag(request):
    serializer = TagSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)