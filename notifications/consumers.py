import json
from channels.generic.websocket import AsyncWebsocketConsumer

class TaskConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        data = json.loads(text_data)
        task_id = data['id']
        status = data['status']

        await self.send(text_data=json.dumps({
            'id': task_id,
            'status': status
        }))
