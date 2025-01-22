from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from .models import Schedule
from django.contrib.auth import get_user_model
from datetime import datetime

User = get_user_model()

class VideoMeetConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # print("scope of verify",self.scope)
        
        self.schedule_id = self.scope['url_route']['kwargs']['schedule_id']
        self.room_group_name = f'video_{self.schedule_id}'
        
        # Verify user has access to this schedule
        if not await self.verify_access():
            await self.close()
            return
            
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    @database_sync_to_async
    def verify_access(self):
        print("scope of verify",self.scope)
        user_id = self.scope['url_route']['kwargs']['user_id']
        
        user = User.objects.get(id=user_id)
        try:
            schedule = Schedule.objects.get(
                id=self.schedule_id,
                status=Schedule.Status.ACCEPTED
            )
            return user in [schedule.teacher, schedule.student]
        except Schedule.DoesNotExist:
            return False

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type')
        
        if message_type == 'chat':
            user_id = self.scope['url_route']['kwargs']['user_id']
            user = await database_sync_to_async(User.objects.get)(id=user_id)
        
            # Handle chat messages with proper sender info
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'type': 'chat',
                        'sender_id': user.id,
                        'sender_name': user.get_full_name() or user.username,  # Use full name or username
                        'text': data.get('text'),
                        'time': datetime.now().strftime('%H:%M')
                    }
                }
            )
        else:
            # Handle WebRTC signaling messages
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'relay_message',
                    'message': data,
                    'sender_channel_name': self.channel_name
                }
            )
    async def chat_message(self, event):
        # Send chat message to WebSocket
        await self.send(text_data=json.dumps(event['message']))
        
    async def relay_message(self, event):
        if self.channel_name != event['sender_channel_name']:
            await self.send(text_data=json.dumps(event['message']))


