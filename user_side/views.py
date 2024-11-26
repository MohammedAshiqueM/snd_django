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
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework.exceptions import AuthenticationFailed
User = get_user_model()

from django.http import JsonResponse



class MyTokenObtainPairView(TokenObtainPairView):
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

                return JsonResponse({
                    "detail": "User is inactive. OTP has been resent.",
                }, status=400)

            response = super().post(request, *args, **kwargs)
            data = response.data

            access_token = data.get("access")
            refresh_token = data.get("refresh")

            http_response = JsonResponse({
                "message": "Login successful",
                "access_token": access_token,
                "refresh_token": refresh_token,
            })

            if access_token:
                http_response.set_cookie(
                    key='access_token',
                    value=access_token,
                    httponly=True,
                    secure=True,
                    samesite='Lax',
                    max_age=3600,
                )

            if refresh_token:
                http_response.set_cookie(
                    key='refresh_token',
                    value=refresh_token,
                    httponly=True,
                    secure=True,
                    samesite='Lax',
                    max_age=604800,
                )

            return http_response

        except AuthenticationFailed as e:
            return JsonResponse({"detail": str(e)}, status=400)

        except Exception as e:
            return JsonResponse({"detail": str(e)}, status=500)    
class TokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh')
        
        if not refresh_token:
            return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            refresh = RefreshToken(refresh_token)
            new_access_token = str(refresh.access_token)
            return Response({"access_token": new_access_token})
        
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
def logout_view(request):
    response = JsonResponse({"message": "Logout successful"})
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response

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
        return Response({'detail': 'Email is already taken'}, status=status.HTTP_409_CONFLICT)

    try:
        otp = f"{randint(10000, 99999)}" 
        user = User.objects.create_user(
            first_name=data.get('firstname', '').strip(),
            last_name=data.get('lastname', '').strip(),
            email=email,
            username=email,
            password=data.get('password'),
            is_active=False,  
            otp_code=otp,
            otp_created_at=now(),
        )
        user.save()
        send_mail(
            subject="Your OTP Verification Code",
            message=f"Your OTP code is {otp}. It is valid for 5 minutes.",
            from_email=config('EMAIL_HOST_USER'),
            recipient_list=[email],
        )

        return Response({'detail': 'User registered. OTP sent to email.'}, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)


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
                
            http_response = JsonResponse({
            "message": "User verified and Login successfully",
            "access_token": access_token,
            "refresh_token": refresh_token,
            })

            if access_token:
                http_response.set_cookie(
                    key='access_token',
                    value=access_token,
                    httponly=True,
                    secure=True, 
                    samesite='Lax',
                    max_age=3600, 
                )
            if refresh_token:
                http_response.set_cookie(
                    key='refresh_token',
                    value=refresh_token,
                    httponly=True,
                    secure=True,
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

    # Check if the user exists
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=status.HTTP_404_NOT_FOUND)

    # Check if user is already verified
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

from google.oauth2.id_token import verify_oauth2_token
from google.auth.transport.requests import Request

# Make sure to use the correct Client ID
GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', cast=str).strip()
 # Replace with your actual Google Client ID

@api_view(['POST'])
def google_login(request):
    token = request.data.get('token')
    if not token:
        return Response({'error': 'No token provided'}, status=400)

    try:
        # Decode the token and get the ID info
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        
        # Log the token and audience for debugging
        print(f"Received token: {token}")
        print(f"Token audience (aud): {idinfo.get('aud')}")
        
        # Check if the audience matches the expected Client ID
        if idinfo['aud'] != GOOGLE_CLIENT_ID:
            print(GOOGLE_CLIENT_ID)
            return Response({'error': 'Invalid audience'}, status=400)

        # If the audience is valid, you can create or authenticate the user
        email = idinfo.get('email')
        name = idinfo.get('name')

        # Create or get the user from the database
        user, created = User.objects.get_or_create(
            username=email, defaults={'email': email, 'first_name': name}
        )

        # Generate JWT tokens for authentication
        refresh = RefreshToken.for_user(user)
        return Response({
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        })

    except ValueError as e:
        print(f"Error while verifying token: {str(e)}")
        return Response({'error': 'Invalid token or audience mismatch'}, status=400)
