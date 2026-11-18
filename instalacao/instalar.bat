@echo off
setlocal
:: Instala (ou atualiza) a Maquina de Tracao no PC do cliente.
:: Clique com o botao direito > Executar como administrador.
set "DEST=C:\MaqTracao"
set "TASK=MaqTracao"
set "SRC=%~dp0MaqTracao"

net session >nul 2>&1 || (echo [ERRO] Execute como administrador. & pause & exit /b 1)
if not exist "%SRC%\MaqTracao.exe" (echo [ERRO] Pasta MaqTracao nao encontrada ao lado deste script. & pause & exit /b 1)

echo [1/6] Parando versao anterior, se houver...
schtasks /end /tn %TASK% >nul 2>&1
taskkill /f /im MaqTracao.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo [2/6] Guardando copia de config.json e tracao.db...
:: Atualizacao: copia config.json (IP e registradores) e tracao.db (ensaios,
:: usuarios, auditoria) para C:\MaqTracao\backups-atualizacao\<data-hora>
:: antes de trocar o programa. Essa pasta nunca e apagada pelo instalador.
set "BKP="
set "TEM_DADOS="
if exist "%DEST%\config.json" set "TEM_DADOS=1"
if exist "%DEST%\tracao.db" set "TEM_DADOS=1"
if defined TEM_DADOS (
  for /f %%T in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "BKP=%DEST%\backups-atualizacao\%%T"
)
if defined BKP (
  mkdir "%BKP%" || (echo [ERRO] Nao consegui criar %BKP% & pause & exit /b 1)
  for %%F in ("%DEST%\config.json" "%DEST%\tracao.db*") do if exist "%%~F" copy /y "%%~F" "%BKP%\" >nul || (echo [ERRO] Falha no backup de %%~nxF. Nada foi alterado. & pause & exit /b 1)
  echo       Copia em %BKP%
)

echo [3/6] Copiando arquivos para %DEST%...
:: Troca so o programa. config.json, tracao.db, data\, logs\ e
:: backups-atualizacao\ sao mantidos.
if exist "%DEST%" (
  for /d %%D in ("%DEST%\*") do if /i not "%%~nxD"=="data" if /i not "%%~nxD"=="logs" if /i not "%%~nxD"=="backups-atualizacao" rmdir /s /q "%%D"
  for %%F in ("%DEST%\*") do (echo %%~nxF| findstr /b /i "config.json tracao.db" >nul || del /f /q "%%F")
)
if not exist "%DEST%\data" mkdir "%DEST%\data"
:: O pacote nunca deve trazer config.json/tracao.db na raiz (o modelo fica em
:: backend\config.json e so e usado na primeira instalacao).
if exist "%SRC%\config.json" del /f /q "%SRC%\config.json"
if exist "%SRC%\tracao.db" del /f /q "%SRC%\tracao.db"
xcopy "%SRC%" "%DEST%\" /e /i /q /y >nul || (echo [ERRO] Falha ao copiar & pause & exit /b 1)
:: Confere que o config.json (registradores) ficou identico ao de antes.
if defined BKP if exist "%BKP%\config.json" (
  fc /b "%BKP%\config.json" "%DEST%\config.json" >nul || (
    copy /y "%BKP%\config.json" "%DEST%\config.json" >nul
    echo [AVISO] config.json tinha mudado e foi restaurado da copia.
  )
)

echo [4/6] Restringindo a pasta a Administradores...
:: Usuarios comuns nao abrem C:\MaqTracao; so a pasta data\ fica liberada
:: (para colocar CSVs manualmente, se precisar).
icacls "%DEST%" /inheritance:r /grant:r *S-1-5-32-544:(OI)(CI)F *S-1-5-18:(OI)(CI)F /C /Q >nul
icacls "%DEST%\data" /grant *S-1-5-32-545:(OI)(CI)M /C /Q >nul

echo [5/6] Registrando inicio automatico com o Windows...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$a = New-ScheduledTaskAction -Execute '%DEST%\MaqTracao.exe' -WorkingDirectory '%DEST%';" ^
  "$t = New-ScheduledTaskTrigger -AtStartup;" ^
  "$s = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1);" ^
  "$p = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest;" ^
  "Register-ScheduledTask -TaskName '%TASK%' -Action $a -Trigger $t -Settings $s -Principal $p -Force | Out-Null" ^
  || (echo [ERRO] Falha ao criar a tarefa agendada & pause & exit /b 1)
schtasks /run /tn %TASK% >nul

echo [6/6] Criando atalho na area de trabalho...
:: Icone: icone.ico ao lado deste script (troque pelo logo de voces, se quiser).
:: Fica fora de C:\MaqTracao porque usuarios comuns nao leem aquela pasta.
set "ICODIR=%ProgramData%\MaqTracao"
if not exist "%ICODIR%" mkdir "%ICODIR%"
if exist "%~dp0icone.ico" copy /y "%~dp0icone.ico" "%ICODIR%\icone.ico" >nul
if exist "%PUBLIC%\Desktop\Maquina de Tracao.url" del /f /q "%PUBLIC%\Desktop\Maquina de Tracao.url"
:: Atalho abre a tela no Edge em modo aplicativo (janela propria, sem barra de endereco).
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$edge = @(\"${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe\", \"$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe\") | Where-Object { Test-Path $_ } | Select-Object -First 1;" ^
  "$s = (New-Object -ComObject WScript.Shell).CreateShortcut(\"$env:PUBLIC\Desktop\Maquina de Tracao.lnk\");" ^
  "if ($edge) { $s.TargetPath = $edge; $s.Arguments = '--app=http://localhost:8000' } else { $s.TargetPath = 'http://localhost:8000' };" ^
  "if (Test-Path \"$env:ProgramData\MaqTracao\icone.ico\") { $s.IconLocation = \"$env:ProgramData\MaqTracao\icone.ico,0\" };" ^
  "$s.Description = 'Maquina de Tracao'; $s.Save()"

echo.
echo ============================================
echo  Instalado em %DEST%
echo  Abra o atalho "Maquina de Tracao" na area de trabalho
echo  ou http://localhost:8000 no navegador.
if defined BKP echo  Copia da configuracao anterior: %BKP%
echo.
echo  Apague esta pasta e o zip deste PC depois de instalar.
echo ============================================
timeout /t 5 /nobreak >nul
start "" http://localhost:8000
pause
