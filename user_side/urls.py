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
from . import views, blogViews, questionView, usersView


urlpatterns = [
    #view
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
    path('skills/', views.get_user_skills, name='skills'),
    
    #blogView
    path('blog/create/', blogViews.blog_creation, name='blog-create'),
    path('blogs/', blogViews.get_all_blogs, name='blogs'), 
    path('blog/<slug:slug>/', blogViews.blog_detail, name='blog_detail'),
    path('blog/<slug:slug>/add-comment/', blogViews.add_comment, name='add-comment'),
    path('blog/<slug:slug>/comments/', blogViews.get_comments, name='comments'),
    path('blog/<slug:slug>/vote/', blogViews.vote_blog, name='blog-vote'),
    #questionView
    path('question/create/', questionView.question_creation, name='question-create'),
    path('questions/', questionView.get_all_question, name='questions'),
    path('question/<int:pk>/', questionView.question_detail, name='question-detail'),
    path('question/<int:pk>/add-answer/', questionView.add_answer, name='add-answer'),
    path('question/<int:pk>/answers/', questionView.get_answers, name='answers'),
    path('question/<int:pk>/vote/', questionView.question_vote, name='question-vote'),
    #usersView
    path('users/', usersView.list_users, name='users'),
    
]

