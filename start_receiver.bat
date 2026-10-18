@echo off
title Robuverse Virtual USB Scanner Receiver
echo ======================================================
echo    ROBUVERSE WIRELESS VIRTUAL USB SCANNER
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

python laptop_receiver.py
pause
