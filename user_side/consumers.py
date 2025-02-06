import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.serializers.json import DjangoJSONEncoder
from datetime import datetime
from .models import Message, OnlineUser, Notification
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import Q
from django.contrib.auth import get_user_model
import logging
from django.db.models import (
    Q, F, Max, Count, OuterRef, Subquery, 
    CharField, DateTimeField, IntegerField
)
import uuid
from django.core.cache import cache
import base64
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from datetime import datetime
import cloudinary.uploader
import logging

logger = logging.getLogger(__name__)

def generate_room_id(user1_id, user2_id):
    """Generate a unique room ID by sorting user IDs."""
    sorted_ids = sorted([user1_id, user2_id])
    return f"room_{sorted_ids[0]}_{sorted_ids[1]}"

class NotificationService:

    @staticmethod
    @database_sync_to_async
    def get_user_channel_name(user_id):
        try:
            online_user = OnlineUser.objects.get(user_id=user_id, is_online=True)
            return f"user_{user_id}" if online_user else None
        except OnlineUser.DoesNotExist:
            return None
        
        
class ChatConsumer(AsyncWebsocketConsumer):
    active_rooms = {}
    
    @database_sync_to_async
    def increment_connection_count(self):
        """Increment the connection count for the user"""
        try:
            online_user, _ = OnlineUser.objects.get_or_create(
                user_id=self.user_id,
                defaults={'is_online': True, 'last_seen': datetime.now()}
            )
            online_user.connection_count = F('connection_count') + 1
            online_user.is_online = True
            online_user.save()
            online_user.refresh_from_db()
            return online_user.connection_count
        except Exception as e:
            logger.error(f"Error incrementing connection count: {e}")
            return 1

    @database_sync_to_async
    def decrement_connection_count(self):
        """Decrement the connection count and update online status"""
        try:
            online_user = OnlineUser.objects.get(user_id=self.user_id)
            online_user.connection_count = F('connection_count') - 1
            online_user.save()
            online_user.refresh_from_db()
            
            # If this was the last connection, mark as offline
            if online_user.connection_count <= 0:
                online_user.is_online = False
                online_user.last_seen = datetime.now()
                online_user.connection_count = 0
                online_user.save()
            return online_user.connection_count
        except OnlineUser.DoesNotExist:
            logger.error(f"OnlineUser not found for user_id: {self.user_id}")
            return 0
        except Exception as e:
            logger.error(f"Error decrementing connection count: {e}")
            return 0
        
    
    @database_sync_to_async
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None
        
    @database_sync_to_async
    def save_message(self, sender_id, receiver_id, message):
        message = Message.objects.create(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=message
        )
        # Update the last message for both users
        return message

    @database_sync_to_async
    def get_chat_history(self):
        messages = Message.objects.filter(
            (Q(sender_id=self.user_id) & Q(receiver_id=self.target_user_id)) |
            (Q(sender_id=self.target_user_id) & Q(receiver_id=self.user_id))
        ).order_by('timestamp')
        history = []
        for msg in messages:
            history.append({
                'content': msg.content,
                'sender_id': msg.sender_id,
                'receiver_id': msg.receiver_id,
                'timestamp': msg.timestamp.isoformat(),
                'media': msg.media.url if msg.media else None,
                'media_type': msg.media_type
            })
        return history

    
    @database_sync_to_async
    def update_user_online_status(self, is_online):
        OnlineUser.objects.update_or_create(
            user_id=self.user_id,
            defaults={'is_online': is_online, 'last_seen': datetime.now()}
        )

    @database_sync_to_async
    def get_online_users(self):
        """Get all online users with positive connection counts"""
        return list(OnlineUser.objects.filter(
            is_online=True, 
            connection_count__gt=0
        ).values_list('user_id', flat=True))

    @database_sync_to_async
    def mark_notifications_read_for_sender(self, sender_id):
        """Mark all notifications from a specific sender as read"""
        with transaction.atomic():
            return (
                Notification.objects.select_for_update()
                .filter(
                    user_id=self.user_id,
                    sender_id=sender_id,
                    is_read=False
                )
                .update(
                    is_read=True,
                )
            )
            
    async def broadcast_online_status(self):
        online_users = await self.get_online_users()
        await self.channel_layer.group_send(
            'online_status',
            {
                'type': 'online_status_update',
                'online_users': online_users
            }
        )

    async def online_status_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'online_status',
            'online_users': event['online_users']
        }))
        
    async def connect(self):
        try:
            # Get authenticated user
            self.user_id = int(self.scope['url_route']['kwargs']['current_user_id'])
            self.user = await self.get_user(self.user_id)
            # print("the user is ",self.user)
            if not self.user:
                await self.close()
                return

            await self.channel_layer.group_add(
                'online_status',
                self.channel_name
            )
            
            # Increment connection count instead of just setting online status
            await self.increment_connection_count()
            await self.accept()
            await self.broadcast_online_status()
            
            # Rest of your existing connect code...
            self.target_user_id = int(self.scope['url_route']['kwargs']['target_user_id'])
            if not self.target_user_id:
                raise ValueError("Target user ID is missing from the scope.")

            # Generate room name and join room group
            self.room_id = generate_room_id(self.user_id, self.target_user_id)
            self.room_group_name = f"chat_{self.room_id}"
            print("room openned............",self.room_id)
            # Track user joining room
            if self.room_id not in ChatConsumer.active_rooms:
                ChatConsumer.active_rooms[self.room_id] = set()
            ChatConsumer.active_rooms[self.room_id].add(self.user_id)
            
            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )
            
                
            await self.channel_layer.group_add(
                f"user_{self.user_id}",
                self.channel_name
            )
                        
            await self.update_user_online_status(True)
            # await self.broadcast_online_status()
            
            # await self.accept()
            await self.mark_notifications_read_for_sender(self.target_user_id)

            # Send chat history
            chat_history = await self.get_chat_history()
            await self.send(text_data=json.dumps({
                'type': 'chat_history',
                'messages': chat_history
            }))

        except Exception as e:
            logger.error(f"Error in connect: {e}")
            await self.close()


    async def disconnect(self, close_code):
        try:
            # Decrement connection count instead of just setting offline status
            remaining_connections = await self.decrement_connection_count()
            # Remove user from active room
            if hasattr(self, 'room_id'):
                if self.room_id in ChatConsumer.active_rooms:
                    ChatConsumer.active_rooms[self.room_id].discard(self.user_id)
                    if not ChatConsumer.active_rooms[self.room_id]:
                        del ChatConsumer.active_rooms[self.room_id]
            
            await self.update_user_online_status(False)
            # Only broadcast status if this was the last connection
            if remaining_connections <= 0:
                await self.broadcast_online_status()
            
            # Leave the room group
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )

            await self.channel_layer.group_discard(
                f"user_{self.user_id}",
                self.channel_name
            )


            await self.channel_layer.group_discard(
                'online_status',
                self.channel_name
            )
            logger.info(f"Disconnected: {close_code}")
        except Exception as e:
            logger.error(f"Error during disconnection: {e}")
    
    @database_sync_to_async
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None


    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            logger.info(f"Received data: {data}")

            if data.get('type') == 'request_online_status':
                await self.broadcast_online_status()
                return

            sender_id = int(self.scope['url_route']['kwargs']['current_user_id'])
            receiver_id = int(self.scope['url_route']['kwargs']['target_user_id'])
            message = data.get('message', '')
            username = data.get('username')
            media = data.get('media')
            media_type = data.get('media_type')

            if not message and not media:
                logger.info("Empty message received, skipping processing.")
                return
            
            if not username:
                user = await self.get_user(sender_id)
                username = user.username if user else f"User {sender_id}"

            logger.info(f"Processing message - Type: {media_type}, Has Media: {bool(media)}")

            # Save message only once with both text and media
            saved_message = await self.save_message_with_media(
                sender_id, receiver_id, message, media, media_type
            )
            
            current_time = datetime.now().isoformat()
            
            # Check if receiver is in the room
            receiver_in_room = (
                self.room_id in ChatConsumer.active_rooms and 
                receiver_id in ChatConsumer.active_rooms[self.room_id]
            )

            # Single message data including both text and media
            message_data = {
                'type': 'chat_message',
                'message': saved_message.content,  # Use saved message content
                'username': username,
                'sender_id': sender_id,
                'receiver_id': receiver_id,
                'timestamp': current_time,
                'media': saved_message.media if saved_message.media else None,
                'media_type': saved_message.media_type if saved_message.media_type else None
            }
                
            logger.info(f"Sending message data: {message_data}")
            
            # Send single message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                message_data
            )

            # Create notification with appropriate content
            if not receiver_in_room:
                notification_message = message if message else "Sent a media file"
                if saved_message.media and message:
                    notification_message = f"{message} (with media)"
                
                await self.channel_layer.group_send(
                    f"notifications_{receiver_id}",
                    {
                        'type': 'notification_message',
                        'message': notification_message,
                        'notification_type': 'message',
                        'sender_id': sender_id,
                        'sender_name': username,
                        'timestamp': current_time
                    }
                )

        except Exception as e:
            logger.error(f"Error in receive: {e}", exc_info=True)
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': str(e)
            })) 
    @database_sync_to_async
    def save_message_with_media(self, sender_id, receiver_id, message, media_data, media_type):
        """Save a message with media to the database and Cloudinary"""
        try:
            cloudinary_url = None
            if media_data:
                logger.info(f"Processing media of type: {media_type}")
                
                # Extract base64 data
                if ';base64,' in media_data:
                    media_data = media_data.split(';base64,')[1]
                
                try:
                    # Upload to Cloudinary
                    upload_result = cloudinary.uploader.upload(
                        f"data:image/{media_type};base64,{media_data}",
                        folder="chat_media",
                        resource_type="auto",
                    )
                    cloudinary_url = upload_result['secure_url']
                    logger.info(f"Media uploaded successfully: {cloudinary_url}")
                except Exception as upload_error:
                    logger.error(f"Cloudinary upload failed: {upload_error}")
                    raise

            # Create message
            message = Message.objects.create(
                sender_id=sender_id,
                receiver_id=receiver_id,
                content=message,
                media=cloudinary_url,
                media_type=media_type if media_type else 'text'
            )
            logger.info(f"Message saved successfully with ID: {message.id}")
            return message

        except Exception as e:
            logger.error(f"Error saving message: {e}", exc_info=True)
            raise

        
    async def chat_message(self, event):
        """Handle chat message sending to WebSocket"""
        try:
            # Remove internal fields before sending
            message_data = {k: v for k, v in event.items() if k != 'type'}
            message_data['type'] = 'new_message'  # Add message type for frontend
            
            logger.info(f"Sending WebSocket message: {message_data}")
            
            await self.send(text_data=json.dumps(message_data))
            
        except Exception as e:
            logger.error(f"Error in chat_message: {e}", exc_info=True)
            


