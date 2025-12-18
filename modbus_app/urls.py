"""
URL routing for modbus_app.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from modbus_app import views

# API Router
router = DefaultRouter()
router.register(r"interfaces", views.ModbusInterfaceViewSet, basename="interface")
router.register(r"devices", views.DeviceViewSet, basename="device")
router.register(r"registers", views.RegisterViewSet, basename="register")
router.register(r"trend-data", views.TrendDataViewSet, basename="trenddata")
router.register(r"dashboard-groups", views.DashboardGroupViewSet, basename="dashboardgroup")
router.register(r"dashboard-widgets", views.DashboardWidgetViewSet, basename="dashboardwidget")
router.register(r"alarms", views.AlarmViewSet, basename="alarm")
router.register(r"alarm-history", views.AlarmHistoryViewSet, basename="alarmhistory")
router.register(r"device-templates", views.DeviceTemplateViewSet, basename="devicetemplate")
router.register(
    r"calculated-registers",
    views.CalculatedRegisterViewSet,
    basename="calculatedregister",
)
router.register(r"audit-logs", views.AuditLogViewSet, basename="auditlog")

app_name = "modbus_app"

urlpatterns = [
    # Dashboard
    path("", views.dashboard_view, name="dashboard"),
    # Configuration views
    path("config/interfaces/", views.interface_list_view, name="interface_list"),
    path("config/interfaces/add/", views.interface_add_view, name="interface_add"),
    path(
        "config/interfaces/<int:pk>/edit/",
        views.interface_edit_view,
        name="interface_edit",
    ),
    path("config/devices/", views.device_list_view, name="device_list"),
    path("config/devices/add/", views.device_add_view, name="device_add"),
    path("config/devices/<int:pk>/edit/", views.device_edit_view, name="device_edit"),
    path("config/registers/", views.register_list_view, name="register_list"),
    path("config/registers/add/", views.register_add_view, name="register_add"),
    path(
        "config/registers/<int:pk>/edit/",
        views.register_edit_view,
        name="register_edit",
    ),
    path("config/dashboard-layout/", views.dashboard_layout_view, name="dashboard_layout"),
    path("config/alarms/", views.alarm_list_view, name="alarm_list"),
    path("config/templates/", views.template_list_view, name="template_list"),
    # API endpoints
    path("api/v1/", include(router.urls)),
]
