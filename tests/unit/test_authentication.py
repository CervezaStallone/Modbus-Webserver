"""
Tests for authentication and authorization.
"""
import pytest
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token


pytestmark = pytest.mark.django_db


class TestAuthenticationRequired:
    """Test that API endpoints require authentication."""
    
    def test_unauthenticated_interface_list_fails(self):
        """Test that unauthenticated requests to interface list are rejected."""
        client = APIClient()
        response = client.get('/api/v1/interfaces/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_unauthenticated_device_list_fails(self):
        """Test that unauthenticated requests to device list are rejected."""
        client = APIClient()
        response = client.get('/api/v1/devices/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_unauthenticated_register_list_fails(self):
        """Test that unauthenticated requests to register list are rejected."""
        client = APIClient()
        response = client.get('/api/v1/registers/')
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
    
    def test_unauthenticated_dashboard_view_redirects(self):
        """Test that unauthenticated requests to dashboard redirect to login."""
        client = APIClient()
        response = client.get('/')
        # Should redirect to login page
        assert response.status_code in [status.HTTP_302_FOUND, status.HTTP_401_UNAUTHORIZED]


class TestAuthenticatedAccess:
    """Test authenticated user access."""
    
    def test_authenticated_user_can_read(self):
        """Test that authenticated users can read API data."""
        # Create user and authenticate
        user = User.objects.create_user(username='testuser', password='testpass123')
        client = APIClient()
        client.force_authenticate(user=user)
        
        # Should be able to read data
        response = client.get('/api/v1/interfaces/')
        assert response.status_code == status.HTTP_200_OK
    
    def test_authenticated_user_cannot_write(self):
        """Test that regular authenticated users cannot write data."""
        # Create regular user
        user = User.objects.create_user(username='testuser', password='testpass123')
        client = APIClient()
        client.force_authenticate(user=user)
        
        # Try to create an interface
        response = client.post('/api/v1/interfaces/', {
            'name': 'Test Interface',
            'interface_type': 'RTU',
            'port': 'COM1',
            'baudrate': 9600,
            'enabled': True
        })
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]
    
    def test_token_authentication_works(self):
        """Test that token authentication works."""
        # Create user and token
        user = User.objects.create_user(username='testuser', password='testpass123')
        token = Token.objects.create(user=user)
        
        # Authenticate with token
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        
        # Should be able to access API
        response = client.get('/api/v1/interfaces/')
        assert response.status_code == status.HTTP_200_OK


class TestAdminAccess:
    """Test admin user access."""
    
    def test_admin_can_read(self):
        """Test that admin users can read API data."""
        # Create admin user
        admin = User.objects.create_superuser(
            username='admin', 
            password='admin123',
            email='admin@example.com'
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        
        # Should be able to read data
        response = client.get('/api/v1/interfaces/')
        assert response.status_code == status.HTTP_200_OK
    
    def test_admin_can_write(self):
        """Test that admin users can write data."""
        # Create admin user
        admin = User.objects.create_superuser(
            username='admin', 
            password='admin123',
            email='admin@example.com'
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        
        # Should be able to create interface
        response = client.post('/api/v1/interfaces/', {
            'name': 'Test Interface',
            'interface_type': 'RTU',
            'port': 'COM1',
            'baudrate': 9600,
            'parity': 'N',
            'stopbits': 1,
            'bytesize': 8,
            'enabled': True
        })
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_200_OK]
    
    def test_admin_can_delete(self):
        """Test that admin users can delete data."""
        from modbus_app.models import ModbusInterface
        
        # Create admin user and interface
        admin = User.objects.create_superuser(
            username='admin', 
            password='admin123',
            email='admin@example.com'
        )
        interface = ModbusInterface.objects.create(
            name='Test Interface',
            interface_type='RTU',
            port='COM1',
            baudrate=9600,
            enabled=True
        )
        
        client = APIClient()
        client.force_authenticate(user=admin)
        
        # Should be able to delete
        response = client.delete(f'/api/v1/interfaces/{interface.id}/')
        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_200_OK]


class TestPermissionEdgeCases:
    """Test edge cases in permission checking."""
    
    def test_audit_log_requires_admin(self):
        """Test that audit log access requires admin privileges."""
        # Create regular user
        user = User.objects.create_user(username='testuser', password='testpass123')
        client = APIClient()
        client.force_authenticate(user=user)
        
        # Should not be able to access audit logs
        response = client.get('/api/v1/audit-logs/')
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]
    
    def test_admin_can_access_audit_logs(self):
        """Test that admins can access audit logs."""
        # Create admin user
        admin = User.objects.create_superuser(
            username='admin', 
            password='admin123',
            email='admin@example.com'
        )
        client = APIClient()
        client.force_authenticate(user=admin)
        
        # Should be able to access audit logs
        response = client.get('/api/v1/audit-logs/')
        assert response.status_code == status.HTTP_200_OK
    
    def test_write_register_requires_admin(self):
        """Test that register write operations require admin."""
        from modbus_app.models import ModbusInterface, Device, Register
        
        # Create test data
        interface = ModbusInterface.objects.create(
            name='Test Interface',
            interface_type='RTU',
            port='COM1',
            baudrate=9600
        )
        device = Device.objects.create(
            name='Test Device',
            interface=interface,
            slave_id=1
        )
        register = Register.objects.create(
            name='Test Register',
            device=device,
            address=0,
            function_code=3,
            writable=True
        )
        
        # Create regular user
        user = User.objects.create_user(username='testuser', password='testpass123')
        client = APIClient()
        client.force_authenticate(user=user)
        
        # Should not be able to write
        response = client.post(
            f'/api/v1/registers/{register.id}/write_value/',
            {'value': 42}
        )
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]
