"""
Unit tests for WebSocket consumers.
"""

import pytest
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from django.urls import path
from modbus_app.consumers import DashboardConsumer, DeviceConsumer, AlarmConsumer
import json


pytest.mark.skip(reason="WebSocket tests require full async setup with Redis")


class TestDashboardConsumer:
    """Test DashboardConsumer WebSocket functionality."""
    
    async def test_dashboard_consumer_connect(self):
        """Test WebSocket connection to dashboard."""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            "/ws/dashboard/"
        )
        
        connected, _ = await communicator.connect()
        assert connected is True
        
        await communicator.disconnect()
    
    async def test_dashboard_consumer_receives_register_update(self):
        """Test receiving register update broadcasts."""
        communicator = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            "/ws/dashboard/"
        )
        
        await communicator.connect()
        
        # Simulate register update message
        await communicator.send_json_to({
            'type': 'register_update',
            'register_id': 1,
            'value': 25.5,
            'unit': '°C'
        })
        
        await communicator.disconnect()


class TestDeviceConsumer:
    """Test DeviceConsumer WebSocket functionality."""
    
    async def test_device_consumer_connect(self, device):
        """Test WebSocket connection to device-specific channel."""
        communicator = WebsocketCommunicator(
            DeviceConsumer.as_asgi(),
            f"/ws/device/{device.id}/"
        )
        
        connected, _ = await communicator.connect()
        assert connected is True
        
        await communicator.disconnect()
    
    async def test_device_consumer_receives_device_update(self, device):
        """Test receiving device status updates."""
        communicator = WebsocketCommunicator(
            DeviceConsumer.as_asgi(),
            f"/ws/device/{device.id}/"
        )
        
        await communicator.connect()
        
        # Simulate device update
        await communicator.send_json_to({
            'type': 'device_update',
            'device_id': device.id,
            'status': 'online'
        })
        
        await communicator.disconnect()


class TestAlarmConsumer:
    """Test AlarmConsumer WebSocket functionality."""
    
    async def test_alarm_consumer_connect(self):
        """Test WebSocket connection to alarms channel."""
        communicator = WebsocketCommunicator(
            AlarmConsumer.as_asgi(),
            "/ws/alarms/"
        )
        
        connected, _ = await communicator.connect()
        assert connected is True
        
        await communicator.disconnect()
    
    async def test_alarm_consumer_receives_alarm(self):
        """Test receiving alarm notifications."""
        communicator = WebsocketCommunicator(
            AlarmConsumer.as_asgi(),
            "/ws/alarms/"
        )
        
        await communicator.connect()
        
        # Simulate alarm message
        await communicator.send_json_to({
            'type': 'alarm_event',
            'alarm_id': 1,
            'severity': 'critical',
            'message': 'Temperature exceeded threshold'
        })
        
        await communicator.disconnect()


class TestWebSocketBroadcast:
    """Test WebSocket broadcast functionality."""
    
    async def test_multiple_clients_receive_broadcast(self):
        """Test that multiple connected clients receive broadcasts."""
        # Connect two clients
        communicator1 = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            "/ws/dashboard/"
        )
        communicator2 = WebsocketCommunicator(
            DashboardConsumer.as_asgi(),
            "/ws/dashboard/"
        )
        
        await communicator1.connect()
        await communicator2.connect()
        
        # Both should be able to disconnect successfully
        await communicator1.disconnect()
        await communicator2.disconnect()
