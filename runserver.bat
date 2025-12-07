@echo off

echo ==========================================
echo   STARTING AURA PYTHON BRIDGE
echo ==========================================
start "AURA_BRIDGE" cmd /k "venv\Scripts\python.exe aura_bridge.py"

echo.
echo ==========================================
echo   STARTING DJANGO SERVER
echo ==========================================
cmd /k "venv\Scripts\python.exe manage.py runserver"
