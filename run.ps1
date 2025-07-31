<#
.SYNOPSIS
UTCP-MCP-Bridge Setup Script for Windows

.DESCRIPTION
This script sets up and runs the UTCP-MCP-Bridge application in a Windows environment.
It creates a virtual environment, installs dependencies, and launches the application.

.INSTRUCTIONS
1. Save this file as 'run.ps1' (PowerShell script)
2. Open PowerShell as Administrator
3. Set execution policy (one-time only):
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
4. Run the script:
   .\run.ps1

.NOTES
- Requires Python 3.8+ installed and in PATH
#>

# Stop on first error
$ErrorActionPreference = "Stop"

# UTCP-MCP-Bridge Configuration
$env:PROVIDERS_PATH = Join-Path $PSScriptRoot "data/providers.json"
$env:HOST = "0.0.0.0"
$env:FASTAPI_PORT = 8778
$env:MCP_PROXY_PORT = 8777
$env:MCP_CLIENT_PORT = 8776
$env:MCP_PROXY_PATH = "/utcp-proxy"
$env:MCP_CLIENT_PATH = "/utcp-client"

# Script Configuration
$VENV_DIR = ".venv"
$REQUIREMENTS_FILE = "requirements.txt"
$MAIN_SCRIPT = "src/main.py"

Write-Host "Starting UTCP-MCP-Bridge setup..." -ForegroundColor Cyan

# Check Python installation
try {
    $pythonVersion = python --version 2>&1
    if (-not ($pythonVersion -match "Python 3\.(8|9|10|11|12|13).*")) {
        throw "Python 3.8+ not found"
    }
    Write-Host "Found $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "Error: Python 3.8+ is required but not found." -ForegroundColor Red
    Write-Host "Please install Python from https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

# Create virtual environment
if (-not (Test-Path -Path $VENV_DIR)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv $VENV_DIR
    Write-Host "Virtual environment created at $VENV_DIR" -ForegroundColor Green
}
else {
    Write-Host "Virtual environment already exists at $VENV_DIR" -ForegroundColor Yellow
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
. "$VENV_DIR\Scripts\Activate.ps1"

# Upgrade pip
Write-Host "Upgrading pip..." -ForegroundColor Cyan
python -m pip install --upgrade pip

# Install requirements
if (Test-Path -Path $REQUIREMENTS_FILE) {
    Write-Host "Installing requirements from $REQUIREMENTS_FILE..." -ForegroundColor Cyan
    pip install -r $REQUIREMENTS_FILE
    Write-Host "Requirements installed successfully" -ForegroundColor Green
}
else {
    Write-Host "No $REQUIREMENTS_FILE found, skipping dependency installation" -ForegroundColor Yellow
}

# Verify main script exists
if (-not (Test-Path -Path $MAIN_SCRIPT)) {
    Write-Host "Error: Main script $MAIN_SCRIPT not found!" -ForegroundColor Red
    exit 1
}

# Run the application
Write-Host "`nRunning UTCP-MCP-Bridge..." -ForegroundColor Cyan
Write-Host "----------------------------------------" -ForegroundColor Cyan
python $MAIN_SCRIPT