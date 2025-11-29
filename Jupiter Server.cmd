@echo off
cd /d "%~dp0"
if not exist .venv (
    echo Initializing Jupiter environment...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate
)

echo Starting Jupiter Server...
python -m jupiter.cli.main server
if errorlevel 1 pause
