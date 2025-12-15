#!/bin/bash
# Modbus Webserver - Start Everything Including App

# Don't exit on error for optional services
set +e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo -e "${YELLOW}⚙️  Virtual environment activeren...${NC}"
    source .venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment geactiveerd${NC}"
elif [ -d "venv" ]; then
    echo -e "${YELLOW}⚙️  Virtual environment activeren...${NC}"
    source venv/bin/activate
    echo -e "${GREEN}✓ Virtual environment geactiveerd${NC}"
fi

# Detect Python command
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo -e "${RED}❌ Python niet gevonden!${NC}"
    exit 1
fi

# PIDs for cleanup
DJANGO_PID=""
CELERY_WORKER_PID=""
CELERY_BEAT_PID=""

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}╔════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║     App gestopt met Ctrl+C             ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Wat wil je doen?${NC}"
    echo "  1) Stop alleen de app (Redis blijft draaien)"
    echo "  2) Stop alles (inclusief Redis)"
    echo ""
    read -p "Kies een optie (1/2): " choice
    
    echo ""
    echo -e "${YELLOW}⏳ Stoppen...${NC}"
    
    # Stop Django
    if [ ! -z "$DJANGO_PID" ]; then
        kill $DJANGO_PID 2>/dev/null && echo -e "${GREEN}✓ Django gestopt${NC}" || echo "  Django al gestopt"
    fi
    
    # Stop Celery Worker
    if [ ! -z "$CELERY_WORKER_PID" ]; then
        kill $CELERY_WORKER_PID 2>/dev/null && echo -e "${GREEN}✓ Celery Worker gestopt${NC}" || echo "  Celery Worker al gestopt"
    fi
    
    # Stop Celery Beat
    if [ ! -z "$CELERY_BEAT_PID" ]; then
        kill $CELERY_BEAT_PID 2>/dev/null && echo -e "${GREEN}✓ Celery Beat gestopt${NC}" || echo "  Celery Beat al gestopt"
    fi
    
    # Stop Redis if option 2
    if [ "$choice" = "2" ]; then
        redis-cli shutdown 2>/dev/null && echo -e "${GREEN}✓ Redis gestopt${NC}" || echo "  Redis niet actief"
    fi
    
    echo ""
    echo -e "${GREEN}Klaar!${NC}"
    exit 0
}

# Trap Ctrl+C
trap cleanup SIGINT SIGTERM

echo "🚀 Starting Modbus Webserver - Alles inclusief app..."
echo ""

# Use .env.local if it exists (for local development)
if [ -f ".env.local" ]; then
    echo -e "${YELLOW}⚙️  Gebruik .env.local voor lokale ontwikkeling${NC}"
    export $(cat .env.local | grep -v '^#' | xargs)
elif [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo -e "${RED}❌ Redis is niet geïnstalleerd!${NC}"
    echo "Installeer Redis eerst:"
    echo "  Ubuntu/Debian: sudo apt install redis-server"
    echo "  macOS: brew install redis"
    echo "  Fedora: sudo dnf install redis"
    exit 1
fi

# Check if Redis is running
if ! pgrep -x "redis-server" > /dev/null; then
    echo -e "${YELLOW}⚙️  Redis starten...${NC}"
    redis-server --daemonize yes --port 6379
    sleep 2
    if pgrep -x "redis-server" > /dev/null; then
        echo -e "${GREEN}✓ Redis gestart${NC}"
    else
        echo -e "${RED}❌ Redis starten mislukt${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✓ Redis draait al${NC}"
fi

# Check and download static files if missing
echo -e "${YELLOW}⚙️  Static files controleren...${NC}"

missing_files=0

# Check Bootstrap CSS
if [ ! -f "static/css/bootstrap.min.css" ]; then
    echo -e "${YELLOW}  → Bootstrap CSS niet gevonden, downloaden...${NC}"
    curl -sS -o static/css/bootstrap.min.css https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}    ✓ Bootstrap CSS gedownload${NC}"
    else
        echo -e "${RED}    ✗ Bootstrap CSS download mislukt${NC}"
        missing_files=1
    fi
fi

# Check Bootstrap JS
if [ ! -f "static/js/bootstrap.bundle.min.js" ]; then
    echo -e "${YELLOW}  → Bootstrap JS niet gevonden, downloaden...${NC}"
    curl -sS -o static/js/bootstrap.bundle.min.js https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}    ✓ Bootstrap JS gedownload${NC}"
    else
        echo -e "${RED}    ✗ Bootstrap JS download mislukt${NC}"
        missing_files=1
    fi
fi