# class NotificationConsumer(AsyncWebsocketConsumer):
#     import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db import transaction
from .models import Notification
import logging

logger = logging.getLogger(__name__)

class NotificationConsumer(AsyncWebsocketConsumer):
    user_connections = {}
    
    async def connect(self):
        try:
            self.user_id = int(self.scope['url_route']['kwargs']['user_id'])
            self.user = await self.get_user(self.user_id)
            
            if not self.user:
                await self.close()
                return
            
            # Clear any existing connections for this user
            if self.user_id in NotificationConsumer.user_connections:
                old_connection = NotificationConsumer.user_connections[self.user_id]['consumer']
                if old_connection.channel_name != self.channel_name:
                    await old_connection.close()
            
            # Store connection with timestamp
            NotificationConsumer.user_connections[self.user_id] = {
                'consumer': self,
                'connected_at': timezone.now()
            }
            
            self.notification_group_name = f"notifications_{self.user_id}"
            await self.channel_layer.group_add(
                self.notification_group_name,
                self.channel_name
            )
            
            await self.accept()
            await self.send_unread_notifications()
            
        except Exception as e:
            logger.error(f"Error in notification connect: {e}")
            await self.close()

    async def notification_message(self, event):
        """Handle incoming real-time notifications with deduplication"""
        print(f"Sending notification: {event}")
        try:
            # Add message_id to event data for tracking
            if 'message_id' not in event:
                event['message_id'] = str(uuid.uuid4())

            # Use Redis or cache to track recently sent notifications
            cache_key = f"sent_notification:{self.user_id}:{event['message_id']}"
            if await self.is_notification_recently_sent(cache_key):
                return

            notification_key = await self.generate_notification_key(event)
            notification = await self.create_or_get_notification(
                notification_key,
                event
            )
            
            if notification:
                await self.mark_notification_sent(cache_key)
                await self.send(text_data=json.dumps({
                    'type': 'new_notification',
                    'notification': {
                        'id': notification.id,
                        'message': notification.message,
                        'notification_type': notification.type,
                        'sender_id': notification.sender_id,
                        'sender_name': event['sender_name'],
                        'timestamp': notification.created_at.isoformat()
                    }
                }))
                
        except Exception as e:
            logger.error(f"Error in notification_message: {e}")
            
    @database_sync_to_async
    def is_notification_recently_sent(self, cache_key):
        """Check if notification was recently sent using cache"""
        return cache.get(cache_key) is not None

    @database_sync_to_async
    def mark_notification_sent(self, cache_key):
        """Mark notification as sent in cache"""
        cache.set(cache_key, True, timeout=10)  # 10 second timeout
        
    @database_sync_to_async
    def generate_notification_key(self, event):
        """Generate a unique key for notification deduplication"""
        return f"{self.user_id}:{event['sender_id']}:{event['message'][:50]}"

    @database_sync_to_async
    def create_or_get_notification(self, notification_key, event):
        """Create notification with deduplication using transaction"""
        with transaction.atomic():
            # Reduce the deduplication window to 10 seconds instead of 1 minute
            time_threshold = timezone.now() - timezone.timedelta(seconds=10)
            
            recent_notification = (
                Notification.objects.select_for_update()
                .filter(
                    user_id=self.user_id,
                    sender_id=event['sender_id'],
                    message=f"New message from {event['sender_name']}: {event['message'][:50]}...",
                    type=event['notification_type'],
                    created_at__gte=time_threshold
                )
                .first()
            )
            
            if recent_notification:
                # Update the existing notification's timestamp
                recent_notification.created_at = timezone.now()
                recent_notification.save()
                return recent_notification
            
            return Notification.objects.create(
                user_id=self.user_id,
                message=f"New message from {event['sender_name']}: {event['message'][:50]}...",
                type=event['notification_type'],
                sender_id=event['sender_id'],
                is_read=False,
                created_at=timezone.now()
            )

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark notification as read with proper locking"""
        with transaction.atomic():
            try:
                notification = (
                    Notification.objects.select_for_update()
                    .get(id=notification_id, user_id=self.user_id)
                )
                if not notification.is_read:
                    notification.is_read = True
                    notification.read_at = timezone.now()
                    notification.save()
                return True
            except Notification.DoesNotExist:
                return False

    @database_sync_to_async
    def mark_all_notifications_read(self):
        """Mark all notifications as read atomically"""
        with transaction.atomic():
            return (
                Notification.objects.select_for_update()
                .filter(user_id=self.user_id, is_read=False)
                .update(
                    is_read=True,
                    read_at=timezone.now()
                )
            )

    @database_sync_to_async
    def create_notification(self, event):
        """Create a new notification in the database"""
        return Notification.objects.create(
            user_id=self.user_id,
            message=f"New message from {event['sender_name']}: {event['message'][:50]}...",
            type=event['notification_type'],
            sender_id=event['sender_id'],
            # referenced_object_id=event['referenced_object_id'],
            is_read=False
        )
        
    @database_sync_to_async
    def get_user(self, user_id):
        User = get_user_model()
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def get_unread_notifications(self):
        """Get all unread notifications for the user"""
        return list(Notification.objects.filter(
            user_id=self.user_id,
            is_read=False
        ).order_by('-created_at').values(
            'id',
            'message',
            'type',
            'created_at',
            'user_id',
            'sender_id', 
            # 'referenced_object_id'
        ))

    async def send_unread_notifications(self):
        """Send all unread notifications to the user"""
        notifications = await self.get_unread_notifications()
        if notifications:
            await self.send(text_data=json.dumps({
                'type': 'unread_notifications',
                'notifications': [
                    {
                        'id': n['id'],
                        'message': n['message'],
                        'notification_type': n['type'],
                        'timestamp': n['created_at'].isoformat(),
                        'user_id': n['user_id'],
                        'sender_id': n['sender_id'],
                        # 'referenced_object_id': n['referenced_object_id']
                    }
                    for n in notifications
                ]
            }))

    async def disconnect(self, close_code):
        print(f"Disconnecting with code: {close_code}")
        try:
            # Remove from notification group
            if hasattr(self, 'notification_group_name'):
                await self.channel_layer.group_discard(
                    self.notification_group_name,
                    self.channel_name
                )
            
            # Clean up user connection
            if (self.user_id in NotificationConsumer.user_connections and 
                NotificationConsumer.user_connections[self.user_id]['consumer'].channel_name == self.channel_name):
                del NotificationConsumer.user_connections[self.user_id]
                
        except Exception as e:
            logger.error(f"Error in notification disconnect: {e}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            if data.get('type') == 'fetch_unread_notifications':
                await self.send_unread_notifications()
            if data.get('type') == 'mark_read':
                success = False
                if 'notification_id' in data:
                    # Mark single notification as read
                    success = await self.mark_notification_read(data['notification_id'])
                elif data.get('mark_all'):
                    # Mark all notifications as read
                    success = await self.mark_all_notifications_read()
                
                if success:
                    # Send confirmation back to client
                    await self.send(text_data=json.dumps({
                        'type': 'mark_read_response',
                        'success': True,
                        'notification_id': data.get('notification_id')
                    }))
                    
                    # Send updated unread notifications
                    await self.send_unread_notifications()
                
        except Exception as e:
            logger.error(f"Error in notification receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Failed to process notification request'
            }))


    @database_sync_to_async
    def get_existing_notification(self, event):
        """Check if a notification already exists for this message"""
        return Notification.objects.filter(
            user_id=self.user_id,
            sender_id=event['sender_id'],
            message=f"New message from {event['sender_name']}: {event['message'][:50]}...",
            type=event['notification_type'],
            created_at__gte=datetime.now().replace(second=0, microsecond=0)  # Within the last minute
        ).exists()