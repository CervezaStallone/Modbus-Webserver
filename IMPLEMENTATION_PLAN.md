# Modbus Webserver - Volledig Implementatieplan
**Project**: Django-based Modbus RTU/TCP Monitoring & Dashboard  
**Datum**: 15 december 2025  
**Status**: In ontwikkeling

---

## 1. ARCHITECTUUR OVERZICHT

### Tech Stack
- **Backend**: Django 5.0, Django REST Framework, Django Channels
- **Database**: SQLite met performance optimalisaties
- **Task Queue**: Celery + Redis
- **WebSockets**: Django Channels + Redis Channel Layer
- **Frontend**: Bootstrap 5 (offline), Chart.js, vanilla JavaScript
- **Modbus**: pymodbus (RTU + TCP support)
- **Testing**: pytest, pytest-django, Factory Boy
- **Deployment**: Docker, Docker Compose, Nginx, Gunicorn

### Systeem Componenten
1. **Web Interface**: Dashboard met configuratie UI
2. **Modbus Service**: RTU/TCP communicatie met apparaten
3. **Data Polling**: Celery background tasks voor register polling
4. **Data Storage**: Time-series data met aggregatie
5. **Real-time Updates**: WebSocket streaming naar dashboard
6. **API Layer**: RESTful endpoints voor externe integratie

---

## 2. DATABASE MODELS

### 2.1 ModbusInterface (Verbinding configuratie)
**Velden**:
- `name`: CharField - Naam van interface
- `protocol`: CharField - Keuze: RTU, TCP
- `enabled`: BooleanField - Interface actief/inactief
- `connection_status`: CharField - online/offline/error
- `last_seen`: DateTimeField - Laatste succesvolle connectie

**RTU Specifiek**:
- `port`: CharField - Serial port (COM1, /dev/ttyUSB0)
- `baudrate`: IntegerField - 9600, 19200, 38400, 57600, 115200
- `parity`: CharField - None, Even, Odd
- `stopbits`: IntegerField - 1, 2
- `bytesize`: IntegerField - 7, 8
- `timeout`: FloatField - Response timeout in seconden

**TCP Specifiek**:
- `host`: CharField - IP adres
- `port`: IntegerField - TCP poort (standaard 502)
- `timeout`: FloatField - Connection timeout

**Metadata**:
- `created_at`, `updated_at`: DateTimeField

### 2.2 Device (Modbus apparaat)
**Velden**:
- `name`: CharField - Naam van apparaat
- `interface`: ForeignKey(ModbusInterface) - Gekoppelde interface
- `slave_id`: IntegerField - Modbus slave address (1-247)
- `enabled`: BooleanField - Apparaat polling aan/uit
- `polling_interval`: IntegerField - Polling frequentie in seconden
- `connection_status`: CharField - online/offline/error
- `last_poll`: DateTimeField - Laatste poll timestamp
- `error_count`: IntegerField - Aantal opeenvolgende fouten
- `description`: TextField - Optionele beschrijving
- `created_at`, `updated_at`: DateTimeField

### 2.3 Register (Modbus register configuratie)
**Velden**:
- `device`: ForeignKey(Device) - Gekoppeld apparaat
- `name`: CharField - Register naam (bijv. "Temperatuur Ketel")
- `function_code`: IntegerField - 1, 2, 3, 4, 5, 6, 15, 16
- `address`: IntegerField - Register adres (0-65535)
- `data_type`: CharField - INT16, UINT16, INT32, UINT32, FLOAT32, BOOL
- `byte_order`: CharField - big_endian, little_endian (voor multi-register)
- `word_order`: CharField - high_low, low_high (voor 32-bit types)
- `count`: IntegerField - Aantal registers (1 voor 16-bit, 2 voor 32-bit)
- `conversion_factor`: DecimalField - Conversie (bijv. 0.1 voor delen door 10)
- `conversion_offset`: DecimalField - Offset voor conversie
- `unit`: CharField - Eenheid (°C, °F, kW, W, V, A, Hz, %, bool, etc.)
- `enabled`: BooleanField - Register polling aan/uit
- `writable`: BooleanField - Register is schrijfbaar
- `created_at`, `updated_at`: DateTimeField

**Conversie formule**: `(raw_value * conversion_factor) + conversion_offset`

### 2.4 TrendData (Time-series data opslag)
**Velden**:
- `register`: ForeignKey(Register) - Gekoppeld register
- `timestamp`: DateTimeField - Meetmoment (indexed)
- `raw_value`: FloatField - Ruwe Modbus waarde
- `converted_value`: FloatField - Geconverteerde waarde
- `quality`: CharField - good, bad, uncertain

**Indexes**:
- Composite index op (register_id, timestamp)
- Index op timestamp voor snelle time-range queries

