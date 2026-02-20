$ErrorActionPreference = "Stop"

$bitlocker = $null
if (Get-Command Get-BitLockerVolume -ErrorAction SilentlyContinue) {
    $bitlocker = Get-BitLockerVolume | Select-Object MountPoint, ProtectionStatus, VolumeStatus
}

$defender = $null
if (Get-Command Get-MpComputerStatus -ErrorAction SilentlyContinue) {
    $defender = Get-MpComputerStatus | Select-Object AMServiceEnabled, AntivirusEnabled, RealTimeProtectionEnabled, NISProtectionEnabled
}

$result = [ordered]@{
    BitLocker = $bitlocker
    Defender = $defender
    Timestamp = (Get-Date).ToString("s")
}

$result | ConvertTo-Json -Depth 4
