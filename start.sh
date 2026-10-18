#!/bin/bash
# Robuverse QR Scanner Startup Script for Raspberry Pi 5

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment on Raspberry Pi..."
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

echo "Starting Robuverse QR Scanner on Raspberry Pi..."
python3 server.py
