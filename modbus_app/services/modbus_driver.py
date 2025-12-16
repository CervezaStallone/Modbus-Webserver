"""
Modbus driver base class and implementations for RTU and TCP protocols.
"""

import logging
import struct
from abc import ABC, abstractmethod

from pymodbus.client import ModbusSerialClient, ModbusTcpClient
from pymodbus.exceptions import ModbusException

logger = logging.getLogger(__name__)


class ModbusDriverBase(ABC):
    """Abstract base class for Modbus drivers."""

    def __init__(self, interface_config):
        """
        Initialize driver with interface configuration.

        Args:
            interface_config: ModbusInterface model instance
        """
        self.interface = interface_config
        self.client = None
        self._connected = False

    @abstractmethod
    def connect(self):
        """Establish connection to Modbus device."""
        pass

    @abstractmethod
    def disconnect(self):
        """Close connection to Modbus device."""
        pass

    def is_connected(self):
        """Check if connection is active."""
        return self._connected and self.client is not None

    def read_coils(self, slave_id, address, count=1):
        """Read coils (FC01)."""
        try:
            if not self.is_connected():
                if not self.connect():
                    logger.error(f"Failed to connect before reading coils")
                    return None

            result = self.client.read_coils(address, count, slave=slave_id)

            if result.isError():
                logger.error(f"Error reading coils from slave {slave_id} at {address}")
                self._connected = False  # Mark connection as failed
                return None

            return result.bits[:count]
        except Exception as e:
            logger.error(f"Exception reading coils: {e}")
            self._connected = False
            return None

    def read_discrete_inputs(self, slave_id, address, count=1):
        """Read discrete inputs (FC02)."""
        try:
            if not self.is_connected():
                if not self.connect():
                    logger.error(f"Failed to connect before reading discrete inputs")
                    return None

            result = self.client.read_discrete_inputs(address, count, slave=slave_id)

            if result.isError():
                logger.error(
                    f"Error reading discrete inputs from slave {slave_id} at {address}"
                )
                self._connected = False
                return None

            return result.bits[:count]
        except Exception as e:
            logger.error(f"Exception reading discrete inputs: {e}")
            self._connected = False
            return None

    def read_holding_registers(self, slave_id, address, count=1):
        """Read holding registers (FC03)."""
        try:
            if not self.is_connected():
                if not self.connect():
                    logger.error(f"Failed to connect before reading holding registers")
                    return None

            result = self.client.read_holding_registers(address, count, slave=slave_id)

            if result.isError():
                logger.error(
                    f"Error reading holding registers from slave {slave_id} at {address}"
                )
                self._connected = False
                return None

            return result.registers
        except Exception as e:
            logger.error(f"Exception reading holding registers: {e}")
            self._connected = False
            return None

    def read_input_registers(self, slave_id, address, count=1):
        """Read input registers (FC04)."""
        try:
            if not self.is_connected():
                if not self.connect():
                    logger.error(f"Failed to connect before reading input registers")
                    return None

            result = self.client.read_input_registers(address, count, slave=slave_id)

            if result.isError():
                logger.error(
                    f"Error reading input registers from slave {slave_id} at {address}"
                )
                self._connected = False
                return None

            return result.registers
        except Exception as e:
            logger.error(f"Exception reading input registers: {e}")
            self._connected = False
            return None

    def write_coil(self, slave_id, address, value):
        """Write single coil (FC05)."""
        try:
            if not self.is_connected():
                if not self.connect():
                    logger.error(f"Failed to connect before writing coil")
                    return False

            result = self.client.write_coil(address, value, slave=slave_id)

            if result.isError():
                logger.error(f"Error writing coil to slave {slave_id} at {address}")
                self._connected = False
                return False

            return True
        except Exception as e:
            logger.error(f"Exception writing coil: {e}")
            self._connected = False
            return False

    def write_register(self, slave_id, address, value):
        """Write single register (FC06)."""
        try:
            if not self.is_connected():
                self.connect()

            result = self.client.write_register(address, value, slave=slave_id)

            if result.isError():
                logger.error(f"Error writing register to slave {slave_id} at {address}")
                return False

            return True
        except Exception as e:
            logger.error(f"Exception writing register: {e}")
            return False

    def write_coils(self, slave_id, address, values):
        """Write multiple coils (FC15)."""
        try:
            if not self.is_connected():
                if not self.connect():
                    logger.error(f"Failed to connect before writing coils")
                    return False

            result = self.client.write_coils(address, values, slave=slave_id)

            if result.isError():
                logger.error(f"Error writing coils to slave {slave_id} at {address}")
                self._connected = False
                return False

            return True
        except Exception as e:
            logger.error(f"Exception writing coils: {e}")
            self._connected = False
            return False

    def write_registers(self, slave_id, address, values):
        """Write multiple registers (FC16)."""
        try:
            if not self.is_connected():
                if not self.connect():
                    logger.error(f"Failed to connect before writing registers")
                    return False

            result = self.client.write_registers(address, values, slave=slave_id)

            if result.isError():
                logger.error(
                    f"Error writing registers to slave {slave_id} at {address}"
                )
                self._connected = False
                return False

            return True
        except Exception as e:
            logger.error(f"Exception writing registers: {e}")
            self._connected = False
            return False

    def convert_registers_to_value(
        self, registers, data_type, byte_order="big", word_order="high_low"
    ):
        """
        Convert register values to actual data type.

        Args:
            registers: List of register values (16-bit integers)
            data_type: Data type (INT16, UINT16, INT32, UINT32, FLOAT32, BOOL, AUTO)
            byte_order: Byte order (big, little)
            word_order: Word order for 32-bit types (high_low, low_high)

        Returns:
            Converted value or None on error
        """
        try:
            if data_type == "AUTO":
                # Auto-detect: default to UINT16 for single register, FLOAT32 for multiple
                if len(registers) == 1:
                    data_type = "UINT16"
                else:
                    data_type = "FLOAT32"

            if data_type == "BOOL":
                return bool(registers[0])

            elif data_type == "INT16":
                value = registers[0]
                if value >= 32768:
                    value -= 65536
                return value

            elif data_type == "UINT16":
                return registers[0]

            elif data_type in ["INT32", "UINT32", "FLOAT32"]:
                if len(registers) < 2:
                    logger.error(f"Not enough registers for {data_type}")
                    return None

                # Handle word order
                if word_order == "low_high":
                    registers = [registers[1], registers[0]]

                # Pack registers to bytes
                if byte_order == "big":
                    bytes_data = struct.pack(">HH", registers[0], registers[1])
                else:
                    bytes_data = struct.pack("<HH", registers[0], registers[1])

                # Unpack to correct type
                if data_type == "INT32":
                    if byte_order == "big":
                        return struct.unpack(">i", bytes_data)[0]
                    else:
                        return struct.unpack("<i", bytes_data)[0]

                elif data_type == "UINT32":
                    if byte_order == "big":
                        return struct.unpack(">I", bytes_data)[0]
                    else:
                        return struct.unpack("<I", bytes_data)[0]

                elif data_type == "FLOAT32":
                    if byte_order == "big":
                        return struct.unpack(">f", bytes_data)[0]
                    else:
                        return struct.unpack("<f", bytes_data)[0]

            else:
                logger.error(f"Unknown data type: {data_type}")
                return None

        except Exception as e:
            logger.error(f"Error converting registers to {data_type}: {e}")
            return None


