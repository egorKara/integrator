param(
  [Parameter(Mandatory = $false)][switch]$AutoElevate
)

$ErrorActionPreference = "Stop"

$adapterName = "Ethernet"
$reportPath = "C:\integrator\reports\nic_stability_hardening_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
$bootstrapLog = "C:\integrator\reports\nic_stability_hardening_uac_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
  "START $(Get-Date -Format s)" | Out-File -FilePath $bootstrapLog -Encoding utf8
  "UAC_RELAUNCH_ATTEMPT=YES" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
  "UAC_USER_INTERACTIVE=$([Environment]::UserInteractive)" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
  "UAC_PROCESS=$PID" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
  "UAC_AUTOELEVATE=$($AutoElevate.IsPresent)" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
  if (-not $AutoElevate.IsPresent) {
    "UAC_RELAUNCH_RESULT=SKIPPED_NO_AUTOELEVATE" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
    "RELAUNCH_BRANCH_EXIT=3" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
    "END $(Get-Date -Format s)" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
    Write-Output "ADMIN_REQUIRED: re-run with -AutoElevate or from elevated PowerShell"
    Write-Output "EXAMPLE: powershell -ExecutionPolicy Bypass -File $PSCommandPath -AutoElevate"
    Write-Output $bootstrapLog
    exit 1
  }
  $argList = @(
    "-ExecutionPolicy", "Bypass",
    "-File", "`"$PSCommandPath`"",
    "-AutoElevate"
  )
  try {
    $proc = Start-Process -FilePath "powershell.exe" -ArgumentList $argList -Verb RunAs -PassThru -ErrorAction Stop
    "UAC_RELAUNCH_RESULT=REQUESTED" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
    "UAC_RELAUNCH_PID=$($proc.Id)" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
    "RELAUNCH_BRANCH_EXIT=0" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
    "END $(Get-Date -Format s)" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
    Write-Output "RELAUNCHED_AS_ADMIN"
    Write-Output $bootstrapLog
    exit 0
  } catch {
    $nativeCode = ""
    if ($_.Exception -is [System.ComponentModel.Win32Exception]) {
      $nativeCode = $_.Exception.NativeErrorCode
    }
    "UAC_RELAUNCH_RESULT=FAILED" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
    "UAC_ERROR_MESSAGE=$($_.Exception.Message)" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
    "UAC_ERROR_HRESULT=$($_.Exception.HResult)" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
    "UAC_ERROR_NATIVE=$nativeCode" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
    "RELAUNCH_BRANCH_EXIT=2" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
    "END $(Get-Date -Format s)" | Out-File -FilePath $bootstrapLog -Append -Encoding utf8
    throw
  }
}

"START $(Get-Date -Format s)" | Out-File -FilePath $reportPath -Encoding utf8
Get-NetAdapter -Name $adapterName | Format-List Name,InterfaceDescription,Status,LinkSpeed,DriverInformation | Out-File -FilePath $reportPath -Append -Encoding utf8
Get-NetAdapterAdvancedProperty -Name $adapterName | Sort-Object DisplayName | Format-Table DisplayName,RegistryKeyword,DisplayValue -AutoSize | Out-File -FilePath $reportPath -Append -Encoding utf8

$keywordTargets = @(
  "*EEE",
  "EnableGreenEthernet",
  "GigaLite",
  "PowerSavingMode",
  "AutoDisableGigabit"
)

foreach ($kw in $keywordTargets) {
  try {
    Set-NetAdapterAdvancedProperty -Name $adapterName -RegistryKeyword $kw -RegistryValue 0 -NoRestart | Out-Null
    "SET OK: $kw -> 0" | Out-File -FilePath $reportPath -Append -Encoding utf8
  } catch {
    "SET SKIP: $kw :: $($_.Exception.Message)" | Out-File -FilePath $reportPath -Append -Encoding utf8
  }
}

Restart-NetAdapter -Name $adapterName -Confirm:$false
ipconfig /flushdns | Out-Null
netsh winsock reset | Out-Null

Start-Sleep -Seconds 3
Get-NetAdapter -Name $adapterName | Format-List Name,Status,LinkSpeed,DriverInformation | Out-File -FilePath $reportPath -Append -Encoding utf8
Get-NetAdapterAdvancedProperty -Name $adapterName | Sort-Object DisplayName | Format-Table DisplayName,RegistryKeyword,DisplayValue -AutoSize | Out-File -FilePath $reportPath -Append -Encoding utf8
Test-NetConnection 192.168.31.124 -Port 22 | Select-Object ComputerName,RemotePort,TcpTestSucceeded | Out-File -FilePath $reportPath -Append -Encoding utf8

$after = Get-NetAdapterAdvancedProperty -Name $adapterName
foreach ($kw in $keywordTargets) {
  $row = $after | Where-Object { $_.RegistryKeyword -eq $kw } | Select-Object -First 1
  if ($null -eq $row) {
    "VERIFY SKIP: $kw not found" | Out-File -FilePath $reportPath -Append -Encoding utf8
  } else {
    "VERIFY: $kw = $($row.DisplayValue)" | Out-File -FilePath $reportPath -Append -Encoding utf8
  }
}

"END $(Get-Date -Format s)" | Out-File -FilePath $reportPath -Append -Encoding utf8
Write-Output $reportPath
