"""
Celery tasks for background processing.
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from celery import shared_task
from modbus_app.models import (
    Device, Register, TrendData, TrendDataAggregated,
    Alarm, AlarmHistory, ModbusInterface
)
from modbus_app.services.register_service import get_register_service
from modbus_app.services.connection_manager import get_connection_manager
from modbus_app.services.data_aggregator import DataAggregator
from modbus_app.services.alarm_checker import AlarmChecker
from modbus_app.utils.websocket_broadcast import (
    broadcast_register_update,
    broadcast_device_update,
    broadcast_alarm,
    broadcast_connection_status
)

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def poll_device_registers(self, device_id):
    """
    Poll all enabled registers for a device.
    
    Args:
        device_id: ID of the device to poll
    """
    try:
        device = Device.objects.select_related('interface').get(id=device_id, enabled=True)
        
        if not device.interface.enabled:
            return
        
        register_service = get_register_service()
        results = register_service.read_device_registers(device)
        
        if not results:
            # No data read, mark device as error
            device.update_status('error')
            broadcast_device_update(device_id, 'error', 'No data received')
            return
        
        # Update device status
        device.update_status('online')
        broadcast_device_update(device_id, 'online')
        
        # Store trend data in bulk
        trend_data_list = []
        now = timezone.now()
        
        for register_id, (raw_value, converted_value) in results.items():
            try:
                register = Register.objects.get(id=register_id)
                
                # Create trend data entry
                trend_data = TrendData(
                    register_id=register_id,
                    timestamp=now,
                    raw_value=raw_value,
                    converted_value=converted_value,
                    quality='good'
                )
                trend_data_list.append(trend_data)
                
                # Broadcast update
                broadcast_register_update(
                    register_id,
                    converted_value,
                    now,
                    register.unit
                )
            
            except Exception as e:
                logger.error(f"Error processing register {register_id}: {e}")
        
        # Bulk create trend data
        if trend_data_list:
            TrendData.objects.bulk_create(trend_data_list)
            logger.debug(f"Stored {len(trend_data_list)} trend data entries for device {device.name}")
    
    except Device.DoesNotExist:
        logger.error(f"Device {device_id} not found or not enabled")
    
    except Exception as e:
        logger.error(f"Error polling device {device_id}: {e}")
        
        # Retry task
        raise self.retry(exc=e, countdown=10)


@shared_task
def poll_all_devices():
    """Poll all enabled devices based on their polling intervals."""
    now = timezone.now()
    
    devices = Device.objects.filter(
        enabled=True,
        interface__enabled=True
    ).select_related('interface')
    
    for device in devices:
        # Check if device should be polled based on interval
        should_poll = False
        
        if device.last_poll is None:
            should_poll = True
        else:
            time_since_poll = (now - device.last_poll).total_seconds()
            if time_since_poll >= device.polling_interval:
                should_poll = True
        
        if should_poll:
            # Trigger device poll task
            poll_device_registers.delay(device.id)


@shared_task
def aggregate_trend_data():
    """Calculate hourly aggregates for all registers."""
    aggregator = DataAggregator()
    results = aggregator.aggregate_all_registers('hourly')
    logger.info(f"Hourly aggregation complete: {results}")


@shared_task
def daily_aggregation():
    """Calculate daily aggregates."""
    aggregator = DataAggregator()
    results = aggregator.aggregate_all_registers('daily')
    logger.info(f"Daily aggregation complete: {results}")


@shared_task
def check_alarms():
    """Check alarm conditions for all enabled alarms."""
    checker = AlarmChecker()
    results = checker.check_all_alarms()
    logger.info(f"Alarm check complete: {results}")
    
    # Broadcast active alarms
    active_alarms = checker.get_active_alarms()
    for alarm_history in active_alarms:
        broadcast_alarm(
            alarm_history.alarm.id,
            'active',
            alarm_history.alarm.register.name,
            alarm_history.trigger_value,
            alarm_history.alarm.message,
            alarm_history.alarm.severity
        )


@shared_task
def update_calculated_registers():
    """Update all calculated register values using safe formula evaluation."""
    from modbus_app.models import CalculatedRegister
    from asteval import Interpreter
    
    calculated_registers = CalculatedRegister.objects.all().prefetch_related('source_registers')
    
    # Create safe evaluator with whitelisted functions only
    aeval = Interpreter()
    # Add only safe mathematical functions
    aeval.symtable['abs'] = abs
    aeval.symtable['min'] = min
    aeval.symtable['max'] = max
    aeval.symtable['round'] = round
    aeval.symtable['pow'] = pow
    
    for calc_reg in calculated_registers:
        try:
            # Get latest values for source registers
            values = {}
            for i, source_reg in enumerate(calc_reg.source_registers.all()):
                latest_data = TrendData.objects.filter(
                    register=source_reg,
                    quality='good'
                ).order_by('-timestamp').first()
                
                if latest_data:
                    values[f'register_{i+1}'] = latest_data.converted_value
                else:
                    values[f'register_{i+1}'] = 0
            
            # Evaluate formula safely using asteval
            try:
                result = aeval(calc_reg.formula, show_errors=False, raise_errors=False)
                
                if aeval.error:
                    logger.error(f"Formula error for {calc_reg.name}: {aeval.error[0].get_error()}")
                    continue
                
                calc_reg.last_value = float(result)
                calc_reg.last_calculated = timezone.now()
                calc_reg.save(update_fields=['last_value', 'last_calculated'])
                
                logger.debug(f"Updated calculated register {calc_reg.name}: {result}")
                
            except (ValueError, TypeError) as e:
                logger.error(f"Error converting formula result for {calc_reg.name}: {e}")
        
        except Exception as e:
            logger.error(f"Error updating calculated register {calc_reg.name}: {e}")


@shared_task
def health_check_interfaces():
    """Check health of all interfaces."""
    interfaces = ModbusInterface.objects.filter(enabled=True)
    connection_manager = get_connection_manager()
    
    for interface in interfaces:
        try:
            is_healthy = connection_manager.health_check(interface)
            
            if is_healthy:
                broadcast_connection_status(interface.id, 'online')
            else:
                broadcast_connection_status(interface.id, 'error')
                
            # Log statistics
            stats = connection_manager.get_statistics(interface.id)
            logger.debug(f"Interface {interface.name} stats: {stats}")
        
        except Exception as e:
            logger.error(f"Error checking interface {interface.name}: {e}")
            interface.update_status('error')
            broadcast_connection_status(interface.id, 'error')


@shared_task
def cleanup_old_data():
    """Clean up old trend data based on retention policy."""
    aggregator = DataAggregator()
    results = aggregator.cleanup_old_data(
        raw_data_days=7,
        hourly_data_days=90,
        daily_data_days=730
    )
    logger.info(f"Data cleanup complete: {results}")
