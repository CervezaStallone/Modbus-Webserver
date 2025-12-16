"""
Pytest configuration and fixtures.
"""

import pytest


@pytest.fixture
def api_client():
    """DRF API client."""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def modbus_interface_rtu(db):
    """Create a test RTU interface."""
    from modbus_app.models import ModbusInterface
    return ModbusInterface.objects.create(
        name='Test RTU',
        protocol='RTU',
        port='COM1',
        baudrate=9600,
        parity='N',
        stopbits=1,
        bytesize=8,
        timeout=3.0,
        enabled=True
    )


@pytest.fixture
def modbus_interface_tcp(db):
    """Create a test TCP interface."""
    from modbus_app.models import ModbusInterface
    return ModbusInterface.objects.create(
        name='Test TCP',
        protocol='TCP',
        host='192.168.1.100',
        tcp_port=502,
        timeout=3.0,
        enabled=True
    )


@pytest.fixture
def device(db, modbus_interface_rtu):
    """Create a test device."""
    from modbus_app.models import Device
    return Device.objects.create(
        name='Test Device',
        interface=modbus_interface_rtu,
        slave_id=1,
        polling_interval=5,
        enabled=True
    )


@pytest.fixture
def register(db, device):
    """Create a test register."""
    from modbus_app.models import Register
    return Register.objects.create(
        device=device,
        name='Test Register',
        function_code=3,
        address=100,
        data_type='UINT16',
        conversion_factor=1.0,
        conversion_offset=0.0,
        unit='°C',
        enabled=True
    )


@pytest.fixture
def test_user(db, django_user_model):
    """Create a test user for each test."""
    import uuid
    username = f'testuser_{uuid.uuid4().hex[:8]}'
    return django_user_model.objects.create_user(
        username=username,
        password='testpass123',
        email=f'{username}@example.com'
    )


@pytest.fixture
def admin_user(db, django_user_model):
    """Create an admin user for each test."""
    import uuid
    username = f'admin_{uuid.uuid4().hex[:8]}'
    return django_user_model.objects.create_superuser(
        username=username,
        password='admin123',
        email=f'{username}@example.com'
    )
