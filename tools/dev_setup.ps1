param(
    [string]$VenvPath = ".venv"
)

if (-not (Test-Path $VenvPath)) {
    python -m venv $VenvPath
}

$python = Join-Path $VenvPath "Scripts\python.exe"

& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
& $python -m pip install -e .
