@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo  Analisador de Ensaios de Tracao
echo ============================================
echo.
echo  Backend  -> http://localhost:8000
echo  Frontend -> http://localhost:5173
echo.
echo  Pressione Ctrl+C para encerrar
echo ============================================
echo.

:: Encerra processos antigos na porta 8000 (backend) — sem wmic (removido no Win11)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":8000"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

:: Activate venv and start backend
start "Backend - FastAPI" cmd /k "cd /d %~dp0 && call venv\Scripts\activate.bat && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

:: Wait for backend to initialize
timeout /t 3 /nobreak >nul

:: Start frontend
start "Frontend - Vite" cmd /k "cd frontend && npm run dev"

:: Open browser after a short delay
timeout /t 5 /nobreak >nul
start http://localhost:5173

echo.
echo Ambos os servidores foram iniciados em janelas separadas.
echo Feche as janelas do cmd para encerrar.
pause
