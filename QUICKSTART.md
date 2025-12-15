# Modbus Webserver - Quick Start Guide

## 🚀 Snel Starten (5 minuten)

### Vereisten

- Python 3.11+
- Redis server
- Git

### Stap 1: Installeer Redis

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis
sudo systemctl enable redis
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Fedora/RHEL:**
```bash
sudo dnf install redis
sudo systemctl start redis
sudo systemctl enable redis
```

**Test Redis:**
```bash
redis-cli ping
# Should return: PONG
```

### Stap 2: Setup Project

```bash
# Installeer dependencies
pip install -r requirements.txt

# Database setup
python manage.py migrate

# Create superuser (voor eerste login)
python manage.py createsuperuser

# Collect static files
python manage.py collectstatic --noinput
```

### Stap 3: Start Services

**Optie A - Automated (Aanbevolen):**
```bash
./start-services.sh
```

Dit script:
- ✓ Checkt of Redis draait
- ✓ Voert migrations uit
- ✓ Verzamelt static files
- ✓ Geeft je de commando's om Django en Celery te starten

**Optie B - Handmatig (3 terminals):**

Terminal 1 - Django:
```bash
python manage.py runserver
```

Terminal 2 - Celery Worker:
```bash
celery -A modbus_webserver worker -l info
```

Terminal 3 - Celery Beat:
```bash
celery -A modbus_webserver beat -l info
```

**Optie C - Separate Scripts:**
```bash
./run-django.sh      # Terminal 1
./run-celery.sh      # Terminal 2 (start beide worker + beat)
```

### Stap 4: Inloggen en Configureren

1. Open browser: **http://localhost:8000/**
2. Klik **"Inloggen"** (rechtsboven in menu)
3. Log in met je superuser credentials
4. Ga naar **"Interfaces"** in het menu
5. Klik **"Nieuwe Interface"**
6. Configureer je eerste Modbus interface (RTU of TCP)

---

## 📱 Eerste Interface Toevoegen

### Modbus TCP Voorbeeld

1. Klik **"Nieuwe Interface"**
2. Vul in:
   - **Naam**: `PLC-1`
   - **Protocol**: `TCP`
   - **Host**: `192.168.1.100`
   - **Port**: `502`
   - **Timeout**: `3.0`
3. Klik **"Test Verbinding"** (optioneel)
4. Klik **"Opslaan"**

### Modbus RTU Voorbeeld

1. Klik **"Nieuwe Interface"**
2. Vul in:
   - **Naam**: `Serial-Modbus`
   - **Protocol**: `RTU`
   - **Port**: `/dev/ttyUSB0` (Linux) of `COM3` (Windows)
   - **Baudrate**: `9600`
   - **Parity**: `None`
   - **Stopbits**: `1`
   - **Bytesize**: `8`
   - **Timeout**: `3.0`
3. Klik **"Opslaan"**

---

## 🔧 Device Toevoegen

1. Ga naar **"Devices"** in menu
2. Klik **"Nieuw Device"** (of ga naar `/admin/` voor form)
3. Configureer:
   - **Naam**: Beschrijvende naam
   - **Interface**: Selecteer je interface
   - **Slave ID**: 1-247
   - **Polling Interval**: 5 seconden (aanbevolen)
   - **Enabled**: ✓

---

## 📊 Registers Toevoegen

1. Ga naar **"Registers"** in menu
2. Selecteer je device
3. Klik **"Nieuw Register"** (of ga naar `/admin/`)
4. Configureer:
   - **Naam**: Bijvoorbeeld "Temperatuur"
   - **Address**: Register adres (0-65535)
   - **Function Code**: FC03 (Read Holding)
   - **Data Type**: FLOAT32, INT16, etc.
   - **Unit**: °C, kW, etc.
   - **Conversion Factor**: 1.0 (of bijv. 0.1 voor delen door 10)
   - **Enabled**: ✓

---

## ✅ Verificatie

### Check of alles werkt:

1. **Dashboard**: Ga naar hoofdpagina - je zou "WebSocket verbinding OK" moeten zien
2. **API Docs**: Ga naar http://localhost:8000/api/docs/ - Swagger UI moet laden
3. **Admin**: Ga naar http://localhost:8000/admin/ - Django admin moet bereikbaar zijn
4. **Redis**: Run `redis-cli ping` - moet "PONG" returnen
5. **Celery**: Check logs - moet tasks uitvoeren elk 5 seconden

### Check Celery Tasks

Open de Celery worker log en zoek naar:
```
[tasks]
  . modbus_app.tasks.poll_all_devices
  . modbus_app.tasks.check_alarms
  . modbus_app.tasks.aggregate_trend_data
  ...
```

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'django'"

Je virtual environment is niet actief of dependencies zijn niet geïnstalleerd:
```bash
pip install -r requirements.txt
```

### "Connection refused" bij Redis

Redis draait niet:
```bash
# Linux
sudo systemctl start redis

# macOS
brew services start redis

# Handmatig
redis-server
```

### "403 Forbidden" bij API calls

Je bent niet ingelogd. Klik op **"Inloggen"** in het menu rechtsboven.

### WebSocket verbinding faalt

1. Check of Redis draait: `redis-cli ping`
2. Check Celery logs voor errors
3. Herstart Django server

### Celery tasks worden niet uitgevoerd

1. Check of Celery worker draait: `ps aux | grep celery`
2. Check of Celery beat draait
3. Check Redis verbinding
4. Herstart Celery: `./run-celery.sh`

### "CSRF token missing"

Dit is gefixed in de templates. Als het nog voorkomt:
1. Hard refresh browser (Ctrl+Shift+R)
2. Clear cookies
3. Log opnieuw in

---

## 🛑 Services Stoppen

```bash
./stop-services.sh
```

Of handmatig:
```bash
# Stop Django
pkill -f "manage.py runserver"

# Stop Celery
pkill -f "celery.*modbus_webserver"

# Stop Redis (optioneel)
redis-cli shutdown
```

---

## 📚 Volgende Stappen

1. **Dashboard Configureren**: Maak widgets aan in `/admin/`
2. **Alarms Instellen**: Configureer thresholds voor registers
3. **Templates Maken**: Herbruikbare device configuraties
4. **API Gebruiken**: Zie `/api/docs/` voor volledige API referentie

---

## 🔗 Nuttige Links

- **Homepage**: http://localhost:8000/
- **Admin Panel**: http://localhost:8000/admin/
- **API Docs**: http://localhost:8000/api/docs/
- **API Schema**: http://localhost:8000/api/schema/

---

## ⚙️ Development Mode vs Production

Je draait nu in **development mode**. Voor productie:

1. Gebruik Gunicorn in plaats van `runserver`
2. Gebruik Nginx als reverse proxy
3. Gebruik Docker Compose (zie `docker-compose.prod.yml`)
4. Set `DEBUG=False` in environment
5. Configureer proper SECRET_KEY

Zie `IMPLEMENTATION_PLAN.md` voor volledige deployment guide.
