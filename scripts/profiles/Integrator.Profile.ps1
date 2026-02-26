Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$script:IntegratorRepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path

function Set-IntegratorProfile {
    param(
        [ValidateSet("safe", "full", "algotrading")]
        [string]$Name = "full"
    )

    $env:INTEGRATOR_PROFILE = $Name
    $env:INTEGRATOR_ROOT = $script:IntegratorRepoRoot
    $env:VAULT_ROOT = Join-Path $script:IntegratorRepoRoot "vault"
    $env:LOCALAI_ROOT = Join-Path $script:IntegratorRepoRoot "LocalAI"
    $env:ALGOTRADING_ROOT = Join-Path $script:IntegratorRepoRoot "vault\Projects\AlgoTrading"
    $env:TSLAB_EXE = "C:\Program Files\TSLab\TSLab 2.2\TSLab.exe"

    Write-Host "[profile] active=$Name root=$env:INTEGRATOR_ROOT"
}

function Invoke-IntegratorBootstrap {
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

    $scriptPath = Join-Path $script:IntegratorRepoRoot "scripts\bootstrap_integrator.ps1"
    if (-not (Test-Path $scriptPath)) {
        throw "Bootstrap script missing: $scriptPath"
    }

    & $scriptPath -Profile $Profile -WithNetwork:$WithNetwork -InstallPreCommit:$InstallPreCommit -InstallProfile:$InstallProfile -RunChecklist:$RunChecklist -RunQuality:$RunQuality -Quick:$Quick -DryRun:$DryRun
}

Set-Alias iboot Invoke-IntegratorBootstrap
Set-Alias iprofile Set-IntegratorProfile
