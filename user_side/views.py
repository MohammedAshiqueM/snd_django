from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated,IsAdminUser
from rest_framework import viewsets, mixins
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes, authentication_classes
import logging
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.views import TokenObtainPairView
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from random import randint
from django.utils.timezone import now, timedelta
# from dotenv import load_dotenv
from social_django.utils import psa
from decouple import config
import os
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
from google.auth.transport import requests
from google.oauth2 import id_token
# from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.exceptions import AuthenticationFailed
from django.http import JsonResponse
from django.urls import reverse
import json
from django.contrib.auth.hashers import make_password
from .utils import api_response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.permissions import AllowAny
from google.oauth2.id_token import verify_oauth2_token
from google.auth.transport.requests import Request
from django.core.paginator import Paginator
from django.db.models import Q
import math
import time
from django.contrib.auth import logout as auth_logout


User = get_user_model()



class MyTokenObtainPairView(TokenObtainPairView):
    """Login the user via jwt"""
    
    serializer_class = MyTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        try:
            email = request.data.get('username', '').strip()
            password = request.data.get('password', '')

            try:
                user = User.objects.get(username=email)
            except User.DoesNotExist:
                raise AuthenticationFailed("Invalid credentials")

            if not user.check_password(password):
                raise AuthenticationFailed("Invalid credentials")

            if user.is_blocked:
                raise AuthenticationFailed("User is blocked")
            
            if not user.is_active:
                user.otp_code = str(randint(10000, 99999))
                user.otp_created_at = now()
                user.save()
                send_mail(
                    subject="Resend OTP Request",
                    message=f"Your OTP code is {user.otp_code}. It is valid for 5 minutes.",
                    from_email=config('EMAIL_HOST_USER'),
                    recipient_list=[user.email],
                    fail_silently=False,
                )

                return api_response(
                    status.HTTP_400_BAD_REQUEST,
                    "User is inactive. OTP has been resent.",
                )

            response = super().post(request, *args, **kwargs)
            data = response.data

            access_token = data.get("access")
            refresh_token = data.get("refresh")

            serialized_user = UserSerializer(user).data
            # role = "admin" if user.is_staff or user.is_superuser else "user"

            http_response = api_response(
                status.HTTP_200_OK,
                "Login successful",
                {"access_token": access_token,
                "refresh_token": refresh_token,
                "user":serialized_user,
                # "role": role,
                }
            )

            if access_token:
                http_response.set_cookie(
                    key='access_token',
                    value=access_token,
                    httponly=True,
                    secure=False,
                    samesite='Lax',
                    max_age=3600,
                )

            if refresh_token:
                http_response.set_cookie(
                    key='refresh_token',
                    value=refresh_token,
                    httponly=True,
                    secure=False,
                    samesite='Lax',
                    max_age=604800,
                )

            return http_response

        except AuthenticationFailed as e:
            return JsonResponse({"detail": str(e)}, status=400)

        except Exception as e:
            return JsonResponse({"detail": str(e)}, status=500)    
        
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get('refresh_token')
        if not refresh_token:
            return Response({"error": "Refresh token not provided"}, status=status.HTTP_400_BAD_REQUEST)

        request.data['refresh'] = refresh_token

        try:
            original_response = super().post(request, *args, **kwargs)
            data = original_response.data

            # Check for the new access token
            new_access_token = data.get("access")
            if not new_access_token:
                return Response({"error": "Access token not found"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Set the new access token in cookies
            http_response = Response(data, status=status.HTTP_200_OK)
            http_response.set_cookie(
                key='access_token',
                value=new_access_token,
                httponly=True,
                secure=False,  # Set to True in production
                samesite='Lax',
                max_age=3600,
            )

            # Optionally include the refresh token again (if needed)
            if 'refresh' in data:
                http_response.set_cookie(
                    key='refresh_token',
                    value=data['refresh'],
                    httponly=True,
                    secure=False,
                    samesite='Lax',
                    max_age=604800,
                )

            return http_response

        except (TokenError, InvalidToken) as e:
            return Response({"error": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def logout_view(request):
    try:

        auth_logout(request)
        
        response = Response({'detail': 'Logout successful'}, status=status.HTTP_200_OK)
        
        # Delete specific cookies
        cookie_names = [
            'access_token',
            'refresh_token',
            '_ga',
            '_gid',
            'csrftoken',
            'sessionid',
        ]
        
        for cookie_name in cookie_names:
            response.delete_cookie(cookie_name, path='/')
        
        return response
    except Exception as e:
        return Response({'detail': 'Logout failed', 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

def is_token_valid(token):
    try:
        RefreshToken(token)
        return True
    except Exception:
        return False

@api_view(['POST'])
def register_user(request):
    """Register new user as inactive and send OTP."""
    data = request.data
    email = data.get('email', '').lower().strip()
    if User.objects.filter(email=email).exists():
        return api_response(status.HTTP_409_CONFLICT,'Email is already taken',)

    try:
        otp = f"{randint(10000, 99999)}" 
        user = User.objects.create_user(
            email=email,
            username=email,
            password=data.get('password'),
            is_active=False,  
            otp_code=otp,
            otp_created_at=now(),
        )
        user.first_name = data.get('firstName', '').strip()
        user.last_name = data.get('lastName', '').strip()
        user.save()
        send_mail(
            subject="Your OTP Verification Code",
            message=f"Your OTP code is {otp}. It is valid for 5 minutes.",
            from_email=config('EMAIL_HOST_USER'),
            recipient_list=[email],
        )

        return api_response(status.HTTP_201_CREATED,'User registered. OTP sent to email.')

    except Exception as e:
        return api_response(status.HTTP_400_BAD_REQUEST,str(e),)


@api_view(['POST'])
def verify_otp(request):
    """Verify OTP and activate user."""
    data = request.data
    email = data.get('email', '').lower().strip()
    otp = data.get('otp', '').strip()

    try:
        user = User.objects.get(email=email)
        if not user.is_otp_valid():
            return Response({'detail': 'OTP has expired'}, status=status.HTTP_400_BAD_REQUEST)

        if user.otp_code == otp:
            user.is_active = True 
            user.otp_code = None
            user.otp_created_at = None
            user.save()
            
            token_serializer = MyTokenObtainPairSerializer()
            tokens = token_serializer.get_token(user)
            
            access_token = str(tokens.access_token)
            refresh_token = str(tokens)
            
            serialized_user = UserSerializer(user).data
                
            http_response = JsonResponse({
            "message": "User verified and Login successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user":serialized_user
            })

            if access_token:
                http_response.set_cookie(
                    key='access_token',
                    value=access_token,
                    httponly=True,
                    secure=False, 
                    samesite='Lax',
                    max_age=3600, 
                )
            if refresh_token:
                http_response.set_cookie(
                    key='refresh_token',
                    value=refresh_token,
                    httponly=True,
                    secure=False,
                    samesite='Lax',
                    max_age=604800,
                )

            return http_response

        return Response({'detail': 'Invalid OTP'}, status=status.HTTP_400_BAD_REQUEST)

    except User.DoesNotExist:
        return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def resend_otp(request):
    """Handle OTP resend requests."""
    email = request.data.get('email', '').strip().lower()

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    if user.is_active:
        return Response({'detail': 'User is already verified.'}, status=status.HTTP_400_BAD_REQUEST)

    # Throttling: Prevent frequent OTP resends
    # if user.otp_created_at and now() - user.otp_created_at < timedelta(minutes=2):
    #     return Response({'detail': 'Please wait 2 minutes before requesting another OTP.'}, status=status.HTTP_429_TOO_MANY_REQUESTS)

    user.otp_code = str(randint(10000, 99999))
    user.otp_created_at = now()
    user.save()
    send_mail(
        subject="Resend OTP Request",
        message=f"Your OTP code is {user.otp_code}. It is valid for 5 minutes.",
        from_email=config('EMAIL_HOST_USER'),
        recipient_list=[user.email],
        fail_silently=False,
    )

    return Response({'detail': 'OTP resent successfully.'}, status=status.HTTP_200_OK)


GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', cast=str).strip()

@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    id_token_str = request.data.get('id_token')
    if not id_token_str:
        return Response({'error': 'No token provided'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID')
        idinfo = id_token.verify_oauth2_token(id_token_str, requests.Request(), GOOGLE_CLIENT_ID)
        
        # Validate audience
        if idinfo['aud'] != GOOGLE_CLIENT_ID:
            raise AuthenticationFailed('Invalid audience')
        
        # Process user data fron idinfo
        email = idinfo.get('email')
        name = idinfo.get('name')
        User = get_user_model()
        
        user, created = User.objects.get_or_create(
            username=email, 
            defaults={
                'email': email, 
                'first_name': name,
                'is_active': True
            }
        )
        
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        
        response = Response({
            'message': 'Login successful', 
            'user': UserSerializer(user).data,
            'access_token': access_token,
            'refresh_token': refresh_token
        })
        
        response.set_cookie(
            'access_token', 
            access_token, 
            httponly=True, 
            secure=False,  # Set to True in production
            samesite='Lax',
            max_age=3600  # 1 hour
        )
        
        response.set_cookie(
            'refresh_token', 
            refresh_token, 
            httponly=True, 
            secure=False,  # Set to True in production
            samesite='Lax',
            max_age=7 * 24 * 3600  # 7 days
        )
        
        return response
    
    except ValueError as e:
        return Response({'error': f'Invalid token: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    except AuthenticationFailed as e:
        return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)  
@csrf_exempt
def forgot_password(request):
    if request.method == "POST":
        data = json.loads(request.body)
        email = data.get("email")
        try:
            user = User.objects.get(email=email)
            user.generate_reset_token()

            # frontend_url = "http://localhost:5173"
            frontend_url = "http://127.0.0.1:5173/" 
            reset_url = f"{frontend_url}reset-password/?token={user.reset_token}"

            send_mail(
                subject="Password Reset Request",
                message=f"Click the link to reset your password: {reset_url}",
                from_email=config('EMAIL_HOST_USER'),
                recipient_list=[email],
            )
            return JsonResponse({"message": "Reset link sent to your email."})
        except User.DoesNotExist:
            return JsonResponse({"message": "Email not found."}, status=404)

    return JsonResponse({"message": "Invalid request method."}, status=400)


@csrf_exempt
def reset_password(request):
    if request.method == "POST":
        data = json.loads(request.body)
        # print(data)
        token = data.get("token")
        password = data.get("password")

        try:
            user = User.objects.get(reset_token=token)
            # print(user.email)
            if user.is_reset_token_valid(token):
                # print("done")
                # print(f"Password before hashing: {user.password}")
                user.set_password(password)
                # print(f"Password after hashing: {user.password}")
                user.reset_token = None
                user.reset_token_expiration = None
                user.save()
                # print(f"In db: {password}")
                return JsonResponse({"message": "Password reset successful."})
            else:
                return JsonResponse({"message": "Invalid or expired token."}, status=400)
        except User.DoesNotExist:
            return JsonResponse({"message": "Invalid token."}, status=400)

    return JsonResponse({"message": "Invalid request method."}, status=400)

from rest_framework.permissions import IsAuthenticated,IsAdminUser,BasePermission

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def AuthCheck(request):
    try:
        # print("Received Cookies:", request.COOKIES)
        # print("Received Headers:", request.headers)
        # print("Authenticated User:", request.user)
        print("inside of htis..........")
        
        return api_response(
            status.HTTP_200_OK,
            "Authenticated User",
            {"isAuthenticated": True}
        )
    except Exception as e:
        # print(f"Error in AuthCheck: {e}")
        return api_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Authentication check failed",
            {"error": str(e)}
        )
        
class IsSuperUser(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)
    
@api_view(['GET'])
def AdminAuthCheck(request):
    print("inside///////////////")
    try:
        print("Received Cookies:", request.COOKIES)
        print("Received Headers:", request.headers)
        print("Authenticated User:", request.user)
        
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    """Retrieve the current user's profile details"""
    
    serializer = UserSerializer(request.user)
    return Response(serializer.data)

@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_user_profile(request):
    if request.content_type == "application/json":
        # print("Raw JSON body:", request.body)
        try:
            data = json.loads(request.body)
            # print("Parsed JSON data:", data)
        except json.JSONDecodeError:
            return Response({"error": "Invalid JSON"}, status=400)
    elif request.content_type.startswith("multipart/form-data"):
        # print("Multipart data:", request.data)
        # print("Files:", request.FILES)
        pass

    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    else:
        # print("Serializer errors:", serializer.errors)
        return Response(serializer.errors, status=400)



def get_tag_suggestions(request):
    query = request.GET.get('search', '')
    if query:
        tags = Tag.objects.filter(name__icontains=query)[:10]
        return JsonResponse({'tags': list(tags.values('id', 'name'))})
    return JsonResponse({'tags': []})


from django.http import JsonResponse, Http404

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_skills(request):
    """To get authenticated user's skills"""
    user_skills = request.user.skills.all() 
    return Response({'skills': [skill.name for skill in user_skills]})

    