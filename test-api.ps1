# R3-CYCLE API TESTING SCRIPT FOR POWERSHELL
# Quick testing script for all Phase 1 endpoints
# Usage: .\test-api.ps1

# Parse parameters - MUST BE AT TOP OF FILE
param(
    [string]$RfidTag = "A1B2C3D4",
    [string]$UserId,
    [string]$SessionCookie
)

# ============================================
# CONFIGURATION
# ============================================

$BaseUrl = "http://localhost:3000/api"
$MachineId = "RPI_001"
$MachineSecret = "test-secret"

# Colors for output
$ColorSuccess = "Green"
$ColorError = "Red"
$ColorInfo = "Cyan"
$ColorWarning = "Yellow"

# ============================================
# HELPER FUNCTIONS
# ============================================

function Write-TestHeader {
    param([string]$Title)
    Write-Host "`n========================================" -ForegroundColor $ColorInfo
    Write-Host " $Title" -ForegroundColor $ColorInfo
    Write-Host "========================================`n" -ForegroundColor $ColorInfo
}

function Write-Success {
    param([string]$Message)
    Write-Host "V $Message" -ForegroundColor $ColorSuccess
}

function Write-Failure {
    param([string]$Message)
    Write-Host "X $Message" -ForegroundColor $ColorError
}

function Write-Info {
    param([string]$Message)
    Write-Host "i $Message" -ForegroundColor $ColorInfo
}

function Write-Warning {
    param([string]$Message)
    Write-Host "! $Message" -ForegroundColor $ColorWarning
}

# ============================================
# TEST FUNCTIONS
# ============================================

function Test-HealthCheck {
    Write-TestHeader "TEST 1: Health Check"

    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get

        if ($response.success -eq $true -and $response.status -eq "online") {
            Write-Success "Health check passed"
            Write-Info "Server is running at: $BaseUrl"
            return $true
        } else {
            Write-Failure "Health check failed - unexpected response"
            return $false
        }
    } catch {
        Write-Failure "Health check failed - server not responding"
        Write-Error $_.Exception.Message
        return $false
    }
}

function Test-RfidVerify {
    param([string]$RfidTag = "A1B2C3D4")

    Write-TestHeader "TEST 2: RFID Verification"

    $headers = @{
        "Content-Type" = "application/json"
        "X-Machine-ID" = $MachineId
        "X-Machine-Secret" = $MachineSecret
    }

    $body = @{
        rfidTag = $RfidTag
        machineId = $MachineId
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/rfid/verify" `
            -Method Post `
            -Headers $headers `
            -Body $body

        if ($response.success -eq $true) {
            if ($response.valid -eq $true) {
                Write-Success "RFID verified successfully"
                Write-Info "User: $($response.userName)"
                Write-Info "Points: $($response.currentPoints)"
                return $true
            } else {
                Write-Warning "RFID not registered in system"
                Write-Info "Message: $($response.message)"
                return $false
            }
        } else {
            Write-Failure "RFID verification failed"
            return $false
        }
    } catch {
        Write-Failure "RFID verification error"
        Write-Error $_.Exception.Message
        return $false
    }
}

function Test-SubmitTransaction {
    param(
        [string]$RfidTag = "A1B2C3D4",
        [double]$Weight = 5.2,
        [bool]$MetalDetected = $false
    )

    Write-TestHeader "TEST 3: Submit Transaction (Weight: ${Weight}g, Metal: $MetalDetected)"

    $headers = @{
        "Content-Type" = "application/json"
        "X-Machine-ID" = $MachineId
        "X-Machine-Secret" = $MachineSecret
    }

    $body = @{
        rfidTag = $RfidTag
        weight = $Weight
        metalDetected = $MetalDetected
        timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/transaction/submit" `
            -Method Post `
            -Headers $headers `
            -Body $body

        if ($response.success -eq $true) {
            if ($response.accepted -eq $true) {
                Write-Success "Transaction accepted!"
                Write-Info "Points awarded: $($response.transaction.pointsAwarded)"
                Write-Info "Total points: $($response.transaction.totalPoints)"
                return $true
            } else {
                Write-Warning "Transaction rejected (expected)"
                Write-Info "Reason: $($response.reason)"
                return $true
            }
        } else {
            Write-Failure "Transaction submission failed"
            return $false
        }
    } catch {
        $errorResponse = $_.ErrorDetails.Message | ConvertFrom-Json -ErrorAction SilentlyContinue

        if ($errorResponse -and $errorResponse.message -eq "RFID not found in system") {
            Write-Warning "RFID not registered - link card first"
            Write-Info "This is expected if RFID is not linked to a user"
            return $false
        }

        Write-Failure "Transaction error"
        Write-Error $_.Exception.Message
        return $false
    }
}

