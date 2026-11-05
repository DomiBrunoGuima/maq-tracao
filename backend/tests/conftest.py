"""Nos testes da API, o login é simulado com um operador já logado e o banco é um
SQLite temporário. test_auth.py desliga essa simulação para testar o login de verdade."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi import Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import main, usuarios  # noqa: E402
from backend.database import Base, get_db  # noqa: E402

OPERADOR_TESTE = usuarios.Usuario(id=1, login="op.teste", nome="Operador Teste",
                                  cargo="Técnico de laboratório", registro="CRQ 123")


def _login_simulado(request: Request) -> None:
    request.state.usuario = OPERADOR_TESTE


@pytest.fixture(autouse=True)
def _api_logada(request, tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'api.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(bind=eng)

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = _db
    if "login_real" not in request.keywords:
        main.app.dependency_overrides[main.exigir_login] = _login_simulado
    yield
    main.app.dependency_overrides.clear()
    eng.dispose()


def pytest_configure(config):
    config.addinivalue_line("markers", "login_real: usa o login de verdade (sem operador simulado)")