# Check Chart.js
if [ ! -f "static/js/chart.min.js" ]; then
    echo -e "${YELLOW}  → Chart.js niet gevonden, downloaden...${NC}"
    curl -sS -o static/js/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}    ✓ Chart.js gedownload${NC}"
    else
        echo -e "${RED}    ✗ Chart.js download mislukt${NC}"
        missing_files=1
    fi
fi

# Check Bootstrap Icons CSS
if [ ! -f "static/css/bootstrap-icons.min.css" ]; then
    echo -e "${YELLOW}  → Bootstrap Icons CSS niet gevonden, downloaden...${NC}"
    curl -sS -o static/css/bootstrap-icons.min.css https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}    ✓ Bootstrap Icons CSS gedownload${NC}"
    else
        echo -e "${RED}    ✗ Bootstrap Icons CSS download mislukt${NC}"
        missing_files=1
    fi
fi

# Check Bootstrap Icons fonts
if [ ! -d "static/css/fonts" ] || [ -z "$(ls -A static/css/fonts 2>/dev/null)" ]; then
    echo -e "${YELLOW}  → Bootstrap Icons fonts niet gevonden, downloaden...${NC}"
    mkdir -p static/css/fonts
    curl -sS -o /tmp/bootstrap-icons-fonts.zip https://github.com/twbs/icons/releases/download/v1.11.3/bootstrap-icons-1.11.3.zip
    if [ $? -eq 0 ]; then
        unzip -q -j /tmp/bootstrap-icons-fonts.zip "bootstrap-icons-1.11.3/font/fonts/*" -d static/css/fonts/
        rm /tmp/bootstrap-icons-fonts.zip
        echo -e "${GREEN}    ✓ Bootstrap Icons fonts gedownload${NC}"
    else
        echo -e "${RED}    ✗ Bootstrap Icons fonts download mislukt${NC}"
        missing_files=1
    fi
fi

if [ $missing_files -eq 0 ]; then
    echo -e "${GREEN}✓ Alle static files aanwezig${NC}"
else
    echo -e "${YELLOW}⚠ Sommige static files ontbreken (zie boven)${NC}"
fi

# Check Django
echo -e "${YELLOW}⚙️  Django setup controleren...${NC}"
$PYTHON_CMD manage.py check 2>/dev/null || $PYTHON_CMD manage.py check
echo -e "${GREEN}✓ Django check geslaagd${NC}"

# Apply migrations
echo -e "${YELLOW}⚙️  Database migraties toepassen...${NC}"
$PYTHON_CMD manage.py migrate --noinput
echo -e "${GREEN}✓ Migraties toegepast${NC}"

# Collect static files
echo -e "${YELLOW}⚙️  Static files verzamelen...${NC}"
$PYTHON_CMD manage.py collectstatic --noinput --clear > /dev/null 2>&1
echo -e "${GREEN}✓ Static files verzameld${NC}"

# Create logs directory if it doesn't exist
mkdir -p logs

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}    Services starten...                ${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""

# Start Celery Worker in background
echo -e "${YELLOW}⚙️  Celery Worker starten...${NC}"
celery -A modbus_webserver worker -l info > logs/celery-worker.log 2>&1 &
CELERY_WORKER_PID=$!
sleep 3
if kill -0 $CELERY_WORKER_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Celery Worker gestart (PID: $CELERY_WORKER_PID)${NC}"
else
    echo -e "${YELLOW}⚠ Celery Worker niet gestart (optioneel)${NC}"
    CELERY_WORKER_PID=""
fi

# Start Celery Beat in background
echo -e "${YELLOW}⚙️  Celery Beat starten...${NC}"
celery -A modbus_webserver beat -l info > logs/celery-beat.log 2>&1 &
CELERY_BEAT_PID=$!
sleep 3
if kill -0 $CELERY_BEAT_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Celery Beat gestart (PID: $CELERY_BEAT_PID)${NC}"
else
    echo -e "${YELLOW}⚠ Celery Beat niet gestart (optioneel)${NC}"
    CELERY_BEAT_PID=""
fi

# Start Django
echo -e "${YELLOW}⚙️  Django development server starten...${NC}"
sleep 1

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  🎉 Alle services draaien!             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Applicatie beschikbaar op:${NC}"
echo -e "  ${BLUE}http://localhost:8000/${NC}"
echo ""
echo -e "${YELLOW}Logs:${NC}"
echo "  Celery Worker: logs/celery-worker.log"
echo "  Celery Beat:   logs/celery-beat.log"
echo ""
echo -e "${RED}Druk op Ctrl+C om te stoppen...${NC}"
echo ""

# Start Django in foreground (so we can see output and catch Ctrl+C)
$PYTHON_CMD manage.py runserver &
DJANGO_PID=$!

# Wait for Django process
wait $DJANGO_PID
