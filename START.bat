@echo off
echo ================================================
echo   VAULTSTREAM - Local Video Platform
echo ================================================
echo.
echo Installing required libraries...
pip install flask werkzeug
echo.
echo Starting server...
echo.
echo Open your browser and go to:
echo   http://localhost:5000
echo.
echo Press CTRL+C to stop the server.
echo ================================================
python app.py
pause
