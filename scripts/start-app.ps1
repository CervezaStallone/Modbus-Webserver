# Modbus Webserver - Start Everything Including App (PowerShell)

# Error handling
$ErrorActionPreference = "Continue"

# Function to Write-ColoredMessage
function Write-ColoredMessage {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

# Function to wait for process to start
function Wait-ProcessStart {
    param(
        [string]$ProcessName,
        [int]$Timeout = 5
    )
    $elapsed = 0
    while ($elapsed -lt $Timeout) {
        if (Get-Process -Name $ProcessName -ErrorAction SilentlyContinue) {
            return $true
        }
        Start-Sleep -Seconds 1
        $elapsed++
    }
    return $false
}

# Global variables for PIDs
$script:DjangoPID = $null
$script:CeleryWorkerPID = $null
$script:CeleryBeatPID = $null

# Cleanup function
function Stop-Services {
    param([string]$StopRedis = "no")
    
    Write-Host ""
    Write-ColoredMessage "╔════════════════════════════════════════╗" "Yellow"
    Write-ColoredMessage "║     App gestopt met Ctrl+C             ║" "Yellow"
    Write-ColoredMessage "╚════════════════════════════════════════╝" "Yellow"
    Write-Host ""
    
    if ($StopRedis -eq "ask") {
        Write-ColoredMessage "Wat wil je doen?" "Cyan"
        Write-Host "  1) Stop alleen de app (Redis blijft draaien)"
        Write-Host "  2) Stop alles (inclusief Redis)"
        Write-Host ""
        $choice = Read-Host "Kies een optie (1/2)"
    } else {
        $choice = "2"
    }
    
    Write-Host ""
    Write-ColoredMessage "⏳ Stoppen..." "Yellow"
    
    # Stop Celery Worker using saved PID
    if ($script:CeleryWorkerPID) {
        try {
            $proc = Get-Process -Id $script:CeleryWorkerPID -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $script:CeleryWorkerPID -Force -ErrorAction Stop
                Write-ColoredMessage "✓ Celery Worker gestopt (PID: $script:CeleryWorkerPID)" "Green"
            }
        } catch {
            Write-Host "  Celery Worker al gestopt"
        }
    }
    
    # Stop Celery Beat using saved PID
    if ($script:CeleryBeatPID) {
        try {
            $proc = Get-Process -Id $script:CeleryBeatPID -ErrorAction SilentlyContinue
            if ($proc) {
                Stop-Process -Id $script:CeleryBeatPID -Force -ErrorAction Stop
                Write-ColoredMessage "✓ Celery Beat gestopt (PID: $script:CeleryBeatPID)" "Green"
            }
        } catch {
            Write-Host "  Celery Beat al gestopt"
        }
    }
    
    # Fallback: stop any remaining celery processes
    $celeryProcs = Get-Process -Name python* -ErrorAction SilentlyContinue | Where-Object {
        try {
            $cmdLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
            $cmdLine -like "*celery*"
        } catch {
            $false
        }
    }
    
    if ($celeryProcs) {
        $celeryProcs | Stop-Process -Force -ErrorAction SilentlyContinue
        Write-ColoredMessage "✓ Extra Celery processen gestopt" "Green"
    }
    
    # Django stops automatically when this script exits (foreground process)
    Write-ColoredMessage "✓ Django gestopt" "Green"
    
    # Stop Redis if option 2
    if ($choice -eq "2") {
        try {
            $redisService = Get-Service -Name Redis -ErrorAction SilentlyContinue
            if ($redisService -and $redisService.Status -eq 'Running') {
                Stop-Service -Name Redis -Force
                Write-ColoredMessage "✓ Redis service gestopt" "Green"
            } elseif (Get-Process -Name redis-server -ErrorAction SilentlyContinue) {
                & redis-cli shutdown 2>&1 | Out-Null
                Write-ColoredMessage "✓ Redis gestopt" "Green"
            } else {
                Write-Host "  Redis niet actief"
            }
        } catch {
            Write-Host "  Redis niet actief"
        }
    }
    
    Write-Host ""
    Write-ColoredMessage "Klaar!" "Green"
}

