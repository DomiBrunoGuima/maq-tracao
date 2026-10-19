@echo off
setlocal
:: Remove a Maquina de Tracao. Mantem config.json, tracao.db e data\ em C:\MaqTracao.
set "DEST=C:\MaqTracao"
set "TASK=MaqTracao"

net session >nul 2>&1 || (echo [ERRO] Execute como administrador. & pause & exit /b 1)

schtasks /end /tn %TASK% >nul 2>&1
schtasks /delete /tn %TASK% /f >nul 2>&1
taskkill /f /im MaqTracao.exe >nul 2>&1
timeout /t 2 /nobreak >nul
if exist "%DEST%\_internal" rmdir /s /q "%DEST%\_internal"
if exist "%DEST%\MaqTracao.exe" del /f /q "%DEST%\MaqTracao.exe"
if exist "%PUBLIC%\Desktop\Maquina de Tracao.url" del /f /q "%PUBLIC%\Desktop\Maquina de Tracao.url"

echo Programa removido. Os dados (config.json, tracao.db, data\, logs\)
echo continuam em %DEST%; apague a pasta manualmente se nao precisar deles.
pause
