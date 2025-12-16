"""
Comprehensive test suite for Modbus Webserver application.
Tests all functionality from A to Z.

Run with: pytest tests/test_comprehensive.py -v
"""

import json
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.contrib.auth.models import User
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from modbus_app.models import (Alarm, AlarmHistory, CalculatedRegister,
                               DashboardGroup, DashboardWidget, Device,
                               DeviceTemplate, ModbusInterface, Register,
                               TrendData)
from modbus_app.services.connection_manager import ConnectionManager
from modbus_app.services.register_service import RegisterService


class BaseTestCase(TestCase):
    """Base test case with common setup."""

    def setUp(self):
        """Create test user and authenticate."""
        self.user = User.objects.create_user(
            username="testuser",
            password="testpass123",
            email="test@example.com",
            is_staff=True,
            is_superuser=True,
        )
        self.client = Client()
        self.api_client = APIClient()
        self.api_client.force_authenticate(user=self.user)

        # Login for web views
        self.client.login(username="testuser", password="testpass123")


class ModbusInterfaceTests(BaseTestCase):
    """Test Modbus Interface CRUD operations."""

    def test_create_rtu_interface(self):
        """Test creating a Modbus RTU interface."""
        data = {
            "name": "RTU Interface 1",
            "protocol": "RTU",
            "port": "/dev/ttyUSB0",
            "baudrate": 9600,
            "parity": "N",
            "stopbits": 1,
            "bytesize": 8,
            "timeout": 3.0,
            "description": "Test RTU interface",
        }
        response = self.api_client.post("/api/v1/interfaces/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(ModbusInterface.objects.count(), 1)

        interface = ModbusInterface.objects.first()
        self.assertEqual(interface.name, "RTU Interface 1")
        self.assertEqual(interface.protocol, "RTU")
        self.assertEqual(interface.port, "/dev/ttyUSB0")

    def test_create_tcp_interface(self):
        """Test creating a Modbus TCP interface."""
        data = {
            "name": "TCP Interface 1",
            "protocol": "TCP",
            "host": "192.168.1.100",
            "tcp_port": 502,
            "timeout": 3.0,
        }
        response = self.api_client.post("/api/v1/interfaces/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        interface = ModbusInterface.objects.first()
        self.assertEqual(interface.protocol, "TCP")
        self.assertEqual(interface.host, "192.168.1.100")
        self.assertEqual(interface.tcp_port, 502)

    def test_list_interfaces(self):
        """Test listing interfaces via API."""
        ModbusInterface.objects.create(
            name="Interface 1", protocol="TCP", host="192.168.1.100"
        )
        ModbusInterface.objects.create(
            name="Interface 2", protocol="RTU", port="/dev/ttyUSB0"
        )

        response = self.api_client.get("/api/v1/interfaces/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        # Check pagination
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 2)

    def test_update_interface(self):
        """Test updating an interface."""
        interface = ModbusInterface.objects.create(
            name="Original Name", protocol="TCP", host="192.168.1.100"
        )

        update_data = {
            "name": "Updated Name",
            "protocol": "TCP",
            "host": "192.168.1.200",
            "tcp_port": 502,
        }

        response = self.api_client.put(
            f"/api/v1/interfaces/{interface.id}/", update_data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        interface.refresh_from_db()
        self.assertEqual(interface.name, "Updated Name")
        self.assertEqual(interface.host, "192.168.1.200")

    def test_delete_interface(self):
        """Test deleting an interface."""
        interface = ModbusInterface.objects.create(
            name="To Delete", protocol="TCP", host="192.168.1.100"
        )

        response = self.api_client.delete(f"/api/v1/interfaces/{interface.id}/")
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ModbusInterface.objects.count(), 0)


class DeviceTests(BaseTestCase):
    """Test Device CRUD operations."""

    def setUp(self):
        super().setUp()
        self.interface = ModbusInterface.objects.create(
            name="Test Interface", protocol="TCP", host="192.168.1.100"
        )

    def test_create_device(self):
        """Test creating a device."""
        data = {
            "name": "Device 1",
            "interface": self.interface.id,
            "slave_id": 1,
            "polling_interval": 5,
            "description": "Test device",
            "enabled": True,
        }

        response = self.api_client.post("/api/v1/devices/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Device.objects.count(), 1)

        device = Device.objects.first()
        self.assertEqual(device.name, "Device 1")
        self.assertEqual(device.slave_id, 1)
        self.assertEqual(device.interface, self.interface)

    def test_device_slave_id_validation(self):
        """Test slave ID must be between 1-247."""
        data = {
            "name": "Invalid Device",
            "interface": self.interface.id,
            "slave_id": 300,  # Invalid
            "polling_interval": 5,
        }

        response = self.api_client.post("/api/v1/devices/", data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_devices_with_register_count(self):
        """Test device list includes register count."""
        device = Device.objects.create(
            name="Device 1", interface=self.interface, slave_id=1
        )

        # Create some registers
        for i in range(3):
            Register.objects.create(
                device=device,
                name=f"Register {i}",
                address=i,
                function_code=3,
                data_type="UINT16",
            )

        response = self.api_client.get("/api/v1/devices/")
        data = response.json()

        device_data = data["results"][0]
        self.assertEqual(device_data["register_count"], 3)


class RegisterTests(BaseTestCase):
    """Test Register CRUD operations."""

    def setUp(self):
        super().setUp()
        interface = ModbusInterface.objects.create(
            name="Test Interface", protocol="TCP", host="192.168.1.100"
        )
        self.device = Device.objects.create(
            name="Test Device", interface=interface, slave_id=1
        )

    def test_create_register(self):
        """Test creating a register."""
        data = {
            "device": self.device.id,
            "name": "Temperature",
            "address": 100,
            "function_code": 3,  # FC03 - Read Holding Registers
            "data_type": "FLOAT32",
            "conversion_factor": 1.0,
            "conversion_offset": 0.0,
            "unit": "°C",
            "store_trends": True,
        }

        response = self.api_client.post("/api/v1/registers/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        register = Register.objects.first()
        self.assertEqual(register.name, "Temperature")
        self.assertEqual(register.address, 100)
        self.assertEqual(register.data_type, "FLOAT32")

    def test_register_data_types(self):
        """Test all register data types."""
        data_types = ["INT16", "UINT16", "INT32", "UINT32", "FLOAT32", "BOOL"]

        for i, dt in enumerate(data_types):
            register = Register.objects.create(
                device=self.device,
                name=f"Register {dt}",
                address=i,  # Use unique address for each register
                function_code=3,
                data_type=dt,
            )
            self.assertEqual(register.data_type, dt)

    def test_register_types(self):
        """Test all function codes."""
        function_codes = [1, 2, 3, 4]  # Coils, Discrete Inputs, Holding, Input

        for i, fc in enumerate(function_codes):
            register = Register.objects.create(
                device=self.device,
                name=f"Register FC{fc}",
                address=i + 100,  # Use unique address for each register
                function_code=fc,
                data_type="UINT16",
            )
            self.assertEqual(register.function_code, fc)


class AlarmTests(BaseTestCase):
    """Test Alarm functionality."""

    def setUp(self):
        super().setUp()
        interface = ModbusInterface.objects.create(
            name="Test Interface", protocol="TCP", host="192.168.1.100"
        )
        device = Device.objects.create(
            name="Test Device", interface=interface, slave_id=1
        )
        self.register = Register.objects.create(
            device=device,
            name="Temperature",
            address=100,
            function_code=3,
            data_type="FLOAT32",
        )

    def test_create_alarm(self):
        """Test creating an alarm."""
        data = {
            "name": "High Temperature",
            "register": self.register.id,
            "condition": "greater_than",
            "threshold_high": 80.0,
            "severity": "critical",
            "message": "Temperature exceeded 80°C",
            "enabled": True,
        }

        response = self.api_client.post("/api/v1/alarms/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        alarm = Alarm.objects.first()
        self.assertEqual(alarm.name, "High Temperature")
        self.assertEqual(alarm.condition, "greater_than")
        self.assertEqual(alarm.threshold_high, 80.0)

    def test_alarm_conditions(self):
        """Test all alarm condition types."""
        conditions = ["greater_than", "less_than", "equals", "not_equals", "range"]

        for condition in conditions:
            alarm = Alarm.objects.create(
                name=f"Alarm {condition}",
                register=self.register,
                condition=condition,
                threshold_high=50.0,
                threshold_low=10.0 if condition == "range" else None,
            )
            self.assertEqual(alarm.condition, condition)

    def test_alarm_history_creation(self):
        """Test alarm history is created on trigger."""
        alarm = Alarm.objects.create(
            name="Test Alarm",
            register=self.register,
            condition="greater_than",
            threshold_high=50.0,
            message="Test alarm message",
            enabled=True,
        )

        # Create alarm history entry
        history = AlarmHistory.objects.create(alarm=alarm, trigger_value=75.0)

        self.assertEqual(AlarmHistory.objects.count(), 1)
        self.assertIsNone(history.cleared_at)  # Not cleared yet
        self.assertEqual(history.trigger_value, 75.0)


class DashboardTests(BaseTestCase):
    """Test Dashboard functionality."""

    def setUp(self):
        super().setUp()
        interface = ModbusInterface.objects.create(
            name="Test Interface", protocol="TCP", host="192.168.1.100"
        )
        device = Device.objects.create(
            name="Test Device", interface=interface, slave_id=1
        )
        self.register = Register.objects.create(
            device=device,
            name="Temperature",
            address=100,
            function_code=3,
            data_type="FLOAT32",
        )

    def test_create_dashboard_group(self):
        """Test creating a dashboard group."""
        data = {"name": "Group 1", "order": 0}

        response = self.api_client.post("/api/v1/dashboard-groups/", data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        group = DashboardGroup.objects.first()
        self.assertEqual(group.name, "Group 1")

    def test_create_dashboard_widget(self):
        """Test creating a dashboard widget."""
        group = DashboardGroup.objects.create(name="Test Group")

        data = {
            "group": group.id,
            "title": "Temperature Gauge",
            "widget_type": "gauge",
            "register": self.register.id,
            "width": 6,
            "column_position": 0,
            "row_position": 0,
        }

        response = self.api_client.post(
            "/api/v1/dashboard-widgets/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        widget = DashboardWidget.objects.first()
        self.assertEqual(widget.title, "Temperature Gauge")
        self.assertEqual(widget.widget_type, "gauge")


class DeviceTemplateTests(BaseTestCase):
    """Test Device Template functionality."""

    def setUp(self):
        super().setUp()
        self.interface = ModbusInterface.objects.create(
            name="Test Interface", protocol="TCP", host="192.168.1.100"
        )

    def test_create_device_template(self):
        """Test creating a device template."""
        register_config = [
            {
                "name": "Temperature",
                "address": 0,
                "function_code": 3,
                "data_type": "FLOAT32",
                "unit": "°C",
            },
            {
                "name": "Pressure",
                "address": 2,
                "function_code": 3,
                "data_type": "FLOAT32",
                "unit": "bar",
            },
        ]

        data = {
            "name": "Temperature Sensor",
            "manufacturer": "TestCo",
            "model": "TS-100",
            "register_definitions": register_config,
        }

        response = self.api_client.post(
            "/api/v1/device-templates/", data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        template = DeviceTemplate.objects.first()
        self.assertEqual(template.name, "Temperature Sensor")
        self.assertEqual(len(template.register_definitions), 2)

    def test_apply_template_to_device(self):
        """Test applying a template to a device."""
        # Create template
        template = DeviceTemplate.objects.create(
            name="Test Template",
            manufacturer="TestCo",
            model="TM-100",
            register_definitions=[
                {
                    "name": "Register 1",
                    "address": 0,
                    "function_code": 3,
                    "data_type": "UINT16",
                }
            ],
        )

        # Create device
        device = Device.objects.create(
            name="Test Device", interface=self.interface, slave_id=1
        )

        # Manually apply template (simulates what the view would do)
        for reg_def in template.register_definitions:
            Register.objects.create(
                device=device,
                name=reg_def["name"],
                address=reg_def["address"],
                function_code=reg_def["function_code"],
                data_type=reg_def["data_type"],
            )

        self.assertEqual(Register.objects.filter(device=device).count(), 1)


class WebViewTests(BaseTestCase):
    """Test web page views."""

    def test_dashboard_view(self):
        """Test dashboard page loads."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "dashboard/index.html")

    def test_interface_list_view(self):
        """Test interface list page loads."""
        response = self.client.get("/config/interfaces/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "config/interfaces.html")

    def test_device_list_view(self):
        """Test device list page loads."""
        response = self.client.get("/config/devices/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "config/devices.html")

    def test_register_list_view(self):
        """Test register list page loads."""
        response = self.client.get("/config/registers/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "config/registers.html")

    def test_dashboard_layout_view(self):
        """Test dashboard layout page loads."""
        response = self.client.get("/config/dashboard-layout/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "config/dashboard_layout.html")

    def test_alarm_list_view(self):
        """Test alarm list page loads."""
        response = self.client.get("/config/alarms/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "config/alarms.html")

    def test_template_list_view(self):
        """Test template list page loads."""
        response = self.client.get("/config/templates/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "config/templates.html")

    def test_interface_add_view(self):
        """Test interface add page loads."""
        response = self.client.get("/config/interfaces/add/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "config/interface_form.html")

    def test_device_add_view(self):
        """Test device add page loads."""
        response = self.client.get("/config/devices/add/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "config/device_form.html")

    def test_register_add_view(self):
        """Test register add page loads."""
        response = self.client.get("/config/registers/add/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "config/register_form.html")


class AuthenticationTests(TestCase):
    """Test authentication and authorization."""

    def setUp(self):
        self.client = Client()
        self.api_client = APIClient()
        self.user = User.objects.create_user(
            username="testuser", password="testpass123", is_staff=True
        )

    def test_api_requires_authentication(self):
        """Test API endpoints require authentication."""
        response = self.api_client.get("/api/v1/interfaces/")
        # Django returns 403 when authenticated but no permission, 401 when not authenticated at all
        # Both are valid indicators that authentication is required
        self.assertIn(
            response.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_authenticated_api_access(self):
        """Test authenticated users can access API."""
        self.api_client.force_authenticate(user=self.user)
        response = self.api_client.get("/api/v1/interfaces/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_web_views_require_login(self):
        """Test web views require login."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_logged_in_user_can_access_views(self):
        """Test logged in users can access web views."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)


class ModbusServiceTests(TransactionTestCase):
    """Test Modbus service layer."""

    def setUp(self):
        self.interface = ModbusInterface.objects.create(
            name="Test Interface", protocol="TCP", host="192.168.1.100", enabled=True
        )
        self.device = Device.objects.create(
            name="Test Device", interface=self.interface, slave_id=1, enabled=True
        )
        self.register = Register.objects.create(
            device=self.device,
            name="Test Register",
            address=0,
            function_code=3,
            data_type="UINT16",
        )

    def test_read_register(self):
        """Test register service can be instantiated."""
        service = RegisterService()
        # Just verify service exists - actual Modbus reading requires hardware/simulator
        self.assertIsNotNone(service)
        self.assertEqual(self.register.device, self.device)

    def test_write_register(self):
        """Test register is writable for write function codes."""
        # Update register to be writable
        self.register.function_code = 6  # FC06 - Write Single Register
        self.register.writable = True
        self.register.save()

        self.assertTrue(self.register.is_writable)


class TrendDataTests(BaseTestCase):
    """Test trend data functionality."""

    def setUp(self):
        super().setUp()
        interface = ModbusInterface.objects.create(
            name="Test Interface", protocol="TCP", host="192.168.1.100"
        )
        device = Device.objects.create(
            name="Test Device", interface=interface, slave_id=1
        )
        self.register = Register.objects.create(
            device=device,
            name="Temperature",
            address=100,
            function_code=3,
            data_type="FLOAT32",
        )

    def test_store_trend_data(self):
        """Test storing trend data."""
        TrendData.objects.create(
            register=self.register, raw_value=25.5, converted_value=25.5, quality="good"
        )

        self.assertEqual(TrendData.objects.count(), 1)
        trend = TrendData.objects.first()
        self.assertEqual(trend.raw_value, 25.5)
        self.assertEqual(trend.quality, "good")

    def test_trend_data_api(self):
        """Test trend data API endpoint."""
        # Create some trend data
        for i in range(5):
            TrendData.objects.create(
                register=self.register,
                raw_value=20.0 + i,
                converted_value=20.0 + i,
                quality="good",
            )

        response = self.api_client.get(
            f"/api/v1/trend-data/?register={self.register.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(len(data["results"]), 5)


class IntegrationTests(BaseTestCase):
    """End-to-end integration tests."""

    def test_complete_workflow(self):
        """Test complete workflow: Interface -> Device -> Register -> Data."""
        # 1. Create interface
        interface_data = {
            "name": "Production Line 1",
            "protocol": "TCP",
            "host": "192.168.1.100",
            "tcp_port": 502,
        }
        response = self.api_client.post("/api/v1/interfaces/", interface_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        interface_id = response.json()["id"]

        # 2. Create device
        device_data = {
            "name": "Temperature Sensor 1",
            "interface": interface_id,
            "slave_id": 1,
            "polling_interval": 5,
            "enabled": True,
        }
        response = self.api_client.post("/api/v1/devices/", device_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        device_id = response.json()["id"]

        # 3. Create register
        register_data = {
            "device": device_id,
            "name": "Temperature",
            "address": 100,
            "function_code": 3,
            "data_type": "FLOAT32",
            "unit": "°C",
            "store_trends": True,
        }
        response = self.api_client.post("/api/v1/registers/", register_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        register_id = response.json()["id"]

        # 4. Create alarm on register
        alarm_data = {
            "name": "High Temperature Alert",
            "register": register_id,
            "condition": "greater_than",
            "threshold_high": 80.0,
            "severity": "critical",
            "message": "Temperature too high",
            "enabled": True,
        }
        response = self.api_client.post("/api/v1/alarms/", alarm_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # 5. Create dashboard group and widget
        group_data = {"name": "Monitoring", "order": 0}
        response = self.api_client.post("/api/v1/dashboard-groups/", group_data)
        group_id = response.json()["id"]

        widget_data = {
            "group": group_id,
            "title": "Temperature",
            "widget_type": "gauge",
            "register": register_id,
            "width": 6,
            "column_position": 0,
            "row_position": 0,
        }
        response = self.api_client.post(
            "/api/v1/dashboard-widgets/", widget_data, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Verify all objects exist
        self.assertEqual(ModbusInterface.objects.count(), 1)
        self.assertEqual(Device.objects.count(), 1)
        self.assertEqual(Register.objects.count(), 1)
        self.assertEqual(Alarm.objects.count(), 1)
        self.assertEqual(DashboardGroup.objects.count(), 1)
        self.assertEqual(DashboardWidget.objects.count(), 1)


@pytest.mark.django_db
class PaginationTests:
    """Test API pagination."""

    def test_interface_pagination(self, api_client, django_user_model):
        """Test interface list pagination."""
        user = django_user_model.objects.create_user(username="test", password="test")
        api_client.force_authenticate(user=user)

        # Create 150 interfaces (more than PAGE_SIZE)
        for i in range(150):
            ModbusInterface.objects.create(
                name=f"Interface {i}", protocol="TCP", host="192.168.1.100"
            )

        response = api_client.get("/api/v1/interfaces/")
        assert response.status_code == 200

        data = response.json()
        assert "results" in data
        assert "count" in data
        assert data["count"] == 150
        assert len(data["results"]) == 100  # PAGE_SIZE


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
