"""
Descobre os arquivos disponíveis no FTP da IHM.

Uso:
    venv\Scripts\python ftp_discover.py
"""

from ftplib import FTP, error_perm

HOST = "192.168.8.10"
PORT = 21

print("Usuário FTP (Enter para 'anonymous'): ", end="")
user = input().strip() or "anonymous"
print("Senha FTP (Enter para vazio): ", end="")
pwd = input().strip()

print(f"\nConectando em {HOST}:{PORT} ...")

ftp = FTP()
ftp.connect(HOST, PORT, timeout=10)
ftp.login(user, pwd)
print(f"Conectado! Sistema: {ftp.getwelcome()}\n")

def list_dir(path="/", level=0):
    indent = "  " * level
    try:
        ftp.cwd(path)
        entries = []
        ftp.retrlines("LIST", entries.append)
        for entry in entries:
            parts = entry.split()
            name = parts[-1]
            is_dir = entry.startswith("d")
            if is_dir:
                print(f"{indent}[DIR]  {name}/")
                if level < 2:
                    list_dir(f"{path}/{name}".replace("//", "/"), level + 1)
            else:
                size = parts[4] if len(parts) >= 5 else "?"
                print(f"{indent}[FILE] {name}  ({size} bytes)")
    except error_perm as e:
        print(f"{indent}(sem permissão: {e})")

list_dir("/")
ftp.quit()

print("\nPronto. Configure no app o diretório e o nome do arquivo CSV que aparecer acima.")
