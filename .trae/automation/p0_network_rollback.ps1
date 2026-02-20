param(
    [string]$BackupPath
)

if (-not $BackupPath) {
    $BackupPath = Get-ChildItem "C:\Users\egork\Documents\trae_projects\integrator\reports\p0_network_backup_*.xml" | Sort-Object LastWriteTime -Descending | Select-Object -First 1 | ForEach-Object { $_.FullName }
}

if (-not $BackupPath -or -not (Test-Path $BackupPath)) {
    Write-Output "Backup not found"
    exit 1
}

$backup = Import-Clixml -Path $BackupPath

$dnsGroups = $backup.Dns | Group-Object InterfaceAlias
foreach ($group in $dnsGroups) {
    $alias = $group.Name
    $servers = @()
    foreach ($item in $group.Group) {
        if ($item.ServerAddresses) {
            $servers += $item.ServerAddresses
        }
    }
    if ($servers.Count -gt 0) {
        Set-DnsClientServerAddress -InterfaceAlias $alias -ServerAddresses $servers -ErrorAction SilentlyContinue
    } else {
        Set-DnsClientServerAddress -InterfaceAlias $alias -ResetServerAddresses -ErrorAction SilentlyContinue
    }
}

foreach ($binding in $backup.IPv6Bindings) {
    if ($binding.Enabled) {
        Enable-NetAdapterBinding -Name $binding.Name -ComponentID ms_tcpip6 -ErrorAction SilentlyContinue
    } else {
        Disable-NetAdapterBinding -Name $binding.Name -ComponentID ms_tcpip6 -ErrorAction SilentlyContinue
    }
}

$rules = @(
    "P0-Block-DNS-UDP-Ethernet",
    "P0-Block-DNS-TCP-Ethernet"
)

foreach ($rule in $rules) {
    Get-NetFirewallRule -DisplayName $rule -ErrorAction SilentlyContinue | Remove-NetFirewallRule -ErrorAction SilentlyContinue
}

Write-Output "Rollback complete"
