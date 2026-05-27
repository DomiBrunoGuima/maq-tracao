from __future__ import annotations

import logging
from ftplib import FTP, error_perm
from pathlib import Path

logger = logging.getLogger(__name__)


def download_csv(
    host: str,
    port: int,
    user: str,
    password: str,
    remote_dir: str,
    remote_filename: str,
    local_path: Path,
) -> None:
    """Baixa um arquivo CSV da IHM via FTP e salva em local_path.

    Levanta exceção em caso de falha (conexão, autenticação, arquivo não encontrado).
    """
    ftp = FTP()
    ftp.connect(host, port, timeout=10)
    try:
        ftp.login(user, password)
        ftp.cwd(remote_dir)
        logger.info(f"[ftp] Baixando '{remote_dir}/{remote_filename}' de {host}:{port}")
        with open(local_path, "wb") as f:
            ftp.retrbinary(f"RETR {remote_filename}", f.write)
        logger.info(f"[ftp] Download concluído → {local_path} ({local_path.stat().st_size} bytes)")
    except error_perm as e:
        raise RuntimeError(f"FTP: permissão negada — {e}") from e
    finally:
        try:
            ftp.quit()
        except Exception:
            pass
