"""
Database models for Modbus Webserver application.
"""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class ModbusInterface(models.Model):
    """
    Modbus connection interface configuration (RTU or TCP).
    """

    PROTOCOL_CHOICES = [
        ("RTU", "Modbus RTU (Serial)"),
        ("TCP", "Modbus TCP/IP"),
    ]

    PARITY_CHOICES = [
        ("N", "None"),
        ("E", "Even"),
        ("O", "Odd"),
    ]

    STATUS_CHOICES = [
        ("online", "Online"),
        ("offline", "Offline"),
        ("error", "Error"),
    ]

    # Common fields
    name = models.CharField(max_length=100, unique=True)
    protocol = models.CharField(max_length=3, choices=PROTOCOL_CHOICES)
    enabled = models.BooleanField(default=True)
    connection_status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="offline"
    )
    last_seen = models.DateTimeField(null=True, blank=True)

    # RTU specific fields
    port = models.CharField(
        max_length=50, blank=True, help_text="Serial port (e.g., COM3, /dev/ttyUSB0)"
    )
    baudrate = models.IntegerField(
        null=True,
        blank=True,
        choices=[
            (9600, "9600"),
            (19200, "19200"),
            (38400, "38400"),
            (57600, "57600"),
            (115200, "115200"),
        ],
        default=9600,
    )
    parity = models.CharField(
        max_length=1, choices=PARITY_CHOICES, default="N", blank=True
    )
    stopbits = models.IntegerField(
        null=True, blank=True, choices=[(1, "1"), (2, "2")], default=1
    )
    bytesize = models.IntegerField(
        null=True, blank=True, choices=[(7, "7"), (8, "8")], default=8
    )

    # TCP specific fields
    host = models.CharField(
        max_length=100, blank=True, help_text="IP address or hostname"
    )
    tcp_port = models.IntegerField(
        null=True,
        blank=True,
        default=502,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
    )

    # Common connection settings
    timeout = models.FloatField(default=3.0, validators=[MinValueValidator(0.1)])

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Modbus Interface"
        verbose_name_plural = "Modbus Interfaces"

    def __str__(self):
        return f"{self.name} ({self.get_protocol_display()})"

    def clean(self):
        """Validate that required fields for protocol type are present."""
        from django.core.exceptions import ValidationError

        if self.protocol == "RTU":
            if not self.port:
                raise ValidationError({"port": "Port is required for RTU protocol"})
        elif self.protocol == "TCP":
            if not self.host:
                raise ValidationError({"host": "Host is required for TCP protocol"})

    def update_status(self, status, save=True):
        """Update connection status and last seen timestamp."""
        self.connection_status = status
        if status == "online":
            self.last_seen = timezone.now()
        if save:
            self.save(update_fields=["connection_status", "last_seen"])


class Device(models.Model):
    """
    Modbus device/slave configuration.
    """

    STATUS_CHOICES = [
        ("online", "Online"),
        ("offline", "Offline"),
        ("error", "Error"),
    ]

    name = models.CharField(max_length=100)
    interface = models.ForeignKey(
        ModbusInterface, on_delete=models.CASCADE, related_name="devices"
    )
    slave_id = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(247)]
    )
    enabled = models.BooleanField(default=True)
    polling_interval = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        help_text="Polling interval in seconds",
    )
    connection_status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="offline"
    )
    last_poll = models.DateTimeField(null=True, blank=True)
    error_count = models.IntegerField(default=0)
    description = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ["interface", "slave_id"]
        indexes = [
            models.Index(fields=["interface", "enabled"]),
            models.Index(fields=["connection_status"]),
        ]

    def __str__(self):
        return f"{self.name} (Slave {self.slave_id})"

    def update_status(self, status, save=True):
        """Update device status."""
        self.connection_status = status
        if status == "online":
            self.error_count = 0
            self.last_poll = timezone.now()
        elif status == "error":
            self.error_count += 1

        if save:
            self.save(update_fields=["connection_status", "last_poll", "error_count"])


