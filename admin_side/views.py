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
    Schedule, Rating, Report, TimeTransaction, TimePlan, TimeOrder
)
from user_side.serializers import (
    MyTokenObtainPairSerializer,TagSerializer,BlogSerializer,UserSerializer,
    RatingSerializer,ReportSerializer,BlogTagSerializer,BlogVoteSerializer,
    FollowerSerializer,QuestionSerializer,ScheduleSerializer,UserSkillSerializer,
    RequestTagSerializer,BlogCommentSerializer,QuestionTagSerializer,QuestionVoteSerializer,
    SkillSharingRequest,TimeTransactionSerializer,SkillSharingRequestSerializer,TimePlanSerializer,TimeOrderSerializer
    )
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

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
    category = request.query_params.get('category', None)
    tags = Tag.objects.all()
    
    if search_query:
        tags = tags.filter(name__icontains=search_query)
        
    if category and category.lower() != 'all':
        tags = tags.filter(name__icontains=category)
        
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

@api_view(['GET'])
@permission_classes([IsSuperUser])        
def transaction_history(request):
    # Filter for successful time orders
    transactions = TimeOrder.objects.filter(status=TimeOrder.OrderStatus.SUCCESSFUL)
    
    # Apply pagination
    paginator = ReportPagination()
    paginated_transactions = paginator.paginate_queryset(transactions.order_by('-created_at'), request)
    
    serializer = TimeOrderSerializer(paginated_transactions, many=True)
    
    # Calculate total time from successful orders
    total_time = sum(
        transaction.plan.minutes 
        for transaction in transactions 
        if transaction.status == TimeOrder.OrderStatus.SUCCESSFUL
    )
    
    total_amount = sum(
        transaction.amount 
        for transaction in transactions 
        if transaction.status == TimeOrder.OrderStatus.SUCCESSFUL
    )
    
    response_data = {
        'transactions': serializer.data,
        'time_balance': {
            'total_time': total_time,
            'total_amount': total_amount,
            'held_time': request.user.held_time
        }
    }
    
    return paginator.get_paginated_response(response_data)
@method_decorator(csrf_exempt, name='update')  #here the model view set is user for understanding its working.
class TimePlanViewSet(viewsets.ModelViewSet):
    def initial(self, request, *args, **kwargs):
        print("Request received:", request.method)
        super().initial(request, *args, **kwargs)
    queryset = TimePlan.objects.all().order_by('price')
    serializer_class = TimePlanSerializer
    # permission_classes = [IsSuperUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        # print("Headers:???????????????????/", request.headers)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)