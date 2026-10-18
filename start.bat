@echo off
title Robuverse QR Scanner Server
echo ======================================================
echo    STARTING ROBUVERSE QR SCANNER SERVER
echo ======================================================
echo.

IF NOT EXIST ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate
    pip install -r requirements.txt
) ELSE (
    call .venv\Scripts\activate
)

echo Starting server...
python server.py
pause
