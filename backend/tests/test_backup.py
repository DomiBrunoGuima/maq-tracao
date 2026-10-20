"""Backup automático para pasta sincronizada."""
from __future__ import annotations

import sqlite3
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.backup import PREFIXO, BackupAgendado, fazer_backup


def _db(tmp_path: Path) -> Path:
    db = tmp_path / "tracao.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE t (x INTEGER)")
    con.execute("INSERT INTO t VALUES (42)")
    con.commit()
    con.close()
    return db


def test_backup_gera_zip_com_banco_e_config(tmp_path):
    db = _db(tmp_path)
    cfg = tmp_path / "config.json"
    cfg.write_text("{}")
    arq = fazer_backup(db, cfg, tmp_path / "nuvem" / "backup")
    with zipfile.ZipFile(arq) as z:
        assert set(z.namelist()) == {"tracao.db", "config.json"}
        z.extract("tracao.db", tmp_path / "rest")
    assert sqlite3.connect(tmp_path / "rest" / "tracao.db").execute("SELECT x FROM t").fetchone() == (42,)


def test_backup_mantem_so_os_ultimos(tmp_path):
    db = _db(tmp_path)
    dest = tmp_path / "b"
    dest.mkdir()
    for i in range(5):
        (dest / f"{PREFIXO}2020010{i}-000000.zip").write_bytes(b"x")
    fazer_backup(db, None, dest, manter=3)
    restantes = sorted(p.name for p in dest.glob(f"{PREFIXO}*.zip"))
    assert len(restantes) == 3
    assert restantes[0] == f"{PREFIXO}20200103-000000.zip"


def test_agendado_respeita_intervalo(tmp_path):
    db = _db(tmp_path)
    cfg = {"backup_ativo": True, "backup_dir": str(tmp_path / "b"), "backup_intervalo_h": 24, "backup_manter": 5}
    ag = BackupAgendado(lambda: cfg, db, tmp_path / "config.json")
    assert ag._devido()
    ag.executar()
    assert not ag._devido()           # acabou de fazer: só daqui a 24 h
    assert ag.status()["ultimo"] is not None
    cfg["backup_ativo"] = False
    assert not ag._devido()


def test_sem_pasta_da_erro_claro(tmp_path):
    ag = BackupAgendado(lambda: {"backup_dir": ""}, _db(tmp_path), tmp_path / "c.json")
    with pytest.raises(ValueError):
        ag.executar()