### 2.5 TrendDataAggregated (Pre-calculated aggregates)
**Velden**:
- `register`: ForeignKey(Register)
- `timestamp`: DateTimeField - Start van aggregatie periode
- `interval`: CharField - hourly, daily, weekly
- `min_value`: FloatField
- `max_value`: FloatField
- `avg_value`: FloatField
- `sample_count`: IntegerField

**Indexes**:
- Composite index op (register_id, interval, timestamp)

### 2.6 DashboardGroup (Dashboard groepering)
**Velden**:
- `name`: CharField - Naam van groep
- `description`: TextField
- `row_order`: IntegerField - Volgorde van boven naar beneden
- `collapsed`: BooleanField - Groep ingeklapt
- `created_at`, `updated_at`: DateTimeField

### 2.7 DashboardWidget (Widget configuratie)
**Velden**:
- `group`: ForeignKey(DashboardGroup) - Gekoppelde groep
- `register`: ForeignKey(Register) - Gekoppeld register
- `widget_type`: CharField - line_chart, bar_chart, gauge, text, status
- `title`: CharField - Widget titel
- `column_position`: IntegerField - Kolom positie (0-11 voor Bootstrap grid)
- `row_position`: IntegerField - Rij positie binnen groep
- `width`: IntegerField - Breedte in Bootstrap columns (1-12)
- `height`: IntegerField - Hoogte in pixels

**Trend Configuratie** (voor chart widgets):
- `trend_enabled`: BooleanField
- `sample_rate`: IntegerField - Sample interval in seconden
- `aggregation_method`: CharField - none, mean, max, min
- `time_range`: IntegerField - Tijd venster in minuten (5, 15, 60, 1440)
- `chart_color`: CharField - Hex color code
- `show_legend`: BooleanField
- `y_axis_mode`: CharField - auto, static
- `y_axis_min`: FloatField - Voor static mode
- `y_axis_max`: FloatField - Voor static mode

**Text Display Configuratie**:
- `decimal_places`: IntegerField - Aantal decimalen
- `show_unit`: BooleanField - Eenheid tonen
- `font_size`: IntegerField - Font grootte

**Metadata**:
- `created_at`, `updated_at`: DateTimeField

### 2.8 Alarm (Alarm configuratie)
**Velden**:
- `register`: ForeignKey(Register)
- `name`: CharField - Alarm naam
- `enabled`: BooleanField
- `condition`: CharField - greater_than, less_than, equals, not_equals, range
- `threshold_high`: FloatField
- `threshold_low`: FloatField (voor range)
- `hysteresis`: FloatField - Hysteresis om alarm flapping te voorkomen
- `severity`: CharField - info, warning, critical
- `active`: BooleanField - Alarm momenteel actief
- `acknowledged`: BooleanField - Alarm bevestigd
- `triggered_at`: DateTimeField - Wanneer alarm actief werd
- `message`: TextField - Alarm bericht
- `created_at`, `updated_at`: DateTimeField

### 2.9 AlarmHistory (Alarm log)
**Velden**:
- `alarm`: ForeignKey(Alarm)
- `timestamp`: DateTimeField
- `event_type`: CharField - triggered, cleared, acknowledged
- `value`: FloatField - Register waarde bij event
- `message`: TextField

### 2.10 DeviceTemplate (Apparaat templates)
**Velden**:
- `name`: CharField - Template naam (bijv. "Victron MultiPlus")
- `manufacturer`: CharField
- `model`: CharField
- `description`: TextField
- `default_polling_interval`: IntegerField
- `register_definitions`: JSONField - JSON array met register configs
- `created_at`, `updated_at`: DateTimeField

### 2.11 CalculatedRegister (Berekende registers)
**Velden**:
- `device`: ForeignKey(Device)
- `name`: CharField
- `formula`: TextField - Python expression (bijv. "register_1 + register_2 * 1.5")
- `source_registers`: ManyToManyField(Register)
- `unit`: CharField
- `update_interval`: IntegerField - Herbereken elke X seconden
- `last_value`: FloatField
- `last_calculated`: DateTimeField

### 2.12 AuditLog (Audit trail)
**Velden**:
- `timestamp`: DateTimeField
- `action`: CharField - created, updated, deleted
- `model_name`: CharField
- `object_id`: IntegerField
- `changes`: JSONField - Dict met wijzigingen
- `ip_address`: GenericIPAddressField

---

## 3. MODBUS SERVICE LAYER

### 3.1 Modbus Drivers
**Bestand**: `modbus_app/services/modbus_driver.py`

**Classes**:
- `ModbusDriverBase`: Abstract base class
- `ModbusRTUDriver`: Serial/RTU implementatie
- `ModbusTCPDriver`: TCP/IP implementatie

**Functionaliteit**:
- Connection pooling voor TCP
- Automatic reconnect met exponential backoff
- Read operations voor alle function codes (1-4)
- Write operations (5, 6, 15, 16)
- Error handling en logging
- Timeout management
- Data type conversie (INT16/UINT16/INT32/UINT32/FLOAT32/BOOL)
- Byte order handling (big/little endian)

