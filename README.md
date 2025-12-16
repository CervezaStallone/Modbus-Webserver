# Modbus Web Server

A complete Django-based web application for monitoring and configuration of Modbus RTU/TCP devices with real-time dashboard, trending, and alarm functionality.

## Features

- Modbus RTU (serial) and TCP/IP protocol support
- Real-time data acquisition and monitoring
- Configurable dashboards with multiple widget types
- Time-series data trending with aggregation
- Alarm system with threshold monitoring
- WebSocket real-time updates
- REST API for external integration
- Background task processing with Celery
- Complete test suite
- Docker deployment ready

## Tech Stack

- **Backend**: Django 5.0, Django REST Framework, Django Channels
- **Database**: SQLite (optimized for performance)
- **Task Queue**: Celery + Redis
- **WebSockets**: Django Channels + Redis
- **Frontend**: Bootstrap 5, Chart.js
- **Modbus**: pymodbus (RTU + TCP)
- **Testing**: pytest, Factory Boy
- **Deployment**: Docker, Nginx, Gunicorn

## Quick Start

### Development Setup (without Docker)

```bash
# Clone repository
git clone <repository-url>
cd modbus-webserver

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Copy environment variables
cp .env.example .env

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

In separate terminals:
```bash
# Celery worker
celery -A modbus_webserver worker -l info

# Celery beat scheduler
celery -A modbus_webserver beat -l info
```

### Development Setup (with Docker)

```bash
# Start all services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

## Project Structure

```
modbus-webserver/
├── modbus_webserver/      # Django project configuration
├── modbus_app/            # Main application
│   ├── models.py          # Database models
│   ├── views.py           # Views
│   ├── serializers.py     # DRF serializers
│   ├── consumers.py       # WebSocket consumers
│   ├── tasks.py           # Celery tasks
│   ├── services/          # Business logic
│   ├── utils/             # Helper functions
│   └── templates/         # HTML templates
├── static/                # Static files (CSS, JS)
├── tests/                 # Test suite
├── nginx/                 # Nginx configuration
└── docs/                  # Documentation
```

## Usage

### 1. Configure Modbus Interface

Navigate to "Configuration > Interfaces" and create a new interface:

**RTU (Serial)**:
- Name: e.g., "COM3 Interface"
- Protocol: RTU
- Port: e.g., "COM3" or "/dev/ttyUSB0"
- Baudrate: 9600, 19200, etc.
- Parity: None, Even, Odd
- Stopbits: 1 or 2
- Bytesize: 7 or 8

**TCP/IP**:
- Name: e.g., "PLC TCP"
- Protocol: TCP
- Host: IP address (e.g., 192.168.1.100)
- Port: 502 (default Modbus)

### 2. Add Device

Navigate to "Configuration > Devices":
- Select interface
- Slave ID (1-247)
- Polling interval in seconds
- Description

### 3. Configure Registers

Select device and add registers:
- Name: e.g., "Boiler Temperature"
- Function Code: 3 (Read Holding Registers)
- Address: Register address
- Data Type: INT16, UINT16, INT32, FLOAT32, etc.
- Conversion: factor and offset
- Unit: °C, kW, etc.
- Trending: On/Off

### 4. Dashboard Widgets

Navigate to "Configuration > Dashboard Layout":
- Create groups
- Add widgets per register
- Configure widget type (line chart, gauge, text)
- Set position and size
- Configure trend parameters (sample rate, Y-axis, colors)

### 5. View Dashboard

Navigate to "Dashboard" to see live data. Data is updated in real-time via WebSockets.

## Testing

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=modbus_app --cov-report=html

# Specific test module
pytest tests/unit/test_models.py

# Verbose output
pytest -v
```

## API Documentation

API documentation is available at:
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## Production Deployment

```bash
# Build and start production containers
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

Application is available at http://localhost

## Configuration

Important environment variables (`.env`):

- `DJANGO_SECRET_KEY`: Secret key for Django (change in production!)
- `DJANGO_DEBUG`: Debug mode (False in production)
- `REDIS_URL`: Redis connection URL
- `DEFAULT_POLLING_INTERVAL`: Default polling frequency (seconds)
- `DATA_RETENTION_DAYS`: How long to keep raw data

See `.env.example` for all options.

## Performance Optimization

SQLite is optimized with:
- Write-Ahead Logging (WAL mode)
- Increased cache size
- Database indexes on critical fields
- Bulk insert operations for trend data
- Pre-calculated aggregates for long time ranges

## Troubleshooting

### Modbus Connection Issues

- Check serial port permissions on Linux: `sudo usermod -a -G dialout $USER`
- Verify baudrate and parity settings match the device
- Test connection with built-in test tool: `python manage.py test_modbus`

### WebSocket Connection Issues

- Verify Redis is running
- Check CHANNEL_LAYERS configuration in settings
- Browser console for JavaScript errors

### Celery Tasks Not Running

- Verify Celery worker and beat are started
- Check Redis connection
- Review Celery logs for errors

## Contributing

1. Fork the project
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## License

This project is available under the MIT License.

## Contact

For questions and support, see the documentation in `/docs` or open an issue.

## Documentation

- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Complete implementation plan
- [docs/API.md](docs/API.md) - API documentation
- [docs/MODBUS_CONFIG.md](docs/MODBUS_CONFIG.md) - Modbus configuration guide
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment instructions
