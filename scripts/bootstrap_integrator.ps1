param(
    [ValidateSet("safe", "full", "algotrading")]
    [string]$Profile = "full",
    [switch]$WithNetwork,
    [switch]$InstallPreCommit,
    [switch]$InstallProfile,
    [switch]$RunChecklist,
    [switch]$RunQuality,
    [switch]$Quick,
    [switch]$DryRun
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Profiles = @{
    safe = @{
        quick = $true
        runQuality = $true
        runChecklist = $true
    }
    full = @{
        quick = $false
        runQuality = $true
        runChecklist = $true
    }
    algotrading = @{
        quick = $false
        runQuality = $true
        runChecklist = $true
    }
}

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][scriptblock]$Action
    )
    Write-Host "[bootstrap] $Name"
    if ($DryRun) {
        Write-Host "[bootstrap] dry-run: skipped"
        return
    }
    & $Action
}

function Ensure-ProfileInstalled {
    $Source = Join-Path $RepoRoot "scripts\profiles\Integrator.Profile.ps1"
    if (-not (Test-Path $Source)) {
        throw "Profile source not found: $Source"
    }

    $ProfileDir = Split-Path -Parent $PROFILE
    if (-not (Test-Path $ProfileDir)) {
        New-Item -ItemType Directory -Path $ProfileDir -Force | Out-Null
    }

    $Target = Join-Path $ProfileDir "Integrator.Profile.ps1"
    Copy-Item -Path $Source -Destination $Target -Force

    $Loader = ". `"$Target`""
    if (-not (Test-Path $PROFILE)) {
        New-Item -ItemType File -Path $PROFILE -Force | Out-Null
    }

    $Current = Get-Content -Path $PROFILE -Raw -ErrorAction SilentlyContinue
    if ($Current -notmatch [regex]::Escape($Loader)) {
        Add-Content -Path $PROFILE -Value "`r`n$Loader`r`n"
    }

    Write-Host "[bootstrap] profile installed: $Target"
}

function Ensure-PreCommit {
    $HasPreCommit = $false
    try {
        python -m pre_commit --version *> $null
        if ($LASTEXITCODE -eq 0) {
            $HasPreCommit = $true
        }
    } catch {
        $HasPreCommit = $false
    }

    if (-not $HasPreCommit) {
        if (-not $WithNetwork) {
            throw "pre-commit is missing. Re-run with -WithNetwork to install dependencies."
        }
        python -m pip install --upgrade pip
        python -m pip install pre-commit
    }

    Set-Location -Path $RepoRoot
    python -m pre_commit install --hook-type pre-commit --hook-type pre-push
    Write-Host "[bootstrap] pre-commit hooks installed"
}

function Run-Checklist {
    param([bool]$UseQuick)

    Set-Location -Path $RepoRoot
    $Args = @("ops_checklist.py", "--json")
    if ($UseQuick) {
        $Args += "--quick"
    }
    python @Args
}

function Run-Quality {
    param([bool]$UseQuick)

    Set-Location -Path $RepoRoot
    python -m ruff check .
    python -m mypy .
    if (-not $UseQuick) {
        python -m unittest discover -s tests -p "test*.py"
    }
}

$Selected = $Profiles[$Profile]
if ($null -eq $Selected) {
    throw "Unknown profile: $Profile"
}

$env:INTEGRATOR_PROFILE = $Profile
$env:INTEGRATOR_ROOT = $RepoRoot
$env:VAULT_ROOT = Join-Path $RepoRoot "vault"
$env:LOCALAI_ROOT = Join-Path $RepoRoot "LocalAI"
$env:ALGOTRADING_ROOT = Join-Path $RepoRoot "vault\Projects\AlgoTrading"
$env:TSLAB_EXE = "C:\Program Files\TSLab\TSLab 2.2\TSLab.exe"

$UseQuick = $Quick.IsPresent -or [bool]$Selected.quick
$UseQuality = $RunQuality.IsPresent -or [bool]$Selected.runQuality
$UseChecklist = $RunChecklist.IsPresent -or [bool]$Selected.runChecklist

Invoke-Step -Name "set env profile=$Profile" -Action {
    Write-Host "[bootstrap] INTEGRATOR_ROOT=$env:INTEGRATOR_ROOT"
    Write-Host "[bootstrap] ALGOTRADING_ROOT=$env:ALGOTRADING_ROOT"
}

if ($InstallPreCommit) {
    Invoke-Step -Name "install pre-commit" -Action { Ensure-PreCommit }
}

if ($InstallProfile) {
    Invoke-Step -Name "install powershell profile" -Action { Ensure-ProfileInstalled }
}

if ($UseChecklist) {
    Invoke-Step -Name "run ops checklist" -Action { Run-Checklist -UseQuick:$UseQuick }
}

if ($UseQuality) {
    Invoke-Step -Name "run quality gates" -Action { Run-Quality -UseQuick:$UseQuick }
}

Write-Host "[bootstrap] done profile=$Profile quick=$UseQuick quality=$UseQuality checklist=$UseChecklist"