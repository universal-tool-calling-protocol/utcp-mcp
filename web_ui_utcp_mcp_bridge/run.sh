#!/bin/bash

set -e  # Exit on any error

# UTCP-MCP-Bridge Configuration
export PROVIDERS_PATH=./data/providers.json
export HOST=127.0.0.1
export FASTAPI_PORT=8778
export MCP_PROXY_PORT=8777
export MCP_CLIENT_PORT=8776
export MCP_PROXY_PATH=/utcp-proxy
export MCP_CLIENT_PATH=/utcp-client

# Script Configuration
VENV_DIR=".venv"
REQUIREMENTS_FILE="requirements.txt"
MAIN_SCRIPT="src/main.py"

echo "Starting UTCP-MCP-Bridge setup..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    echo "Virtual environment created at $VENV_DIR"
else
    echo "Virtual environment already exists at $VENV_DIR"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements if file exists
if [ -f "$REQUIREMENTS_FILE" ]; then
    echo "Installing requirements from $REQUIREMENTS_FILE..."
    pip install -r "$REQUIREMENTS_FILE"
    echo "Requirements installed successfully"
else
    echo "No $REQUIREMENTS_FILE file found, skipping dependency installation"
fi

# Check if main script exists
if [ ! -f "$MAIN_SCRIPT" ]; then
    echo "Main script $MAIN_SCRIPT not found!"
    exit 1
fi

# Run the application
echo "Running UTCP-MCP-Bridge..."
echo "----------------------------------------"
python "$MAIN_SCRIPT"