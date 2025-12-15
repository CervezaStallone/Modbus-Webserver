"""
Views voor de Modbus webapp.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.utils import timezone
from datetime import timedelta
from .models import (
    ModbusInterface, Device, Register, TrendData, TrendDataAggregated,
    DashboardGroup, DashboardWidget, Alarm, AlarmHistory,
    DeviceTemplate, CalculatedRegister, AuditLog
)
from .serializers import (
    ModbusInterfaceSerializer, ModbusInterfaceListSerializer,
    DeviceSerializer, DeviceListSerializer,
    RegisterSerializer, RegisterListSerializer,
    TrendDataSerializer, TrendDataAggregatedSerializer,
    DashboardGroupSerializer, DashboardWidgetSerializer,
    AlarmSerializer, AlarmHistorySerializer,
    DeviceTemplateSerializer, CalculatedRegisterSerializer,
    AuditLogSerializer
)
from .services.register_service import RegisterService


# Template views
@login_required
def dashboard_view(request):
    """Main dashboard view."""
    return render(request, 'dashboard/index.html', {
        'title': 'Dashboard'
    })


@login_required
def interface_list_view(request):
    """Interface configuration list view."""
    return render(request, 'config/interfaces.html')


@login_required
def device_list_view(request):
    """Device configuration list view."""
    return render(request, 'config/devices.html')


@login_required
def register_list_view(request):
    """Register configuration list view."""
    return render(request, 'config/registers.html')


# API ViewSets
class ModbusInterfaceViewSet(viewsets.ModelViewSet):
    """ViewSet voor Modbus interfaces."""
    queryset = ModbusInterface.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ModbusInterfaceListSerializer
        return ModbusInterfaceSerializer
    
    def get_permissions(self):
        """Admin only for write operations."""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'test_connection']:
            return [IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test verbinding met Modbus interface."""
        interface = self.get_object()
        register_service = RegisterService()
        
        try:
            driver = register_service.get_driver(interface)
            driver.connect()
            
            # Update status
            interface.update_status('online')
            
            return Response({
                'status': 'success',
                'message': f'Verbinding met {interface.name} succesvol getest'
            })
        except Exception as e:
            interface.update_status('error')
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        finally:
            if driver:
                driver.disconnect()
    
    @action(detail=True, methods=['get'])
    def devices(self, request, pk=None):
        """Haal alle devices op voor deze interface."""
        interface = self.get_object()
        devices = interface.devices.all()
        serializer = DeviceListSerializer(devices, many=True)
        return Response(serializer.data)