### 3.2 Register Service
**Bestand**: `modbus_app/services/register_service.py`

**Functionaliteit**:
- `read_register(register_obj)`: Lees enkele register
- `read_device_registers(device_obj)`: Lees alle registers van device
- `write_register(register_obj, value)`: Schrijf naar register
- `batch_read_registers(register_list)`: Optimized batch reading
- `convert_value(raw, register)`: Apply conversie formule
- `validate_write_value(register, value)`: Valideer write waarde

### 3.3 Connection Manager
**Bestand**: `modbus_app/services/connection_manager.py`

**Functionaliteit**:
- Connection pool management
- Health check per interface
- Automatic connection recovery
- Statistics tracking (success rate, response times)

---

## 4. CELERY BACKGROUND TASKS

### 4.1 Celery Configuration
**Bestand**: `modbus_webserver/celery.py`

**Setup**:
- Redis broker en result backend
- Task routing
- Beat scheduler voor periodic tasks
- Worker concurrency settings

### 4.2 Polling Tasks
**Bestand**: `modbus_app/tasks.py`

**Tasks**:

1. **`poll_device_registers`**: 
   - Poll alle enabled registers van een device
   - Opslaan in TrendData
   - WebSocket broadcast van nieuwe data
   - Error handling en retry logic

2. **`poll_all_devices`**: 
   - Scheduled task (elke 5 sec)
   - Bepaal welke devices gepolld moeten worden
   - Start poll_device_registers tasks

3. **`aggregate_trend_data`**:
   - Scheduled task (elk uur)
   - Bereken hourly aggregates (min/max/avg)
   - Opslaan in TrendDataAggregated

4. **`daily_aggregation`**:
   - Scheduled task (dagelijks 00:05)
   - Bereken daily aggregates
   - Cleanup oude raw data (retention policy)

5. **`check_alarms`**:
   - Scheduled task (elke 10 sec)
   - Check alarm conditions
   - Trigger/clear alarms
   - Create alarm history entries

6. **`update_calculated_registers`**:
   - Scheduled task (elke 5 sec)
   - Evalueer formulas
   - Update calculated values

7. **`health_check_interfaces`**:
   - Scheduled task (elke 30 sec)
   - Test connectivity per interface
   - Update connection_status

### 4.3 Beat Schedule
**Configuratie in**: `modbus_webserver/settings.py`

```python
CELERY_BEAT_SCHEDULE = {
    'poll-all-devices': {'task': 'poll_all_devices', 'schedule': 5.0},
    'aggregate-hourly': {'task': 'aggregate_trend_data', 'schedule': crontab(minute=5)},
    'aggregate-daily': {'task': 'daily_aggregation', 'schedule': crontab(hour=0, minute=5)},
    'check-alarms': {'task': 'check_alarms', 'schedule': 10.0},
    'calculated-registers': {'task': 'update_calculated_registers', 'schedule': 5.0},
    'health-check': {'task': 'health_check_interfaces', 'schedule': 30.0},
}
```

---

## 5. REST API

### 5.1 API Endpoints
**Framework**: Django REST Framework

**URL Structure**: `/api/v1/...`

**Endpoints**:

#### Modbus Interfaces
- `GET /api/v1/interfaces/` - List alle interfaces
- `POST /api/v1/interfaces/` - Create interface
- `GET /api/v1/interfaces/{id}/` - Detail view
- `PUT /api/v1/interfaces/{id}/` - Update
- `DELETE /api/v1/interfaces/{id}/` - Delete
- `POST /api/v1/interfaces/{id}/test/` - Test connectie

#### Devices
- `GET /api/v1/devices/` - List devices
- `POST /api/v1/devices/` - Create device
- `GET /api/v1/devices/{id}/` - Detail
- `PUT /api/v1/devices/{id}/` - Update
- `DELETE /api/v1/devices/{id}/` - Delete
- `GET /api/v1/devices/{id}/registers/` - Registers van device
- `POST /api/v1/devices/{id}/poll/` - Trigger manual poll

#### Registers
- `GET /api/v1/registers/` - List registers
- `POST /api/v1/registers/` - Create register
- `GET /api/v1/registers/{id}/` - Detail
- `PUT /api/v1/registers/{id}/` - Update
- `DELETE /api/v1/registers/{id}/` - Delete
- `GET /api/v1/registers/{id}/current-value/` - Laatste waarde
- `POST /api/v1/registers/{id}/write/` - Schrijf waarde
- `GET /api/v1/registers/{id}/trend-data/` - Trend data (met time range)

