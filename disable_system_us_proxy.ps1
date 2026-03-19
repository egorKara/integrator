$ErrorActionPreference = "Stop"

function Stop-AllBridgeProcesses {
  $pids = @()
  $procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -match 'us_socks_bridge.py' }
  foreach ($p in $procs) {
    $pids += [int]$p.ProcessId
    Stop-Process -Id ([int]$p.ProcessId) -Force -ErrorAction SilentlyContinue
  }
  return $pids
}

function Refresh-WinInet {
  if (-not ("WinInet.Native" -as [type])) {
    Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
namespace WinInet {
  public class Native {
    [DllImport("wininet.dll", SetLastError = true)]
    public static extern bool InternetSetOption(IntPtr hInternet, int dwOption, IntPtr lpBuffer, int dwBufferLength);
  }
}
"@
  }
  [WinInet.Native]::InternetSetOption([IntPtr]::Zero, 37, [IntPtr]::Zero, 0) | Out-Null
  [WinInet.Native]::InternetSetOption([IntPtr]::Zero, 39, [IntPtr]::Zero, 0) | Out-Null
}

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$report = "C:\integrator\reports\system_us_proxy_disable_$ts.log"
$stateFile = "C:\integrator\reports\system_us_proxy_state.json"
$runtimeCfg = "C:\integrator\reports\system_us_proxy_runtime.json"
$regPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings"
$runRegPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$runName = "IntegratorUSProxyBridge"

"START $(Get-Date -Format s)" | Out-File -FilePath $report -Encoding utf8

$killed = Stop-AllBridgeProcesses
if (@($killed).Count -gt 0) {
  "BRIDGE_STOP=$(@($killed) -join ',')" | Out-File -FilePath $report -Append -Encoding utf8
}

if (Test-Path $stateFile) {
  $old = Get-Content $stateFile -Raw | ConvertFrom-Json
  $oldProxyServer = [string]$old.ProxyServer
  $oldHttp = [string]$old.HTTP_PROXY
  $oldHttps = [string]$old.HTTPS_PROXY
  $oldAll = [string]$old.ALL_PROXY
  $restoreDirect = $false
  if ($oldProxyServer -match "127\.0\.0\.1:19080") { $restoreDirect = $true }
  if ($oldHttp -like "socks5://127.0.0.1:*") { $restoreDirect = $true }
  if ($oldHttps -like "socks5://127.0.0.1:*") { $restoreDirect = $true }
  if ($oldAll -like "socks5://127.0.0.1:*") { $restoreDirect = $true }
  if ($restoreDirect) {
    [Environment]::SetEnvironmentVariable("HTTP_PROXY", $null, "User")
    [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $null, "User")
    [Environment]::SetEnvironmentVariable("ALL_PROXY", $null, "User")
    [Environment]::SetEnvironmentVariable("NO_PROXY", $null, "User")
    $env:HTTP_PROXY = $null
    $env:HTTPS_PROXY = $null
    $env:ALL_PROXY = $null
    $env:NO_PROXY = $null
    Set-ItemProperty -Path $regPath -Name ProxyEnable -Value 0 -Type DWord
    Remove-ItemProperty -Path $regPath -Name ProxyServer -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path $regPath -Name ProxyOverride -ErrorAction SilentlyContinue
    Remove-ItemProperty -Path $runRegPath -Name $runName -ErrorAction SilentlyContinue
    "RESTORE_MODE=DIRECT_FALLBACK" | Out-File -FilePath $report -Append -Encoding utf8
  } else {
    [Environment]::SetEnvironmentVariable("HTTP_PROXY", $old.HTTP_PROXY, "User")
    [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $old.HTTPS_PROXY, "User")
    [Environment]::SetEnvironmentVariable("ALL_PROXY", $old.ALL_PROXY, "User")
    [Environment]::SetEnvironmentVariable("NO_PROXY", $old.NO_PROXY, "User")
    $env:HTTP_PROXY = $old.HTTP_PROXY
    $env:HTTPS_PROXY = $old.HTTPS_PROXY
    $env:ALL_PROXY = $old.ALL_PROXY
    $env:NO_PROXY = $old.NO_PROXY
    if ($null -ne $old.ProxyEnable) {
      Set-ItemProperty -Path $regPath -Name ProxyEnable -Value ([int]$old.ProxyEnable) -Type DWord
      if ([int]$old.ProxyEnable -eq 0) {
        Remove-ItemProperty -Path $regPath -Name ProxyServer -ErrorAction SilentlyContinue
        Remove-ItemProperty -Path $regPath -Name ProxyOverride -ErrorAction SilentlyContinue
      }
    }
    if ($null -ne $old.ProxyServer) {
      Set-ItemProperty -Path $regPath -Name ProxyServer -Value ([string]$old.ProxyServer)
    }
    if ($null -ne $old.ProxyOverride) {
      Set-ItemProperty -Path $regPath -Name ProxyOverride -Value ([string]$old.ProxyOverride)
    }
    if ($null -ne $old.RunValue -and [string]::IsNullOrWhiteSpace([string]$old.RunValue) -eq $false) {
      Set-ItemProperty -Path $runRegPath -Name $runName -Value ([string]$old.RunValue)
    } else {
      Remove-ItemProperty -Path $runRegPath -Name $runName -ErrorAction SilentlyContinue
    }
  }
  Remove-Item $stateFile -Force -ErrorAction SilentlyContinue
  "RESTORE_FROM_STATE=YES" | Out-File -FilePath $report -Append -Encoding utf8
} else {
  [Environment]::SetEnvironmentVariable("HTTP_PROXY", $null, "User")
  [Environment]::SetEnvironmentVariable("HTTPS_PROXY", $null, "User")
  [Environment]::SetEnvironmentVariable("ALL_PROXY", $null, "User")
  [Environment]::SetEnvironmentVariable("NO_PROXY", $null, "User")
  $env:HTTP_PROXY = $null
  $env:HTTPS_PROXY = $null
  $env:ALL_PROXY = $null
  $env:NO_PROXY = $null
  Set-ItemProperty -Path $regPath -Name ProxyEnable -Value 0 -Type DWord
  Remove-ItemProperty -Path $runRegPath -Name $runName -ErrorAction SilentlyContinue
  "RESTORE_FROM_STATE=NO_FALLBACK" | Out-File -FilePath $report -Append -Encoding utf8
}

Remove-Item $runtimeCfg -Force -ErrorAction SilentlyContinue

Refresh-WinInet
"END $(Get-Date -Format s)" | Out-File -FilePath $report -Append -Encoding utf8
Write-Output $report
