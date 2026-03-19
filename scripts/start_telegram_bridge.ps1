param(
    [string]$Token,
    [string]$GithubToken,
    [string]$GithubTokenFile,
    [string]$ChatId,
    [string]$Repo = "egorKara/integrator",
    [switch]$Persist,
    [switch]$ConfigureOnly,
    [switch]$Once,
    [switch]$DryRun,
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

function Resolve-Value {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [string]$Provided,
        [string]$Prompt,
        [switch]$Secret
    )
    $value = ([string]$Provided).Trim()
    if (-not $value) {
        $fromProcess = [Environment]::GetEnvironmentVariable($Name, "Process")
        if ($fromProcess) {
            $value = $fromProcess.Trim()
        }
    }
    if (-not $value) {
        $fromUser = [Environment]::GetEnvironmentVariable($Name, "User")
        if ($fromUser) {
            $value = $fromUser.Trim()
        }
    }
    if (-not $value) {
        if ($Secret) {
            $secure = Read-Host -AsSecureString $Prompt
            $value = Convert-SecureToText -Secure $secure
        } else {
            $value = (Read-Host $Prompt).Trim()
        }
    }
    if (-not $value) {
        throw "missing_$Name"
    }
    return $value
}

function Resolve-GitHubToken {
    param(
        [string]$ProvidedToken,
        [string]$ProvidedTokenFile
    )
    $token = ([string]$ProvidedToken).Trim()
    $tokenFile = ([string]$ProvidedTokenFile).Trim()
    if (-not $tokenFile) {
        $tokenFile = ([string][Environment]::GetEnvironmentVariable("GITHUB_TOKEN_FILE", "Process")).Trim()
    }
    if (-not $tokenFile) {
        $tokenFile = ([string][Environment]::GetEnvironmentVariable("GITHUB_TOKEN_FILE", "User")).Trim()
    }
    if (-not $tokenFile) {
        $tokenFile = ([string][Environment]::GetEnvironmentVariable("INTEGRATOR_GITHUB_TOKEN_FILE", "Process")).Trim()
    }
    if (-not $tokenFile) {
        $tokenFile = ([string][Environment]::GetEnvironmentVariable("INTEGRATOR_GITHUB_TOKEN_FILE", "User")).Trim()
    }
    if (-not $token -and $tokenFile -and (Test-Path -LiteralPath $tokenFile)) {
        $text = (Get-Content -LiteralPath $tokenFile -Raw -Encoding UTF8).Trim()
        if ($text) {
            return @{
                token = $text
                tokenFile = $tokenFile
            }
        }
    }
    if (-not $token) {
        $processToken = [Environment]::GetEnvironmentVariable("GITHUB_TOKEN", "Process")
        if ($processToken) {
            $token = $processToken.Trim()
        }
    }
    if (-not $token) {
        $userToken = [Environment]::GetEnvironmentVariable("GITHUB_TOKEN", "User")
        if ($userToken) {
            $token = $userToken.Trim()
        }
    }
    if (-not $token) {
        $secure = Read-Host -AsSecureString "Введите GitHub Token"
        $token = Convert-SecureToText -Secure $secure
    }
    if (-not $token) {
        throw "missing_GITHUB_TOKEN"
    }
    return @{
        token = $token
        tokenFile = $tokenFile
    }
}

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

$Token = Resolve-Value -Name "TELEGRAM_BOT_TOKEN" -Provided $Token -Prompt "Введите Telegram Bot Token" -Secret
$githubResolved = Resolve-GitHubToken -ProvidedToken $GithubToken -ProvidedTokenFile $GithubTokenFile
$GithubToken = [string]$githubResolved.token
$GithubTokenFile = [string]$githubResolved.tokenFile
$ChatId = Resolve-Value -Name "TELEGRAM_BRIDGE_ALLOWED_CHAT_IDS" -Provided $ChatId -Prompt "Введите chat_id (или список через запятую)"
$Repo = Resolve-Value -Name "TELEGRAM_BRIDGE_REPO" -Provided $Repo -Prompt "Введите repo owner/repo"

[Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", $Token, "Process")
[Environment]::SetEnvironmentVariable("GITHUB_TOKEN", $GithubToken, "Process")
[Environment]::SetEnvironmentVariable("GITHUB_TOKEN_FILE", $GithubTokenFile, "Process")
[Environment]::SetEnvironmentVariable("TELEGRAM_BRIDGE_ALLOWED_CHAT_IDS", $ChatId, "Process")
[Environment]::SetEnvironmentVariable("TELEGRAM_BRIDGE_REPO", $Repo, "Process")

if ($Persist) {
    [Environment]::SetEnvironmentVariable("TELEGRAM_BOT_TOKEN", $Token, "User")
    [Environment]::SetEnvironmentVariable("GITHUB_TOKEN", $GithubToken, "User")
    [Environment]::SetEnvironmentVariable("GITHUB_TOKEN_FILE", $GithubTokenFile, "User")
    [Environment]::SetEnvironmentVariable("TELEGRAM_BRIDGE_ALLOWED_CHAT_IDS", $ChatId, "User")
    [Environment]::SetEnvironmentVariable("TELEGRAM_BRIDGE_REPO", $Repo, "User")
}

Set-Location -Path $RepoRoot

if ($ConfigureOnly) {
    if ($Json) {
        $result = @{
            kind = "telegram_remote_bridge_config"
            status = "pass"
            configured = $true
            persisted = [bool]$Persist
            github_token_file = $GithubTokenFile
            repo = $Repo
            chat_id = $ChatId
        }
        Write-Output (ConvertTo-Json $result -Compress)
    }
    exit 0
}

$Args = @("-m", "tools.telegram_remote_bridge")
if ($Once) {
    $Args += "--once"
}
if ($DryRun) {
    $Args += "--dry-run"
}
if ($Json) {
    $Args += "--json"
}

python @Args
