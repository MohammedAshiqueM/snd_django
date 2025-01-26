from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
from .models import Schedule
from django.contrib.auth import get_user_model
from datetime import datetime
import json
import subprocess
import sys
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from datetime import datetime
import tempfile
import os

User = get_user_model()
# class CodeEditorConsumer(AsyncWebsocketConsumer):
#     SUPPORTED_LANGUAGES = {
#         'python': {
#             'file_extension': '.py',
#             'run_command': lambda filename: [sys.executable, filename]
#         },
#         'javascript': {
#             'file_extension': '.js',
#             'run_command': lambda filename: ['node', filename]
#         },
#         'cpp': {
#             'file_extension': '.cpp',
#             'run_command': lambda filename: [
#                 'g++', filename, '-o', filename.replace('.cpp', ''), 
#                 '&&', filename.replace('.cpp', '')
#             ]
#         },
#         'java': {
#             'file_extension': '.java',
#             'run_command': lambda filename: [
#                 'javac', filename, 
#                 '&&', 'java', os.path.splitext(os.path.basename(filename))[0]
#             ]
#         },
#         'typescript': {
#             'file_extension': '.ts',
#             'run_command': lambda filename: ['ts-node', filename]
#         },
#         'rust': {
#             'file_extension': '.rs',
#             'run_command': lambda filename: ['rustc', filename, '-o', filename.replace('.rs', ''), '&&', filename.replace('.rs', '')]
#         },
#         'go': {
#             'file_extension': '.go',
#             'run_command': lambda filename: ['go', 'run', filename]
#         }
#     }

class VideoMeetConsumer(AsyncWebsocketConsumer):
    SUPPORTED_LANGUAGES = {
        'python': {
            'file_extension': '.py',
            'run_command': lambda filename: [sys.executable, filename]
        },
        'javascript': {
            'file_extension': '.js',
            'run_command': lambda filename: ['node', filename]
        },
        'cpp': {
            'file_extension': '.cpp',
            'run_command': lambda filename: [
                'g++', filename, '-o', filename.replace('.cpp', ''), 
                '&&', filename.replace('.cpp', '')
            ]
        },
        'java': {
            'file_extension': '.java',
            'run_command': lambda filename: [
                'javac', filename, 
                '&&', 'java', os.path.splitext(os.path.basename(filename))[0]
            ]
        },
        'typescript': {
            'file_extension': '.ts',
            'run_command': lambda filename: ['ts-node', filename]
        },
        'rust': {
            'file_extension': '.rs',
            'run_command': lambda filename: ['rustc', filename, '-o', filename.replace('.rs', ''), '&&', filename.replace('.rs', '')]
        },
        'go': {
            'file_extension': '.go',
            'run_command': lambda filename: ['go', 'run', filename]
        }
    }
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
        if message_type in ['code_change', 'language_change']:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'relay_message',
                    'message': data,
                    'sender_channel_name': self.channel_name
                }
            )
        
        elif message_type == 'run_code':
            await self.run_code(data)
        
        elif message_type == 'clear_terminal':
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'clear_terminal'
                }
            )  
            
        elif message_type == 'chat':
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
           
    async def clear_terminal(self, event):
        await self.send(text_data=json.dumps({
            'type': 'clear_terminal'
        })) 
        
    async def code_execution_result(self, event):
        await self.send(text_data=json.dumps({
            'type': 'code_execution_result',
            'output': event.get('output', ''),
            'error': event.get('error', ''),
            'language': event.get('language', '')
        }))
        
    async def run_code(self, data):
        language = data.get('language', 'python')
        content = data.get('content', '')

        if language not in self.SUPPORTED_LANGUAGES:
            await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'code_execution_result',
                'error': f'Unsupported language: {language}',
                'language': language
            }
        )
            return

        try:
            with tempfile.NamedTemporaryFile(
                suffix=self.SUPPORTED_LANGUAGES[language]['file_extension'], 
                delete=False
            ) as temp_file:
                temp_file.write(content.encode('utf-8'))
                temp_file.flush()
                temp_filename = temp_file.name

            # Execute the code
            process = await self.async_run_command(
                self.SUPPORTED_LANGUAGES[language]['run_command'](temp_filename)
            )

            # Broadcast execution results to all participants
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'code_execution_result',
                    'output': process['stdout'],
                    'error': process['stderr'],
                    'language': language
                }
            )

        except Exception as e:
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'code_execution_result',
                    'error': str(e),
                    'language': language
                }
            )
        finally:
            # Clean up temporary file
            if 'temp_filename' in locals():
                os.unlink(temp_filename)

    
    
    async def async_run_command(self, command):
        # Asynchronously run shell commands
        process = await self.run_subprocess(command)
        return {
            'stdout': process.stdout.decode('utf-8').strip() if process.stdout else '',
            'stderr': process.stderr.decode('utf-8').strip() if process.stderr else ''
        }

    @database_sync_to_async
    def run_subprocess(self, command):
        return subprocess.run(
            command, 
            capture_output=True, 
            shell=isinstance(command, str) or len(command) > 2
        )
        
    async def chat_message(self, event):
        # Send chat message to WebSocket
        await self.send(text_data=json.dumps(event['message']))
        
    async def relay_message(self, event):
        if self.channel_name != event['sender_channel_name']:
            await self.send(text_data=json.dumps(event['message']))


