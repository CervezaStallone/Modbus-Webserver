"""
Django admin configuration for modbus_app models.
"""
from django.contrib import admin
from modbus_app.models import (
    ModbusInterface, Device, Register, TrendData, TrendDataAggregated,
    DashboardGroup, DashboardWidget, Alarm, AlarmHistory,
    DeviceTemplate, CalculatedRegister, AuditLog
)


@admin.register(ModbusInterface)
class ModbusInterfaceAdmin(admin.ModelAdmin):
    list_display = ['name', 'protocol', 'enabled', 'connection_status', 'last_seen']
    list_filter = ['protocol', 'enabled', 'connection_status']
    search_fields = ['name', 'host', 'port']
    readonly_fields = ['connection_status', 'last_seen', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'protocol', 'enabled')
        }),
        ('RTU Configuration', {
            'fields': ('port', 'baudrate', 'parity', 'stopbits', 'bytesize'),
            'classes': ('collapse',)
        }),
        ('TCP Configuration', {
            'fields': ('host', 'tcp_port'),
            'classes': ('collapse',)
        }),
        ('Connection Settings', {
            'fields': ('timeout', 'connection_status', 'last_seen')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ['name', 'interface', 'slave_id', 'enabled', 'connection_status', 'polling_interval', 'last_poll']
    list_filter = ['interface', 'enabled', 'connection_status']
    search_fields = ['name', 'description']
    readonly_fields = ['connection_status', 'last_poll', 'error_count', 'created_at', 'updated_at']


@admin.register(Register)
class RegisterAdmin(admin.ModelAdmin):
    list_display = ['name', 'device', 'address', 'function_code', 'data_type', 'unit', 'enabled']
    list_filter = ['device', 'function_code', 'data_type', 'enabled']
    search_fields = ['name', 'device__name']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('device', 'name', 'enabled')
        }),
        ('Modbus Configuration', {
            'fields': ('function_code', 'address', 'data_type', 'count', 'byte_order', 'word_order')
        }),
        ('Conversion', {
            'fields': ('conversion_factor', 'conversion_offset', 'unit')
        }),
        ('Permissions', {
            'fields': ('writable',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TrendData)
class TrendDataAdmin(admin.ModelAdmin):
    list_display = ['register', 'timestamp', 'converted_value', 'quality']
    list_filter = ['register', 'quality', 'timestamp']
    search_fields = ['register__name']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(TrendDataAggregated)
class TrendDataAggregatedAdmin(admin.ModelAdmin):
    list_display = ['register', 'interval', 'timestamp', 'min_value', 'max_value', 'avg_value', 'sample_count']
    list_filter = ['register', 'interval', 'timestamp']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(DashboardGroup)
class DashboardGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'row_order', 'collapsed']
    search_fields = ['name']
    ordering = ['row_order', 'name']


@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['title', 'group', 'register', 'widget_type', 'column_position', 'row_position']
    list_filter = ['group', 'widget_type']
    search_fields = ['title', 'register__name']
    
    fieldsets = (
        ('Basic Configuration', {
            'fields': ('group', 'register', 'title', 'widget_type')
        }),
        ('Layout', {
            'fields': ('column_position', 'row_position', 'width', 'height')
        }),
        ('Trend Configuration', {
            'fields': ('trend_enabled', 'sample_rate', 'aggregation_method', 'time_range', 
                      'chart_color', 'show_legend', 'y_axis_mode', 'y_axis_min', 'y_axis_max'),
            'classes': ('collapse',)
        }),
        ('Text Display Configuration', {
            'fields': ('decimal_places', 'show_unit', 'font_size'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Alarm)
class AlarmAdmin(admin.ModelAdmin):
    list_display = ['name', 'register', 'severity', 'enabled', 'condition', 'last_triggered']
    list_filter = ['severity', 'enabled', 'condition']
    search_fields = ['name', 'register__name', 'message']
    readonly_fields = ['last_triggered', 'created_at', 'updated_at']


@admin.register(AlarmHistory)
class AlarmHistoryAdmin(admin.ModelAdmin):
    list_display = ['alarm', 'triggered_at', 'trigger_value', 'cleared_at', 'acknowledged']
    list_filter = ['alarm', 'acknowledged', 'triggered_at']
    readonly_fields = ['triggered_at', 'cleared_at', 'trigger_value', 'acknowledged_at', 'acknowledged_by']
    date_hierarchy = 'triggered_at'


@admin.register(DeviceTemplate)
class DeviceTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'manufacturer', 'model', 'default_polling_interval']
    list_filter = ['manufacturer']
    search_fields = ['name', 'manufacturer', 'model']


@admin.register(CalculatedRegister)
class CalculatedRegisterAdmin(admin.ModelAdmin):
    list_display = ['name', 'device', 'last_value', 'unit', 'last_calculated']
    list_filter = ['device']
    search_fields = ['name', 'formula']
    readonly_fields = ['last_value', 'last_calculated', 'created_at', 'updated_at']
    filter_horizontal = ['source_registers']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'action', 'model_name', 'object_id', 'ip_address']
    list_filter = ['action', 'model_name', 'timestamp']
    readonly_fields = ['timestamp', 'action', 'model_name', 'object_id', 'changes', 'ip_address']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
