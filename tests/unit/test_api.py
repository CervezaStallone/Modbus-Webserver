"""
Unit tests for API endpoints.
"""

from datetime import timedelta

import pytest
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from modbus_app.models import (Alarm, Device, ModbusInterface, Register,
                               TrendData)

pytestmark = pytest.mark.django_db


class TestInterfaceAPI:
    """Test ModbusInterface API endpoints."""

    def test_list_interfaces(self, admin_user):
        """Test listing interfaces."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Create test interface
        ModbusInterface.objects.create(
            name="Test Interface", protocol="RTU", port="COM1", baudrate=9600
        )

        response = client.get("/api/v1/interfaces/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 1

    def test_create_interface(self, admin_user):
        """Test creating an interface."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        data = {
            "name": "New Interface",
            "protocol": "TCP",
            "host": "192.168.1.100",
            "tcp_port": 502,
            "timeout": 3.0,
            "enabled": True,
        }

        response = client.post("/api/v1/interfaces/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert ModbusInterface.objects.filter(name="New Interface").exists()

    def test_update_interface(self, admin_user, modbus_interface_rtu):
        """Test updating an interface."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        data = {
            "name": "Updated Name",
            "protocol": "RTU",
            "port": "COM2",
            "baudrate": 19200,
            "parity": "E",
            "stopbits": 1,
            "bytesize": 8,
            "timeout": 3.0,
            "enabled": False,
        }

        response = client.put(
            f"/api/v1/interfaces/{modbus_interface_rtu.id}/", data, format="json"
        )
        assert response.status_code == status.HTTP_200_OK

        modbus_interface_rtu.refresh_from_db()
        assert modbus_interface_rtu.name == "Updated Name"
        assert modbus_interface_rtu.baudrate == 19200

    def test_delete_interface(self, admin_user, modbus_interface_rtu):
        """Test deleting an interface."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.delete(f"/api/v1/interfaces/{modbus_interface_rtu.id}/")
        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]
        assert not ModbusInterface.objects.filter(id=modbus_interface_rtu.id).exists()


class TestDeviceAPI:
    """Test Device API endpoints."""

    def test_list_devices(self, admin_user, device):
        """Test listing devices."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get("/api/v1/devices/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_create_device(self, admin_user, modbus_interface_rtu):
        """Test creating a device."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        data = {
            "name": "New Device",
            "interface": modbus_interface_rtu.id,
            "slave_id": 5,
            "polling_interval": 10,
            "enabled": True,
        }

        response = client.post("/api/v1/devices/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Device.objects.filter(name="New Device").exists()

    def test_device_unique_slave_id_per_interface(self, admin_user, device):
        """Test that slave_id must be unique per interface."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Try to create device with same slave_id on same interface
        data = {
            "name": "Duplicate Device",
            "interface": device.interface.id,
            "slave_id": device.slave_id,  # Same as existing device
            "polling_interval": 5,
            "enabled": True,
        }

        response = client.post("/api/v1/devices/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestRegisterAPI:
    """Test Register API endpoints."""

    def test_list_registers(self, admin_user, register):
        """Test listing registers."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        response = client.get("/api/v1/registers/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_create_register(self, admin_user, device):
        """Test creating a register."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        data = {
            "device": device.id,
            "name": "Temperature Sensor",
            "function_code": 4,
            "address": 200,
            "data_type": "INT16",
            "conversion_factor": 0.1,
            "conversion_offset": 0.0,
            "unit": "°C",
            "enabled": True,
            "writable": False,
        }

        response = client.post("/api/v1/registers/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Register.objects.filter(name="Temperature Sensor").exists()

    def test_register_current_value(self, admin_user, register):
        """Test that register includes current value."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Create trend data
        TrendData.objects.create(
            register=register,
            timestamp=timezone.now(),
            raw_value=250,
            converted_value=25.0,
            quality="good",
        )

        response = client.get(f"/api/v1/registers/{register.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert "current_value" in response.data
        assert response.data["current_value"]["value"] == 25.0


class TestTrendDataAPI:
    """Test TrendData API endpoints."""

    def test_list_trend_data(self, admin_user, register):
        """Test listing trend data."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        # Create some trend data
        for i in range(5):
            TrendData.objects.create(
                register=register,
                timestamp=timezone.now() - timedelta(minutes=i),
                raw_value=i * 10,
                converted_value=float(i * 10),
                quality="good",
            )

        # Query all trend data and filter by register
        response = client.get(f"/api/v1/trend-data/?register={register.id}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 5

    def test_trend_data_filtering_by_time(self, admin_user, register):
        """Test filtering trend data by time range."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        now = timezone.now()

        # Create data at different times
        TrendData.objects.create(
            register=register,
            timestamp=now - timedelta(hours=2),
            raw_value=10,
            converted_value=10.0,
            quality="good",
        )
        recent_td = TrendData.objects.create(
            register=register,
            timestamp=now - timedelta(minutes=30),
            raw_value=20,
            converted_value=20.0,
            quality="good",
        )

        # Query all trend data for this register
        response = client.get(f"/api/v1/trend-data/?register={register.id}")
        assert response.status_code == status.HTTP_200_OK
        # Should get both records
        assert len(response.data["results"]) == 2


class TestAlarmAPI:
    """Test Alarm API endpoints."""

    def test_list_alarms(self, admin_user, register):
        """Test listing alarms."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        Alarm.objects.create(
            register=register,
            name="Test Alarm",
            condition="greater_than",
            threshold_high=100.0,
            severity="warning",
            message="Value too high",
            enabled=True,
        )

        response = client.get("/api/v1/alarms/")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

    def test_create_alarm(self, admin_user, register):
        """Test creating an alarm."""
        client = APIClient()
        client.force_authenticate(user=admin_user)

        data = {
            "register": register.id,
            "name": "Critical Temperature",
            "condition": "greater_than",
            "threshold_high": 80.0,
            "severity": "critical",
            "message": "Temperature exceeded safe limit",
            "enabled": True,
        }

        response = client.post("/api/v1/alarms/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Alarm.objects.filter(name="Critical Temperature").exists()
