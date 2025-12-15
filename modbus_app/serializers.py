"""
DRF Serializers voor alle Modbus models.
"""
from rest_framework import serializers
from django.utils import timezone
from .models import (
    ModbusInterface, Device, Register, TrendData, TrendDataAggregated,
    DashboardGroup, DashboardWidget, Alarm, AlarmHistory,
    DeviceTemplate, CalculatedRegister, AuditLog
)


class ModbusInterfaceSerializer(serializers.ModelSerializer):
    """Serializer voor ModbusInterface met validatie."""
    
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    protocol_display = serializers.CharField(source='get_protocol_display', read_only=True)
    
    class Meta:
        model = ModbusInterface
        fields = [
            'id', 'name', 'protocol', 'protocol_display',
            'port', 'baudrate', 'parity', 'stopbits', 'bytesize',
            'host', 'tcp_port', 'timeout',
            'connection_status', 'status_display', 'last_seen',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['connection_status', 'last_seen', 'created_at', 'updated_at']
    
    def validate(self, data):
        """Valideer protocol-specifieke velden."""
        protocol = data.get('protocol')
        
        if protocol == 'RTU':
            if not data.get('port'):
                raise serializers.ValidationError("Port is verplicht voor RTU protocol")
        elif protocol == 'TCP':
            if not data.get('host'):
                raise serializers.ValidationError("TCP host is verplicht voor TCP protocol")
            if not data.get('tcp_port'):
                raise serializers.ValidationError("TCP port is verplicht voor TCP protocol")
        
        return data


class DeviceSerializer(serializers.ModelSerializer):
    """Serializer voor Device."""
    
    interface_name = serializers.CharField(source='interface.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    register_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Device
        fields = [
            'id', 'name', 'interface', 'interface_name', 'slave_id',
            'description', 'enabled', 'polling_interval',
            'connection_status', 'status_display', 'last_poll', 'error_count',
            'register_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['connection_status', 'last_poll', 'error_count', 'created_at', 'updated_at']
    
    def get_register_count(self, obj):
        """Tel aantal registers van dit device."""
        return obj.registers.filter(enabled=True).count()


class RegisterSerializer(serializers.ModelSerializer):
    """Serializer voor Register."""
    
    device_name = serializers.CharField(source='device.name', read_only=True)
    function_code_display = serializers.SerializerMethodField()
    current_value = serializers.SerializerMethodField()
    
    class Meta:
        model = Register
        fields = [
            'id', 'device', 'device_name', 'name', 'address',
            'function_code', 'function_code_display', 'data_type',
            'byte_order', 'word_order', 'count',
            'conversion_factor', 'conversion_offset', 'unit',
            'enabled', 'writable',
            'current_value', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_function_code_display(self, obj):
        """Geef beschrijving van function code."""
        fc_map = {
            1: 'Read Coils',
            2: 'Read Discrete Inputs',
            3: 'Read Holding Registers',
            4: 'Read Input Registers',
            5: 'Write Single Coil',
            6: 'Write Single Register',
            15: 'Write Multiple Coils',
            16: 'Write Multiple Registers'
        }
        return fc_map.get(obj.function_code, f'FC{obj.function_code}')
    
    def get_current_value(self, obj):
        """Haal laatste waarde op uit TrendData."""
        latest = TrendData.objects.filter(register=obj).order_by('-timestamp').first()
        if latest:
            return {
                'value': latest.converted_value,
                'timestamp': latest.timestamp,
                'quality': latest.quality
            }
        return None


class TrendDataSerializer(serializers.ModelSerializer):
    """Serializer voor TrendData."""
    
    register_name = serializers.CharField(source='register.name', read_only=True)
    device_name = serializers.CharField(source='register.device.name', read_only=True)
    
    class Meta:
        model = TrendData
        fields = [
            'id', 'register', 'register_name', 'device_name',
            'timestamp', 'raw_value', 'converted_value', 'quality'
        ]
        read_only_fields = ['id', 'timestamp']


class TrendDataAggregatedSerializer(serializers.ModelSerializer):
    """Serializer voor TrendDataAggregated."""
    
    register_name = serializers.CharField(source='register.name', read_only=True)
    interval_display = serializers.CharField(source='get_interval_display', read_only=True)
    
    class Meta:
        model = TrendDataAggregated
        fields = [
            'id', 'register', 'register_name', 'interval', 'interval_display',
            'timestamp', 'min_value', 'max_value', 'avg_value', 'sample_count'
        ]
        read_only_fields = ['id', 'timestamp']


class DashboardWidgetSerializer(serializers.ModelSerializer):
    """Serializer voor DashboardWidget."""
    
    register_name = serializers.CharField(source='register.name', read_only=True)
    widget_type_display = serializers.CharField(source='get_widget_type_display', read_only=True)
    
    class Meta:
        model = DashboardWidget
        fields = [
            'id', 'group', 'register', 'register_name',
            'widget_type', 'widget_type_display', 'title',
            'column_position', 'row_position', 'width', 'height',
            'trend_enabled', 'sample_rate', 'aggregation_method', 'time_range',
            'chart_color', 'show_legend', 'y_axis_mode', 'y_axis_min', 'y_axis_max',
            'decimal_places', 'show_unit', 'font_size',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class DashboardGroupSerializer(serializers.ModelSerializer):
    """Serializer voor DashboardGroup met widgets."""
    
    widgets = DashboardWidgetSerializer(many=True, read_only=True)
    widget_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DashboardGroup
        fields = [
            'id', 'name', 'description', 'order', 'collapsed',
            'widget_count', 'widgets',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_widget_count(self, obj):
        """Tel aantal widgets in deze groep."""
        return obj.widgets.count()


class AlarmSerializer(serializers.ModelSerializer):
    """Serializer voor Alarm."""
    
    register_name = serializers.CharField(source='register.name', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    is_active_status = serializers.BooleanField(source='is_active', read_only=True)
    
    class Meta:
        model = Alarm
        fields = [
            'id', 'register', 'register_name', 'name', 'condition',
            'threshold_high', 'threshold_low', 'hysteresis', 'severity', 'severity_display',
            'message', 'enabled', 'is_active_status',
            'last_triggered', 'created_at', 'updated_at'
        ]
        read_only_fields = ['is_active_status', 'last_triggered', 'created_at', 'updated_at']


class AlarmHistorySerializer(serializers.ModelSerializer):
    """Serializer voor AlarmHistory."""
    
    alarm_name = serializers.CharField(source='alarm.name', read_only=True)
    severity_display = serializers.CharField(source='alarm.get_severity_display', read_only=True)
    
    class Meta:
        model = AlarmHistory
        fields = [
            'id', 'alarm', 'alarm_name', 'severity_display',
            'triggered_at', 'cleared_at', 'trigger_value',
            'acknowledged', 'acknowledged_at', 'acknowledged_by'
        ]
        read_only_fields = ['id', 'triggered_at']


class DeviceTemplateSerializer(serializers.ModelSerializer):
    """Serializer voor DeviceTemplate."""
    
    register_count = serializers.SerializerMethodField()
    
    class Meta:
        model = DeviceTemplate
        fields = [
            'id', 'name', 'manufacturer', 'model', 'description',
            'register_definitions', 'register_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_register_count(self, obj):
        """Tel registers in template."""
        return len(obj.register_definitions) if obj.register_definitions else 0


class CalculatedRegisterSerializer(serializers.ModelSerializer):
    """Serializer voor CalculatedRegister."""
    
    device_name = serializers.CharField(source='device.name', read_only=True)
    
    class Meta:
        model = CalculatedRegister
        fields = [
            'id', 'device', 'device_name', 'name', 'formula', 'unit',
            'update_interval', 'last_value', 'last_calculated',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['last_value', 'last_calculated', 'created_at', 'updated_at']


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer voor AuditLog."""
    
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    
    class Meta:
        model = AuditLog
        fields = [
            'id', 'timestamp', 'action', 'action_display',
            'model_name', 'object_id', 'changes', 'ip_address'
        ]
        read_only_fields = ['id', 'timestamp']


# Simplified serializers voor list views
class ModbusInterfaceListSerializer(serializers.ModelSerializer):
    """Vereenvoudigde serializer voor interface lijst."""
    status_display = serializers.CharField(source='get_connection_status_display', read_only=True)
    device_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ModbusInterface
        fields = ['id', 'name', 'protocol', 'connection_status', 'status_display', 'device_count']
    
    def get_device_count(self, obj):
        return obj.devices.count()


class DeviceListSerializer(serializers.ModelSerializer):
    """Vereenvoudigde serializer voor device lijst."""
    interface_name = serializers.CharField(source='interface.name', read_only=True)
    status_display = serializers.CharField(source='get_connection_status_display', read_only=True)
    
    class Meta:
        model = Device
        fields = ['id', 'name', 'interface_name', 'slave_id', 'enabled', 'connection_status', 'status_display']


class RegisterListSerializer(serializers.ModelSerializer):
    """Vereenvoudigde serializer voor register lijst."""
    device_name = serializers.CharField(source='device.name', read_only=True)
    
    class Meta:
        model = Register
        fields = ['id', 'name', 'device_name', 'address', 'function_code', 'enabled', 'writable']
