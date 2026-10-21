"""Senha das Configurações (técnico).

A tela de Configurações e as rotas que mudam registradores/configuração exigem
um token, obtido com a senha. A senha padrão fica no código (vai compilada no
executável); trocando pela tela, o hash novo é salvo no config.json em
"senha_config". Se essa chave for apagada, volta a valer a senha padrão.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import time

SENHA_PADRAO = "tracao2026"
_ITER = 200_000
_VALIDADE_S = 8 * 3600

_tokens: dict[str, float] = {}


def hash_senha(senha: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(salt), _ITER)
    return f"pbkdf2${salt}${dk.hex()}"


def confere(senha: str, cfg: dict) -> bool:
    salvo = cfg.get("senha_config") or ""
    try:
        _, salt, _h = salvo.split("$")
    except ValueError:
        return hmac.compare_digest(senha.encode("utf-8"), SENHA_PADRAO.encode("utf-8"))
    return hmac.compare_digest(hash_senha(senha, salt), salvo)


def novo_token() -> str:
    agora = time.time()
    for t, exp in list(_tokens.items()):
        if exp < agora:
            _tokens.pop(t, None)
    token = secrets.token_urlsafe(32)
    _tokens[token] = agora + _VALIDADE_S
    return token


def token_valido(token: str | None) -> bool:
    return bool(token) and _tokens.get(token, 0) > time.time()


def encerrar(token: str | None) -> None:
    if token:
        _tokens.pop(token, None)
