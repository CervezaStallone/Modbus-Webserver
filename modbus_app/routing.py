"""
WebSocket URL routing for modbus_app.
"""

from django.urls import path

from modbus_app import consumers

websocket_urlpatterns = [
    path("ws/dashboard/", consumers.DashboardConsumer.as_asgi()),
    path("ws/device/<int:device_id>/", consumers.DeviceConsumer.as_asgi()),
    path("ws/alarms/", consumers.AlarmConsumer.as_asgi()),
]
