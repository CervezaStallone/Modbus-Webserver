"""
Service layer for register operations.
"""

import logging

from modbus_app.services.modbus_driver import create_driver

logger = logging.getLogger(__name__)


class RegisterService:
    """Service for reading and writing Modbus registers."""

    def __init__(self):
        self.drivers = {}  # Cache drivers per interface

    def get_driver(self, interface):
        """Get or create driver for interface."""
        if interface.id not in self.drivers:
            self.drivers[interface.id] = create_driver(interface)
        return self.drivers[interface.id]

    def read_register(self, register):
        """
        Read single register value.

        Args:
            register: Register model instance

        Returns:
            tuple: (raw_value, converted_value) or (None, None) on error
        """
        try:
            device = register.device
            interface = device.interface

            if not interface.enabled or not device.enabled or not register.enabled:
                logger.debug(
                    f"Register {register.name} or its device/interface is disabled"
                )
                return None, None

            driver = self.get_driver(interface)

            # Determine which read function to use based on function code
            if register.function_code == 1:
                raw_data = driver.read_coils(
                    device.slave_id, register.address, register.count
                )
            elif register.function_code == 2:
                raw_data = driver.read_discrete_inputs(
                    device.slave_id, register.address, register.count
                )
            elif register.function_code == 3:
                raw_data = driver.read_holding_registers(
                    device.slave_id, register.address, register.count
                )
            elif register.function_code == 4:
                raw_data = driver.read_input_registers(
                    device.slave_id, register.address, register.count
                )
            else:
                logger.error(
                    f"Unsupported read function code: {register.function_code}"
                )
                return None, None

            if raw_data is None:
                return None, None

            # Convert raw data to value based on data type
            if register.function_code in [1, 2]:  # Coils/discrete inputs
                raw_value = 1 if raw_data[0] else 0
            else:  # Registers
                raw_value = driver.convert_registers_to_value(
                    raw_data,
                    register.data_type,
                    register.byte_order,
                    register.word_order,
                )

            if raw_value is None:
                return None, None

            # Apply conversion formula
            converted_value = register.convert_value(raw_value)

            return raw_value, converted_value

        except Exception as e:
            logger.error(f"Error reading register {register.name}: {e}")
            return None, None

    def read_device_registers(self, device):
        """
        Read all enabled registers for a device.

        Args:
            device: Device model instance

        Returns:
            dict: {register_id: (raw_value, converted_value)}
        """
        results = {}

        for register in device.registers.filter(enabled=True):
            raw, converted = self.read_register(register)
            if raw is not None:
                results[register.id] = (raw, converted)

        return results

    def write_register(self, register, value):
        """
        Write value to register.

        Args:
            register: Register model instance
            value: Value to write

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            device = register.device
            interface = device.interface

            if not interface.enabled or not device.enabled or not register.enabled:
                logger.error(
                    f"Register {register.name} or its device/interface is disabled"
                )
                return False

            if not register.is_writable:
                logger.error(f"Register {register.name} is not writable")
                return False

            driver = self.get_driver(interface)

            # Convert value if needed
            # For simplicity, assuming value is already in correct format
            # In production, you'd want proper validation and conversion

            if register.function_code == 5:
                # Write single coil
                return driver.write_coil(device.slave_id, register.address, bool(value))

            elif register.function_code == 6:
                # Write single register
                return driver.write_register(
                    device.slave_id, register.address, int(value)
                )

            elif register.function_code == 15:
                # Write multiple coils
                values = [bool(value)]  # Single value for now
                return driver.write_coils(device.slave_id, register.address, values)

            elif register.function_code == 16:
                # Write multiple registers
                values = [int(value)]  # Single value for now
                return driver.write_registers(device.slave_id, register.address, values)

            else:
                logger.error(
                    f"Unsupported write function code: {register.function_code}"
                )
                return False

        except Exception as e:
            logger.error(f"Error writing to register {register.name}: {e}")
            return False

    def batch_read_registers(self, register_list):
        """
        Read multiple registers efficiently.

        Args:
            register_list: List of Register model instances

        Returns:
            dict: {register_id: (raw_value, converted_value)}
        """
        results = {}

        # Group registers by device for efficiency
        from collections import defaultdict

        registers_by_device = defaultdict(list)

        for register in register_list:
            if (
                register.enabled
                and register.device.enabled
                and register.device.interface.enabled
            ):
                registers_by_device[register.device.id].append(register)

        # Read all registers for each device
        for device_id, registers in registers_by_device.items():
            for register in registers:
                raw, converted = self.read_register(register)
                if raw is not None:
                    results[register.id] = (raw, converted)

        return results

    def close_all_connections(self):
        """Close all driver connections."""
        for driver in self.drivers.values():
            try:
                driver.disconnect()
            except Exception as e:
                logger.error(f"Error closing driver connection: {e}")

        self.drivers.clear()


# Global service instance
_register_service = None


def get_register_service():
    """Get global RegisterService instance."""
    global _register_service
    if _register_service is None:
        _register_service = RegisterService()
    return _register_service
