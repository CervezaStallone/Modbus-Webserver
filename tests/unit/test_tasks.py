"""
Unit tests for Celery tasks.
"""

from datetime import timedelta
from unittest.mock import Mock, call, patch

import pytest
from django.utils import timezone

from modbus_app.models import CalculatedRegister, Device, Register, TrendData
from modbus_app.tasks import (aggregate_trend_data, check_alarms,
                              cleanup_old_data, daily_aggregation,
                              health_check_interfaces, poll_all_devices,
                              poll_device_registers,
                              update_calculated_registers)

pytestmark = pytest.mark.django_db


class TestPollDeviceRegisters:
    """Test poll_device_registers task."""

    @patch("modbus_app.tasks.get_register_service")
    @patch("modbus_app.tasks.broadcast_register_update")
    @patch("modbus_app.tasks.broadcast_device_update")
    def test_poll_device_success(
        self,
        mock_broadcast_device,
        mock_broadcast_register,
        mock_get_service,
        device,
        register,
    ):
        """Test successful device polling."""
        # Setup mock service
        mock_service = Mock()
        mock_service.read_device_registers.return_value = {
            register.id: (100, 10.0)  # raw_value, converted_value
        }
        mock_get_service.return_value = mock_service

        # Execute task
        poll_device_registers(device.id)

        # Verify service was called
        mock_service.read_device_registers.assert_called_once()

        # Verify trend data was created
        trend_data = TrendData.objects.filter(register=register).first()
        assert trend_data is not None
        assert trend_data.raw_value == 100
        assert trend_data.converted_value == 10.0
        assert trend_data.quality == "good"

        # Verify broadcasts
        mock_broadcast_device.assert_called_once()
        mock_broadcast_register.assert_called_once()

    @patch("modbus_app.tasks.get_register_service")
    @patch("modbus_app.tasks.broadcast_device_update")
    def test_poll_device_no_data(self, mock_broadcast_device, mock_get_service, device):
        """Test polling when no data is returned."""
        mock_service = Mock()
        mock_service.read_device_registers.return_value = {}  # No data
        mock_get_service.return_value = mock_service

        poll_device_registers(device.id)

        # Verify device status updated to error
        device.refresh_from_db()
        assert device.connection_status == "error"

    @patch("modbus_app.tasks.get_register_service")
    def test_poll_device_disabled_interface(self, mock_get_service, device):
        """Test that disabled interfaces are not polled."""
        device.interface.enabled = False
        device.interface.save()

        poll_device_registers(device.id)

        # Service should not be called
        assert not mock_get_service.called


class TestPollAllDevices:
    """Test poll_all_devices task."""

    @patch("modbus_app.tasks.poll_device_registers.delay")
    def test_poll_all_devices_triggers_polls(self, mock_poll_task, device):
        """Test that poll_all_devices triggers individual device polls."""
        # Set last_poll to None so device needs polling
        device.last_poll = None
        device.save()

        poll_all_devices()

        # Verify individual poll was triggered
        mock_poll_task.assert_called_once_with(device.id)

    @patch("modbus_app.tasks.poll_device_registers.delay")
    def test_poll_respects_interval(self, mock_poll_task, device):
        """Test that polling respects device interval."""
        # Set last_poll to recent time
        device.last_poll = timezone.now() - timedelta(seconds=2)
        device.polling_interval = 10  # 10 seconds
        device.save()

        poll_all_devices()

        # Should not poll yet
        assert not mock_poll_task.called


class TestAggregationTasks:
    """Test aggregation tasks."""

    @patch("modbus_app.tasks.DataAggregator")
    def test_aggregate_trend_data(self, mock_aggregator_class):
        """Test hourly aggregation task."""
        mock_aggregator = Mock()
        mock_aggregator.aggregate_all_registers.return_value = {"success": 5}
        mock_aggregator_class.return_value = mock_aggregator

        aggregate_trend_data()

        mock_aggregator.aggregate_all_registers.assert_called_once_with("hourly")

    @patch("modbus_app.tasks.DataAggregator")
    def test_daily_aggregation(self, mock_aggregator_class):
        """Test daily aggregation task."""
        mock_aggregator = Mock()
        mock_aggregator.aggregate_all_registers.return_value = {"success": 3}
        mock_aggregator_class.return_value = mock_aggregator

        daily_aggregation()

        mock_aggregator.aggregate_all_registers.assert_called_once_with("daily")


class TestCheckAlarms:
    """Test alarm checking task."""

    @patch("modbus_app.tasks.AlarmChecker")
    @patch("modbus_app.tasks.broadcast_alarm")
    def test_check_alarms(self, mock_broadcast, mock_checker_class):
        """Test alarm checking task."""
        mock_checker = Mock()
        mock_checker.check_all_alarms.return_value = {"checked": 5, "triggered": 1}
        mock_checker.get_active_alarms.return_value = []
        mock_checker_class.return_value = mock_checker

        check_alarms()

        mock_checker.check_all_alarms.assert_called_once()
        mock_checker.get_active_alarms.assert_called_once()


class TestCalculatedRegisters:
    """Test calculated register updates."""

    def test_update_calculated_registers(self, device, register):
        """Test calculated register formula evaluation."""
        # Create calculated register
        calc_reg = CalculatedRegister.objects.create(
            device=device, name="Power (kW)", formula="register_1 * 0.001", unit="kW"
        )
        calc_reg.source_registers.add(register)

        # Create trend data for source register
        TrendData.objects.create(
            register=register,
            timestamp=timezone.now(),
            raw_value=5000,
            converted_value=5000.0,
            quality="good",
        )

        # Execute task
        update_calculated_registers()

        # Verify calculation
        calc_reg.refresh_from_db()
        assert calc_reg.last_value == 5.0  # 5000 * 0.001
        assert calc_reg.last_calculated is not None


class TestHealthCheck:
    """Test health check task."""

    @patch("modbus_app.tasks.get_connection_manager")
    @patch("modbus_app.tasks.broadcast_connection_status")
    def test_health_check_interfaces(
        self, mock_broadcast, mock_get_manager, modbus_interface_rtu
    ):
        """Test interface health checking."""
        mock_manager = Mock()
        mock_manager.health_check.return_value = True
        mock_manager.get_statistics.return_value = {"success_count": 10}
        mock_get_manager.return_value = mock_manager

        health_check_interfaces()

        mock_manager.health_check.assert_called_once()
        mock_broadcast.assert_called_once_with(modbus_interface_rtu.id, "online")


class TestCleanupOldData:
    """Test data cleanup task."""

    @patch("modbus_app.tasks.DataAggregator")
    def test_cleanup_old_data(self, mock_aggregator_class):
        """Test old data cleanup task."""
        mock_aggregator = Mock()
        mock_aggregator.cleanup_old_data.return_value = {
            "raw_deleted": 100,
            "hourly_deleted": 50,
            "daily_deleted": 10,
        }
        mock_aggregator_class.return_value = mock_aggregator

        cleanup_old_data()

        mock_aggregator.cleanup_old_data.assert_called_once_with(
            raw_data_days=7, hourly_data_days=90, daily_data_days=730
        )
