"""Testes de cadastro (clientes, ensaios, relatórios salvos), busca, qualidade dos
dados e regressão do trecho elástico, usando um banco SQLite temporário."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend import main
from backend.acquisition import build_ensaio_dataframe, persist_ensaio
from backend.calculator import calculate_kpis, elastic_fit
from backend.database import Base, EnsaioDB, get_db, migrate
from backend.qualidade import avaliar_qualidade


def _samples(romper: bool = True, n: int = 200) -> list[dict]:
    """Curva sintética: trecho linear, encruamento até Fmáx e queda brusca."""
    out = []
    for i in range(n):
        d = i * 0.05
        if i < 60:
            f = 400.0 * d                          # elástico (k = 400 N/mm)
        else:
            f = 1200.0 + 300.0 * np.log1p(d - 3.0)  # encruamento
        out.append({"t_ms": i * 100, "forca": f, "deslocamento": d})
    if romper:
        last = out[-1]
        for j in range(1, 4):
            out.append({"t_ms": last["t_ms"] + j * 100, "forca": 5.0, "deslocamento": last["deslocamento"] + j * 0.05})
    return out


@pytest.fixture()
def client(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 't.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(bind=eng)

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = _db
    c = TestClient(main.app)
    c.Session = Session
    yield c
    main.app.dependency_overrides.clear()


def _novo_ensaio(client, filename="CLP_1.csv", romper=True) -> int:
    db = client.Session()
    try:
        meta, df = build_ensaio_dataframe(_samples(romper), 20.0, 50.0, filename=filename)
        rec = persist_ensaio(db, meta, df, filename=filename,
                             params={"area_seccao": 20.0, "comprimento_inicial": 50.0})
        return rec.id
    finally:
        db.close()


def test_elastic_fit_r2_and_rupture():
    meta, df = build_ensaio_dataframe(_samples(), 20.0, 50.0)
    fit = elastic_fit(df)
    assert fit is not None
    assert fit["r2"] > 0.999
    # E = k·L0/A = 400·50/20 = 1000 MPa
    assert fit["inclinacao"] == pytest.approx(1000.0, rel=0.02)

    kpis = calculate_kpis(df, ihm_params={"area_seccao": 20.0, "comprimento_inicial": 50.0})
    assert kpis["ruptura_detectada"] is True
    assert kpis["r2_elastico"] > 0.999
    assert kpis["tensao_rp02_MPa"] is not None


def test_qualidade_status():
    _, df = build_ensaio_dataframe(_samples(), 20.0, 50.0)
    params = {"area_seccao": 20.0, "comprimento_inicial": 50.0}
    itens = {i["chave"]: i for i in avaliar_qualidade(df, calculate_kpis(df, params), params)}
    assert set(itens) == {"dados_faltantes", "dados_completos", "curva_valida",
                          "ruptura_detectada", "alongamento_estimado"}
    assert itens["dados_completos"]["status"] == "ok"
    assert itens["curva_valida"]["status"] == "ok"
    assert itens["ruptura_detectada"]["status"] == "ok"
    assert itens["dados_faltantes"]["status"] == "ok"
    assert itens["alongamento_estimado"]["status"] == "info"

    _, df2 = build_ensaio_dataframe(_samples(romper=False), 20.0, 50.0)
    itens2 = {i["chave"]: i for i in avaliar_qualidade(df2, calculate_kpis(df2, params), params)}
    assert itens2["ruptura_detectada"]["status"] == "aviso"


def test_clientes_ensaio_relatorio_e_busca(client):
    r = client.post("/api/clientes", json={"nome": "Metalúrgica São João", "cidade_uf": "Campinas/SP"})
    assert r.status_code == 201
    cid = r.json()["id"]

    eid = _novo_ensaio(client)
    r = client.patch(f"/api/ensaios/{eid}", json={"cliente_id": cid, "amostra": "Barra aço 1020", "norma": "ASTM E8/E8M"})
    assert r.status_code == 200
    assert r.json()["cliente_nome"] == "Metalúrgica São João"

    lista = client.get("/api/ensaios").json()
    assert lista[0]["amostra"] == "Barra aço 1020"

    q = client.get(f"/api/ensaios/{eid}/qualidade").json()
    assert q["status"] in ("ok", "aviso")

    campos = client.get(f"/api/ensaios/{eid}/campos-relatorio").json()
    assert campos["cliente"]["nome"] == "Metalúrgica São João"
    assert campos["condicoes"]["norma_referencia"] == "ASTM E8/E8M"
    assert campos["condicoes"]["comprimento_inicial_mm"] == "50,00"

    r = client.post("/api/relatorio", json={"ensaio_id": eid, "empresa": {"numero_relatorio": "0001/2026"}})
    assert r.status_code == 200
    rid = int(r.headers["X-Relatorio-Id"])
    rels = client.get(f"/api/relatorios?cliente_id={cid}").json()
    assert [x["id"] for x in rels] == [rid]
    assert "<html" in client.get(f"/api/relatorios/{rid}/html").text.lower()

    # Busca sem acento e com várias palavras
    res = client.get("/api/busca", params={"q": "sao joao aco"}).json()["resultados"]
    assert [(x["tipo"], x["id"]) for x in res] == [("teste", eid)]
    res = client.get("/api/busca", params={"q": "metalurgica", "tipo": "relatorio"}).json()["resultados"]
    assert [x["id"] for x in res] == [rid]
    res = client.get("/api/busca", params={"q": "campinas", "tipo": "cliente"}).json()["resultados"]
    assert [x["id"] for x in res] == [cid]

    # Apagar o cliente não apaga o ensaio
    assert client.delete(f"/api/clientes/{cid}").status_code == 204
    assert client.get(f"/api/ensaios/{eid}").json()["cliente_id"] is None


def test_normas():
    c = TestClient(main.app)
    tracao = c.get("/api/normas", params={"tipo": "tracao"}).json()
    assert any(n["codigo"] == "ASTM D638" for n in tracao)
    assert all(n["tipo"] == "tracao" for n in tracao)


def test_migra_banco_antigo(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'old.db'}")
    with eng.begin() as conn:
        conn.execute(text("CREATE TABLE ensaios (id INTEGER PRIMARY KEY, nome VARCHAR, filename VARCHAR)"))
        conn.execute(text("INSERT INTO ensaios (nome, filename) VALUES ('a', 'a.csv')"))
    Base.metadata.create_all(bind=eng)
    migrate(eng)
    with eng.begin() as conn:
        cols = {r[1] for r in conn.execute(text("PRAGMA table_info(ensaios)"))}
        assert {"cliente_id", "amostra", "norma", "setup_json"} <= cols
        assert conn.execute(text("SELECT amostra FROM ensaios")).scalar() == ""


def _novo_ensaio_flexao(client, filename="FLX_1.csv") -> int:
    from backend.flexao.acquisition import build_ensaio_flexao_dataframe, persist_ensaio_flexao
    samples = [{"t_ms": i * 100, "forca": 50.0 * i if i < 38 else 5.0, "deslocamento": i * 0.5}
               for i in range(40)]
    geom = {"largura_mm": 10.0, "espessura_mm": 4.0, "span_mm": 64.0, "norma": "ISO 178"}
    db = client.Session()
    try:
        meta, df = build_ensaio_flexao_dataframe(samples, 10.0, 4.0, 64.0, filename=filename)
        return persist_ensaio_flexao(db, meta, df, filename=filename, geom=geom).id
    finally:
        db.close()


def test_relatorio_flexao(client):
    fid = _novo_ensaio_flexao(client)
    outro = _novo_ensaio_flexao(client, "FLX_2.csv")
    eid = _novo_ensaio(client)

    campos = client.get(f"/api/flexao/ensaios/{fid}/campos-relatorio").json()
    assert campos["condicoes"]["distancia_garras_mm"] == "64,00"
    assert campos["condicoes"]["largura_cp_mm"] == "10,00"

    r = client.post("/api/relatorio", json={
        "ensaio_id": fid, "tipo": "flexao", "include_graficos_adicionais": True,
        "include_comparativo": True, "comparacao_ids": [outro], "include_raw_data": True,
    })
    assert r.status_code == 200, r.text
    html = r.text
    assert "Relatório de Ensaio de Flexão" in html
    assert "Resistência à Flexão (σfM)" in html
    assert "Tração" not in html
    rid = int(r.headers["X-Relatorio-Id"])

    rels = {x["id"]: x for x in client.get("/api/relatorios").json()}
    assert rels[rid]["tipo"] == "flexao" and rels[rid]["ensaio_id"] == fid
    assert [x["id"] for x in client.get("/api/relatorios", params={"tipo": "tracao"}).json()] == []

    # Reimportar o ensaio de tração de mesmo id não mexe no relatório da flexão
    assert eid == fid
    db = client.Session()
    try:
        main._cadastro_de(db, db.query(EnsaioDB).get(eid))
        db.commit()
    finally:
        db.close()
    assert rels[rid]["ensaio_id"] == client.get("/api/relatorios").json()[0]["ensaio_id"] == fid
