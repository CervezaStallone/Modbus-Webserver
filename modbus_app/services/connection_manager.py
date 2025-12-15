"""
Connection Manager voor Modbus interfaces.
Beheert connection pooling, health checks en automatic recovery.
"""
import logging
from typing import Dict, Optional
from datetime import datetime, timedelta
from django.utils import timezone
from ..models import ModbusInterface
from .modbus_driver import ModbusRTUDriver, ModbusTCPDriver

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Beheer Modbus connecties met pooling en health checking.
    """
    
    def __init__(self):
        self._connections: Dict[int, object] = {}
        self._last_health_check: Dict[int, datetime] = {}
        self._connection_stats: Dict[int, dict] = {}
    
    def get_connection(self, interface: ModbusInterface):
        """
        Haal of creëer een connection voor de gegeven interface.
        
        Args:
            interface: ModbusInterface object
            
        Returns:
            Driver instance (ModbusRTUDriver of ModbusTCPDriver)
            
        Raises:
            Exception: Als connectie niet gemaakt kan worden
        """
        # Check of interface enabled is
        if not interface.enabled:
            raise Exception(f"Interface {interface.name} is niet enabled")
        
        # Check of we al een connectie hebben
        if interface.id in self._connections:
            driver = self._connections[interface.id]
            
            # Test of connectie nog werkt
            if self._test_connection(driver):
                return driver
            else:
                # Connectie werkt niet meer, verwijder
                logger.warning(f"Connection voor {interface.name} werkt niet meer, reconnecting...")
                self._close_connection(interface.id)
        
        # Maak nieuwe connectie
        return self._create_connection(interface)
    
    def _create_connection(self, interface: ModbusInterface):
        """Creëer nieuwe driver instance."""
        try:
            if interface.protocol == 'RTU':
                driver = ModbusRTUDriver(
                    port=interface.port,
                    baudrate=interface.baudrate or 9600,
                    parity=interface.parity or 'N',
                    stopbits=interface.stopbits or 1,
                    bytesize=interface.bytesize or 8,
                    timeout=interface.timeout
                )
            elif interface.protocol == 'TCP':
                driver = ModbusTCPDriver(
                    host=interface.host,
                    tcp_port=interface.tcp_port or 502,
                    timeout=interface.timeout
                )
            else:
                raise ValueError(f"Onbekend protocol: {interface.protocol}")
            
            # Connecteer
            driver.connect()
            
            # Opslaan in pool
            self._connections[interface.id] = driver
            
            # Initialiseer stats
            if interface.id not in self._connection_stats:
                self._connection_stats[interface.id] = {
                    'success_count': 0,
                    'error_count': 0,
                    'last_success': None,
                    'last_error': None,
                    'total_response_time': 0.0
                }
            
            logger.info(f"Connection gemaakt voor {interface.name}")
            return driver
            
        except Exception as e:
            logger.error(f"Fout bij maken connectie voor {interface.name}: {e}")
            interface.update_status('error')
            raise
    
    def _close_connection(self, interface_id: int):
        """Sluit en verwijder een connectie uit de pool."""
        if interface_id in self._connections:
            try:
                driver = self._connections[interface_id]
                driver.disconnect()
            except Exception as e:
                logger.error(f"Fout bij sluiten connectie {interface_id}: {e}")
            finally:
                del self._connections[interface_id]
    
    def _test_connection(self, driver) -> bool:
        """
        Test of een connectie nog werkt.
        
        Args:
            driver: Driver instance om te testen
            
        Returns:
            True als connectie werkt, False anders
        """
        try:
            # Voor TCP kunnen we de connectie status checken
            if hasattr(driver, 'client') and hasattr(driver.client, 'is_socket_open'):
                return driver.client.is_socket_open()
            
            # Voor RTU is het lastiger, we gaan ervan uit dat het werkt
            # tenzij een read operation faalt
            return True
            
        except Exception:
            return False
    
    def health_check(self, interface: ModbusInterface) -> bool:
        """
        Voer health check uit op interface.
        
        Args:
            interface: ModbusInterface om te checken
            
        Returns:
            True als interface bereikbaar is, False anders
        """
        try:
            driver = self.get_connection(interface)
            
            # Probeer een simpele test read (address 0, 1 register)
            # Dit is low-impact maar test wel de connectie
            result = driver.read_holding_registers(
                address=0,
                count=1,
                slave=1  # Test met slave 1
            )
            
            # Als we hier komen zonder exception is de interface bereikbaar
            interface.update_status('online')
            self._record_success(interface.id)
            
            logger.info(f"Health check OK voor {interface.name}")
            return True
            
        except Exception as e:
            logger.warning(f"Health check failed voor {interface.name}: {e}")
            interface.update_status('error')
            self._record_error(interface.id)
            
            # Sluit de connectie bij error
            self._close_connection(interface.id)
            
            return False
    
    def _record_success(self, interface_id: int):
        """Registreer succesvolle operatie voor statistics."""
        if interface_id in self._connection_stats:
            stats = self._connection_stats[interface_id]
            stats['success_count'] += 1
            stats['last_success'] = timezone.now()
    
    def _record_error(self, interface_id: int):
        """Registreer error voor statistics."""
        if interface_id in self._connection_stats:
            stats = self._connection_stats[interface_id]
            stats['error_count'] += 1
            stats['last_error'] = timezone.now()
    
    def get_statistics(self, interface_id: int) -> dict:
        """
        Haal statistieken op voor een interface.
        
        Args:
            interface_id: ID van interface
            
        Returns:
            Dict met statistieken
        """
        if interface_id in self._connection_stats:
            stats = self._connection_stats[interface_id]
            
            # Bereken success rate
            total = stats['success_count'] + stats['error_count']
            success_rate = (stats['success_count'] / total * 100) if total > 0 else 0
            
            return {
                'success_count': stats['success_count'],
                'error_count': stats['error_count'],
                'success_rate': round(success_rate, 2),
                'last_success': stats['last_success'],
                'last_error': stats['last_error'],
                'is_connected': interface_id in self._connections
            }
        
        return {
            'success_count': 0,
            'error_count': 0,
            'success_rate': 0,
            'last_success': None,
            'last_error': None,
            'is_connected': False
        }
    
    def close_all(self):
        """Sluit alle connecties."""
        interface_ids = list(self._connections.keys())
        for interface_id in interface_ids:
            self._close_connection(interface_id)
        
        logger.info("Alle connecties gesloten")
    
    def reconnect(self, interface_id: int) -> bool:
        """
        Force reconnect voor een interface.
        
        Args:
            interface_id: ID van interface
            
        Returns:
            True als reconnect succesvol, False anders
        """
        # Sluit huidige connectie
        self._close_connection(interface_id)
        
        # Probeer opnieuw te connecteren
        try:
            interface = ModbusInterface.objects.get(id=interface_id)
            self._create_connection(interface)
            return True
        except Exception as e:
            logger.error(f"Reconnect failed voor interface {interface_id}: {e}")
            return False


# Global connection manager instance
_connection_manager = None


def get_connection_manager() -> ConnectionManager:
    """
    Haal de globale ConnectionManager instance op (singleton).
    
    Returns:
        ConnectionManager instance
    """
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager
