<#
.SYNOPSIS
    One-command launcher for Charity Flow on Windows PowerShell.
.DESCRIPTION
    Checks Python, sets up virtualenv, installs requirements, sets up .env,
    verifies MongoDB connection, seeds database, detects free port, and starts server.
#>

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "           Charity Flow - Starting Local Environment      " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$backendDir = Join-Path $PSScriptRoot "charityflow-backend"
if (!(Test-Path $backendDir)) {
    Write-Host "[ERROR] Directory 'charityflow-backend' not found." -ForegroundColor Red
    exit 1
}

# 1. Python Detection
$pythonCmd = $null
$detectedVersion = $null

# Check python.exe first
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    try {
        $v = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $v) {
            $pythonCmd = "python"
            $detectedVersion = $v.Trim()
        }
    } catch {}
}

# If not found, check py launcher
if (-not $pythonCmd -and (Get-Command "py" -ErrorAction SilentlyContinue)) {
    try {
        $v = py -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>$null
        if ($LASTEXITCODE -eq 0 -and $v) {
            $pythonCmd = "py"
            $detectedVersion = $v.Trim()
        }
    } catch {}
}

if (-not $pythonCmd) {
    Write-Host "[ERROR] Python was not detected on this system." -ForegroundColor Red
    Write-Host "Please install Python 3.11 or 3.12 from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host "Ensure 'Add python.exe to PATH' is checked during installation." -ForegroundColor Yellow
    exit 1
}

$vParts = $detectedVersion.Split(".")
$major = [int]$vParts[0]
$minor = [int]$vParts[1]

if ($major -lt 3 -or ($major -eq 3 -and $minor -lt 11)) {
    Write-Host "[ERROR] Detected Python version $detectedVersion. Charity Flow requires Python 3.11+." -ForegroundColor Red
    Write-Host "Please install Python 3.11 or 3.12 from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

if ($minor -ge 14) {
    Write-Host "[i] Detected Python $detectedVersion ($pythonCmd). (Note: Python 3.11 or 3.12 is recommended for pre-compiled wheels)." -ForegroundColor Yellow
} else {
    Write-Host "[OK] Detected compatible Python $detectedVersion ($pythonCmd)" -ForegroundColor Green
}

# 2. Virtual Environment Setup
$venvDir = Join-Path $backendDir "venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvUvicorn = Join-Path $venvDir "Scripts\uvicorn.exe"

if (!(Test-Path $venvPython)) {
    Write-Host "[*] Creating virtual environment in charityflow-backend\venv..." -ForegroundColor Yellow
    $parts = $pythonCmd -split " "
    $exe = $parts[0]
    $argsList = if ($parts.Length -gt 1) { $parts[1..($parts.Length-1)] } else { @() }
    & $exe @argsList -m venv $venvDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
}

# 3. Requirements Installation
Write-Host "[*] Checking and installing dependencies..." -ForegroundColor Yellow
$reqFile = Join-Path $backendDir "requirements.txt"
& $venvPython -m pip install -r $reqFile --quiet
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to install dependencies from requirements.txt." -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Dependencies are up to date." -ForegroundColor Green

# 4. Environment Configuration (.env)
$envFile = Join-Path $backendDir ".env"
$envExample = Join-Path $backendDir ".env.example"

if (!(Test-Path $envFile)) {
    Write-Host "[*] .env file not found. Initializing from .env.example..." -ForegroundColor Yellow
    if (!(Test-Path $envExample)) {
        Write-Host "[ERROR] .env.example not found at $envExample." -ForegroundColor Red
        exit 1
    }
    
    # Generate random 32-byte hex for JWT_SECRET
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    $bytes = New-Object byte[] 32
    $rng.GetBytes($bytes)
    $jwtSecret = ([System.BitConverter]::ToString($bytes)).Replace("-", "").ToLower()

    # Admin Password Setup
    Write-Host ""
    $inputPass = if ($env:SEED_ADMIN_PASSWORD) {
        $env:SEED_ADMIN_PASSWORD
    } else {
        try { Read-Host "Set a seed password for admin@charityflow.org (press Enter to auto-generate)" } catch { "" }
    }
    if ([string]::IsNullOrWhiteSpace($inputPass)) {
        $pBytes = New-Object byte[] 9
        $rng.GetBytes($pBytes)
        $adminPassword = [System.Convert]::ToBase64String($pBytes).Replace("+", "X").Replace("/", "Y").Substring(0, 12) + "@1"
        Write-Host ""
        Write-Host "==========================================================" -ForegroundColor Cyan
        Write-Host " [NOTICE] Auto-generated Admin Password:" -ForegroundColor Yellow
        Write-Host " Email:    admin@charityflow.org" -ForegroundColor White
        Write-Host " Password: $adminPassword" -ForegroundColor Green
        Write-Host " Save this password now! It will NOT be printed again." -ForegroundColor Yellow
        Write-Host "==========================================================" -ForegroundColor Cyan
        Write-Host ""
    } else {
        $adminPassword = $inputPass.Trim()
    }

    $content = Get-Content $envExample -Raw
    $content = $content -replace "JWT_SECRET=.*", "JWT_SECRET=$jwtSecret"
    $content = $content -replace "SEED_ADMIN_PASSWORD=.*", "SEED_ADMIN_PASSWORD=$adminPassword"
    if ($env:MONGO_URI) {
        $content = $content -replace "MONGO_URI=.*", "MONGO_URI=$env:MONGO_URI"
    }
    Set-Content -Path $envFile -Value $content -Encoding UTF8
    Write-Host "[OK] Created charityflow-backend\.env with secure JWT_SECRET and admin password." -ForegroundColor Green
} else {
    Write-Host "[OK] Existing .env file found in charityflow-backend." -ForegroundColor Green
}

# 5. MongoDB Connectivity Check (3-second timeout)
Write-Host "[*] Verifying MongoDB database connection..." -ForegroundColor Yellow

$mongoCheckScript = @"
import sys, os
sys.path.insert(0, r'$backendDir')
try:
    from config import MONGO_URI
    from pymongo import MongoClient
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    client.admin.command('ping')
    print('CONNECTED')
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
"@

$checkResult = & $venvPython -c $mongoCheckScript 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Could not connect to MongoDB!" -ForegroundColor Red
    Write-Host "MongoDB response: $checkResult" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To resolve this:" -ForegroundColor Cyan
    Write-Host " 1. If using local MongoDB: Start the service in Administrator PowerShell:" -ForegroundColor White
    Write-Host "      net start MongoDB" -ForegroundColor Green
    Write-Host " 2. If using MongoDB Atlas: Verify your MONGO_URI in charityflow-backend\.env" -ForegroundColor White
    Write-Host "    and ensure your IP address is whitelisted in Atlas Network Access." -ForegroundColor White
    Write-Host ""
    exit 1
}
Write-Host "[OK] MongoDB is reachable." -ForegroundColor Green

