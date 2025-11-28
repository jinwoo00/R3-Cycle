# Quick file sync script - Fixed syntax
# Run: .\SYNC_FILES_FIXED.ps1

$piIP = "192.168.85.204"

Write-Host "Syncing files to Raspberry Pi ($piIP)..." -ForegroundColor Yellow

# Sync setup_db.py
Write-Host "Syncing setup_db.py..." -ForegroundColor Gray
scp raspberry_pi/setup_db.py "r3cycle@${piIP}:/home/r3cycle/r3cycle/setup_db.py"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] setup_db.py synced" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Failed to sync setup_db.py" -ForegroundColor Red
}

# Sync main.py
Write-Host "Syncing main.py..." -ForegroundColor Gray
scp raspberry_pi/main.py "r3cycle@${piIP}:/home/r3cycle/r3cycle/main.py"
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] main.py synced" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] Failed to sync main.py" -ForegroundColor Red
}

Write-Host ""
Write-Host "Done! Now go to Raspberry Pi SSH and run:" -ForegroundColor Cyan
Write-Host "  rm -f offline.db" -ForegroundColor White
Write-Host "  python3 setup_db.py" -ForegroundColor White
Write-Host "  sudo python3 main.py" -ForegroundColor White

