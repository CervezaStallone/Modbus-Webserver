"""
Unit tests for service layer.
"""

from datetime import timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest
from django.utils import timezone

from modbus_app.models import (Alarm, AlarmHistory, Device, ModbusInterface,
                               Register, TrendData)
from modbus_app.services.alarm_checker import AlarmChecker
from modbus_app.services.data_aggregator import DataAggregator
from modbus_app.services.modbus_driver import (ModbusRTUDriver,
                                               ModbusTCPDriver, create_driver)
from modbus_app.services.register_service import RegisterService

pytestmark = pytest.mark.django_db


class TestModbusDriverCreation:
    """Test Modbus driver creation."""

    def test_create_rtu_driver(self, modbus_interface_rtu):
        """Test creating RTU driver from interface."""
        driver = create_driver(modbus_interface_rtu)
        assert isinstance(driver, ModbusRTUDriver)
        assert driver.interface == modbus_interface_rtu

    def test_create_tcp_driver(self, modbus_interface_tcp):
        """Test creating TCP driver from interface."""
        driver = create_driver(modbus_interface_tcp)
        assert isinstance(driver, ModbusTCPDriver)
        assert driver.interface == modbus_interface_tcp


class TestRegisterService:
    """Test RegisterService functionality."""

    @patch("modbus_app.services.register_service.create_driver")
    def test_get_driver_caches_driver(self, mock_create_driver):
        """Test that drivers are cached per interface."""
        mock_driver = Mock()
        mock_create_driver.return_value = mock_driver

        service = RegisterService()
        interface = Mock(id=1)

        # First call should create driver
        driver1 = service.get_driver(interface)
        assert driver1 == mock_driver
        assert mock_create_driver.call_count == 1

        # Second call should use cached driver
        driver2 = service.get_driver(interface)
        assert driver2 == mock_driver
        assert mock_create_driver.call_count == 1  # Not called again

    @patch("modbus_app.services.register_service.create_driver")
    def test_read_register_disabled_returns_none(self, mock_create_driver, register):
        """Test that reading disabled register returns None."""
        register.enabled = False
        register.save()

        service = RegisterService()
        raw, converted = service.read_register(register)

        assert raw is None
        assert converted is None
        assert not mock_create_driver.called

    @patch("modbus_app.services.register_service.create_driver")
    def test_read_register_applies_conversion(self, mock_create_driver, register):
        """Test that register conversion is applied correctly."""
        # Setup mock driver
        mock_driver = Mock()
        mock_driver.read_holding_registers.return_value = [100]
        mock_driver.convert_registers_to_value.return_value = 100
        mock_create_driver.return_value = mock_driver

        # Set conversion factor
        register.conversion_factor = 0.1
        register.conversion_offset = 5.0
        register.save()

        service = RegisterService()
        raw, converted = service.read_register(register)

        assert raw == 100
        assert converted == 15.0  # (100 * 0.1) + 5.0


class TestAlarmChecker:
    """Test AlarmChecker functionality."""

    def test_check_alarm_greater_than_trigger(self, register):
        """Test greater_than alarm triggering."""
        # Create alarm
        alarm = Alarm.objects.create(
            register=register,
            name="High Temperature",
            condition="greater_than",
            threshold_high=50.0,
            enabled=True,
            severity="warning",
            message="Temperature too high",
        )

        # Create trend data above threshold
        TrendData.objects.create(
            register=register,
            timestamp=timezone.now(),
            raw_value=60,
            converted_value=60.0,
            quality="good",
        )

        checker = AlarmChecker()
        triggered = checker.check_alarm(alarm)

        assert triggered is True
        assert alarm.is_active() is True

    def test_check_alarm_less_than_trigger(self, register):
        """Test less_than alarm triggering."""
        alarm = Alarm.objects.create(
            register=register,
            name="Low Temperature",
            condition="less_than",
            threshold_high=10.0,
            enabled=True,
            severity="critical",
            message="Temperature too low",
        )

        TrendData.objects.create(
            register=register,
            timestamp=timezone.now(),
            raw_value=5,
            converted_value=5.0,
            quality="good",
        )

        checker = AlarmChecker()
        triggered = checker.check_alarm(alarm)

        assert triggered is True
        assert alarm.is_active() is True

    def test_check_alarm_disabled_does_not_trigger(self, register):
        """Test that disabled alarms do not trigger."""
        alarm = Alarm.objects.create(
            register=register,
            name="Disabled Alarm",
            condition="greater_than",
            threshold_high=50.0,
            enabled=False,  # Disabled
            severity="warning",
            message="Should not trigger",
        )

        TrendData.objects.create(
            register=register,
            timestamp=timezone.now(),
            raw_value=100,
            converted_value=100.0,
            quality="good",
        )

        checker = AlarmChecker()
        triggered = checker.check_alarm(alarm)

        assert triggered is False
        assert alarm.is_active() is False


class TestDataAggregator:
    """Test DataAggregator functionality."""

    def test_aggregate_hourly_calculates_stats(self, register):
        """Test hourly aggregation calculates min/max/avg correctly."""
        now = timezone.now()
        hour_start = now.replace(minute=0, second=0, microsecond=0)

        # Create sample data
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for i, value in enumerate(values):
            TrendData.objects.create(
                register=register,
                timestamp=hour_start + timedelta(minutes=i * 10),
                raw_value=value,
                converted_value=value,
                quality="good",
            )

        aggregator = DataAggregator()
        count = aggregator.aggregate_hourly(register, hour_start)

        assert count == 1  # One aggregation record created

        # Verify aggregation exists with correct values
        from modbus_app.models import TrendDataAggregated

        agg = TrendDataAggregated.objects.filter(
            register=register, timestamp=hour_start, interval="hourly"
        ).first()

        assert agg is not None
        assert agg.min_value == 10.0
        assert agg.max_value == 50.0
        assert agg.avg_value == 30.0
        assert agg.sample_count == 5

    def test_aggregate_hourly_no_data_returns_zero(self, register):
        """Test aggregation with no data returns 0."""
        now = timezone.now()
        hour_start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=5)

        aggregator = DataAggregator()
        count = aggregator.aggregate_hourly(register, hour_start)

        assert count == 0
