# Build script for Jupiter Windows Executable
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Set-Location $ProjectRoot

Write-Host "Building Jupiter Executable..."

# Ensure PyInstaller is installed
if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Host "PyInstaller not found. Installing..."
    pip install pyinstaller
}

# Clean previous builds
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

# Build command
# We need to include jupiter/web as data
# Entry point is jupiter/cli/main.py

$sep = [IO.Path]::PathSeparator
$data_arg = "--add-data 'jupiter/web;jupiter/web'"
if ($IsWindows) {
    $data_arg = "--add-data ""jupiter/web;jupiter/web"""
}

Write-Host "Running PyInstaller..."
python -m PyInstaller --noconfirm --onefile --console --name "jupiter" `
    --add-data "jupiter/web;jupiter/web" `
    --hidden-import "uvicorn.logging" `
    --hidden-import "uvicorn.loops" `
    --hidden-import "uvicorn.loops.auto" `
    --hidden-import "uvicorn.protocols" `
    --hidden-import "uvicorn.protocols.http" `
    --hidden-import "uvicorn.protocols.http.auto" `
    --hidden-import "uvicorn.lifespan" `
    --hidden-import "uvicorn.lifespan.on" `
    "jupiter/cli/main.py"

if (Test-Path "dist/jupiter.exe") {
    Write-Host "Build successful! Executable is in dist/jupiter.exe"
} else {
    Write-Error "Build failed."
}
