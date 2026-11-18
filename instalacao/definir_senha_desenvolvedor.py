"""Define (ou troca) a senha do acesso desenvolvedor (AUTOMATIC).

Uso, na raiz do repositório:

    python instalacao/definir_senha_desenvolvedor.py

A senha é digitada sem aparecer na tela e nunca é gravada: o script grava só o
hash PBKDF2-SHA256 (salt aleatório) em backend/credencial_desenvolvedor.py.
Depois faça commit desse arquivo e gere um novo build para o cliente.

    python instalacao/definir_senha_desenvolvedor.py --desativar

apaga o hash e desativa o login do desenvolvedor.
"""
from __future__ import annotations

import getpass
import hashlib
import re
import secrets
import sys
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parents[1] / "backend" / "credencial_desenvolvedor.py"
ITER = 200_000  # o mesmo de backend/usuarios.py
MIN_CARACTERES = 10


def gerar_hash(senha: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(salt), ITER)
    return f"pbkdf2_sha256${ITER}${salt}${dk.hex()}"


def gravar(valor: str) -> None:
    texto = ARQUIVO.read_text(encoding="utf-8")
    novo, n = re.subn(r'^SENHA_HASH = ".*"$', f'SENHA_HASH = "{valor}"', texto, flags=re.M)
    if n != 1:
        sys.exit(f"Não achei a linha SENHA_HASH em {ARQUIVO}.")
    ARQUIVO.write_text(novo, encoding="utf-8")


def main() -> None:
    if "--desativar" in sys.argv[1:]:
        gravar("")
        print("Login do desenvolvedor desativado. Faça commit de", ARQUIVO.relative_to(ARQUIVO.parents[1]))
        return

    print("Senha do acesso desenvolvedor (login: desenvolvedor)")
    senha = getpass.getpass("Nova senha: ")
    if len(senha) < MIN_CARACTERES or not any(c.isalpha() for c in senha) or not any(c.isdigit() for c in senha):
        sys.exit(f"A senha precisa ter ao menos {MIN_CARACTERES} caracteres, com letras e números.")
    if getpass.getpass("Repita a senha: ") != senha:
        sys.exit("As senhas não conferem. Nada foi alterado.")
    gravar(gerar_hash(senha))
    rel = ARQUIVO.relative_to(ARQUIVO.parents[1])
    print(f"Pronto. Só o hash foi gravado em {rel}.")
    print("Agora: git add", rel, '&& git commit -m "Senha do desenvolvedor" && git push, e gere um novo build.')


if __name__ == "__main__":
    main()
