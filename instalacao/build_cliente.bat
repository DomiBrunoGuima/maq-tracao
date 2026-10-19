@echo off
setlocal
:: Gera o pacote de instalacao do cliente: build-cliente\MaqTracao-instalador.zip
:: Rode no SEU PC (precisa de Python 3.11+ e Node 20+), nunca no PC do cliente.
cd /d "%~dp0.."

echo ============================================
echo  Maquina de Tracao - pacote para o cliente
echo ============================================

python --version >nul 2>&1 || (echo [ERRO] Python nao encontrado & pause & exit /b 1)
node --version >nul 2>&1 || (echo [ERRO] Node.js nao encontrado & pause & exit /b 1)

echo [1/4] Build do frontend...
pushd frontend
call npm ci || (popd & echo [ERRO] npm ci falhou & pause & exit /b 1)
call npm run build || (popd & echo [ERRO] build do frontend falhou & pause & exit /b 1)
popd

echo [2/4] Ambiente Python de build...
if not exist venv-build python -m venv venv-build
call venv-build\Scripts\activate.bat
python -m pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt pyinstaller || (echo [ERRO] pip falhou & pause & exit /b 1)

echo [3/4] Empacotando backend + frontend em MaqTracao.exe...
pyinstaller --noconfirm --clean --log-level WARN --distpath build-cliente\dist --workpath build-cliente\work instalacao\maq_tracao.spec || (echo [ERRO] PyInstaller falhou & pause & exit /b 1)

echo [4/4] Montando o pacote...
set "PKG=build-cliente\MaqTracao-instalador"
if exist "%PKG%" rmdir /s /q "%PKG%"
mkdir "%PKG%"
xcopy "build-cliente\dist\MaqTracao" "%PKG%\MaqTracao\" /e /i /q /y >nul
copy /y instalacao\instalar.bat "%PKG%\" >nul
copy /y instalacao\desinstalar.bat "%PKG%\" >nul
if exist build-cliente\MaqTracao-instalador.zip del build-cliente\MaqTracao-instalador.zip
powershell -NoProfile -Command "Compress-Archive -Path '%PKG%\*' -DestinationPath 'build-cliente\MaqTracao-instalador.zip'"

echo.
echo ============================================
echo  Pronto: build-cliente\MaqTracao-instalador.zip
echo  Leve esse zip ao PC do cliente e rode instalar.bat
echo  como administrador.
echo ============================================
pause
