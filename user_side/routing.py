from django.urls import re_path
from . import consumers,videoConsumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<current_user_id>\d+)/(?P<target_user_id>\d+)/$', consumers.ChatConsumer.as_asgi()),
    re_path(r'ws/notifications/(?P<user_id>\d+)/$', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/video/(?P<schedule_id>\d+)/(?P<user_id>\d+)/$', videoConsumers.VideoMeetConsumer.as_asgi()),
]