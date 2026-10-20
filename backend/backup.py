"""Backup automático para uma pasta sincronizada com a nuvem.

O programa não fala com nenhuma nuvem: ele grava um .zip com o banco (tracao.db)
e o config.json numa pasta que o app do Google Drive, OneDrive ou Dropbox já
sincroniza. Assim não há senha guardada no programa e a cópia é feita mesmo sem
internet; o app da nuvem sobe quando a conexão voltar.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import threading
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Callable

PREFIXO = "MaqTracao-backup-"


def fazer_backup(db_path: Path, config_path: Path | None, destino: Path, manter: int = 30) -> Path:
    """Cria o .zip do backup em ``destino`` e apaga os mais antigos além de ``manter``."""
    destino = Path(destino)
    destino.mkdir(parents=True, exist_ok=True)
    nome = f"{PREFIXO}{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    final = destino / nome

    with tempfile.TemporaryDirectory() as tmp:
        # API de backup do SQLite: cópia consistente mesmo com o programa gravando
        copia = Path(tmp) / "tracao.db"
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(copia))
        try:
            src.backup(dst)
        finally:
            dst.close()
            src.close()
        # Escreve com nome temporário e renomeia: o app da nuvem nunca sobe um zip pela metade
        parcial = destino / (nome + ".parcial")
        with zipfile.ZipFile(parcial, "w", zipfile.ZIP_DEFLATED) as z:
            z.write(copia, "tracao.db")
            if config_path and Path(config_path).exists():
                z.write(config_path, "config.json")
        parcial.replace(final)

    if manter > 0:
        antigos = sorted(destino.glob(f"{PREFIXO}*.zip"))[:-manter]
        for f in antigos:
            try:
                f.unlink()
            except OSError:
                pass
    return final


def listar_backups(destino: str) -> list[dict]:
    if not destino or not Path(destino).is_dir():
        return []
    out = []
    for f in sorted(Path(destino).glob(f"{PREFIXO}*.zip"), reverse=True):
        st = f.stat()
        out.append({"arquivo": f.name, "tamanho_kb": round(st.st_size / 1024, 1),
                    "data": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")})
    return out


class BackupAgendado:
    """Thread que confere a cada minuto se já passou o intervalo desde o último
    backup e, se a opção estiver ligada, faz um novo."""

    def __init__(self, get_config: Callable[[], dict], db_path: Path, config_path: Path) -> None:
        self._get_config = get_config
        self._db_path = db_path
        self._config_path = config_path
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self.ultimo: str | None = None      # ISO do último backup feito nesta execução
        self.ultimo_arquivo: str | None = None
        self.erro: str | None = None

    def _estado_path(self, destino: str) -> Path:
        return Path(destino) / ".ultimo-backup.json"

    def _ultimo_ts(self, destino: str) -> float:
        """Momento do último backup (gravado na própria pasta, sobrevive a reinício)."""
        try:
            return float(json.loads(self._estado_path(destino).read_text())["ts"])
        except Exception:
            return 0.0

    def executar(self) -> dict:
        cfg = self._get_config()
        destino = (cfg.get("backup_dir") or "").strip()
        if not destino:
            raise ValueError("Escolha a pasta do backup em Configurações.")
        with self._lock:
            try:
                arq = fazer_backup(self._db_path, self._config_path, Path(destino),
                                   int(cfg.get("backup_manter", 30) or 0))
            except Exception as exc:
                self.erro = f"{type(exc).__name__}: {exc}"
                raise
            agora = time.time()
            self._estado_path(destino).write_text(json.dumps({"ts": agora, "arquivo": arq.name}))
            self.ultimo = datetime.fromtimestamp(agora).isoformat(timespec="seconds")
            self.ultimo_arquivo = arq.name
            self.erro = None
            print(f"[backup] {arq}", flush=True)
            return {"arquivo": arq.name, "pasta": destino, "data": self.ultimo}

    def status(self) -> dict:
        cfg = self._get_config()
        destino = (cfg.get("backup_dir") or "").strip()
        ts = self._ultimo_ts(destino) if destino else 0.0
        intervalo_h = float(cfg.get("backup_intervalo_h", 24) or 24)
        return {
            "ativo": bool(cfg.get("backup_ativo")),
            "pasta": destino,
            "pasta_existe": bool(destino) and Path(destino).is_dir(),
            "ultimo": datetime.fromtimestamp(ts).isoformat(timespec="seconds") if ts else None,
            "proximo": datetime.fromtimestamp(ts + intervalo_h * 3600).isoformat(timespec="seconds") if ts else None,
            "erro": self.erro,
            "backups": listar_backups(destino)[:10],
        }

    def _devido(self) -> bool:
        cfg = self._get_config()
        destino = (cfg.get("backup_dir") or "").strip()
        if not cfg.get("backup_ativo") or not destino:
            return False
        intervalo = float(cfg.get("backup_intervalo_h", 24) or 24) * 3600
        return time.time() - self._ultimo_ts(destino) >= intervalo

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                if self._devido():
                    self.executar()
            except Exception as exc:
                print(f"[backup] Falha: {exc}", flush=True)
            self._stop.wait(60)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="backup", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
