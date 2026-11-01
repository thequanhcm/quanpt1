# Production Deployment Script for QUAN AI BRAIN
# Run as Administrator on Windows Server

param(
    [string]$Environment = "production",
    [string]$Version = "v30.0.0",
    [switch]$SkipTests,
    [switch]$SkipBackup,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$StartTime = Get-Date
$LogDir = "C:\quanai\logs\deploy"
$BackupDir = "C:\quanai\backups"

# Create log directory
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Write-Host $LogMessage
    Add-Content -Path "$LogDir\deploy_$(Get-Date -Format 'yyyyMMdd').log" -Value $LogMessage
}

function Test-Administrator {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Start-Deployment {
    Write-Log "========================================"
    Write-Log "Starting QUAN AI BRAIN Deployment"
    Write-Log "Environment: $Environment"
    Write-Log "Version: $Version"
    Write-Log "========================================"
    
    # Check admin rights
    if (-not (Test-Administrator)) {
        Write-Log "ERROR: Must run as Administrator" -Level "ERROR"
        exit 1
    }
    
    try {
        # Step 1: Pre-deployment checks
        Write-Log "Step 1/8: Pre-deployment checks"
        Test-PreRequisites
        
        # Step 2: Backup current version
        if (-not $SkipBackup) {
            Write-Log "Step 2/8: Creating backup"
            Start-Backup
        }
        
        # Step 3: Stop services
        Write-Log "Step 3/8: Stopping services"
        Stop-Services
        
        # Step 4: Pull latest code
        Write-Log "Step 4/8: Pulling latest code"
        Update-Code
        
        # Step 5: Install dependencies
        Write-Log "Step 5/8: Installing dependencies"
        Install-Dependencies
        
        # Step 6: Run migrations
        Write-Log "Step 6/8: Running database migrations"
        Run-Migrations
        
        # Step 7: Run tests (optional)
        if (-not $SkipTests) {
            Write-Log "Step 7/8: Running tests"
            Run-Tests
        }
        
        # Step 8: Start services
        Write-Log "Step 8/8: Starting services"
        Start-Services
        
        # Verify deployment
        Write-Log "Verifying deployment..."
        Test-Deployment
        
        $EndTime = Get-Date
        $Duration = New-TimeSpan -Start $StartTime -End $EndTime
        Write-Log "========================================"
        Write-Log "Deployment completed successfully!"
        Write-Log "Duration: $($Duration.TotalMinutes) minutes"
        Write-Log "========================================"
        
    } catch {
        Write-Log "ERROR: Deployment failed - $_" -Level "ERROR"
        Write-Log "Initiating rollback..." -Level "WARNING"
        Start-Rollback
        exit 1
    }
}

function Test-PreRequisites {
    # Check Python
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not installed or not in PATH"
    }
    Write-Log "Python: $pythonVersion"
    
    # Check Git
    $gitVersion = git --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Git not installed"
    }
    Write-Log "Git: $gitVersion"
    
    # Check Redis
    $redisStatus = Get-Service -Name "Redis" -ErrorAction SilentlyContinue
    if (-not $redisStatus) {
        Write-Log "WARNING: Redis service not found" -Level "WARNING"
    }
    
    # Check PostgreSQL
    $pgStatus = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
    if (-not $pgStatus) {
        Write-Log "WARNING: PostgreSQL service not found" -Level "WARNING"
    }
    
    # Check disk space
    $disk = Get-WmiObject Win32_LogicalDisk -Filter "DeviceID='C:'"
    $FreeGB = [math]::Round($disk.FreeSpace / 1GB, 2)
    if ($FreeGB -lt 10) {
        throw "Insufficient disk space: $FreeGB GB free (need 10 GB)"
    }
    Write-Log "Disk space: $FreeGB GB free"
}

function Start-Backup {
    $BackupTimestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $BackupPath = "$BackupDir\backup_$BackupTimestamp"
    
    New-Item -ItemType Directory -Path $BackupPath -Force | Out-Null
    
    # Backup database
    Write-Log "Backing up database..."
    pg_dump -U quanai quanai | gzip > "$BackupPath\database.sql.gz"
    
    # Backup configuration
    Write-Log "Backing up configuration..."
    Copy-Item -Path ".env" -Destination "$BackupPath\.env" -ErrorAction SilentlyContinue
    Copy-Item -Path "config\*" -Destination "$BackupPath\" -Recurse -ErrorAction SilentlyContinue
    
    # Backup logs
    Write-Log "Backing up logs..."
    Copy-Item -Path "logs\*" -Destination "$BackupPath\logs\" -Recurse -ErrorAction SilentlyContinue
    
    # Create manifest
    @{
        Timestamp = $BackupTimestamp
        Version = (git describe --tags --always)
        Branch = (git branch --show-current)
        Commit = (git rev-parse HEAD)
    } | ConvertTo-Json | Out-File "$BackupPath\manifest.json"
    
    Write-Log "Backup created: $BackupPath"
    Set-Variable -Name "LastBackupPath" -Value $BackupPath -Scope Script
}

