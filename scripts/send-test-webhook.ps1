[CmdletBinding()]
param(
    [string] $WebhookUrl = $(
        if ($env:WEBHOOK_URL) {
            $env:WEBHOOK_URL
        }
        else {
            "http://localhost:8123/api/webhook/e_redes_smart_metering_plus"
        }
    ),
    [string] $TestCpe = $(
        if ($env:TEST_CPE) {
            $env:TEST_CPE
        }
        else {
            "PT000000000000000000"
        }
    )
)

$ErrorActionPreference = "Stop"
$sourceTimestamp = [DateTime]::UtcNow.ToString("yyyy-MM-dd HH:mm:ss")

$payload = @{
    cpe                                  = $TestCpe
    SourceTimestamp                      = $sourceTimestamp
    activeEnergyExport                   = 0
    activeEnergyImport                   = 14817930
    instantaneousActivePowerExport       = 0
    instantaneousActivePowerImport       = 2518
    maxActivePowerExport                 = 0
    maxActivePowerExportTime             = "0000-00-00 00:00:00"
    maxActivePowerImportTotalLastAverage = 3680
    maxActivePowerImportTotalTime        = "2025-09-09 11:45:00"
    voltageL1                            = 237.1
    clock                                = "2025-09-24 19:33:20"
} | ConvertTo-Json

Invoke-RestMethod `
    -Method Post `
    -Uri $WebhookUrl `
    -ContentType "application/json" `
    -Body $payload | Out-Null

Write-Host "Test webhook sent to $WebhookUrl"
