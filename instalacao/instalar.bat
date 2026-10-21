@echo off
setlocal
:: Instala (ou atualiza) a Maquina de Tracao no PC do cliente.
:: Clique com o botao direito > Executar como administrador.
set "DEST=C:\MaqTracao"
set "TASK=MaqTracao"
set "SRC=%~dp0MaqTracao"

net session >nul 2>&1 || (echo [ERRO] Execute como administrador. & pause & exit /b 1)
if not exist "%SRC%\MaqTracao.exe" (echo [ERRO] Pasta MaqTracao nao encontrada ao lado deste script. & pause & exit /b 1)

echo [1/5] Parando versao anterior, se houver...
schtasks /end /tn %TASK% >nul 2>&1
taskkill /f /im MaqTracao.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/5] Copiando arquivos para %DEST%...
:: Troca so o programa. config.json, tracao.db, data\ e logs\ sao mantidos.
if exist "%DEST%" (
  for /d %%D in ("%DEST%\*") do if /i not "%%~nxD"=="data" if /i not "%%~nxD"=="logs" rmdir /s /q "%%D"
  for %%F in ("%DEST%\*") do (echo %%~nxF| findstr /b /i "config.json tracao.db" >nul || del /f /q "%%F")
)
if not exist "%DEST%\data" mkdir "%DEST%\data"
xcopy "%SRC%" "%DEST%\" /e /i /q /y >nul || (echo [ERRO] Falha ao copiar & pause & exit /b 1)

echo [3/5] Restringindo a pasta a Administradores...
:: Usuarios comuns nao abrem C:\MaqTracao; so a pasta data\ fica liberada
:: (para colocar CSVs manualmente, se precisar).
icacls "%DEST%" /inheritance:r /grant:r *S-1-5-32-544:(OI)(CI)F *S-1-5-18:(OI)(CI)F /C /Q >nul
icacls "%DEST%\data" /grant *S-1-5-32-545:(OI)(CI)M /C /Q >nul

echo [4/5] Registrando inicio automatico com o Windows...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$a = New-ScheduledTaskAction -Execute '%DEST%\MaqTracao.exe' -WorkingDirectory '%DEST%';" ^
  "$t = New-ScheduledTaskTrigger -AtStartup;" ^
  "$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1);" ^
  "$p = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest;" ^
  "Register-ScheduledTask -TaskName '%TASK%' -Action $a -Trigger $t -Settings $s -Principal $p -Force | Out-Null" ^
  || (echo [ERRO] Falha ao criar a tarefa agendada & pause & exit /b 1)
schtasks /run /tn %TASK% >nul

echo [5/5] Criando atalho na area de trabalho...
(
  echo [InternetShortcut]
  echo URL=http://localhost:8000
) > "%PUBLIC%\Desktop\Maquina de Tracao.url"

echo.
echo ============================================
echo  Instalado em %DEST%
echo  Abra o atalho "Maquina de Tracao" na area de trabalho
echo  ou http://localhost:8000 no navegador.
echo.
echo  Apague esta pasta e o zip deste PC depois de instalar.
echo ============================================
timeout /t 5 /nobreak >nul
start "" http://localhost:8000
pause
