@echo off
setlocal
:: Gera o pacote do cliente compilado com Nuitka (codigo de maquina, mais dificil
:: de reverter que o PyInstaller): build-cliente\MaqTracao-instalador.zip
:: Rode no SEU PC (Python 3.11+ e Node 20+), nunca no PC do cliente.
:: Na primeira vez o Nuitka baixa sozinho um compilador C. Leva 20 a 40 minutos.
cd /d "%~dp0.."

echo ============================================
echo  Maquina de Tracao - pacote Nuitka
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
pip install --quiet -r requirements.txt nuitka ordered-set zstandard || (echo [ERRO] pip falhou & pause & exit /b 1)

echo [3/4] Compilando com Nuitka (demora)...
if exist build-cliente\nuitka rmdir /s /q build-cliente\nuitka
python -m nuitka --standalone --assume-yes-for-downloads ^
  --windows-console-mode=disable --enable-plugin=no-qt ^
  --output-dir=build-cliente\nuitka --output-filename=MaqTracao.exe ^
  --include-package=backend --nofollow-import-to=backend.tests ^
  --include-package=uvicorn --include-package=pymodbus ^
  --nofollow-import-to=pytest --nofollow-import-to=tkinter --nofollow-import-to=IPython ^
  --include-data-dir=frontend\dist=frontend\dist ^
  --include-data-files=backend\config.json=backend\config.json ^
  instalacao\servidor.py || (echo [ERRO] Nuitka falhou & pause & exit /b 1)

echo [4/4] Montando o pacote...
set "PKG=build-cliente\MaqTracao-instalador"
if exist "%PKG%" rmdir /s /q "%PKG%"
mkdir "%PKG%"
xcopy "build-cliente\nuitka\servidor.dist" "%PKG%\MaqTracao\" /e /i /q /y >nul
copy /y instalacao\instalar.bat "%PKG%\" >nul
copy /y instalacao\desinstalar.bat "%PKG%\" >nul
copy /y instalacao\icone.ico "%PKG%\" >nul
if exist build-cliente\MaqTracao-instalador.zip del build-cliente\MaqTracao-instalador.zip
powershell -NoProfile -Command "Compress-Archive -Path '%PKG%\*' -DestinationPath 'build-cliente\MaqTracao-instalador.zip'"

echo.
echo ============================================
echo  Pronto: build-cliente\MaqTracao-instalador.zip
echo  Leve esse zip ao PC do cliente e rode instalar.bat
echo  como administrador.
echo ============================================
pause
