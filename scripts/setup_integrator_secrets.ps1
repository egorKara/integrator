param(
    [string]$Repo = "egorKara/integrator",
    [string]$ChatId = "",
    [switch]$RotateGithubToken,
    [switch]$RotateTelegramToken,
    [switch]$Json
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Convert-SecureToText {
    param([Parameter(Mandatory = $true)][System.Security.SecureString]$Secure)
    $Ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($Secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Ptr)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Ptr)
    }
}

function Resolve-OrPrompt {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string]$Provided = "",
        [switch]$Secret,
        [switch]$Rotate
    )
    $value = ([string]$Provided).Trim()
    if (-not $value -and -not $Rotate) {
        $value = ([string][Environment]::GetEnvironmentVariable($Name, "User")).Trim()
    }
    if (-not $value) {
        if ($Secret) {
            $secure = Read-Host -AsSecureString "Введите $Name"
            $value = Convert-SecureToText -Secure $secure
        } else {
            $value = (Read-Host "Введите $Name").Trim()
        }
    }
    if (-not $value) {
        throw "missing_$Name"
    }
    return $value
}

function Resolve-GitHubToken {
    param(
        [string]$TokenFile,
        [switch]$Rotate
    )
    if (-not $Rotate -and (Test-Path -LiteralPath $TokenFile)) {
        $fileValue = (Get-Content -LiteralPath $TokenFile -Raw -Encoding UTF8).Trim()
        if ($fileValue) {
            return $fileValue
        }
    }
    return (Resolve-OrPrompt -Name "GITHUB_TOKEN" -Secret -Rotate:$Rotate)
}

function Test-GitHubToken {
    param([Parameter(Mandatory = $true)][string]$Token)
    $previous = [Environment]::GetEnvironmentVariable("INTEGRATOR_TMP_GH_TOKEN", "Process")
    [Environment]::SetEnvironmentVariable("INTEGRATOR_TMP_GH_TOKEN", $Token, "Process")
    try {
        $script = "import os; from github_api import github_api_request; t=os.environ.get('INTEGRATOR_TMP_GH_TOKEN') or ''; r=github_api_request('GET','https://api.github.com/user',token=t); raise SystemExit(0 if r.ok else 1)"
        & python -c $script | Out-Null
        return ($LASTEXITCODE -eq 0)
    } finally {
        [Environment]::SetEnvironmentVariable("INTEGRATOR_TMP_GH_TOKEN", $previous, "Process")
    }
}

function Test-TelegramToken {
    param([Parameter(Mandatory = $true)][string]$Token)
    $previous = [Environment]::GetEnvironmentVariable("INTEGRATOR_TMP_TG_TOKEN", "Process")
    [Environment]::SetEnvironmentVariable("INTEGRATOR_TMP_TG_TOKEN", $Token, "Process")
    try {
        $script = "import json, os, urllib.request; t=os.environ.get('INTEGRATOR_TMP_TG_TOKEN') or ''; u=f'https://api.telegram.org/bot{t}/getMe'; req=urllib.request.Request(u,method='GET'); out=json.loads(urllib.request.urlopen(req,timeout=20).read().decode('utf-8','replace')); raise SystemExit(0 if bool(out.get('ok')) else 1)"
        & python -c $script | Out-Null
        return ($LASTEXITCODE -eq 0)
    } finally {
        [Environment]::SetEnvironmentVariable("INTEGRATOR_TMP_TG_TOKEN", $previous, "Process")
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$secretsDir = Join-Path $env:USERPROFILE ".integrator\secrets"
$githubTokenFile = Join-Path $secretsDir "github_token.txt"

New-Item -ItemType Directory -Path $secretsDir -Force | Out-Null

$telegramToken = Resolve-OrPrompt -Name "TELEGRAM_BOT_TOKEN" -Secret -Rotate:$RotateTelegramToken
$githubToken = Resolve-GitHubToken -TokenFile $githubTokenFile -Rotate:$RotateGithubToken
$chatIds = Resolve-OrPrompt -Name "TELEGRAM_BRIDGE_ALLOWED_CHAT_IDS" -Provided $ChatId
$repoSlug = Resolve-OrPrompt -Name "TELEGRAM_BRIDGE_REPO" -Provided $Repo

if (-not (Test-TelegramToken -Token $telegramToken)) {
    throw "invalid_TELEGRAM_BOT_TOKEN"
}
if (-not (Test-GitHubToken -Token $githubToken)) {
    throw "invalid_GITHUB_TOKEN"
}

Set-Content -LiteralPath $githubTokenFile -Value $githubToken -Encoding UTF8 -NoNewline

[Environment]::SetEnvironmentVariable("GITHUB_TOKEN_FILE", $githubTokenFile, "User")
[Environment]::SetEnvironmentVariable("INTEGRATOR_GITHUB_TOKEN_FILE", $githubTokenFile, "User")
[Environment]::SetEnvironmentVariable("GITHUB_TOKEN", $null, "User")
[Environment]::SetEnvironmentVariable("GH_TOKEN", $null, "User")
[Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", $telegramToken, "User")
[Environment]::SetEnvironmentVariable("TELEGRAM_BRIDGE_ALLOWED_CHAT_IDS", $chatIds, "User")
[Environment]::SetEnvironmentVariable("TELEGRAM_BRIDGE_REPO", $repoSlug, "User")

[Environment]::SetEnvironmentVariable("GITHUB_TOKEN_FILE", $githubTokenFile, "Process")
[Environment]::SetEnvironmentVariable("INTEGRATOR_GITHUB_TOKEN_FILE", $githubTokenFile, "Process")
[Environment]::SetEnvironmentVariable("GITHUB_TOKEN", $null, "Process")
[Environment]::SetEnvironmentVariable("GH_TOKEN", $null, "Process")
[Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", $telegramToken, "Process")
[Environment]::SetEnvironmentVariable("TELEGRAM_BRIDGE_ALLOWED_CHAT_IDS", $chatIds, "Process")
[Environment]::SetEnvironmentVariable("TELEGRAM_BRIDGE_REPO", $repoSlug, "Process")

Set-Location -Path $repoRoot

if ($Json) {
    $row = @{
        kind = "integrator_secrets_setup"
        status = "pass"
        github_token_file = $githubTokenFile
        repo = $repoSlug
        chat_id = $chatIds
    }
    Write-Output (ConvertTo-Json $row -Compress)
} else {
    Write-Output "secrets_configured"
}
