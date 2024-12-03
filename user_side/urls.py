"""
URL configuration for snd_backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import MyTokenObtainPairView,CustomTokenRefreshView
from . import views

urlpatterns = [
    path('token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('register/', views.register_user, name='register'),
    path('otp/', views.verify_otp, name='otp'),
    path('resent-otp/', views.resend_otp, name='otp'),
    path('auth/google-login/', views.google_login, name='google-login'),
    path('forget-password/', views.forgot_password, name='forget-password'),
    path('reset-password/', views.reset_password, name='reset-password'),
    path('auth/check/', views.AuthCheck, name='auth-check'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.get_user_profile, name='profile'),
    path('profile/update/', views.update_user_profile, name='profile-update'),
    path('tags/', views.get_tag_suggestions, name='tag-suggestions'),
    
    
]

