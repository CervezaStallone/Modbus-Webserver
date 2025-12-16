# Start Celery Worker and Beat for Modbus Webserver

# Function to Write-ColoredMessage
function Write-ColoredMessage {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

Write-Host "🚀 Starting Celery Services..."
Write-Host ""

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    & .\venv\Scripts\Activate.ps1
    Write-ColoredMessage "✓ Virtual environment activated" "Green"
} elseif (Test-Path ".venv\Scripts\Activate.ps1") {
    & .\.venv\Scripts\Activate.ps1
    Write-ColoredMessage "✓ Virtual environment activated" "Green"
}

Write-Host ""

# Start Worker in new window
Write-ColoredMessage "⚙️  Starting Celery Worker..." "Yellow"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$PWD'; if (Test-Path 'venv\Scripts\Activate.ps1') { .\venv\Scripts\Activate.ps1 }; python -m celery -A modbus_webserver worker --pool=solo -l info"
)
Write-ColoredMessage "✓ Celery Worker started in new window" "Green"

Start-Sleep -Seconds 2

# Start Beat in new window
Write-ColoredMessage "⚙️  Starting Celery Beat..." "Yellow"
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$PWD'; if (Test-Path 'venv\Scripts\Activate.ps1') { .\venv\Scripts\Activate.ps1 }; python -m celery -A modbus_webserver beat -l info"
)
Write-ColoredMessage "✓ Celery Beat started in new window" "Green"

Write-Host ""
Write-ColoredMessage "╔════════════════════════════════════════╗" "Green"
Write-ColoredMessage "║  ✅ Celery services started!          ║" "Green"
Write-ColoredMessage "╚════════════════════════════════════════╝" "Green"
Write-Host ""
Write-Host "Worker and Beat are running in separate windows."
Write-Host "Close those windows to stop them."