class Register(models.Model):
    """
    Modbus register configuration.
    """

    FUNCTION_CODE_CHOICES = [
        (1, "FC01 - Read Coils"),
        (2, "FC02 - Read Discrete Inputs"),
        (3, "FC03 - Read Holding Registers"),
        (4, "FC04 - Read Input Registers"),
        (5, "FC05 - Write Single Coil"),
        (6, "FC06 - Write Single Register"),
        (15, "FC15 - Write Multiple Coils"),
        (16, "FC16 - Write Multiple Registers"),
    ]

    DATA_TYPE_CHOICES = [
        ("AUTO", "Auto Detect"),
        ("INT16", "16-bit Signed Integer"),
        ("UINT16", "16-bit Unsigned Integer"),
        ("INT32", "32-bit Signed Integer"),
        ("UINT32", "32-bit Unsigned Integer"),
        ("FLOAT32", "32-bit Float"),
        ("BOOL", "Boolean"),
    ]

    BYTE_ORDER_CHOICES = [
        ("big", "Big Endian"),
        ("little", "Little Endian"),
    ]

    WORD_ORDER_CHOICES = [
        ("high_low", "High Word First"),
        ("low_high", "Low Word First"),
    ]

    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="registers"
    )
    name = models.CharField(max_length=100)
    function_code = models.IntegerField(choices=FUNCTION_CODE_CHOICES)
    address = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(65535)]
    )
    data_type = models.CharField(
        max_length=10, choices=DATA_TYPE_CHOICES, default="UINT16"
    )
    byte_order = models.CharField(
        max_length=10, choices=BYTE_ORDER_CHOICES, default="big"
    )
    word_order = models.CharField(
        max_length=10, choices=WORD_ORDER_CHOICES, default="high_low"
    )
    count = models.IntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(4)]
    )

    # Conversion settings
    conversion_factor = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=1.0,
        help_text="Multiply raw value by this factor",
    )
    conversion_offset = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        default=0.0,
        help_text="Add this offset after multiplication",
    )
    unit = models.CharField(
        max_length=20,
        blank=True,
        help_text="Unit of measurement (°C, kW, A, V, Hz, %, etc.)",
    )

    # Settings
    enabled = models.BooleanField(default=True)
    writable = models.BooleanField(default=False)
    last_value = models.FloatField(null=True, blank=True, help_text="Last read value")
    last_read = models.DateTimeField(
        null=True, blank=True, help_text="Last successful read"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["device", "address"]
        unique_together = ["device", "address", "function_code"]
        indexes = [
            models.Index(fields=["device", "enabled"]),
            models.Index(fields=["function_code"]),
        ]

    def __str__(self):
        return f"{self.device.name} - {self.name} @ {self.address}"

    def convert_value(self, raw_value):
        """Apply conversion formula to raw value."""
        return float(raw_value) * float(self.conversion_factor) + float(
            self.conversion_offset
        )

    @property
    def is_writable(self):
        """Check if register is writable based on function code."""
        return self.function_code in [5, 6, 15, 16] and self.writable


class TrendData(models.Model):
    """
    Time-series data storage for register values.
    """

    QUALITY_CHOICES = [
        ("good", "Good"),
        ("bad", "Bad"),
        ("uncertain", "Uncertain"),
    ]

    register = models.ForeignKey(
        Register, on_delete=models.CASCADE, related_name="trend_data"
    )
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    raw_value = models.FloatField()
    converted_value = models.FloatField()
    quality = models.CharField(max_length=10, choices=QUALITY_CHOICES, default="good")

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["register", "-timestamp"]),
            models.Index(fields=["timestamp"]),
            models.Index(fields=["register", "quality", "-timestamp"]),
        ]
        verbose_name_plural = "Trend Data"

    def __str__(self):
        return f"{self.register.name} @ {self.timestamp}: {self.converted_value}"

    @property
    def value(self):
        """Alias for converted_value for backwards compatibility."""
        return self.converted_value


