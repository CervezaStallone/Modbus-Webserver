"""
Factory Boy factories for creating test data.
"""

import factory
from factory.django import DjangoModelFactory
from modbus_app.models import (
    ModbusInterface, Device, Register, TrendData,
    DashboardGroup, DashboardWidget, Alarm
)


class ModbusInterfaceFactory(DjangoModelFactory):
    """Factory for ModbusInterface model."""
    
    class Meta:
        model = ModbusInterface
    
    name = factory.Sequence(lambda n: f'Interface {n}')
    protocol = 'RTU'
    port = 'COM1'
    baudrate = 9600
    parity = 'N'
    stopbits = 1
    bytesize = 8
    timeout = 3.0
    enabled = True


class TCPInterfaceFactory(ModbusInterfaceFactory):
    """Factory for TCP ModbusInterface."""
    
    protocol = 'TCP'
    host = '192.168.1.100'
    tcp_port = 502
    port = ''


class DeviceFactory(DjangoModelFactory):
    """Factory for Device model."""
    
    class Meta:
        model = Device
    
    name = factory.Sequence(lambda n: f'Device {n}')
    interface = factory.SubFactory(ModbusInterfaceFactory)
    slave_id = factory.Sequence(lambda n: n + 1)
    polling_interval = 5
    enabled = True


class RegisterFactory(DjangoModelFactory):
    """Factory for Register model."""
    
    class Meta:
        model = Register
    
    device = factory.SubFactory(DeviceFactory)
    name = factory.Sequence(lambda n: f'Register {n}')
    function_code = 3
    address = factory.Sequence(lambda n: n)
    data_type = 'UINT16'
    conversion_factor = 1.0
    conversion_offset = 0.0
    unit = '°C'
    enabled = True


class TrendDataFactory(DjangoModelFactory):
    """Factory for TrendData model."""
    
    class Meta:
        model = TrendData
    
    register = factory.SubFactory(RegisterFactory)
    raw_value = factory.Faker('pyfloat', min_value=0, max_value=100)
    converted_value = factory.LazyAttribute(lambda obj: obj.raw_value * 0.1)
    quality = 'good'


class DashboardGroupFactory(DjangoModelFactory):
    """Factory for DashboardGroup model."""
    
    class Meta:
        model = DashboardGroup
    
    name = factory.Sequence(lambda n: f'Group {n}')
    row_order = factory.Sequence(lambda n: n)
    collapsed = False


class DashboardWidgetFactory(DjangoModelFactory):
    """Factory for DashboardWidget model."""
    
    class Meta:
        model = DashboardWidget
    
    group = factory.SubFactory(DashboardGroupFactory)
    register = factory.SubFactory(RegisterFactory)
    title = factory.Sequence(lambda n: f'Widget {n}')
    widget_type = 'line_chart'
    column_position = 0
    row_position = 0
    width = 6
    height = 300


class AlarmFactory(DjangoModelFactory):
    """Factory for Alarm model."""
    
    class Meta:
        model = Alarm
    
    register = factory.SubFactory(RegisterFactory)
    name = factory.Sequence(lambda n: f'Alarm {n}')
    condition = 'greater_than'
    threshold_high = 80.0
    severity = 'warning'
    message = 'Threshold exceeded'
    enabled = True
