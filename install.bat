@echo off
echo ============================================
echo  Winner Predictor - Instalacja
echo ============================================

echo [1/2] Instalacja zależności Python (backend)...
cd /d "%~dp0backend"
pip install -r requirements.txt

echo.
echo [2/2] Instalacja zależności Node.js (frontend)...
cd /d "%~dp0frontend"
npm install

echo.
echo ============================================
echo  Instalacja zakonczona!
echo  Edytuj backend/.env i wpisz swoj klucz API
echo  Nastepnie uruchom start.bat
echo ============================================
pause
