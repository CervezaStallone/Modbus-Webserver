# Modbus Webserver

Een complete Django-based webapplicatie voor monitoring en configuratie van Modbus RTU/TCP apparaten met real-time dashboard, trending, en alarm functionaliteit.

## Features

- Modbus RTU (serieel) en TCP/IP protocol support
- Real-time data acquisition en monitoring
- Configureerbare dashboards met meerdere widget types
- Time-series data trending met aggregatie
- Alarm systeem met threshold monitoring
- WebSocket real-time updates
- REST API voor externe integratie
- Background task processing met Celery
- Complete test suite
- Docker deployment ready

## Tech Stack

- **Backend**: Django 5.0, Django REST Framework, Django Channels
- **Database**: SQLite (geoptimaliseerd voor performance)
- **Task Queue**: Celery + Redis
- **WebSockets**: Django Channels + Redis
- **Frontend**: Bootstrap 5, Chart.js
- **Modbus**: pymodbus (RTU + TCP)
- **Testing**: pytest, Factory Boy
- **Deployment**: Docker, Nginx, Gunicorn

## Quick Start

### Development Setup (zonder Docker)

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

In aparte terminals:
```bash
# Celery worker
celery -A modbus_webserver worker -l info

# Celery beat scheduler
celery -A modbus_webserver beat -l info
```

### Development Setup (met Docker)

```bash
# Start alle services
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

## Project Structure

```
modbus-webserver/
├── modbus_webserver/      # Django project configuratie
├── modbus_app/            # Hoofd applicatie
│   ├── models.py          # Database models
│   ├── views.py           # Views
│   ├── serializers.py     # DRF serializers
│   ├── consumers.py       # WebSocket consumers
│   ├── tasks.py           # Celery tasks
│   ├── services/          # Business logic
│   ├── utils/             # Helper functies
│   └── templates/         # HTML templates
├── static/                # Static files (CSS, JS)
├── tests/                 # Test suite
├── nginx/                 # Nginx configuratie
└── docs/                  # Documentatie
```

## Usage

### 1. Modbus Interface Configureren

Ga naar "Configuration > Interfaces" en maak een nieuwe interface aan:

**RTU (Serieel)**:
- Naam: bijv. "COM3 Interface"
- Protocol: RTU
- Port: bijv. "COM3" of "/dev/ttyUSB0"
- Baudrate: 9600, 19200, etc.
- Parity: None, Even, Odd
- Stopbits: 1 of 2
- Bytesize: 7 of 8

**TCP/IP**:
- Naam: bijv. "PLC TCP"
- Protocol: TCP
- Host: IP adres (bijv. 192.168.1.100)
- Port: 502 (standaard Modbus)

### 2. Device Toevoegen

Ga naar "Configuration > Devices":
- Kies interface
- Slave ID (1-247)
- Polling interval in seconden
- Beschrijving

### 3. Registers Configureren

Selecteer device en voeg registers toe:
- Naam: bijv. "Temperatuur Ketel"
- Function Code: 3 (Read Holding Registers)
- Adres: Register adres
- Data Type: INT16, UINT16, INT32, FLOAT32, etc.
- Conversie: factor en offset
- Eenheid: °C, kW, etc.
- Trenden: Aan/uit

### 4. Dashboard Widgets

Ga naar "Configuration > Dashboard Layout":
- Maak groepen aan
- Voeg widgets toe per register
- Configureer widget type (line chart, gauge, text)
- Stel positie en grootte in
- Configureer trend parameters (sample rate, Y-as, kleuren)

### 5. Dashboard Bekijken

Ga naar "Dashboard" om live data te zien. Data wordt real-time bijgewerkt via WebSockets.

## Testing

```bash
# Run alle tests
pytest

# Met coverage report
pytest --cov=modbus_app --cov-report=html

# Specifieke test module
pytest tests/unit/test_models.py

# Verbose output
pytest -v
```

## API Documentation

API documentatie is beschikbaar op:
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- OpenAPI Schema: http://localhost:8000/api/schema/

## Production Deployment

```bash
# Build en start productie containers
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Run migrations
docker-compose exec web python manage.py migrate

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Create superuser
docker-compose exec web python manage.py createsuperuser
```

Applicatie is beschikbaar op http://localhost

## Configuration

Belangrijke environment variables (`.env`):

- `DJANGO_SECRET_KEY`: Secret key voor Django (verander in productie!)
- `DJANGO_DEBUG`: Debug mode (False in productie)
- `REDIS_URL`: Redis connection URL
- `DEFAULT_POLLING_INTERVAL`: Default polling frequentie (seconden)
- `DATA_RETENTION_DAYS`: Hoe lang raw data bewaren

Zie `.env.example` voor alle opties.

## Performance Optimalisatie

SQLite is geoptimaliseerd met:
- Write-Ahead Logging (WAL mode)
- Verhoogde cache size
- Database indexen op kritieke velden
- Bulk insert operaties voor trend data
- Pre-calculated aggregates voor lange time ranges

## Troubleshooting

### Modbus connectie problemen

- Check seriële poort permissions op Linux: `sudo usermod -a -G dialout $USER`
- Verificeer baudrate en parity settings matchen met apparaat
- Test connectie met built-in test tool: `python manage.py test_modbus`

### WebSocket connectie problemen

- Controleer Redis is running
- Check CHANNEL_LAYERS configuratie in settings
- Browser console voor JavaScript errors

### Celery tasks draaien niet

- Controleer Celery worker en beat zijn gestart
- Check Redis connectie
- Bekijk Celery logs voor errors

## Contributing

1. Fork het project
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push naar branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## License

Dit project is beschikbaar onder de MIT License.

## Contact

Voor vragen en support, zie de documentatie in `/docs` of open een issue.

## Documentatie

- [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) - Volledig implementatieplan
- [docs/API.md](docs/API.md) - API documentatie
- [docs/MODBUS_CONFIG.md](docs/MODBUS_CONFIG.md) - Modbus configuratie guide
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment instructies
