@echo off
cd /d "%~dp0"
echo Starting Stock Dashboard...
python launcher.py
if errorlevel 1 (
    echo.
    echo Something went wrong. Make sure you have run:
    echo   pip install -r requirements.txt
    pause
)
