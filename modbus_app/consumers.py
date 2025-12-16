"""
WebSocket consumers for real-time updates.
"""

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.serializers.json import DjangoJSONEncoder


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for dashboard real-time updates.
    """

    async def connect(self):
        """Accept WebSocket connection and join dashboard group."""
        self.room_group_name = "dashboard"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        """Leave dashboard group."""
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """Receive message from WebSocket (not used for now)."""
        pass

    async def register_update(self, event):
        """Receive register update from room group and send to WebSocket."""
        await self.send(text_data=json.dumps(event["data"], cls=DjangoJSONEncoder))


class DeviceConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for device-specific updates.
    """

    async def connect(self):
        """Accept WebSocket connection and join device group."""
        self.device_id = self.scope["url_route"]["kwargs"]["device_id"]
        self.room_group_name = f"device_{self.device_id}"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        """Leave device group."""
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """Receive message from WebSocket."""
        pass

    async def device_update(self, event):
        """Receive device update from room group and send to WebSocket."""
        await self.send(text_data=json.dumps(event["data"], cls=DjangoJSONEncoder))


class AlarmConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for alarm notifications.
    """

    async def connect(self):
        """Accept WebSocket connection and join alarms group."""
        self.room_group_name = "alarms"

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        """Leave alarms group."""
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """Receive message from WebSocket."""
        pass

    async def alarm_event(self, event):
        """Receive alarm event from room group and send to WebSocket."""
        await self.send(text_data=json.dumps(event["data"], cls=DjangoJSONEncoder))