#### Dashboard
- `GET /api/v1/dashboard/groups/` - List groepen
- `POST /api/v1/dashboard/groups/` - Create groep
- `PUT /api/v1/dashboard/groups/{id}/` - Update groep
- `DELETE /api/v1/dashboard/groups/{id}/` - Delete groep
- `GET /api/v1/dashboard/widgets/` - List widgets
- `POST /api/v1/dashboard/widgets/` - Create widget
- `PUT /api/v1/dashboard/widgets/{id}/` - Update widget
- `DELETE /api/v1/dashboard/widgets/{id}/` - Delete widget
- `GET /api/v1/dashboard/data/` - Alle dashboard data

#### Alarms
- `GET /api/v1/alarms/` - List alarms
- `POST /api/v1/alarms/` - Create alarm
- `GET /api/v1/alarms/active/` - Actieve alarms
- `POST /api/v1/alarms/{id}/acknowledge/` - Bevestig alarm

#### Templates
- `GET /api/v1/templates/` - List device templates
- `POST /api/v1/devices/from-template/` - Create device van template

#### System
- `GET /api/v1/system/health/` - Health check
- `GET /api/v1/system/stats/` - Systeem statistieken

### 5.2 Serializers
**Bestand**: `modbus_app/serializers.py`

Serializers voor alle models met nested relationships waar nodig.

### 5.3 API Documentation
**Tool**: drf-spectacular (OpenAPI 3.0)

**Endpoints**:
- `/api/schema/` - OpenAPI schema
- `/api/docs/` - Swagger UI
- `/api/redoc/` - ReDoc interface

---

## 6. WEBSOCKET LAYER

### 6.1 Django Channels Setup
**Bestand**: `modbus_webserver/asgi.py`

**Channel Layers**: Redis backend voor message passing

### 6.2 WebSocket Consumers
**Bestand**: `modbus_app/consumers.py`

**Consumers**:

1. **`DashboardConsumer`**:
   - URL: `/ws/dashboard/`
   - Subscribes naar dashboard updates
   - Receives: Real-time register values
   - Sends: JSON met {register_id, value, timestamp, unit}

2. **`DeviceConsumer`**:
   - URL: `/ws/device/{device_id}/`
   - Real-time updates voor specifiek device
   - Connection status changes
   - Register values

3. **`AlarmConsumer`**:
   - URL: `/ws/alarms/`
   - Real-time alarm notifications
   - Alarm triggered/cleared events

### 6.3 Routing
**Bestand**: `modbus_app/routing.py`

WebSocket URL routing configuratie.

### 6.4 Broadcasting
**Utility**: `modbus_app/utils/websocket_broadcast.py`

Helper functies voor broadcasting naar channels:
- `broadcast_register_update(register_id, value)`
- `broadcast_alarm(alarm_event)`
- `broadcast_connection_status(interface_id, status)`

---

## 7. FRONTEND

### 7.1 Template Structuur

**Base Templates**:
- `templates/base.html` - Base layout met navbar
- `templates/navbar.html` - Inklapbare sidebar
- `templates/components/` - Herbruikbare components

**Dashboard**:
- `templates/dashboard/index.html` - Hoofdpagina
- `templates/dashboard/group.html` - Dashboard groep
- `templates/dashboard/widgets/` - Widget templates per type

**Configuration**:
- `templates/config/interfaces.html` - Interface overzicht
- `templates/config/interface_form.html` - Interface create/edit
- `templates/config/devices.html` - Device overzicht
- `templates/config/device_form.html` - Device create/edit
- `templates/config/registers.html` - Register overzicht per device
- `templates/config/register_form.html` - Register create/edit
- `templates/config/dashboard_config.html` - Dashboard configuratie
- `templates/config/alarms.html` - Alarm configuratie

### 7.2 Static Files

**Bootstrap 5**:
- `static/css/bootstrap.min.css` (offline)
- `static/js/bootstrap.bundle.min.js` (offline)

**Chart.js**:
- `static/js/chart.min.js` (offline)

**Custom CSS**:
- `static/css/dashboard.css` - Dashboard styling
- `static/css/navbar.css` - Navbar styling
- `static/css/widgets.css` - Widget styling

**Custom JavaScript**:
- `static/js/dashboard.js` - Dashboard logica
- `static/js/websocket.js` - WebSocket client
- `static/js/charts.js` - Chart rendering
- `static/js/forms.js` - Form validatie en interactie

**Icons & Fonts**:
- Bootstrap Icons (offline)
- System fonts

### 7.3 JavaScript Modules

**Dashboard Module** (`static/js/dashboard.js`):
- WebSocket connection management
- Chart initialization en updates
- Widget rendering
- Real-time data binding

**WebSocket Module** (`static/js/websocket.js`):
- Connection handling
- Reconnection logic
- Message routing
- Event handlers

**Chart Module** (`static/js/charts.js`):
- Chart.js configuratie
- Time-series data formatting
- Dynamic chart updates
- Zoom/pan handling

### 7.4 UI Components

**Navbar** (inklapbaar):
- Dashboard link
- Configuratie dropdown
  - Interfaces
  - Devices
  - Registers
  - Dashboard Layout
  - Alarms
  - Templates
