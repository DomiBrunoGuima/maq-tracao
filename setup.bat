@echo off
setlocal EnableDelayedExpansion

echo ============================================
echo  Analisador de Ensaios de Tracao - Setup
echo ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Python nao encontrado. Instale Python 3.11+ de python.org
    pause
    exit /b 1
)
echo [OK] Python encontrado

:: Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERRO] Node.js nao encontrado. Instale Node.js 20+ de nodejs.org
    pause
    exit /b 1
)
echo [OK] Node.js encontrado

echo.
echo [1/4] Criando ambiente virtual Python...
if not exist "venv" (
    python -m venv venv
)

echo [2/4] Instalando dependencias Python...
call venv\Scripts\activate.bat
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias Python
    pause
    exit /b 1
)
echo [OK] Dependencias Python instaladas

echo [3/4] Gerando arquivo de exemplo H0001.csv...
python generate_sample.py
echo [OK] Dados de exemplo gerados em data\H0001.csv

echo [4/4] Instalando dependencias do frontend...
cd frontend
call npm install --silent
if errorlevel 1 (
    echo [ERRO] Falha ao instalar dependencias Node.js
    cd ..
    pause
    exit /b 1
)
cd ..
echo [OK] Dependencias frontend instaladas

echo.
echo ============================================
echo  Setup concluido com sucesso!
echo  Execute: start.bat para iniciar o software
echo ============================================
pause
