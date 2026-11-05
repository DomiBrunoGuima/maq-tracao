"""Login, usuários e auditoria.

- Acesso mestre: login ``mestre``, senha fixa (só o hash fica no código). Não pode ser
  alterado, desativado nem excluído pela tela. É o único que abre a Gestão de usuários.
- Usuários (operadores): criados pelo mestre, que gera a senha. Senhas guardadas com
  PBKDF2-SHA256 (200 mil iterações, salt aleatório por usuário).
- Sessão: token aleatório num cookie HttpOnly; no banco fica só o SHA-256 do token.
  Expira após ``SESSAO_OCIOSA_H`` horas sem uso e ``SESSAO_MAX_H`` horas no total.
- Tentativas erradas: após ``MAX_TENTATIVAS`` erros seguidos o login fica bloqueado
  por ``BLOQUEIO_MIN`` minutos.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from .database import AuditoriaDB, SessaoDB, UsuarioDB

COOKIE = "maq_sessao"
SESSAO_OCIOSA_H = 8
SESSAO_MAX_H = 24
MAX_TENTATIVAS = 5
BLOQUEIO_MIN = 5
_ITER = 200_000

# ── Acesso mestre (fixo) ──────────────────────────────────────────────────
# Só o hash da senha fica no código (o repositório é público). A senha foi
# entregue ao responsável pela máquina e não está escrita em nenhum arquivo.
MESTRE_ID = 0
MESTRE_LOGIN = "mestre"
MESTRE_NOME = "Administrador (acesso mestre)"
_MESTRE_SALT = bytes.fromhex("038fa1162853eb3a880fafeefa0d260e")
_MESTRE_HASH = "6c03a01518a1b9df4e182d206e5b7cc8799e53066e7812f9fbe59e5a16032e68"


@dataclass
class Usuario:
    id: int
    login: str
    nome: str
    cargo: str = ""
    registro: str = ""
    email: str = ""
    mestre: bool = False
    trocar_senha: bool = False

    def publico(self) -> dict:
        return {
            "id": self.id, "login": self.login, "nome": self.nome, "cargo": self.cargo,
            "registro": self.registro, "email": self.email, "mestre": self.mestre,
            "trocar_senha": self.trocar_senha,
        }


MESTRE = Usuario(id=MESTRE_ID, login=MESTRE_LOGIN, nome=MESTRE_NOME, cargo="Administrador", mestre=True)


def _de_db(u: UsuarioDB) -> Usuario:
    return Usuario(id=u.id, login=u.login, nome=u.nome, cargo=u.cargo or "", registro=u.registro or "",
                   email=u.email or "", trocar_senha=bool(u.trocar_senha))


# ── Senhas ────────────────────────────────────────────────────────────────

def hash_senha(senha: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(salt), _ITER)
    return f"pbkdf2_sha256${_ITER}${salt}${dk.hex()}"


def confere_senha(senha: str, salvo: str) -> bool:
    try:
        _alg, it, salt, h = salvo.split("$")
        dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), bytes.fromhex(salt), int(it))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(dk.hex(), h)


def _confere_mestre(senha: str) -> bool:
    dk = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), _MESTRE_SALT, _ITER)
    return hmac.compare_digest(dk.hex(), _MESTRE_HASH)


# Sem letras/números que se confundem (0/O, 1/l/I).
_ALFABETO = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789"


def gerar_senha(n: int = 10) -> str:
    """Senha aleatória legível, com ao menos uma maiúscula, minúscula e dígito."""
    while True:
        s = "".join(secrets.choice(_ALFABETO) for _ in range(n))
        if any(c.isupper() for c in s) and any(c.islower() for c in s) and any(c.isdigit() for c in s):
            return s


def valida_senha_nova(senha: str) -> str | None:
    """Mensagem de erro, ou None se a senha serve."""
    if len(senha) < 8:
        return "A senha precisa ter ao menos 8 caracteres."
    if not any(c.isalpha() for c in senha) or not any(c.isdigit() for c in senha):
        return "A senha precisa ter letras e números."
    return None


def normaliza_login(login: str) -> str:
    return (login or "").strip().lower()


# ── Bloqueio por tentativas erradas ───────────────────────────────────────

_falhas: dict[str, list[float]] = {}
_lock = threading.Lock()


def bloqueado_ate(login: str) -> float:
    """Timestamp até quando o login está bloqueado (0 se livre)."""
    with _lock:
        tent = _falhas.get(login) or []
        if len(tent) >= MAX_TENTATIVAS:
            fim = tent[-1] + BLOQUEIO_MIN * 60
            if fim > time.time():
                return fim
            _falhas.pop(login, None)
        return 0.0


def _registra_falha(login: str) -> None:
    with _lock:
        _falhas.setdefault(login, []).append(time.time())
        _falhas[login] = _falhas[login][-MAX_TENTATIVAS:]


def _limpa_falhas(login: str) -> None:
    with _lock:
        _falhas.pop(login, None)


def autenticar(db: Session, login: str, senha: str) -> Usuario | None:
    login = normaliza_login(login)
    if login == MESTRE_LOGIN:
        ok = _confere_mestre(senha)
        usuario = MESTRE if ok else None
    else:
        u = db.query(UsuarioDB).filter(UsuarioDB.login == login).first()
        ok = bool(u and u.ativo and confere_senha(senha, u.senha_hash))
        usuario = _de_db(u) if ok else None
        if ok:
            u.ultimo_login = datetime.utcnow()
            db.commit()
    if ok:
        _limpa_falhas(login)
    else:
        _registra_falha(login)
    return usuario


# ── Sessões ───────────────────────────────────────────────────────────────

def _h(token: str) -> str:
    return hashlib.sha256(token.encode("ascii", "replace")).hexdigest()


def criar_sessao(db: Session, usuario: Usuario, ip: str = "") -> str:
    token = secrets.token_urlsafe(32)
    agora = datetime.utcnow()
    # Limpa sessões vencidas de vez em quando
    db.query(SessaoDB).filter(SessaoDB.ultimo_uso < agora - timedelta(hours=SESSAO_OCIOSA_H)).delete()
    db.add(SessaoDB(token_hash=_h(token), usuario_id=usuario.id, criada_em=agora, ultimo_uso=agora, ip=ip))
    db.commit()
    return token


def encerrar_sessao(db: Session, token: str | None) -> None:
    if token:
        db.query(SessaoDB).filter(SessaoDB.token_hash == _h(token)).delete()
        db.commit()


def encerrar_sessoes_do_usuario(db: Session, usuario_id: int, exceto_token: str | None = None) -> None:
    q = db.query(SessaoDB).filter(SessaoDB.usuario_id == usuario_id)
    if exceto_token:
        q = q.filter(SessaoDB.token_hash != _h(exceto_token))
    q.delete()
    db.commit()


def usuario_da_sessao(db: Session, token: str | None) -> Usuario | None:
    if not token:
        return None
    s = db.query(SessaoDB).filter(SessaoDB.token_hash == _h(token)).first()
    if not s:
        return None
    agora = datetime.utcnow()
    if (agora - s.ultimo_uso > timedelta(hours=SESSAO_OCIOSA_H)
            or agora - s.criada_em > timedelta(hours=SESSAO_MAX_H)):
        db.delete(s)
        db.commit()
        return None
    if s.usuario_id == MESTRE_ID:
        usuario = MESTRE
    else:
        u = db.query(UsuarioDB).filter(UsuarioDB.id == s.usuario_id).first()
        if not u or not u.ativo:
            db.delete(s)
            db.commit()
            return None
        usuario = _de_db(u)
    if agora - s.ultimo_uso > timedelta(minutes=1):
        s.ultimo_uso = agora
    # Commit devolve a conexão ao pool (importante nas rotas de streaming).
    db.commit()
    return usuario


# ── Auditoria ─────────────────────────────────────────────────────────────

def auditar(db: Session, usuario: Usuario | None, acao: str, detalhe: str = "", ip: str = "",
            login: str | None = None) -> None:
    try:
        db.add(AuditoriaDB(
            usuario_id=usuario.id if usuario else None,
            usuario=login if login is not None else (usuario.login if usuario else ""),
            acao=acao, detalhe=detalhe[:2000], ip=ip,
        ))
        db.commit()
    except Exception as exc:  # auditoria nunca derruba a operação
        db.rollback()
        print(f"[auditoria] falha ao registrar {acao}: {exc}", flush=True)