class DeviceViewSet(viewsets.ModelViewSet):
    """ViewSet voor Modbus devices."""
    queryset = Device.objects.select_related('interface').all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return DeviceListSerializer
        return DeviceSerializer
    
    def get_permissions(self):
        """Admin only for write operations."""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'poll_now', 'apply_template']:
            return [IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=True, methods=['post'])
    def poll_now(self, request, pk=None):
        """Voer handmatig een poll uit voor dit device."""
        device = self.get_object()
        
        # Importeer hier om circular import te voorkomen
        from .tasks import poll_device_registers
        
        # Voer poll taak asynchroon uit
        task = poll_device_registers.delay(device.id)
        
        return Response({
            'status': 'success',
            'message': f'Poll gestart voor {device.name}',
            'task_id': task.id
        })
    
    @action(detail=True, methods=['get'])
    def registers(self, request, pk=None):
        """Haal alle registers op voor dit device."""
        device = self.get_object()
        registers = device.registers.all()
        serializer = RegisterListSerializer(registers, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def apply_template(self, request, pk=None):
        """Pas device template toe op dit device."""
        device = self.get_object()
        template_id = request.data.get('template_id')
        
        if not template_id:
            return Response({
                'status': 'error',
                'message': 'template_id is verplicht'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            template = DeviceTemplate.objects.get(id=template_id)
            
            # Maak registers aan op basis van template
            created_count = 0
            for reg_def in template.register_definitions:
                Register.objects.create(
                    device=device,
                    name=reg_def['name'],
                    address=reg_def['address'],
                    function_code=reg_def['function_code'],
                    data_type=reg_def.get('data_type', 'UINT16'),
                    byte_order=reg_def.get('byte_order', 'big'),
                    word_order=reg_def.get('word_order', 'high_low'),
                    count=reg_def.get('count', 1),
                    conversion_factor=reg_def.get('conversion_factor', 1.0),
                    conversion_offset=reg_def.get('conversion_offset', 0.0),
                    unit=reg_def.get('unit', ''),
                    enabled=True,
                    writable=reg_def.get('writable', False)
                )
                created_count += 1
            
            return Response({
                'status': 'success',
                'message': f'{created_count} registers aangemaakt van template {template.name}'
            })
        except DeviceTemplate.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Template niet gevonden'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class RegisterViewSet(viewsets.ModelViewSet):
    """ViewSet voor Modbus registers."""
    queryset = Register.objects.select_related('device', 'device__interface').all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return RegisterListSerializer
        return RegisterSerializer
    
    def get_permissions(self):
        """Admin only for write operations."""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'write_value']:
            return [IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=True, methods=['post'])
    def read_now(self, request, pk=None):
        """Lees direct de waarde van dit register."""
        register = self.get_object()
        register_service = RegisterService()
        
        try:
            value = register_service.read_register(register)
            
            return Response({
                'status': 'success',
                'value': value,
                'unit': register.unit,
                'timestamp': timezone.now()
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def write_value(self, request, pk=None):
        """Schrijf waarde naar dit register."""
        register = self.get_object()
        
        if not register.is_writable():
            return Response({
                'status': 'error',
                'message': 'Dit register is niet schrijfbaar'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        value = request.data.get('value')
        if value is None:
            return Response({
                'status': 'error',
                'message': 'value is verplicht'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        register_service = RegisterService()
        
        try:
            # Converteer naar float
            value = float(value)
            
            # Schrijf waarde
            register_service.write_register(register, value)
            
            return Response({
                'status': 'success',
                'message': f'Waarde {value} geschreven naar {register.name}'
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def trend_data(self, request, pk=None):
        """Haal trend data op voor dit register."""
        register = self.get_object()
        
        # Parse query parameters
        hours = int(request.query_params.get('hours', 24))
        interval = request.query_params.get('interval', None)
        
        start_time = timezone.now() - timedelta(hours=hours)
        
        if interval:
            # Gebruik geaggregeerde data
            data = TrendDataAggregated.objects.filter(
                register=register,
                interval=interval,
                timestamp__gte=start_time
            ).order_by('timestamp')
            serializer = TrendDataAggregatedSerializer(data, many=True)
        else:
            # Gebruik raw data
            data = TrendData.objects.filter(
                register=register,
                timestamp__gte=start_time
            ).order_by('timestamp')
            serializer = TrendDataSerializer(data, many=True)
        
        return Response(serializer.data)


class TrendDataViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet voor TrendData (read-only)."""
    queryset = TrendData.objects.select_related('register', 'register__device').all()
    serializer_class = TrendDataSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter op register en tijd."""
        queryset = super().get_queryset()
        
        register_id = self.request.query_params.get('register_id')
        if register_id:
            queryset = queryset.filter(register_id=register_id)
        
        hours = int(self.request.query_params.get('hours', 24))
        start_time = timezone.now() - timedelta(hours=hours)
        queryset = queryset.filter(timestamp__gte=start_time)
        
        return queryset.order_by('-timestamp')


class DashboardGroupViewSet(viewsets.ModelViewSet):
    """ViewSet voor Dashboard groepen."""
    queryset = DashboardGroup.objects.prefetch_related('widgets').all()
    serializer_class = DashboardGroupSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Admin only for write operations."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def active_dashboard(self, request):
        """Haal complete dashboard configuratie op."""
        groups = self.get_queryset().order_by('row_order')
        serializer = self.get_serializer(groups, many=True)
        return Response(serializer.data)


class DashboardWidgetViewSet(viewsets.ModelViewSet):
    """ViewSet voor Dashboard widgets."""
    queryset = DashboardWidget.objects.select_related('group', 'register', 'calculated_register').all()
    serializer_class = DashboardWidgetSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Admin only for write operations."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()


class AlarmViewSet(viewsets.ModelViewSet):
    """ViewSet voor Alarms."""
    queryset = Alarm.objects.select_related('register').all()
    serializer_class = AlarmSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Admin only for write operations."""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'acknowledge', 'silence']:
            return [IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Haal alle actieve alarms op."""
        active_alarms = self.get_queryset().filter(enabled=True)
        active_history = AlarmHistory.objects.filter(
            alarm__in=active_alarms,
            cleared_at__isnull=True
        ).select_related('alarm', 'alarm__register')
        
        serializer = AlarmHistorySerializer(active_history, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """Bevestig een alarm."""
        alarm = self.get_object()
        
        # Vind meest recente actieve alarm history entry
        history_entry = AlarmHistory.objects.filter(
            alarm=alarm,
            cleared_at__isnull=True
        ).order_by('-triggered_at').first()
        
        if not history_entry:
            return Response({
                'status': 'error',
                'message': 'Geen actief alarm gevonden'
            }, status=status.HTTP_404_NOT_FOUND)
        
        history_entry.acknowledged = True
        history_entry.acknowledged_at = timezone.now()
        history_entry.acknowledged_by = request.user.username if request.user.is_authenticated else 'anonymous'
        history_entry.save()
        
        return Response({
            'status': 'success',
            'message': f'Alarm {alarm.name} bevestigd'
        })


class AlarmHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet voor Alarm history (read-only)."""
    queryset = AlarmHistory.objects.select_related('alarm', 'alarm__register').all()
    serializer_class = AlarmHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter op alarm en tijd."""
        queryset = super().get_queryset()
        
        alarm_id = self.request.query_params.get('alarm_id')
        if alarm_id:
            queryset = queryset.filter(alarm_id=alarm_id)
        
        days = int(self.request.query_params.get('days', 7))
        start_time = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(triggered_at__gte=start_time)
        
        return queryset.order_by('-triggered_at')


class DeviceTemplateViewSet(viewsets.ModelViewSet):
    """ViewSet voor Device templates."""
    queryset = DeviceTemplate.objects.all()
    serializer_class = DeviceTemplateSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Admin only for write operations."""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return super().get_permissions()


class CalculatedRegisterViewSet(viewsets.ModelViewSet):
    """ViewSet voor Calculated registers."""
    queryset = CalculatedRegister.objects.all()
    serializer_class = CalculatedRegisterSerializer
    permission_classes = [IsAuthenticated]
    
    def get_permissions(self):
        """Admin only for write operations."""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'calculate_now']:
            return [IsAdminUser()]
        return super().get_permissions()
    
    @action(detail=True, methods=['post'])
    def calculate_now(self, request, pk=None):
        """Bereken direct de waarde van dit calculated register."""
        calc_register = self.get_object()
        
        # Importeer hier om circular import te voorkomen
        from .tasks import update_calculated_registers
        
        # Voer berekening uit
        task = update_calculated_registers.delay(calc_register.id)
        
        return Response({
            'status': 'success',
            'message': f'Berekening gestart voor {calc_register.name}',
            'task_id': task.id
        })


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet voor Audit logs (read-only)."""
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsAdminUser]  # Only admins can view audit logs
    
    def get_queryset(self):
        """Filter op model naam en tijd."""
        queryset = super().get_queryset()
        
        model_name = self.request.query_params.get('model_name')
        if model_name:
            queryset = queryset.filter(model_name=model_name)
        
        days = int(self.request.query_params.get('days', 30))
        start_time = timezone.now() - timedelta(days=days)
        queryset = queryset.filter(timestamp__gte=start_time)
        
        return queryset.order_by('-timestamp')
