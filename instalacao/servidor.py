"""Ponto de entrada da versão instalada no cliente (vira MaqTracao.exe).

Sobe o backend FastAPI, que também serve o frontend já buildado, em uma única
porta. Os arquivos que mudam ficam ao lado do executável e não dentro dele:

    config.json   configurações (IP da IHM, registradores...), editável
    tracao.db     banco SQLite dos ensaios
    data/         pasta monitorada de CSVs (padrão)
    logs/         servidor.log

Opções:
    --abrir       abre o navegador quando o servidor estiver no ar
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path

# PyInstaller marca sys.frozen; o Nuitka define __compiled__.
NUITKA = "__compiled__" in globals()
FROZEN = getattr(sys, "frozen", False) or NUITKA

# Pasta da instalação (gravável) e pasta com os arquivos empacotados.
if NUITKA:
    HOME = Path(sys.argv[0]).resolve().parent
elif FROZEN:
    HOME = Path(sys.executable).resolve().parent
else:
    HOME = Path(__file__).resolve().parent.parent
BUNDLE = Path(getattr(sys, "_MEIPASS", HOME))


def _redirect_output() -> None:
    """Sem console (exe janela/tarefa agendada) stdout/stderr são None."""
    logs = HOME / "logs"
    logs.mkdir(exist_ok=True)
    log = open(logs / "servidor.log", "a", encoding="utf-8", buffering=1)
    sys.stdout = log
    sys.stderr = log
    print(f"\n==== {time.strftime('%Y-%m-%d %H:%M:%S')} iniciando ====", flush=True)


def _ensure_config() -> dict:
    """Na primeira execução copia o config.json padrão para a instalação."""
    cfg_file = HOME / "config.json"
    if not cfg_file.exists():
        default = BUNDLE / "backend" / "config.json"
        cfg = json.loads(default.read_text(encoding="utf-8")) if default.exists() else {}
        cfg["watch_directory"] = str(HOME / "data")
        cfg_file.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    (HOME / "data").mkdir(exist_ok=True)
    try:
        return json.loads(cfg_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _port_in_use(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1" if host in ("0.0.0.0", "") else host, port)) == 0


def main() -> None:
    if FROZEN or sys.stdout is None:
        _redirect_output()

    os.chdir(HOME)  # tracao.db e data/ são relativos à pasta de trabalho
    os.environ["MAQ_TRACAO_HOME"] = str(HOME)
    cfg = _ensure_config()

    # "server_host": "0.0.0.0" no config.json libera o acesso por outros PCs da rede.
    host = str(cfg.get("server_host", "127.0.0.1"))
    port = int(cfg.get("server_port", 8000))
    url = f"http://localhost:{port}"
    abrir = "--abrir" in sys.argv

    if _port_in_use(host, port):
        print(f"[servidor] já está rodando em {url}", flush=True)
        if abrir:
            webbrowser.open(url)
        return

    if abrir:
        def _open_when_ready() -> None:
            for _ in range(60):
                if _port_in_use(host, port):
                    webbrowser.open(url)
                    return
                time.sleep(0.5)
        threading.Thread(target=_open_when_ready, daemon=True).start()

    import logging
    logging.basicConfig(level=logging.INFO, stream=sys.stdout,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    import uvicorn
    from backend.main import app

    print(f"[servidor] {url} (host {host})", flush=True)
    uvicorn.run(app, host=host, port=port, log_config=None, access_log=False)


if __name__ == "__main__":
    main()
