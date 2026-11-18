"""Login, acesso mestre, gestão de usuários, auditoria e dados do usuário no relatório."""
from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from backend import credencial_desenvolvedor, main, usuarios
from backend.acquisition import build_ensaio_dataframe, persist_ensaio
from backend.database import EnsaioDB, get_db

from .test_cadastro import _samples

pytestmark = pytest.mark.login_real

# A senha real do mestre não está no repositório: nos testes o hash é trocado
# pelo de uma senha conhecida. O mesmo vale para o desenvolvedor.
SENHA_MESTRE = "senha-de-teste-123"
SENHA_DEV = "dev-de-teste-4567"


@pytest.fixture()
def cli(monkeypatch):
    salt = b"salt-de-teste-16"
    monkeypatch.setattr(usuarios, "_MESTRE_SALT", salt)
    monkeypatch.setattr(usuarios, "_MESTRE_HASH",
                        hashlib.pbkdf2_hmac("sha256", SENHA_MESTRE.encode(), salt, usuarios._ITER).hex())
    monkeypatch.setattr(credencial_desenvolvedor, "SENHA_HASH", usuarios.hash_senha(SENHA_DEV))
    usuarios._falhas.clear()
    c = TestClient(main.app)
    yield c
    usuarios._falhas.clear()


def _login(c, login, senha):
    return c.post("/api/auth/login", json={"login": login, "senha": senha})


def _criar(c, login="joao.silva", nome="João da Silva", **extra):
    r = c.post("/api/usuarios", json={"login": login, "nome": nome, **extra})
    assert r.status_code == 201, r.text
    return r.json()


def _db():
    return next(main.app.dependency_overrides[get_db]())


def test_api_exige_login(cli):
    assert cli.get("/api/ensaios").status_code == 401
    assert cli.get("/api/control/stream").status_code == 401
    assert cli.get("/api/health").status_code == 200


def test_mestre_fixo(cli):
    assert _login(cli, "mestre", "errada").status_code == 401
    r = _login(cli, "MESTRE", SENHA_MESTRE)
    assert r.status_code == 200
    assert r.json()["mestre"] is True
    # Cookie de sessão HttpOnly
    assert "httponly" in r.headers["set-cookie"].lower()
    assert cli.get("/api/auth/me").json()["login"] == "mestre"
    # Senha do mestre não muda e o login dele não pode ser usado por outro usuário
    assert cli.post("/api/auth/senha", json={"atual": SENHA_MESTRE, "nova": "Outra1234"}).status_code == 403
    assert cli.post("/api/usuarios", json={"login": "mestre", "nome": "X"}).status_code == 422
    assert cli.post("/api/usuarios", json={"login": "desenvolvedor", "nome": "X"}).status_code == 422
    # Mestre (cliente) não abre as Configurações: registradores, CLP e modo da máquina
    me = cli.get("/api/auth/me").json()
    assert me["gerencia_usuarios"] is True and me["configura"] is False
    corpo = {**main._config, "flexao_habilitada": not main._config.get("flexao_habilitada", True)}
    assert cli.put("/api/config", json=corpo).status_code == 403
    assert cli.post("/api/control/probe", json={}).status_code == 403


