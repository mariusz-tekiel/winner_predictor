@echo off
echo ============================================
echo  Winner Predictor - Uruchamianie
echo ============================================

:: Backend
echo [1/2] Uruchamianie backendu (FastAPI)...
start "Backend" cmd /k "cd /d "%~dp0backend" && uvicorn app.main:app --reload --port 8000"

timeout /t 3 >nul

:: Frontend
echo [2/2] Uruchamianie frontendu (React)...
start "Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
echo Docs API: http://localhost:8000/docs
echo.
pause
