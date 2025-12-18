"""
Utility functions for WebSocket broadcasting.
"""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def broadcast_register_update(register_id, value, timestamp, unit=""):
    """
    Broadcast register value update to dashboard.

    Args:
        register_id: ID of the register
        value: Converted value
        timestamp: Timestamp of the measurement
        unit: Unit of measurement
    """
    try:
        channel_layer = get_channel_layer()

        if channel_layer is None:
            return

        data = {
            "type": "register_update",
            "register_id": register_id,
            "value": value,
            "timestamp": (timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp)),
            "unit": unit,
        }

        async_to_sync(channel_layer.group_send)(
            "dashboard",
            {
                "type": "register_update",
                "data": data,
            },
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error broadcasting register update for register {register_id}: {e}")


def broadcast_device_update(device_id, status, error_message=""):
    """
    Broadcast device status update.

    Args:
        device_id: ID of the device
        status: Connection status (online/offline/error)
        error_message: Optional error message
    """
    try:
        channel_layer = get_channel_layer()

        if channel_layer is None:
            return

        data = {
            "type": "device_update",
            "device_id": device_id,
            "status": status,
            "error_message": error_message,
        }

        async_to_sync(channel_layer.group_send)(
            f"device_{device_id}",
            {
                "type": "device.update",
                "data": data,
            },
        )

        # Also send to dashboard
        async_to_sync(channel_layer.group_send)(
            "dashboard",
            {
                "type": "register.update",
                "data": data,
            },
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error broadcasting device update for device {device_id}: {e}")


def broadcast_alarm(alarm_id, event_type, register_name, value, message, severity):
    """
    Broadcast alarm event.

    Args:
        alarm_id: ID of the alarm
        event_type: Type of event (triggered/cleared/acknowledged)
        register_name: Name of the register
        value: Current value that triggered the alarm
        message: Alarm message
        severity: Alarm severity
    """
    try:
        channel_layer = get_channel_layer()

        if channel_layer is None:
            return

        data = {
            "type": "alarm_event",
            "alarm_id": alarm_id,
            "event_type": event_type,
            "register_name": register_name,
            "value": value,
            "message": message,
            "severity": severity,
        }

        async_to_sync(channel_layer.group_send)(
            "alarms",
            {
                "type": "alarm.event",
                "data": data,
            },
        )

        # Also send to dashboard
        async_to_sync(channel_layer.group_send)(
            "dashboard",
            {
                "type": "register.update",
                "data": data,
            },
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error broadcasting alarm for alarm {alarm_id}: {e}")


def broadcast_connection_status(interface_id, status):
    """
    Broadcast interface connection status.

    Args:
        interface_id: ID of the interface
        status: Connection status
    """
    try:
        channel_layer = get_channel_layer()

        if channel_layer is None:
            return

        data = {
            "type": "interface_status",
            "interface_id": interface_id,
            "status": status,
        }

        async_to_sync(channel_layer.group_send)(
            "dashboard",
            {
                "type": "register.update",
                "data": data,
            },
        )
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error broadcasting connection status for interface {interface_id}: {e}")
