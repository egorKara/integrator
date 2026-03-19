param(
  [Parameter(Mandatory = $false)][string]$LocalSocks = "socks5h://127.0.0.1:19080"
)

$ErrorActionPreference = "Stop"

$ts = Get-Date -Format "yyyyMMdd_HHmmss"
$report = "C:\integrator\reports\us_tun_verify_$ts.log"

"START $(Get-Date -Format s)" | Out-File -FilePath $report -Encoding utf8

$directIp = ((curl.exe -sS -m 20 https://api.ipify.org?format=json) | Out-String).Trim()
$socksIp = ((curl.exe -sS -m 20 -x $LocalSocks https://api.ipify.org?format=json) | Out-String).Trim()
$yt = ((curl.exe -sS -o NUL -w "%{http_code}" -m 20 -x $LocalSocks https://www.youtube.com) | Out-String).Trim()
$openai = ((curl.exe -sS -o NUL -w "%{http_code}" -m 20 -x $LocalSocks https://openai.com) | Out-String).Trim()

"DIRECT_IPIFY=$directIp" | Out-File -FilePath $report -Append -Encoding utf8
"SOCKS_IPIFY=$socksIp" | Out-File -FilePath $report -Append -Encoding utf8
"SOCKS_YT=$yt" | Out-File -FilePath $report -Append -Encoding utf8
"SOCKS_OPENAI=$openai" | Out-File -FilePath $report -Append -Encoding utf8
"END $(Get-Date -Format s)" | Out-File -FilePath $report -Append -Encoding utf8
Write-Output $report