- System dropdown
  - Health Status
  - Logs
  - Settings
- Toggle button voor collapse

**Dashboard Grid**:
- Bootstrap grid system (12 columns)
- Draggable widgets (toekomstige feature)
- Responsive breakpoints
- Groep collapse/expand

**Widget Types**:
1. Line Chart - Time-series trend
2. Bar Chart - Vergelijking values
3. Gauge - Single value met min/max
4. Text Display - Numerieke waarde met eenheid
5. Status Indicator - Online/offline/error met kleuren

**Forms**:
- Bootstrap form styling
- Client-side validatie
- Dynamic field visibility (RTU vs TCP)
- Inline register editing op device page

---

## 8. DATABASE OPTIMALISATIES

### 8.1 Indexes
**Implementatie**: In model Meta classes

**Indexen**:
- `TrendData`: (register_id, timestamp)
- `TrendDataAggregated`: (register_id, interval, timestamp)
- `AlarmHistory`: (alarm_id, timestamp)
- `AuditLog`: (timestamp, model_name)
- `Register`: (device_id, enabled)
- `Device`: (interface_id, enabled)

### 8.2 Bulk Operations
**Locatie**: `modbus_app/utils/bulk_operations.py`

**Functies**:
- `bulk_create_trend_data(data_list)`: Batch insert 1000+ records
- `bulk_update_registers(updates)`: Bulk update values
- Gebruik van `bulk_create()` en `bulk_update()` Django ORM

### 8.3 Query Optimalisatie
**Technieken**:
- `select_related()` voor ForeignKey
- `prefetch_related()` voor ManyToMany
- `only()` en `defer()` voor field selection
- `iterator()` voor grote datasets
- Raw SQL voor complexe aggregaties

### 8.4 Caching
**Backend**: Redis

**Cache Strategy**:
- Dashboard data: 5 seconden TTL
- Device status: 10 seconden TTL
- Interface lijst: 60 seconden TTL
- Template-level caching voor statische components

**Implementatie**:
```python
from django.core.cache import cache
cache.set(f'register_value_{register_id}', value, timeout=5)
```

### 8.5 Data Retention
**Policy**:
- Raw data: 7 dagen
- Hourly aggregates: 90 dagen
- Daily aggregates: 2 jaar

**Cleanup Task**: Celery scheduled task `cleanup_old_data`

### 8.6 SQLite Optimalisaties
**Settings in Django**:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'OPTIONS': {
            'timeout': 20,
            'check_same_thread': False,
        },
    }
}
```

**Pragma's** (uitgevoerd bij startup):
- `PRAGMA journal_mode=WAL;` - Write-Ahead Logging
- `PRAGMA synchronous=NORMAL;` - Sneller dan FULL
- `PRAGMA cache_size=10000;` - Groter cache
- `PRAGMA temp_store=MEMORY;` - Temp storage in memory

---

## 9. TESTING FRAMEWORK

### 9.1 Test Setup
**Framework**: pytest + pytest-django

**Configuratie**: `pytest.ini`

**Fixtures**: `tests/fixtures.py`

### 9.2 Test Categories

#### Unit Tests
**Locatie**: `tests/unit/`

**Bestanden**:
- `test_models.py` - Model validatie, methods
- `test_serializers.py` - Serializer logic
- `test_services.py` - Service layer functies
- `test_utils.py` - Utility functies

#### Integration Tests
**Locatie**: `tests/integration/`

**Bestanden**:
- `test_api_endpoints.py` - API endpoints
- `test_modbus_communication.py` - Modbus drivers met mock
- `test_celery_tasks.py` - Background tasks
- `test_websockets.py` - WebSocket consumers

#### Mock Modbus Devices
**Locatie**: `tests/mocks/modbus_mock.py`

**Functionaliteit**:
- Simulated Modbus RTU/TCP server
- Configurable responses
- Error simulation (timeouts, exceptions)
- Register value simulation

### 9.3 Test Factories
**Tool**: Factory Boy

**Bestand**: `tests/factories.py`

Factories voor alle models:
- `ModbusInterfaceFactory`
- `DeviceFactory`
- `RegisterFactory`
- `TrendDataFactory`
- etc.

### 9.4 Coverage
**Tool**: pytest-cov

**Target**: >80% code coverage

**Command**: `pytest --cov=modbus_app --cov-report=html`

### 9.5 Performance Tests
**Locatie**: `tests/performance/`

**Tests**:
- Database query performance
- Bulk operations speed
- WebSocket latency
- Celery task throughput

---

## 10. DOCKER & DEPLOYMENT

### 10.1 Docker Setup

**Bestanden**:
- `Dockerfile` - Django app container
- `docker-compose.yml` - Complete stack
- `docker-compose.dev.yml` - Development overrides
- `docker-compose.prod.yml` - Production overrides

**Containers**:
1. **web**: Django + Gunicorn
2. **nginx**: Reverse proxy + static files
3. **redis**: Cache + message broker + channel layer
4. **celery-worker**: Background task worker
5. **celery-beat**: Scheduler
6. **celery-flower** (optional): Task monitoring

### 10.2 Dockerfile
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python manage.py collectstatic --noinput
CMD ["gunicorn", "modbus_webserver.asgi:application", "-k", "uvicorn.workers.UvicornWorker"]
```

