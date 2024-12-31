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
from . import views


urlpatterns = [
    #view
    path('check/', views.AdminAuthCheck, name='admin-check'),
    path('reports/', views.list_reports, name='report-list'),
    path('report/<int:pk>/details/', views.report_details, name='report-details'),
    path('user/<int:pk>/block-unblock/', views.block_unblock, name='block-unblock'),
    
    
]