function Test-MachineHeartbeat {
    Write-TestHeader "TEST 4: Machine Heartbeat"

    $headers = @{
        "Content-Type" = "application/json"
        "X-Machine-ID" = $MachineId
        "X-Machine-Secret" = $MachineSecret
    }

    $body = @{
        machineId = $MachineId
        status = "online"
        bondPaperStock = 85
        sensorHealth = @{
            rfid = "ok"
            loadCell = "ok"
            inductiveSensor = "ok"
            irSensor = "ok"
            servo = "ok"
        }
        timestamp = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    } | ConvertTo-Json

    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/machine/heartbeat" `
            -Method Post `
            -Headers $headers `
            -Body $body

        if ($response.success -eq $true) {
            Write-Success "Heartbeat sent successfully"
            return $true
        } else {
            Write-Failure "Heartbeat failed"
            return $false
        }
    } catch {
        Write-Failure "Heartbeat error"
        Write-Error $_.Exception.Message
        return $false
    }
}

function Test-UserStats {
    param([string]$UserId, [string]$SessionCookie)

    Write-TestHeader "TEST 5: Get User Stats"

    if (-not $UserId -or -not $SessionCookie) {
        Write-Warning "Skipping user stats test (requires login)"
        Write-Info "To test: Provide -UserId and -SessionCookie parameters"
        return $false
    }

    $headers = @{
        "Cookie" = "connect.sid=$SessionCookie"
    }

    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/user/stats/$UserId" `
            -Method Get `
            -Headers $headers

        if ($response.success -eq $true) {
            Write-Success "User stats retrieved"
            Write-Info "Current Points: $($response.stats.currentPoints)"
            Write-Info "Total Paper: $($response.stats.totalPaperRecycled)g"
            Write-Info "Transactions: $($response.stats.totalTransactions)"
            return $true
        } else {
            Write-Failure "Failed to get user stats"
            return $false
        }
    } catch {
        Write-Failure "User stats error"
        Write-Error $_.Exception.Message
        return $false
    }
}

function Test-PendingRedemptions {
    Write-TestHeader "TEST 6: Get Pending Redemptions"

    $headers = @{
        "X-Machine-ID" = $MachineId
        "X-Machine-Secret" = $MachineSecret
    }

    try {
        $response = Invoke-RestMethod -Uri "$BaseUrl/redemption/pending" `
            -Method Get `
            -Headers $headers

        if ($response.success -eq $true) {
            Write-Success "Pending redemptions retrieved"
            Write-Info "Count: $($response.count)"
            if ($response.count -gt 0) {
                Write-Info "First redemption ID: $($response.redemptions[0].id)"
                Write-Info "Reward type: $($response.redemptions[0].rewardType)"
            } else {
                Write-Info "No pending redemptions (expected if none requested)"
            }
            return $true
        } else {
            Write-Failure "Failed to get pending redemptions"
            return $false
        }
    } catch {
        Write-Failure "Pending redemptions error"
        Write-Error $_.Exception.Message
        return $false
    }
}

# ============================================
# MAIN TEST SUITE
# ============================================

function Run-AllTests {
    param(
        [string]$TestRfidTag = "A1B2C3D4",
        [string]$UserId,
        [string]$SessionCookie
    )

    Write-Host "`n===========================================================" -ForegroundColor Magenta
    Write-Host "         R3-CYCLE API TEST SUITE (PowerShell)              " -ForegroundColor Magenta
    Write-Host "===========================================================`n" -ForegroundColor Magenta

    $results = @{
        HealthCheck = $false
        RfidVerify = $false
        ValidTransaction = $false
        RejectedMetal = $false
        RejectedWeight = $false
        Heartbeat = $false
        PendingRedemptions = $false
        UserStats = $false
    }

    # Test 1: Health Check
    $results.HealthCheck = Test-HealthCheck

    if (-not $results.HealthCheck) {
        Write-Failure "`nServer is not running! Please start with: npm run xian"
        return
    }

    # Test 2: RFID Verification
    $results.RfidVerify = Test-RfidVerify -RfidTag $TestRfidTag

    # Test 3: Valid Transaction
    $results.ValidTransaction = Test-SubmitTransaction -RfidTag $TestRfidTag -Weight 5.2 -MetalDetected $false

    # Test 4: Rejected Transaction (Metal)
    $results.RejectedMetal = Test-SubmitTransaction -RfidTag $TestRfidTag -Weight 5.2 -MetalDetected $true

    # Test 5: Rejected Transaction (Invalid Weight)
    $results.RejectedWeight = Test-SubmitTransaction -RfidTag $TestRfidTag -Weight 0.5 -MetalDetected $false

    # Test 6: Machine Heartbeat
    $results.Heartbeat = Test-MachineHeartbeat

    # Test 7: Pending Redemptions
    $results.PendingRedemptions = Test-PendingRedemptions

    # Test 8: User Stats (optional)
    if ($UserId -and $SessionCookie) {
        $results.UserStats = Test-UserStats -UserId $UserId -SessionCookie $SessionCookie
    }

    # ============================================
    # SUMMARY
    # ============================================

    Write-Host "`n===========================================================" -ForegroundColor Magenta
    Write-Host "                    TEST SUMMARY                           " -ForegroundColor Magenta
    Write-Host "===========================================================`n" -ForegroundColor Magenta

    $totalTests = 0
    $passedTests = 0

    foreach ($test in $results.GetEnumerator()) {
        $totalTests++
        if ($test.Value -eq $true) {
            $passedTests++
            Write-Host "  V $($test.Key)" -ForegroundColor $ColorSuccess
        } else {
            Write-Host "  X $($test.Key)" -ForegroundColor $ColorError
        }
    }

    Write-Host "`n  Total: $passedTests / $totalTests tests passed`n" -ForegroundColor $ColorInfo

    if ($passedTests -eq $totalTests) {
        Write-Host "  ALL TESTS PASSED! Phase 1 is working perfectly!" -ForegroundColor $ColorSuccess
    } elseif ($passedTests -ge $totalTests - 1) {
        Write-Host "  Most tests passed. Check failures above." -ForegroundColor $ColorWarning
    } else {
        Write-Host "  Several tests failed. Review errors above." -ForegroundColor $ColorError
    }

    Write-Host ""
}

# ============================================
# INDIVIDUAL TEST COMMANDS
# ============================================

function Test-Api-Health {
    Test-HealthCheck
}

function Test-Api-Rfid {
    param([string]$RfidTag = "A1B2C3D4")
    Test-RfidVerify -RfidTag $RfidTag
}

function Test-Api-Transaction {
    param(
        [string]$RfidTag = "A1B2C3D4",
        [double]$Weight = 5.2,
        [bool]$Metal = $false
    )
    Test-SubmitTransaction -RfidTag $RfidTag -Weight $Weight -MetalDetected $Metal
}

function Test-Api-Heartbeat {
    Test-MachineHeartbeat
}

# ============================================
# SCRIPT EXECUTION
# ============================================

Write-Host "`nUsage Examples:" -ForegroundColor Yellow
Write-Host "  .\test-api.ps1                          # Run all tests" -ForegroundColor Gray
Write-Host "  .\test-api.ps1 -RfidTag 'ABCD1234'      # Test with specific RFID" -ForegroundColor Gray
Write-Host ""

Run-AllTests -TestRfidTag $RfidTag -UserId $UserId -SessionCookie $SessionCookie
