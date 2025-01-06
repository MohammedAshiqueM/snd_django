from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<current_user_id>\d+)/(?P<target_user_id>\d+)/$', consumers.ChatConsumer.as_asgi()),

]