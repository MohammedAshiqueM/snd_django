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
from . import views, blogViews, questionView, usersView, sessionView


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
    path('check/', views.AuthCheck, name='check'),
    
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
    path('all-users/', usersView.all_users, name='all-users'),
    path('users/<int:pk>/details/', usersView.user_details, name='user-details'),
    path('users/<int:pk>/report/', usersView.report_user, name='user-report'),
    path('users/<int:pk>/follow-unfollow/', usersView.follow_unfollow, name='follow-unfollow'),
    path("ws-handshake/<int:user_id>/<int:target_id>/", usersView.websocket_handshake, name="websocket_handshake"),
    path("notification-handshake/<int:user_id>/", usersView.notification_handshake, name="notification_handshake"),
    path('meeting/<int:schedule_id>/join/', usersView.join_meeting, name='join_meeting'),
    path('meeting/<int:schedule_id>/verify/', usersView.verify_meeting, name='verify_meeting'),
    
    path('mark/<int:contact_id>/', usersView.mark_messages_as_read, name='mark'),
    path('onlilne-status/', usersView.get_online_status, name='online-status'),
    path('notifications/', usersView.list_notifications, name='list_notifications'),
    path('notifications/unread_count/', usersView.unread_notification_count, name='unread_notification_count'),
    path('notifications/<int:pk>/mark_read/', usersView.mark_notification_read, name='mark_notification_read'),
    # path('notifications/mark_all_read/', usersView.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('time-transactions/', usersView.time_transactions, name='time-transactions'),
    path('time-plans/', usersView.list_time_plans, name='time-plans-list'),
    path('time-plans/<int:plan_id>/create-order/', usersView.create_order, name='create-order'),
    path('time-plans/<int:plan_id>/verify-payment/',usersView.verify_payment, name='verify-payment'),
    path('purchases/', usersView.user_purchase_history, name='user-purchases'),
    path('ratings/', usersView.create_rating, name='create-rating'),
     
    #sessionView
    path('requests/', sessionView.skill_sharing_request_list, name='skill_sharing_request_list'),
    path('requests/<int:pk>/', sessionView.skill_sharing_request_detail, name='skill_sharing_request_detail'),
    path('requests/my/', sessionView.my_skill_request, name='my_skill_request'),
    path('propose/', sessionView.propose_list, name='propose_list'),
    path('propose/<int:pk>/', sessionView.propose_detail, name='propose_detail'),
    path('requests/<int:request_id>/propose/', sessionView.request_proposes, name='request_propose'),
    path('propose/send/', sessionView.send_proposes, name='send_proposes'),
    path('propose/receved/', sessionView.receved_proposes, name='receved_proposes'),
    path('schedules/teaching/', sessionView.teaching_schedules, name='teaching-schedules'),
    path('schedules/learning/', sessionView.learning_schedules, name='learning-schedules'),
    path('session/<int:pk>/', sessionView.session_details, name='session-details'),
    path('transfer-time/', sessionView.transfer_time, name='transfer-time'),
    
]

