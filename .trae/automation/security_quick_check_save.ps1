$ErrorActionPreference = "Stop"

$repoRoot = (Get-Location).Path
$reports = Join-Path $repoRoot "reports"
if (-not (Test-Path $reports)) {
    New-Item -ItemType Directory -Path $reports | Out-Null
}

$stamp = (Get-Date).ToString("yyyyMMdd_HHmmss")
$outPath = Join-Path $reports ("security_quick_check_{0}.json" -f $stamp)

$bitlocker = [ordered]@{ status = "tool-missing"; data = $null; error = $null }
if (Get-Command Get-BitLockerVolume -ErrorAction SilentlyContinue) {
    try {
        $data = Get-BitLockerVolume | Select-Object MountPoint, ProtectionStatus, VolumeStatus
        $bitlocker.status = "ok"
        $bitlocker.data = $data
    } catch {
        $bitlocker.status = "error"
        $bitlocker.error = $_.Exception.Message
    }
}

$defender = [ordered]@{ status = "tool-missing"; data = $null; error = $null }
if (Get-Command Get-MpComputerStatus -ErrorAction SilentlyContinue) {
    try {
        $data = Get-MpComputerStatus | Select-Object AMServiceEnabled, AntivirusEnabled, RealTimeProtectionEnabled, NISProtectionEnabled
        $defender.status = "ok"
        $defender.data = $data
    } catch {
        $defender.status = "error"
        $defender.error = $_.Exception.Message
    }
}

$result = [ordered]@{
    Timestamp = (Get-Date).ToString("s")
    RepoRoot = $repoRoot
    User = $env:USERNAME
    ComputerName = $env:COMPUTERNAME
    BitLocker = $bitlocker
    Defender = $defender
}

$json = $result | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($outPath, $json, [System.Text.Encoding]::UTF8)

Write-Output $outPath
