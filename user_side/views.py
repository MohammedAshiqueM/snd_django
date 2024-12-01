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


User = get_user_model()



class MyTokenObtainPairView(TokenObtainPairView):
    """Login the user via jwt"""
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

            http_response = api_response(
                status.HTTP_200_OK,
                "Login successful",
                {"access_token": access_token,
                "refresh_token": refresh_token,}
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
            return super().post(request, *args, **kwargs)
        except (TokenError, InvalidToken) as e:
            return Response({"error": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])      
def logout_view(request):
        response = Response({'detail': 'Logout successful'}, status=status.HTTP_200_OK)
        
        response.delete_cookie('access_token', path='/')
        response.delete_cookie('refresh_token', path='/')
        
        response.set_cookie('access_token', '', expires=0, httponly=True, samesite='None', secure=True) 
        response.set_cookie('refresh_token', '', expires=0, httponly=True, samesite='None', secure=True)

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
        return api_response(status.HTTP_409_CONFLICT,'Email is already taken',)

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

from google.oauth2.id_token import verify_oauth2_token
from google.auth.transport.requests import Request

GOOGLE_CLIENT_ID = config('GOOGLE_CLIENT_ID', cast=str).strip()

@api_view(['POST'])
@permission_classes([AllowAny])
def google_login(request):
    print("inside....")
    print("Full request headers:", request.headers)
    print("Full request method:", request.method)
    print("Full request path:", request.path)
    print("All cookies:", request.COOKIES)
    token = request.COOKIES.get('token')
    if not token:
        return Response({'error': 'No token provided'}, status=400)

    try:
        
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        if idinfo['aud'] != GOOGLE_CLIENT_ID:
            return Response({'error': 'Invalid audience'}, status=400)

        email = idinfo.get('email')
        name = idinfo.get('name')

        user, created = User.objects.get_or_create(
            username=email, defaults={'email': email, 'first_name': name}
        )

        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)

        response = JsonResponse({'message': 'Login successful'})
        response.set_cookie(
            key='access_token',
            value=access_token,
            httponly=True,
            secure=True,  
            samesite='Lax', 
        )
        response.set_cookie(
            key='refresh_token',
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite='Lax',
        )
        return response

    except ValueError as e:
        return Response({'error': 'Invalid token or audience mismatch'}, status=400)


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
        print(data)
        token = data.get("token")
        password = data.get("password")

        try:
            user = User.objects.get(reset_token=token)
            print(user.email)
            if user.is_reset_token_valid(token):
                print("done")
                print(f"Password before hashing: {user.password}")
                user.set_password(password)
                # print(f"Password after hashing: {user.password}")
                user.reset_token = None
                user.reset_token_expiration = None
                user.save()
                print(f"In db: {password}")
                return JsonResponse({"message": "Password reset successful."})
            else:
                return JsonResponse({"message": "Invalid or expired token."}, status=400)
        except User.DoesNotExist:
            return JsonResponse({"message": "Invalid token."}, status=400)

    return JsonResponse({"message": "Invalid request method."}, status=400)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def AuthCheck(request):
    try:
        print("Received Cookies:", request.COOKIES)
        print("Received Headers:", request.headers)
        print("Authenticated User:", request.user)
        
        return api_response(
            status.HTTP_200_OK,
            "Authenticated User",
            {"isAuthenticated": True}
        )
    except Exception as e:
        print(f"Error in AuthCheck: {e}")
        return api_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Authentication check failed",
            {"error": str(e)}
        )