"""
Servidor FTP local para testar a transferência de CSV sem a IHM real.

Serve o diretório data/ na porta 2121 com usuário "ihm" e senha "1234".

Uso:
    venv\Scripts\python ftp_server_test.py

Configurar no app:
    IP da IHM:         127.0.0.1
    Porta FTP:         2121
    Usuário FTP:       ihm
    Senha FTP:         1234
    Diretório remoto:  /
    Nome do arquivo:   H0001.csv
"""

import subprocess
import sys
from pathlib import Path

# Instala pyftpdlib se necessário
try:
    import pyftpdlib  # noqa: F401
except ImportError:
    print("[setup] Instalando pyftpdlib...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyftpdlib", "--quiet"])

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

DATA_DIR = Path(__file__).parent / "data"
FTP_USER = "ihm"
FTP_PASS = "1234"
FTP_PORT = 2121  # porta > 1024 não exige administrador

if not DATA_DIR.exists():
    print(f"[erro] Diretório '{DATA_DIR}' não encontrado.")
    print("       Execute setup.bat primeiro para gerar o arquivo de exemplo.")
    sys.exit(1)

csvs = list(DATA_DIR.glob("*.csv"))
if not csvs:
    print(f"[erro] Nenhum .csv encontrado em '{DATA_DIR}'.")
    print("       Execute setup.bat primeiro para gerar o arquivo de exemplo.")
    sys.exit(1)

authorizer = DummyAuthorizer()
authorizer.add_user(FTP_USER, FTP_PASS, str(DATA_DIR), perm="elradfmwMT")

handler = FTPHandler
handler.authorizer = authorizer
handler.passive_ports = range(60000, 60100)

server = FTPServer(("127.0.0.1", FTP_PORT), handler)

print(f"\n{'='*50}")
print(f"  Servidor FTP de teste rodando")
print(f"{'='*50}")
print(f"  Endereço : 127.0.0.1:{FTP_PORT}")
print(f"  Usuário  : {FTP_USER}")
print(f"  Senha    : {FTP_PASS}")
print(f"  Diretório: {DATA_DIR}")
print(f"  Arquivos : {[c.name for c in csvs]}")
print(f"\n  Configure no app e clique 'Buscar CSV via FTP'")
print(f"  Ctrl+C para parar\n")

server.serve_forever()
