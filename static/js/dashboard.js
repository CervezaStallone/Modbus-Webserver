/**
 * Dashboard main JavaScript
 */

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initialized');
    
    // WebSocket connection will be initialized in the template
    // This file contains helper functions for dashboard functionality
});

/**
 * Update register value display
 */
function updateRegisterValue(registerId, value, unit) {
    const element = document.querySelector(`[data-register-id="${registerId}"]`);
    if (element) {
        element.textContent = formatValue(value, unit);
    }
}

/**
 * Format value with unit
 */
function formatValue(value, unit, decimals = 2) {
    const formatted = typeof value === 'number' ? value.toFixed(decimals) : value;
    return unit ? `${formatted} ${unit}` : formatted;
}

/**
 * Update device status indicator
 */
function updateDeviceStatus(deviceId, status) {
    const element = document.querySelector(`[data-device-id="${deviceId}"] .status-indicator`);
    if (element) {
        element.className = `status-indicator ${status}`;
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    // Simple notification system
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.style.position = 'fixed';
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

/**
 * Handle alarm notification
 */
function handleAlarm(alarmData) {
    const severityClass = {
        'info': 'info',
        'warning': 'warning',
        'critical': 'danger'
    }[alarmData.severity] || 'warning';
    
    showNotification(
        `<strong>Alarm: ${alarmData.register_name}</strong><br>${alarmData.message}`,
        severityClass
    );
}