### 10.3 docker-compose.yml
Services configuratie:
- Environment variables
- Volume mounts
- Network configuratie
- Health checks
- Restart policies

### 10.4 Nginx Configuration
**Bestand**: `nginx/nginx.conf`

**Configuratie**:
- Reverse proxy naar Gunicorn
- Static files serving
- WebSocket proxy
- Gzip compression
- Security headers

### 10.5 Environment Variables
**Bestand**: `.env.example`

**Variabelen**:
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `REDIS_URL`
- `CELERY_BROKER_URL`
- `DATABASE_PATH`
- `ALLOWED_HOSTS`

### 10.6 Production Deployment

**Gunicorn Setup**:
- Uvicorn workers (ASGI support)
- Auto-reload workers
- Graceful shutdown

**Health Checks**:
- `/health/` endpoint
- Database connectivity
- Redis connectivity
- Celery worker status

**Logging**:
- Structured logging
- Log rotation
- Error aggregation (Sentry ready)

---

## 11. BESTANDSSTRUCTUUR

```
modbus-webserver/
├── modbus_webserver/              # Django project
│   ├── __init__.py
│   ├── settings.py                # Basis settings
│   ├── settings_dev.py            # Development settings
│   ├── settings_prod.py           # Production settings
│   ├── urls.py                    # URL routing
│   ├── asgi.py                    # ASGI config (WebSockets)
│   ├── wsgi.py                    # WSGI config
│   └── celery.py                  # Celery config
│
├── modbus_app/                    # Hoofd applicatie
│   ├── __init__.py
│   ├── models.py                  # Database models (alle 12)
│   ├── admin.py                   # Django admin
│   ├── views.py                   # Django views
│   ├── serializers.py             # DRF serializers
│   ├── urls.py                    # App URLs
│   ├── routing.py                 # WebSocket routing
│   ├── consumers.py               # WebSocket consumers
│   ├── tasks.py                   # Celery tasks
│   ├── forms.py                   # Django forms
│   │
│   ├── services/                  # Business logic layer
│   │   ├── __init__.py
│   │   ├── modbus_driver.py      # Modbus RTU/TCP drivers
│   │   ├── register_service.py   # Register read/write
│   │   ├── connection_manager.py # Connection pooling
│   │   ├── data_aggregator.py    # Aggregatie logic
│   │   └── alarm_checker.py      # Alarm evaluation
│   │
│   ├── utils/                     # Helper functies
│   │   ├── __init__.py
│   │   ├── websocket_broadcast.py
│   │   ├── bulk_operations.py
│   │   ├── conversions.py        # Data type conversies
│   │   └── validators.py         # Custom validators
│   │
│   ├── management/                # Custom commands
│   │   └── commands/
│   │       ├── init_db.py        # Database initialisatie
│   │       ├── load_templates.py # Load device templates
│   │       └── test_modbus.py    # Modbus test utility
│   │
│   ├── migrations/                # Database migrations
│   │   └── 0001_initial.py
│   │
│   └── templates/                 # Django templates
│       ├── base.html
│       ├── navbar.html
│       ├── dashboard/
│       │   ├── index.html
│       │   ├── group.html
│       │   └── widgets/
│       │       ├── line_chart.html
│       │       ├── gauge.html
│       │       ├── text_display.html
│       │       └── status.html
│       └── config/
│           ├── interfaces.html
│           ├── interface_form.html
│           ├── devices.html
│           ├── device_form.html
│           ├── registers.html
│           ├── register_form.html
│           ├── dashboard_config.html
│           └── alarms.html
│
├── static/                        # Static files
│   ├── css/
│   │   ├── bootstrap.min.css     # Offline Bootstrap
│   │   ├── dashboard.css
│   │   ├── navbar.css
│   │   └── widgets.css
│   ├── js/
│   │   ├── bootstrap.bundle.min.js
│   │   ├── chart.min.js          # Offline Chart.js
│   │   ├── dashboard.js
│   │   ├── websocket.js
│   │   ├── charts.js
│   │   └── forms.js
│   └── icons/                     # Bootstrap icons
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py               # pytest configuratie
│   ├── fixtures.py               # Test fixtures
│   ├── factories.py              # Factory Boy factories
│   ├── mocks/
│   │   └── modbus_mock.py
│   ├── unit/
│   │   ├── test_models.py
│   │   ├── test_serializers.py
│   │   ├── test_services.py
│   │   └── test_utils.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   ├── test_modbus_communication.py
│   │   ├── test_celery_tasks.py
│   │   └── test_websockets.py
│   └── performance/
│       ├── test_bulk_operations.py
│       └── test_query_performance.py
│
├── nginx/                         # Nginx config
│   └── nginx.conf
│
├── docs/                          # Documentatie
│   ├── API.md
│   ├── MODBUS_CONFIG.md
│   └── DEPLOYMENT.md
│
├── requirements.txt               # Python dependencies
├── requirements-dev.txt           # Development dependencies
├── .gitignore
├── .env.example                   # Environment variables template
├── Dockerfile
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── pytest.ini                     # pytest configuratie
├── manage.py                      # Django management
├── README.md
└── IMPLEMENTATION_PLAN.md         # Dit document
```

