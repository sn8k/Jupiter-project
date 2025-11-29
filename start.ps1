# start.ps1 - PowerShell launch script for Jupiter

$ErrorActionPreference = "Stop"

# Get project root
$projectRoot = $args[0]
if (-not $projectRoot) {
    $projectRoot = Get-Location
}

# Create venv if needed
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[Jupiter] Creation du venv..."
    python -m venv .venv
}

# Activate venv (dot-source to affect current session)
. ".\.venv\Scripts\Activate.ps1"

# Install dependencies
if (Test-Path "requirements.txt") {
    Write-Host "[Jupiter] Installation des dependances..."
    pip install -r requirements.txt
}

# Scan
Write-Host "[Jupiter] Scan du dossier cible..."
python -m jupiter.cli.main scan "$projectRoot" --output rapport.json

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERREUR] Le scan a echoue." -ForegroundColor Red
    exit
}

Write-Host "[Jupiter] Rapport genere : rapport.json"

# Launch API
Write-Host "[Jupiter] Lancement de l'API (port 8000)..."
# We use cmd /k to keep the window open and run python
# We assume python is in PATH because of venv activation inheritance
Start-Process -FilePath "cmd.exe" -ArgumentList "/k python -m jupiter.cli.main server `"$projectRoot`" --host 0.0.0.0 --port 8000" -WindowStyle Normal

# Launch GUI
Write-Host "[Jupiter] Lancement de la Web UI (port 8050)..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/k python -m jupiter.cli.main gui `"$projectRoot`" --host 0.0.0.0 --port 8050" -WindowStyle Normal

Write-Host "[Jupiter] Tout est lance."