function Stop-Services {
    $Services = @("quanai-server", "quanai-responder", "quanai-learning", "quanai-watchdog")
    
    foreach ($Service in $Services) {
        $ServiceObj = Get-Service -Name $Service -ErrorAction SilentlyContinue
        if ($ServiceObj -and $ServiceObj.Status -eq "Running") {
            Write-Log "Stopping $Service..."
            Stop-Service -Name $Service -Force
        }
    }
    
    # Also stop any running Python processes
    Get-Process python -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*quanai*" -or $_.CommandLine -like "*server.py*"
    } | ForEach-Object {
        Write-Log "Stopping process: $($_.Id)"
        Stop-Process -Id $_.Id -Force
    }
    
    Start-Sleep -Seconds 5
}

function Update-Code {
    Write-Log "Fetching latest code..."
    git fetch origin
    
    Write-Log "Checking out branch..."
    git checkout feature/cognitive-state-integration
    
    Write-Log "Pulling latest changes..."
    git pull origin feature/cognitive-state-integration
    
    $CurrentCommit = git rev-parse --short HEAD
    Write-Log "Current commit: $CurrentCommit"
}

function Install-Dependencies {
    Write-Log "Upgrading pip..."
    python -m pip install --upgrade pip
    
    Write-Log "Installing requirements..."
    pip install -r requirements.txt
    
    if (Test-Path "requirements-prod.txt") {
        Write-Log "Installing production requirements..."
        pip install -r requirements-prod.txt
    }
    
    Write-Log "Verifying installations..."
    pip list | Out-File "logs\installed_packages.txt"
}

function Run-Migrations {
    Write-Log "Running database migrations..."
    python tools/run_migrations.py
    
    if ($LASTEXITCODE -ne 0) {
        throw "Database migrations failed"
    }
    
    Write-Log "Migrations completed successfully"
}

function Run-Tests {
    Write-Log "Running smoke tests..."
    pytest tests/smoke_tests/ -v --tb=short
    
    if ($LASTEXITCODE -ne 0) {
        Write-Log "WARNING: Some tests failed" -Level "WARNING"
        $confirm = Read-Host "Continue with deployment? (y/n)"
        if ($confirm -ne 'y') {
            throw "Deployment aborted by user"
        }
    }
    
    Write-Log "Tests completed"
}

function Start-Services {
    Write-Log "Starting services..."
    
    # Start as Windows services if installed
    $Services = @("quanai-server", "quanai-responder", "quanai-learning", "quanai-watchdog")
    
    foreach ($Service in $Services) {
        $ServiceObj = Get-Service -Name $Service -ErrorAction SilentlyContinue
        if ($ServiceObj) {
            Write-Log "Starting $Service..."
            Start-Service -Name $Service
        }
    }
    
    # If not installed as services, start manually
    $ManualServices = @(
        @{Name="server"; Script="tools/server.py"},
        @{Name="responder"; Script="tools/netchat_auto_responder.py"},
        @{Name="learning"; Script="tools/learning_daemon.py"},
        @{Name="watchdog"; Script="tools/watchdog.py"}
    )
    
    foreach ($Svc in $ManualServices) {
        $Process = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
            $_.CommandLine -like "*$($Svc.Script)*"
        }
        
        if (-not $Process) {
            Write-Log "Starting $($Svc.Name)..."
            Start-Process python -ArgumentList ".\.venv\Scripts\$($Svc.Script)" -WindowStyle Hidden
        }
    }
    
    Start-Sleep -Seconds 10
}

function Test-Deployment {
    Write-Log "Running deployment verification..."
    
    $Endpoints = @(
        "http://localhost:8216/api/health",
        "http://localhost:8765/api/health",
        "http://localhost:18036/api/health"
    )
    
    foreach ($Endpoint in $Endpoints) {
        Write-Log "Checking $Endpoint..."
        $Response = Invoke-WebRequest -Uri $Endpoint -TimeoutSec 10 -UseBasicParsing
        if ($Response.StatusCode -ne 200) {
            throw "Health check failed for $Endpoint"
        }
    }
    
    Write-Log "All health checks passed"
    
    # Run verification script
    if (Test-Path "tools\verify_production.py") {
        python tools\verify_production.py
    }
}

function Start-Rollback {
    Write-Log "Starting rollback procedure..." -Level "WARNING"
    
    if (Test-Path $LastBackupPath) {
        Write-Log "Restoring from backup: $LastBackupPath"
        
        # Restore database
        Write-Log "Restoring database..."
        gunzip -c "$LastBackupPath\database.sql.gz" | psql -U quanai quanai
        
        # Restore code
        Write-Log "Restoring code..."
        git reset --hard HEAD~1
        
        # Restart services
        Start-Services
    } else {
        Write-Log "ERROR: No backup found for rollback" -Level "ERROR"
    }
}

# Execute deployment
Start-Deployment