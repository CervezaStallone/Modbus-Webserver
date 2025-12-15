# Modbus Webserver - Stop Everything (PowerShell)

# Function to Write-ColoredMessage
function Write-ColoredMessage {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

Write-Host "🛑 Modbus Webserver stoppen..."
Write-Host ""

# Stop Django
Write-ColoredMessage "⏳ Django stoppen..." "Yellow"
$djangoProcesses = Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*manage.py*runserver*"
}
if ($djangoProcesses) {
    $djangoProcesses | Stop-Process -Force
    Write-ColoredMessage "✓ Django gestopt" "Green"
} else {
    Write-Host "  Django draait niet"
}

# Stop Celery Worker
Write-ColoredMessage "⏳ Celery Worker stoppen..." "Yellow"
$celeryWorkerProcesses = Get-Process -Name celery,python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*celery*worker*modbus_webserver*"
}
if ($celeryWorkerProcesses) {
    $celeryWorkerProcesses | Stop-Process -Force
    Write-ColoredMessage "✓ Celery Worker gestopt" "Green"
} else {
    Write-Host "  Celery Worker draait niet"
}

# Stop Celery Beat
Write-ColoredMessage "⏳ Celery Beat stoppen..." "Yellow"
$celeryBeatProcesses = Get-Process -Name celery,python -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*celery*beat*modbus_webserver*"
}
if ($celeryBeatProcesses) {
    $celeryBeatProcesses | Stop-Process -Force
    Write-ColoredMessage "✓ Celery Beat gestopt" "Green"
} else {
    Write-Host "  Celery Beat draait niet"
}

# Stop Redis
Write-ColoredMessage "⏳ Redis stoppen..." "Yellow"
try {
    if (Get-Process -Name redis-server -ErrorAction SilentlyContinue) {
        & redis-cli shutdown 2>&1 | Out-Null
        Write-ColoredMessage "✓ Redis gestopt" "Green"
    } else {
        Write-Host "  Redis draait niet"
    }
} catch {
    Write-Host "  Redis draait niet"
}

# Stop any remaining background jobs
Get-Job | Stop-Job -PassThru | Remove-Job -Force

Write-Host ""
Write-ColoredMessage "╔════════════════════════════════════════╗" "Green"
Write-ColoredMessage "║  ✅ Alle services gestopt!             ║" "Green"
Write-ColoredMessage "╚════════════════════════════════════════╝" "Green"
