# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: gera dist\MaqTracao\MaqTracao.exe (rode via build_cliente.bat).
# O código Python vai só como bytecode dentro do executável; o frontend vai
# já buildado (frontend/dist). config.json entra apenas como modelo padrão.
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).parent

hidden = (
    collect_submodules("uvicorn")
    + collect_submodules("pymodbus")
    + [m for m in collect_submodules("backend") if ".tests" not in m]
)

a = Analysis(
    [str(ROOT / "instalacao" / "servidor.py")],
    pathex=[str(ROOT)],
    datas=[
        (str(ROOT / "frontend" / "dist"), "frontend/dist"),
        (str(ROOT / "backend" / "config.json"), "backend"),
    ],
    hiddenimports=hidden,
    excludes=["backend.tests", "pytest", "tkinter", "IPython", "notebook"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MaqTracao",
    console=False,
    debug=False,
    strip=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="MaqTracao", strip=False, upx=False)
