import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import ChatRoom, Message

User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        sender_id = data['sender_id']
        room_id = data['room_id']
        
        # Save message to database
        saved_message = await self.save_message(room_id, sender_id, message)
        
        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'sender_id': sender_id,
                'sender_name': saved_message['sender_name'],
                'timestamp': saved_message['timestamp'],
                'message_id': saved_message['message_id']
            }
        )
    
    # Receive message from room group
    async def chat_message(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_name': event['sender_name'],
            'timestamp': event['timestamp'],
            'message_id': event['message_id']
        }))
    
    @database_sync_to_async
    def save_message(self, room_id, sender_id, content):
        room = ChatRoom.objects.get(id=room_id)
        sender = User.objects.get(id=sender_id)
        message = Message.objects.create(
            room=room,
            sender=sender,
            content=content
        )
        
        # Update the room's updated_at timestamp
        room.save()
        
        return {
            'message_id': message.id,
            'sender_name': f"{sender.first_name} {sender.last_name}",
            'timestamp': message.timestamp.strftime("%b %d, %Y %H:%M")
        }