def test_desenvolvedor_acesso_completo(cli, monkeypatch, tmp_path):
    monkeypatch.setattr(main, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(main, "_config", dict(main._config))
    assert _login(cli, "desenvolvedor", "errada").status_code == 401
    r = _login(cli, "Desenvolvedor", SENHA_DEV)
    assert r.status_code == 200
    me = r.json()
    assert me["desenvolvedor"] is True and me["mestre"] is False
    assert me["configura"] is True and me["gerencia_usuarios"] is True
    # Muda o modo da máquina (tração + flexão -> só tração) e fica auditado
    corpo = {**main._config, "auto_load": False, "flexao_habilitada": False}
    r = cli.put("/api/config", json=corpo)
    assert r.status_code == 200, r.text
    assert r.json()["flexao_habilitada"] is False
    # Também gerencia usuários e vê a auditoria
    _criar(cli, login="ana.op", nome="Ana")
    acoes = [e["acao"] for e in cli.get("/api/auditoria").json()]
    assert "config_alterada" in acoes and "usuario_criado" in acoes
    # Senha fixa: não muda pela tela
    assert cli.post("/api/auth/senha", json={"atual": SENHA_DEV, "nova": "Outra1234"}).status_code == 403


def test_desenvolvedor_sem_senha_definida_fica_desativado(cli, monkeypatch):
    assert _login(cli, "desenvolvedor", SENHA_DEV).status_code == 200
    monkeypatch.setattr(credencial_desenvolvedor, "SENHA_HASH", "")
    # A sessão aberta cai e o login não entra com nenhuma senha
    assert cli.get("/api/auth/me").status_code == 401
    assert _login(cli, "desenvolvedor", "").status_code == 401
    assert _login(cli, "desenvolvedor", SENHA_DEV).status_code == 401


def test_gestao_de_usuarios(cli):
    _login(cli, "mestre", SENHA_MESTRE)
    novo = _criar(cli, cargo="Técnico", registro="CRQ 4567", email="joao@ex.com")
    senha = novo["senha"]
    assert len(senha) == 10
    uid = novo["usuario"]["id"]
    assert cli.post("/api/usuarios", json={"login": "joao.silva", "nome": "Y"}).status_code == 409
    assert [u["login"] for u in cli.get("/api/usuarios").json()] == ["joao.silva"]
    # Senha não aparece na listagem
    assert "senha" not in str(cli.get("/api/usuarios").json()).replace("trocar_senha", "")

    op = TestClient(main.app)
    assert _login(op, "joao.silva", senha).status_code == 200
    # Operador não gerencia usuários nem vê auditoria
    assert op.get("/api/usuarios").status_code == 403
    assert op.get("/api/auditoria").status_code == 403
    assert op.get("/api/ensaios").status_code == 200

    # Redefinir senha derruba a sessão e pode exigir troca no próximo login
    r = cli.post(f"/api/usuarios/{uid}/senha", json={"trocar_no_login": True})
    nova = r.json()["senha"]
    assert nova != senha
    assert op.get("/api/ensaios").status_code == 401
    assert _login(op, "joao.silva", senha).status_code == 401
    assert _login(op, "joao.silva", nova).json()["trocar_senha"] is True
    assert op.get("/api/ensaios").status_code == 403   # precisa trocar antes
    assert op.post("/api/auth/senha", json={"atual": nova, "nova": "curta"}).status_code == 422
    assert op.post("/api/auth/senha", json={"atual": nova, "nova": "Minha2026x"}).status_code == 200
    assert op.get("/api/ensaios").status_code == 200

    # Desativar bloqueia o acesso
    cli.put(f"/api/usuarios/{uid}", json={"login": "joao.silva", "nome": "João da Silva", "ativo": False})
    assert op.get("/api/ensaios").status_code == 401
    assert _login(op, "joao.silva", "Minha2026x").status_code == 401

    acoes = [a["acao"] for a in cli.get("/api/auditoria").json()]
    for a in ("usuario_criado", "senha_redefinida", "senha_trocada", "usuario_editado", "login", "login_falhou"):
        assert a in acoes

    assert cli.delete(f"/api/usuarios/{uid}").status_code == 204
    assert cli.get("/api/usuarios").json() == []


def test_bloqueio_por_tentativas(cli):
    for _ in range(usuarios.MAX_TENTATIVAS):
        assert _login(cli, "mestre", "errada").status_code == 401
    assert _login(cli, "mestre", SENHA_MESTRE).status_code == 429


def test_logout(cli):
    _login(cli, "mestre", SENHA_MESTRE)
    assert cli.post("/api/auth/logout").status_code == 200
    assert cli.get("/api/auth/me").status_code == 401


def test_relatorio_com_dados_do_usuario(cli):
    _login(cli, "mestre", SENHA_MESTRE)
    senha = _criar(cli, login="maria", nome="Maria Souza", cargo="Engenheira de materiais",
                   registro="CREA 98765")["senha"]
    op = TestClient(main.app)
    _login(op, "maria", senha)

    db = _db()
    meta, df = build_ensaio_dataframe(_samples(), 20.0, 50.0, filename="CLP_U.csv")
    rec = persist_ensaio(db, meta, df, filename="CLP_U.csv",
                         params={"area_seccao": 20.0, "comprimento_inicial": 50.0})
    # Ensaio iniciado pela Maria (o Controle grava isso ao iniciar)
    main._aplicar_cadastro(db, rec, {"usuario_id": 2, "usuario_nome": "Carlos Operador", "operador": "Carlos Operador"})
    eid = rec.id
    assert db.query(EnsaioDB).get(eid).usuario_nome == "Carlos Operador"
    db.close()

    assert op.get("/api/ensaios").json()[0]["usuario_nome"] == "Carlos Operador"
    r = op.post("/api/relatorio", json={"ensaio_id": eid})
    assert r.status_code == 200, r.text
    html = r.text
    assert "Emitido em" in html and "por Maria Souza" in html
    assert "Relatório emitido por" in html and "Engenheira de materiais" in html and "CREA 98765" in html
    assert "Ensaio executado por" in html and "Carlos Operador" in html
    rel = op.get("/api/relatorios").json()[0]
    assert rel["id"] == int(r.headers["X-Relatorio-Id"])
    acoes = [(a["usuario"], a["acao"]) for a in cli.get("/api/auditoria").json()]
    assert ("maria", "relatorio_gerado") in acoes