---

## 12. DEPENDENCIES (requirements.txt)

### Core
- Django==5.0
- djangorestframework==3.14.0
- channels==4.0.0
- channels-redis==4.1.0

### Modbus
- pymodbus==3.5.0
- pyserial==3.5

### Celery
- celery==5.3.0
- redis==5.0.0

### Database
- psycopg2-binary==2.9.9 (voor PostgreSQL optie)

### API Documentation
- drf-spectacular==0.27.0

### Production
- gunicorn==21.2.0
- uvicorn[standard]==0.27.0
- whitenoise==6.6.0

### Development
- pytest==7.4.0
- pytest-django==4.5.2
- pytest-cov==4.1.0
- factory-boy==3.3.0
- django-debug-toolbar==4.2.0
- black==23.12.0
- flake8==7.0.0

---

## 13. ONTWIKKEL WORKFLOW

### 13.1 Development Setup
```bash
# Clone repository
git clone <repo>
cd modbus-webserver

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup database
python manage.py migrate
python manage.py createsuperuser

# Load initial data
python manage.py load_templates

# Run development servers
python manage.py runserver  # Django
celery -A modbus_webserver worker -l info  # Celery worker
celery -A modbus_webserver beat -l info    # Celery beat
```

### 13.2 Docker Development
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### 13.3 Testing
```bash
# Run all tests
pytest

# With coverage
pytest --cov=modbus_app --cov-report=html

# Specific test file
pytest tests/unit/test_models.py

# With verbose output
pytest -v
```

### 13.4 Code Quality
```bash
# Format code
black .

# Lint
flake8 modbus_app/

# Type checking (optional)
mypy modbus_app/
```

---

## 14. IMPLEMENTATIE VOLGORDE

### Fase 1: Basis Setup (Dag 1)
- [x] Project structuur aanmaken
- [x] Django project initialisatie
- [x] .gitignore
- [x] requirements.txt
- [x] Docker basis setup
- [x] Git repository

### Fase 2: Database & Models (Dag 1-2)
- [ ] Alle 12 models implementeren
- [ ] Migrations genereren en testen
- [ ] Model methods en properties
- [ ] Database indexen
- [ ] SQLite optimalisaties

### Fase 3: Modbus Service (Dag 2-3)
- [ ] RTU driver implementatie
- [ ] TCP driver implementatie
- [ ] Connection manager
- [ ] Register service
- [ ] Data conversie utilities
- [ ] Unit tests voor drivers

### Fase 4: Admin & Basic Views (Dag 3)
- [ ] Django admin configuratie
- [ ] Basic CRUD views
- [ ] URL routing
- [ ] Forms voor alle models

### Fase 5: Celery Tasks (Dag 4)
- [ ] Celery configuratie
- [ ] Polling tasks
- [ ] Aggregatie tasks
- [ ] Alarm checking
- [ ] Beat schedule
- [ ] Task tests

### Fase 6: REST API (Dag 4-5)
- [ ] DRF setup
- [ ] Serializers
- [ ] ViewSets
- [ ] URL routing
- [ ] OpenAPI documentatie
- [ ] API tests

### Fase 7: WebSockets (Dag 5-6)
- [ ] Django Channels setup
- [ ] Consumers implementatie
- [ ] Routing
- [ ] Broadcasting utilities
- [ ] WebSocket tests

### Fase 8: Frontend Templates (Dag 6-7)
- [ ] Base template en navbar
- [ ] Dashboard template
- [ ] Configuration templates
- [ ] Widget templates
- [ ] Bootstrap offline setup

### Fase 9: JavaScript & Charts (Dag 7-8)
- [ ] WebSocket client
- [ ] Dashboard JavaScript
- [ ] Chart.js integratie
- [ ] Real-time updates
- [ ] Form interactivity

### Fase 10: Testing (Dag 8-9)
- [ ] Unit tests volledig
- [ ] Integration tests
- [ ] Mock Modbus devices
- [ ] Performance tests
- [ ] Coverage >80%

### Fase 11: Production Setup (Dag 9-10)
- [ ] Docker Compose production
- [ ] Nginx configuratie
- [ ] Gunicorn setup
- [ ] Environment variables
- [ ] Health checks
- [ ] Logging