# 6. Database Seeding (Idempotent)
Write-Host "[*] Running idempotent database seed (seed_all)..." -ForegroundColor Yellow
Push-Location $backendDir
try {
    & $venvPython -m seed.seed_all
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[WARN] Database seed returned non-zero code. Continuing startup..." -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}

# 7. Port Detection (Find free port starting at 8000)
$targetPort = 8000
while ($true) {
    $activeConn = Get-NetTCPConnection -LocalPort $targetPort -State Listen -ErrorAction SilentlyContinue
    if ($activeConn) {
        $ownerPid = $activeConn[0].OwningProcess
        $ownerProc = try { (Get-Process -Id $ownerPid -ErrorAction SilentlyContinue).ProcessName } catch { "Unknown" }
        Write-Host "[i] Port $targetPort is occupied by '$ownerProc' (PID: $ownerPid). Checking next port..." -ForegroundColor Yellow
        $targetPort++
    } else {
        break
    }
}

Write-Host "[OK] Selected available port: $targetPort" -ForegroundColor Green

# 8. Start Server and Open Browser
$appUrl = "http://localhost:$targetPort"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "   Charity Flow server starting successfully!             " -ForegroundColor Green
Write-Host "   Application: $appUrl" -ForegroundColor White
Write-Host "   Health Check: $appUrl/health" -ForegroundColor White
Write-Host "   API Docs:     $appUrl/docs" -ForegroundColor White
Write-Host "   Press CTRL+C to stop the server.                       " -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""

if (-not $env:NO_BROWSER) {
    try { Start-Process $appUrl } catch {}
}

Push-Location $backendDir
try {
    $env:PORT = "$targetPort"
    & $venvUvicorn main:app --host 0.0.0.0 --port $targetPort
} finally {
    Pop-Location
}
