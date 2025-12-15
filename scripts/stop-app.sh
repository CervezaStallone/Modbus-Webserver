#!/bin/bash
# Modbus Webserver - Stop Everything

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "🛑 Modbus Webserver stoppen..."
echo ""

# Stop Django
echo -e "${YELLOW}⏳ Django stoppen...${NC}"
pkill -f "manage.py runserver" && echo -e "${GREEN}✓ Django gestopt${NC}" || echo "  Django draait niet"

# Stop Celery Worker
echo -e "${YELLOW}⏳ Celery Worker stoppen...${NC}"
pkill -f "celery.*worker.*modbus_webserver" && echo -e "${GREEN}✓ Celery Worker gestopt${NC}" || echo "  Celery Worker draait niet"

# Stop Celery Beat
echo -e "${YELLOW}⏳ Celery Beat stoppen...${NC}"
pkill -f "celery.*beat.*modbus_webserver" && echo -e "${GREEN}✓ Celery Beat gestopt${NC}" || echo "  Celery Beat draait niet"

# Stop Redis
echo -e "${YELLOW}⏳ Redis stoppen...${NC}"
redis-cli shutdown 2>/dev/null && echo -e "${GREEN}✓ Redis gestopt${NC}" || echo "  Redis draait niet"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Alle services gestopt!             ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
