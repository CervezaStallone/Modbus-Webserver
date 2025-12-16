"""
Unit tests for models.
"""

import pytest
from django.core.exceptions import ValidationError

from modbus_app.models import Device, ModbusInterface, Register


@pytest.mark.django_db
class TestModbusInterface:
    """Tests for ModbusInterface model."""

    def test_create_rtu_interface(self, modbus_interface_rtu):
        """Test creating RTU interface."""
        assert modbus_interface_rtu.name == "Test RTU"
        assert modbus_interface_rtu.protocol == "RTU"
        assert modbus_interface_rtu.port == "COM1"
        assert modbus_interface_rtu.baudrate == 9600

    def test_create_tcp_interface(self, modbus_interface_tcp):
        """Test creating TCP interface."""
        assert modbus_interface_tcp.name == "Test TCP"
        assert modbus_interface_tcp.protocol == "TCP"
        assert modbus_interface_tcp.host == "192.168.1.100"
        assert modbus_interface_tcp.tcp_port == 502

    def test_update_status(self, modbus_interface_rtu):
        """Test updating interface status."""
        modbus_interface_rtu.update_status("online")
        assert modbus_interface_rtu.connection_status == "online"
        assert modbus_interface_rtu.last_seen is not None


@pytest.mark.django_db
class TestDevice:
    """Tests for Device model."""

    def test_create_device(self, device):
        """Test creating device."""
        assert device.name == "Test Device"
        assert device.slave_id == 1
        assert device.polling_interval == 5

    def test_update_status(self, device):
        """Test updating device status."""
        device.update_status("online")
        assert device.connection_status == "online"
        assert device.error_count == 0


@pytest.mark.django_db
class TestRegister:
    """Tests for Register model."""

    def test_create_register(self, register):
        """Test creating register."""
        assert register.name == "Test Register"
        assert register.function_code == 3
        assert register.address == 100
        assert register.data_type == "UINT16"

    def test_convert_value(self, register):
        """Test value conversion."""
        raw_value = 100
        converted = register.convert_value(raw_value)
        assert converted == 100.0

        # Test with conversion factor
        register.conversion_factor = 0.1
        converted = register.convert_value(raw_value)
        assert converted == 10.0

        # Test with offset
        register.conversion_offset = 5.0
        converted = register.convert_value(raw_value)
        assert converted == 15.0

    def test_is_writable(self, register):
        """Test is_writable property."""
        assert not register.is_writable

        register.function_code = 6
        register.writable = True
        assert register.is_writable