### Fase 12: Documentation & Polish (Dag 10)
- [ ] API documentatie
- [ ] Deployment guide
- [ ] User manual
- [ ] Code comments
- [ ] README

---

## 15. SUCCESS CRITERIA

### Functionaliteit
- ✓ Modbus RTU en TCP interfaces configureerbaar
- ✓ Devices toevoegen met registers
- ✓ Real-time data polling werkt
- ✓ Dashboard toont live data
- ✓ Trends worden correct opgeslagen
- ✓ Alarm systeem functioneel
- ✓ Write operations werken
- ✓ WebSocket updates real-time

### Performance
- ✓ Dashboard laadt binnen 2 seconden
- ✓ WebSocket latency <100ms
- ✓ Bulk insert >1000 records/sec
- ✓ Query response time <100ms gemiddeld
- ✓ 100+ devices supported zonder performance degradatie

### Testing
- ✓ >80% code coverage
- ✓ Alle unit tests passing
- ✓ Integration tests passing
- ✓ Mock Modbus devices werkend

### Deployment
- ✓ Docker Compose werkt out-of-the-box
- ✓ Health checks functioneel
- ✓ Logging configured
- ✓ Production-ready

### Code Quality
- ✓ PEP8 compliant
- ✓ Type hints waar mogelijk
- ✓ Comprehensive comments
- ✓ No critical security issues

---

## 16. TOEKOMSTIGE UITBREIDINGEN

### Fase 2 Features (na initial release):
1. **User Authentication**: Multi-user met permissions
2. **Drag & Drop Dashboard**: Interactive widget placement
3. **Data Export**: Scheduled CSV/Excel reports
4. **Email Notifications**: Voor alarms
5. **Mobile App**: React Native companion app
6. **MQTT Integration**: Publish data naar MQTT broker
7. **Grafana Integration**: Grafana data source plugin
8. **OPC UA**: OPC UA protocol support
9. **Cloud Sync**: Optional cloud backup
10. **Plugin System**: Extensible plugin architecture

---

## VERIFICATIE CHECKLIST

Gebruik deze checklist om te verifiëren dat alles geïmplementeerd is:

### Project Setup
- [ ] Django project exists
- [ ] .gitignore aanwezig
- [ ] requirements.txt compleet
- [ ] Docker files aanwezig
- [ ] README.md aanwezig

### Models (12 total)
- [ ] ModbusInterface
- [ ] Device
- [ ] Register
- [ ] TrendData
- [ ] TrendDataAggregated
- [ ] DashboardGroup
- [ ] DashboardWidget
- [ ] Alarm
- [ ] AlarmHistory
- [ ] DeviceTemplate
- [ ] CalculatedRegister
- [ ] AuditLog

### Services
- [ ] ModbusRTUDriver
- [ ] ModbusTCPDriver
- [ ] ConnectionManager
- [ ] RegisterService
- [ ] DataAggregator
- [ ] AlarmChecker

### Celery Tasks
- [ ] poll_device_registers
- [ ] poll_all_devices
- [ ] aggregate_trend_data
- [ ] daily_aggregation
- [ ] check_alarms
- [ ] update_calculated_registers
- [ ] health_check_interfaces

### API Endpoints
- [ ] Interfaces CRUD
- [ ] Devices CRUD
- [ ] Registers CRUD
- [ ] Dashboard CRUD
- [ ] Alarms CRUD
- [ ] System endpoints

### WebSockets
- [ ] DashboardConsumer
- [ ] DeviceConsumer
- [ ] AlarmConsumer
- [ ] Broadcasting utilities

### Templates
- [ ] base.html
- [ ] navbar.html
- [ ] dashboard/index.html
- [ ] Config templates (6+)
- [ ] Widget templates (4+)

### JavaScript
- [ ] dashboard.js
- [ ] websocket.js
- [ ] charts.js
- [ ] forms.js

### Static Files
- [ ] Bootstrap offline
- [ ] Chart.js offline
- [ ] Custom CSS files
- [ ] Icons

### Tests
- [ ] Unit tests (models, services, utils)
- [ ] Integration tests (API, Modbus, Celery, WebSocket)
- [ ] Mock Modbus devices
- [ ] Performance tests
- [ ] >80% coverage

### Docker
- [ ] Dockerfile
- [ ] docker-compose.yml
- [ ] docker-compose.dev.yml
- [ ] docker-compose.prod.yml
- [ ] nginx.conf

### Documentation
- [ ] IMPLEMENTATION_PLAN.md (dit document)
- [ ] README.md
- [ ] API.md
- [ ] DEPLOYMENT.md

---

**EINDE IMPLEMENTATIEPLAN**

Dit document dient als complete verificatie van wat er gebouwd moet worden. Alle features, bestanden, en functionaliteit zijn hier gedocumenteerd.
