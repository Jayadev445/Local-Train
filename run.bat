@echo off
echo ===================================================
echo   Train Management Application - Setup and Run
echo ===================================================
echo.

echo [1/2] Installing required dependencies...
pip install -r requirements.txt

echo.
echo [2/2] Starting the Flask Application...
echo.
echo ===================================================
echo   The app will be available at http://localhost:5000
echo   Press CTRL+C to stop the server
echo ===================================================
echo.

python app.py

pause
