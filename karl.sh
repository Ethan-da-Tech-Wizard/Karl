#!/usr/bin/env bash
set -e

# Change directory to the script's location to support running from anywhere
cd "$(dirname "$0")"

echo "=================================================="
echo "⚡ Starting Karl Introspection Environment..."
echo "=================================================="

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment in venv..."
    python3 -m venv venv
    echo "Upgrading pip..."
    venv/bin/pip install --upgrade pip
    echo "Installing required Python dependencies..."
    venv/bin/pip install -r requirements.txt
fi

# Ensure models directory exists
mkdir -p data/models

# Download base model if it doesn't exist
if [ ! -f "data/models/deepseek-r1-1.5b.gguf" ]; then
    echo "Base model not found. Starting automatic download..."
    venv/bin/python download_test_model.py
fi

# Launch the PyQt app
echo "Launching Karl..."
venv/bin/python main.py