class ModbusRTUDriver(ModbusDriverBase):
    """Modbus RTU (Serial) driver implementation."""

    def connect(self):
        """Establish serial connection."""
        try:
            self.client = ModbusSerialClient(
                port=self.interface.port,
                baudrate=self.interface.baudrate,
                parity=self.interface.parity,
                stopbits=self.interface.stopbits,
                bytesize=self.interface.bytesize,
                timeout=self.interface.timeout,
            )

            connected = self.client.connect()
            self._connected = connected

            if connected:
                logger.info(
                    f"Connected to RTU interface {self.interface.name} on {self.interface.port}"
                )
            else:
                logger.error(
                    f"Failed to connect to RTU interface {self.interface.name}"
                )

            return connected

        except Exception as e:
            logger.error(f"Exception connecting to RTU interface: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Close serial connection."""
        try:
            if self.client:
                self.client.close()
            self._connected = False
            logger.info(f"Disconnected from RTU interface {self.interface.name}")
        except Exception as e:
            logger.error(f"Exception disconnecting from RTU interface: {e}")


class ModbusTCPDriver(ModbusDriverBase):
    """Modbus TCP/IP driver implementation."""

    def connect(self):
        """Establish TCP connection."""
        try:
            self.client = ModbusTcpClient(
                host=self.interface.host,
                port=self.interface.tcp_port,
                timeout=self.interface.timeout,
            )

            connected = self.client.connect()
            self._connected = connected

            if connected:
                logger.info(
                    f"Connected to TCP interface {self.interface.name} at {self.interface.host}:{self.interface.tcp_port}"
                )
            else:
                logger.error(
                    f"Failed to connect to TCP interface {self.interface.name}"
                )

            return connected

        except Exception as e:
            logger.error(f"Exception connecting to TCP interface: {e}")
            self._connected = False
            return False

    def disconnect(self):
        """Close TCP connection."""
        try:
            if self.client:
                self.client.close()
            self._connected = False
            logger.info(f"Disconnected from TCP interface {self.interface.name}")
        except Exception as e:
            logger.error(f"Exception disconnecting from TCP interface: {e}")


def create_driver(interface):
    """
    Factory function to create appropriate driver for interface.

    Args:
        interface: ModbusInterface model instance

    Returns:
        ModbusRTUDriver or ModbusTCPDriver instance
    """
    if interface.protocol == "RTU":
        return ModbusRTUDriver(interface)
    elif interface.protocol == "TCP":
        return ModbusTCPDriver(interface)
    else:
        raise ValueError(f"Unknown protocol: {interface.protocol}")