class TrendDataAggregated(models.Model):
    """
    Pre-calculated aggregates for performance.
    """

    INTERVAL_CHOICES = [
        ("hourly", "Hourly"),
        ("daily", "Daily"),
        ("weekly", "Weekly"),
    ]

    register = models.ForeignKey(
        Register, on_delete=models.CASCADE, related_name="aggregated_data"
    )
    timestamp = models.DateTimeField(db_index=True)
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES)
    min_value = models.FloatField()
    max_value = models.FloatField()
    avg_value = models.FloatField()
    sample_count = models.IntegerField()

    class Meta:
        ordering = ["-timestamp"]
        unique_together = ["register", "interval", "timestamp"]
        indexes = [
            models.Index(fields=["register", "interval", "-timestamp"]),
        ]
        verbose_name_plural = "Trend Data Aggregated"

    def __str__(self):
        return f"{self.register.name} {self.interval} @ {self.timestamp}"


class DashboardGroup(models.Model):
    """
    Dashboard grouping for organizing widgets.
    """

    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    row_order = models.IntegerField(default=0)
    collapsed = models.BooleanField(default=False)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["row_order", "name"]

    def __str__(self):
        return self.name


class DashboardWidget(models.Model):
    """
    Dashboard widget configuration.
    """

    WIDGET_TYPE_CHOICES = [
        ("line_chart", "Line Chart"),
        ("bar_chart", "Bar Chart"),
        ("gauge", "Gauge"),
        ("text", "Text Display"),
        ("status", "Status Indicator"),
    ]

    AGGREGATION_CHOICES = [
        ("none", "None (Raw Data)"),
        ("mean", "Mean/Average"),
        ("max", "Maximum"),
        ("min", "Minimum"),
    ]

    Y_AXIS_MODE_CHOICES = [
        ("auto", "Auto Scale"),
        ("static", "Static Range"),
    ]

    group = models.ForeignKey(
        DashboardGroup, on_delete=models.CASCADE, related_name="widgets"
    )
    register = models.ForeignKey(
        Register, on_delete=models.CASCADE, related_name="widgets"
    )

    # Widget settings
    widget_type = models.CharField(
        max_length=20, choices=WIDGET_TYPE_CHOICES, default="line_chart"
    )
    title = models.CharField(max_length=100)
    column_position = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(11)],
        help_text="Column position (0-11 for Bootstrap grid)",
    )
    row_position = models.IntegerField(default=0)
    width = models.IntegerField(
        default=6,
        validators=[MinValueValidator(1), MaxValueValidator(12)],
        help_text="Width in Bootstrap columns (1-12)",
    )
    height = models.IntegerField(default=300, help_text="Height in pixels")

    # Trend configuration
    trend_enabled = models.BooleanField(default=True)
    sample_rate = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        help_text="Sample interval in seconds",
    )
    aggregation_method = models.CharField(
        max_length=10, choices=AGGREGATION_CHOICES, default="none"
    )
    time_range = models.IntegerField(
        default=60,
        validators=[MinValueValidator(1)],
        help_text="Time window in minutes",
    )
    chart_color = models.CharField(
        max_length=7, default="#007bff", help_text="Hex color code"
    )
    show_legend = models.BooleanField(default=True)
    y_axis_mode = models.CharField(
        max_length=10, choices=Y_AXIS_MODE_CHOICES, default="auto"
    )
    y_axis_min = models.FloatField(null=True, blank=True)
    y_axis_max = models.FloatField(null=True, blank=True)

    # Text display configuration
    decimal_places = models.IntegerField(
        default=2, validators=[MinValueValidator(0), MaxValueValidator(6)]
    )
    show_unit = models.BooleanField(default=True)
    font_size = models.IntegerField(
        default=24, validators=[MinValueValidator(8), MaxValueValidator(72)]
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["group", "row_position", "column_position"]
        indexes = [
            models.Index(fields=["group", "row_position"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.group.name})"


class Alarm(models.Model):
    """
    Alarm configuration for register monitoring.
    """

    CONDITION_CHOICES = [
        ("greater_than", "Greater Than"),
        ("less_than", "Less Than"),
        ("equals", "Equals"),
        ("not_equals", "Not Equals"),
        ("range", "Out of Range"),
    ]

    SEVERITY_CHOICES = [
        ("info", "Info"),
        ("warning", "Warning"),
        ("critical", "Critical"),
    ]

    register = models.ForeignKey(
        Register, on_delete=models.CASCADE, related_name="alarms"
    )
    name = models.CharField(max_length=100)
    enabled = models.BooleanField(default=True)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES)
    threshold_high = models.FloatField()
    threshold_low = models.FloatField(null=True, blank=True)
    hysteresis = models.FloatField(
        default=0.0, help_text="Hysteresis to prevent alarm flapping"
    )
    severity = models.CharField(
        max_length=10, choices=SEVERITY_CHOICES, default="warning"
    )
    message = models.TextField(help_text="Alarm message/description")
    last_triggered = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-severity", "register"]
        indexes = [
            models.Index(fields=["register", "enabled"]),
            models.Index(fields=["last_triggered"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.register.name}"

    def check_condition(self, value):
        """Check if alarm condition is met."""
        if self.condition == "greater_than":
            return value > self.threshold_high
        elif self.condition == "less_than":
            return value < self.threshold_high
        elif self.condition == "equals":
            return abs(value - self.threshold_high) < 0.001
        elif self.condition == "not_equals":
            return abs(value - self.threshold_high) >= 0.001
        elif self.condition == "range":
            return value < self.threshold_low or value > self.threshold_high
        return False

    def is_active(self):
        """Check if alarm is currently active (has uncleared history entry)."""
        return self.history.filter(cleared_at__isnull=True).exists()


class AlarmHistory(models.Model):
    """
    Historical log of alarm events.
    """

    alarm = models.ForeignKey(Alarm, on_delete=models.CASCADE, related_name="history")
    triggered_at = models.DateTimeField(default=timezone.now, db_index=True)
    cleared_at = models.DateTimeField(null=True, blank=True)
    trigger_value = models.FloatField()
    acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-triggered_at"]
        indexes = [
            models.Index(fields=["alarm", "-triggered_at"]),
            models.Index(fields=["cleared_at"]),
        ]
        verbose_name_plural = "Alarm History"

    def __str__(self):
        status = "Active" if self.cleared_at is None else "Cleared"
        return f"{self.alarm.name} - {status} @ {self.triggered_at}"


class DeviceTemplate(models.Model):
    """
    Pre-configured device templates for common devices.
    """

    name = models.CharField(max_length=100, unique=True)
    manufacturer = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    default_polling_interval = models.IntegerField(default=5)
    register_definitions = models.JSONField(
        help_text="JSON array with register configurations", default=list
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["manufacturer", "model"]

    def __str__(self):
        return f"{self.manufacturer} {self.model}"


class CalculatedRegister(models.Model):
    """
    Virtual registers calculated from other registers.
    """

    device = models.ForeignKey(
        Device, on_delete=models.CASCADE, related_name="calculated_registers"
    )
    name = models.CharField(max_length=100)
    formula = models.TextField(
        help_text="Python expression (e.g., 'register_1 + register_2 * 1.5')"
    )
    source_registers = models.ManyToManyField(Register, related_name="calculated_by")
    unit = models.CharField(max_length=20, blank=True)
    update_interval = models.IntegerField(
        default=5, help_text="Recalculate every X seconds"
    )
    last_value = models.FloatField(null=True, blank=True)
    last_calculated = models.DateTimeField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["device", "name"]

    def __str__(self):
        return f"{self.device.name} - {self.name} (Calculated)"


class AuditLog(models.Model):
    """
    Audit trail for configuration changes.
    """

    ACTION_CHOICES = [
        ("created", "Created"),
        ("updated", "Updated"),
        ("deleted", "Deleted"),
    ]

    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.IntegerField()
    changes = models.JSONField(help_text="Dictionary of changes", default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp"]),
            models.Index(fields=["model_name", "object_id"]),
        ]

    def __str__(self):
        return f"{self.action} {self.model_name} #{self.object_id} @ {self.timestamp}"
