@echo off
setlocal ENABLEDELAYEDEXPANSION
cls

rem Se placer dans le dossier du script
cd /d "%~dp0"

rem Récupère le dossier racine passé en argument
set "PROJECT_ROOT=%~1"

if "%PROJECT_ROOT%"=="" (
    echo Aucun dossier specifie.
    set /p "PROJECT_ROOT=Veuillez entrer le chemin du projet a analyser (Entree pour dossier courant) : "
)

if "%PROJECT_ROOT%"=="" (
    set "PROJECT_ROOT=%CD%"
)

echo Cible : !PROJECT_ROOT!

rem Création de l'environnement virtuel si besoin
if not exist ".venv\Scripts\python.exe" (
    echo [Jupiter] Creation du venv...
    python -m venv .venv
)

rem Activation du venv
call ".venv\Scripts\activate.bat"

rem Installation des dependances si requirements.txt existe
if exist "requirements.txt" (
    echo [Jupiter] Installation des dependances...
    pip install -r requirements.txt
)

rem SCAN avant lancement de l’API / GUI
echo [Jupiter] Scan du dossier cible...
python -m jupiter.cli.main scan "%PROJECT_ROOT%" --output rapport.json

if %ERRORLEVEL% NEQ 0 (
    echo [ERREUR] Le scan a echoue. Arret.
    goto :eof
)

echo [Jupiter] Rapport genere : rapport.json

rem Lancement de l'API
echo [Jupiter] Lancement de l'API (port 8000)...
start "Jupiter API" cmd /k "python -m jupiter.cli.main server \"%PROJECT_ROOT%\" --host 0.0.0.0 --port 8000"

rem Lancement de la WebUI
echo [Jupiter] Lancement de la Web UI (port 8050)...
start "Jupiter GUI" cmd /k "python -m jupiter.cli.main gui \"%PROJECT_ROOT%\" --host 0.0.0.0 --port 8050"

echo [Jupiter] Tout est lance. Rapport JSON pret.
endlocal