Write-Host "🚀 Starting Modbus Webserver - Alles inclusief app..."
Write-Host ""

# Activate virtual environment if it exists
if (Test-Path ".venv\Scripts\Activate.ps1") {
    Write-ColoredMessage "⚙️  Virtual environment activeren..." "Yellow"
    & .\.venv\Scripts\Activate.ps1
    Write-ColoredMessage "✓ Virtual environment geactiveerd" "Green"
} elseif (Test-Path "venv\Scripts\Activate.ps1") {
    Write-ColoredMessage "⚙️  Virtual environment activeren..." "Yellow"
    & .\venv\Scripts\Activate.ps1
    Write-ColoredMessage "✓ Virtual environment geactiveerd" "Green"
}

# Detect Python command
$PythonCmd = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCmd = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PythonCmd = "python3"
} else {
    Write-ColoredMessage "❌ Python niet gevonden!" "Red"
    exit 1
}

# Load environment variables from .env.local or .env
if (Test-Path ".env.local") {
    Write-ColoredMessage "⚙️  Gebruik .env.local voor lokale ontwikkeling" "Yellow"
    Get-Content .env.local | Where-Object { $_ -notmatch '^#' -and $_ -match '\S' } | ForEach-Object {
        $parts = $_ -split '=', 2
        if ($parts.Length -eq 2) {
            [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
        }
    }
} elseif (Test-Path ".env") {
    Get-Content .env | Where-Object { $_ -notmatch '^#' -and $_ -match '\S' } | ForEach-Object {
        $parts = $_ -split '=', 2
        if ($parts.Length -eq 2) {
            [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim(), "Process")
        }
    }
}

# Check if Redis is running (process or service)
$redisProcess = Get-Process -Name redis-server -ErrorAction SilentlyContinue
$redisService = Get-Service -Name Redis -ErrorAction SilentlyContinue
$redisCommand = Get-Command redis-server -ErrorAction SilentlyContinue

# Check if Redis is already running
if ($redisProcess) {
    Write-ColoredMessage "✓ Redis draait al (proces)" "Green"
} elseif ($redisService -and $redisService.Status -eq 'Running') {
    Write-ColoredMessage "✓ Redis service draait al" "Green"
} else {
    # Redis is not running, try to start it
    if (-not $redisService -and -not $redisCommand) {
        Write-ColoredMessage "❌ Redis is niet geïnstalleerd!" "Red"
        Write-Host "Installeer Redis eerst:"
        Write-Host "  Windows: Download van https://redis.io/download"
        Write-Host "  Of gebruik WSL/Docker voor Redis"
        exit 1
    }
    
    # Try to start Redis
    if ($redisService) {
        # Start as Windows Service
        Write-ColoredMessage "⚙️  Redis service starten..." "Yellow"
        Start-Service -Name Redis
        Start-Sleep -Seconds 2
        $redisService = Get-Service -Name Redis -ErrorAction SilentlyContinue
        if ($redisService.Status -eq 'Running') {
            Write-ColoredMessage "✓ Redis service gestart" "Green"
        } else {
            Write-ColoredMessage "❌ Redis service starten mislukt" "Red"
            exit 1
        }
    } elseif ($redisCommand) {
        # Start as standalone process
        Write-ColoredMessage "⚙️  Redis starten..." "Yellow"
        Start-Process -FilePath "redis-server" -ArgumentList "--port 6379" -WindowStyle Hidden
        Start-Sleep -Seconds 2
        if (Get-Process -Name redis-server -ErrorAction SilentlyContinue) {
            Write-ColoredMessage "✓ Redis gestart" "Green"
        } else {
            Write-ColoredMessage "❌ Redis starten mislukt" "Red"
            exit 1
        }
    }
}

# Check and download static files if missing
Write-ColoredMessage "⚙️  Static files controleren..." "Yellow"

$missingFiles = $false

# Check Bootstrap CSS
if (-not (Test-Path "static\css\bootstrap.min.css")) {
    Write-ColoredMessage "  → Bootstrap CSS niet gevonden, downloaden..." "Yellow"
    try {
        Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" -OutFile "static\css\bootstrap.min.css" -ErrorAction Stop
        Write-ColoredMessage "    ✓ Bootstrap CSS gedownload" "Green"
    } catch {
        Write-ColoredMessage "    ✗ Bootstrap CSS download mislukt" "Red"
        $missingFiles = $true
    }
}

# Check Bootstrap JS
if (-not (Test-Path "static\js\bootstrap.bundle.min.js")) {
    Write-ColoredMessage "  → Bootstrap JS niet gevonden, downloaden..." "Yellow"
    try {
        Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js" -OutFile "static\js\bootstrap.bundle.min.js" -ErrorAction Stop
        Write-ColoredMessage "    ✓ Bootstrap JS gedownload" "Green"
    } catch {
        Write-ColoredMessage "    ✗ Bootstrap JS download mislukt" "Red"
        $missingFiles = $true
    }
}

# Check Chart.js
if (-not (Test-Path "static\js\chart.min.js")) {
    Write-ColoredMessage "  → Chart.js niet gevonden, downloaden..." "Yellow"
    try {
        Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js" -OutFile "static\js\chart.min.js" -ErrorAction Stop
        Write-ColoredMessage "    ✓ Chart.js gedownload" "Green"
    } catch {
        Write-ColoredMessage "    ✗ Chart.js download mislukt" "Red"
        $missingFiles = $true
    }
}

# Check Bootstrap Icons CSS
if (-not (Test-Path "static\css\bootstrap-icons.min.css")) {
    Write-ColoredMessage "  → Bootstrap Icons CSS niet gevonden, downloaden..." "Yellow"
    try {
        Invoke-WebRequest -Uri "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" -OutFile "static\css\bootstrap-icons.min.css" -ErrorAction Stop
        Write-ColoredMessage "    ✓ Bootstrap Icons CSS gedownload" "Green"
    } catch {
        Write-ColoredMessage "    ✗ Bootstrap Icons CSS download mislukt" "Red"
        $missingFiles = $true
    }
}

# Check Bootstrap Icons fonts
if (-not (Test-Path "static\css\fonts") -or ((Get-ChildItem "static\css\fonts" -ErrorAction SilentlyContinue).Count -eq 0)) {
    Write-ColoredMessage "  → Bootstrap Icons fonts niet gevonden, downloaden..." "Yellow"
    try {
        New-Item -ItemType Directory -Path "static\css\fonts" -Force | Out-Null
        $tempZip = "$env:TEMP\bootstrap-icons-fonts.zip"
        Invoke-WebRequest -Uri "https://github.com/twbs/icons/releases/download/v1.11.3/bootstrap-icons-1.11.3.zip" -OutFile $tempZip -ErrorAction Stop
        Expand-Archive -Path $tempZip -DestinationPath "$env:TEMP\bootstrap-icons-temp" -Force
        Copy-Item "$env:TEMP\bootstrap-icons-temp\bootstrap-icons-1.11.3\font\fonts\*" "static\css\fonts\" -Force
        Remove-Item $tempZip -Force
        Remove-Item "$env:TEMP\bootstrap-icons-temp" -Recurse -Force
        Write-ColoredMessage "    ✓ Bootstrap Icons fonts gedownload" "Green"
    } catch {
        Write-ColoredMessage "    ✗ Bootstrap Icons fonts download mislukt" "Red"
        $missingFiles = $true
    }
}

if (-not $missingFiles) {
    Write-ColoredMessage "✓ Alle static files aanwezig" "Green"
} else {
    Write-ColoredMessage "⚠ Sommige static files ontbreken (zie boven)" "Yellow"
}

# Check Django
Write-ColoredMessage "⚙️  Django setup controleren..." "Yellow"
& $PythonCmd manage.py check
if ($LASTEXITCODE -eq 0) {
    Write-ColoredMessage "✓ Django check geslaagd" "Green"
} else {
    Write-ColoredMessage "⚠ Django check had waarschuwingen" "Yellow"
}

# Apply migrations
Write-ColoredMessage "⚙️  Database migraties toepassen..." "Yellow"
& $PythonCmd manage.py migrate --noinput
Write-ColoredMessage "✓ Migraties toegepast" "Green"

# Collect static files
Write-ColoredMessage "⚙️  Static files verzamelen..." "Yellow"
& $PythonCmd manage.py collectstatic --noinput --clear 2>&1 | Out-Null
Write-ColoredMessage "✓ Static files verzameld" "Green"

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

Write-Host ""
Write-ColoredMessage "═══════════════════════════════════════" "Green"
Write-ColoredMessage "    Services starten...                " "Green"
Write-ColoredMessage "═══════════════════════════════════════" "Green"
Write-Host ""

# Start Celery Worker in background (with solo pool for Windows)
Write-ColoredMessage "⚙️  Celery Worker starten..." "Yellow"
$workerProcess = Start-Process -FilePath "$PythonCmd" -ArgumentList "-m","celery","-A","modbus_webserver","worker","--pool=solo","-l","info" -WindowStyle Minimized -PassThru

Start-Sleep -Seconds 3
if ($workerProcess -and !$workerProcess.HasExited) {
    $script:CeleryWorkerPID = $workerProcess.Id
    Write-ColoredMessage "✓ Celery Worker gestart (PID: $($workerProcess.Id))" "Green"
} else {
    Write-ColoredMessage "⚠ Celery Worker niet gestart (optioneel)" "Yellow"
}

# Start Celery Beat in background (with database scheduler)
Write-ColoredMessage "⚙️  Celery Beat starten..." "Yellow"
$beatProcess = Start-Process -FilePath "$PythonCmd" -ArgumentList "-m","celery","-A","modbus_webserver","beat","-l","info","--scheduler","django_celery_beat.schedulers:DatabaseScheduler" -WindowStyle Minimized -PassThru

Start-Sleep -Seconds 3
if ($beatProcess -and !$beatProcess.HasExited) {
    $script:CeleryBeatPID = $beatProcess.Id
    Write-ColoredMessage "✓ Celery Beat gestart (PID: $($beatProcess.Id))" "Green"
} else {
    Write-ColoredMessage "⚠ Celery Beat niet gestart (optioneel)" "Yellow"
}

# Start Django
Write-ColoredMessage "⚙️  Django development server starten..." "Yellow"
Start-Sleep -Seconds 1

Write-Host ""
Write-ColoredMessage "╔════════════════════════════════════════╗" "Green"
Write-ColoredMessage "║  🎉 Alle services draaien!             ║" "Green"
Write-ColoredMessage "╚════════════════════════════════════════╝" "Green"
Write-Host ""
Write-ColoredMessage "Applicatie beschikbaar op:" "Green"
Write-ColoredMessage "  http://localhost:8000/" "Cyan"
Write-Host ""
Write-ColoredMessage "Logs:" "Yellow"
Write-Host "  Celery Worker: logs\celery-worker.log"
Write-Host "  Celery Beat:   logs\celery-beat.log"
Write-Host ""
Write-ColoredMessage "Press Ctrl+C to stop..." "Red"
Write-Host ""

# Start Django in foreground
try {
    & $PythonCmd manage.py runserver
} finally {
    Stop-Services -StopRedis 'ask'
}
