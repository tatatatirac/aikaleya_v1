from channels.generic.websocket import AsyncJsonWebsocketConsumer


class ClientCalendarConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.client_id = self.scope["url_route"]["kwargs"]["client_id"]
        self.group_name = f"client_calendar_{self.client_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def calendar_event(self, event):
        await self.send_json(event["payload"])

