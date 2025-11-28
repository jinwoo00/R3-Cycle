# Quick Sync Script - Sync files from Windows to Raspberry Pi
# Usage: .\sync_to_pi.ps1 -PiIP "192.168.1.100"

param(
    [Parameter(Mandatory=$true)]
    [string]$PiIP,
    
    [string]$PiUser = "r3cycle",
    [string]$PiPath = "/home/r3cycle/r3cycle"
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "R3-Cycle File Sync to Raspberry Pi" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if raspberry_pi directory exists
if (-not (Test-Path "raspberry_pi")) {
    Write-Host "[ERROR] Please run this script from the R3-Cycle project root directory" -ForegroundColor Red
    exit 1
}

Write-Host "Target: ${PiUser}@${PiIP}:${PiPath}" -ForegroundColor Gray
Write-Host ""

# Test connection first
Write-Host "[1/4] Testing connection..." -ForegroundColor Yellow
try {
    $testResult = ssh -o ConnectTimeout=5 "$PiUser@$PiIP" "echo 'Connection OK'" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Cannot connect to Raspberry Pi. Check:" -ForegroundColor Red
        Write-Host "  - IP address is correct: $PiIP" -ForegroundColor Red
        Write-Host "  - SSH is enabled on Pi" -ForegroundColor Red
        Write-Host "  - Network connectivity" -ForegroundColor Red
        exit 1
    }
    Write-Host "  ✓ Connection successful" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] SSH not available. Install OpenSSH Client:" -ForegroundColor Red
    Write-Host "  Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0" -ForegroundColor Yellow
    exit 1
}

# Create directory on Pi if it doesn't exist
Write-Host ""
Write-Host "[2/4] Creating directory on Pi..." -ForegroundColor Yellow
ssh "$PiUser@$PiIP" "mkdir -p $PiPath" | Out-Null
Write-Host "  ✓ Directory ready" -ForegroundColor Green

# List of files/directories to sync
$filesToSync = @(
    @{Source = "raspberry_pi/main.py"; Dest = "$PiPath/main.py"; Desc = "Main program"},
    @{Source = "raspberry_pi/config.py"; Dest = "$PiPath/config.py"; Desc = "Configuration"},
    @{Source = "raspberry_pi/realtime_client.py"; Dest = "$PiPath/realtime_client.py"; Desc = "Real-time client"},
    @{Source = "raspberry_pi/database.py"; Dest = "$PiPath/database.py"; Desc = "Database module"},
    @{Source = "raspberry_pi/sync.py"; Dest = "$PiPath/sync.py"; Desc = "Sync module"},
    @{Source = "raspberry_pi/setup_db.py"; Dest = "$PiPath/setup_db.py"; Desc = "Database setup"},
    @{Source = "raspberry_pi/r3cycle.service"; Dest = "$PiPath/r3cycle.service"; Desc = "Service file"},
    @{Source = "raspberry_pi/install.sh"; Dest = "$PiPath/install.sh"; Desc = "Install script"},
    @{Source = "raspberry_pi/tests"; Dest = "$PiPath/tests"; Desc = "Test scripts"},
    @{Source = "raspberry_pi/setup.sh"; Dest = "$PiPath/setup.sh"; Desc = "Setup script"}
)

# Sync files
Write-Host ""
Write-Host "[3/4] Syncing files..." -ForegroundColor Yellow

$syncedCount = 0
$skippedCount = 0

foreach ($item in $filesToSync) {
    if (Test-Path $item.Source) {
        try {
            Write-Host "  Syncing: $($item.Desc)..." -ForegroundColor Gray
            
            # Use scp for file transfer
            if (Test-Path $item.Source -PathType Container) {
                # Directory
                scp -r $item.Source/* "$PiUser@$PiIP`:$($item.Dest)/" 2>&1 | Out-Null
            } else {
                # File
                scp $item.Source "$PiUser@$PiIP`:$($item.Dest)" 2>&1 | Out-Null
            }
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ $($item.Desc)" -ForegroundColor Green
                $syncedCount++
            } else {
                Write-Host "    ✗ Failed: $($item.Desc)" -ForegroundColor Red
            }
        } catch {
            Write-Host "    ✗ Error: $($item.Desc) - $_" -ForegroundColor Red
        }
    } else {
        Write-Host "  Skipping: $($item.Desc) (not found)" -ForegroundColor Yellow
        $skippedCount++
    }
}

# Set permissions on Pi
Write-Host ""
Write-Host "[4/4] Setting file permissions..." -ForegroundColor Yellow
ssh "${PiUser}@${PiIP}" "cd ${PiPath}; chmod +x *.py *.sh 2>/dev/null; chmod +x tests/*.py 2>/dev/null; chown -R r3cycle:r3cycle ${PiPath}" | Out-Null
Write-Host "  ✓ Permissions set" -ForegroundColor Green

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Sync Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor Yellow
Write-Host "  Synced:    $syncedCount files" -ForegroundColor White
Write-Host "  Skipped:   $skippedCount files" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "1. SSH to Pi: ssh $PiUser@$PiIP" -ForegroundColor White
Write-Host "2. Navigate:  cd $PiPath" -ForegroundColor White
Write-Host "3. Test:      python3 tests/test_api.py" -ForegroundColor White
Write-Host "4. Run:       sudo python3 main.py" -ForegroundColor White
Write-Host ""
