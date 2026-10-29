from __future__ import annotations

import asyncio
import io
import json
import os
import socket
import sys
import time
import unicodedata
from contextlib import asynccontextmanager
from pathlib import Path

# Windows: o console usa cp1252 e prints de debug com Unicode (ex.: setas, σ, ε)
# lançavam UnicodeEncodeError, que derrubava ate a gravacao do ensaio. Forca UTF-8
# com fallback para nao quebrar nunca por causa de um print.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except Exception:
        pass

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session, defer

from . import acesso
from .acquisition import build_ensaio_dataframe, persist_ensaio
from .calculator import calculate_kpis, format_chart_data
from .database import (
    ClienteDB,
    EnsaioDB,
    EnsaioFlexaoDB,
    ParametrosIHMDB,
    RelatorioDB,
    SessionLocal,
    engine,
    get_db,
)
from .backup import BackupAgendado
from .flexao.acquisition import build_ensaio_flexao_dataframe, persist_ensaio_flexao
from .flexao.calculator import calculate_kpis as calculate_kpis_flexao
from .flexao.calculator import format_chart_data as format_chart_data_flexao
from .models import (
    Cliente,
    ClienteIn,
    ConfigModel,
    EnsaioUpdate,
    RelatorioSummary,
    ControlSetpointsRequest,
    ControlStartRequest,
    ControlStatus,
    EnsaioDetail,
    EnsaioFlexaoDetail,
    EnsaioFlexaoSummary,
    EnsaioSummary,
    FlexaoControlStartRequest,
    ParametrosIHM,
    RegisterProbeRequest,
    ReportRequest,
)
from .ftp_client import download_csv as ftp_download_csv
from .modbus_client import (
    ModbusController,
    RealtimeModbusReader,
    capture_registers,
    probe_register,
    resolve_register,
)
from .simulator import SIM, SimController, SimReader, sim_capture
from .normas import listar_normas
from .parser import parse_csv
from .qualidade import avaliar_qualidade, avaliar_qualidade_flexao, resumo_status
from .report import generate_html_report
from .watcher import DirectoryWatcher

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

# Na instalação do cliente (servidor.py / executável) MAQ_TRACAO_HOME aponta
# para a pasta da instalação, onde ficam config.json, tracao.db e data/.
_HOME = os.environ.get("MAQ_TRACAO_HOME")
_CONFIG_FILE = (Path(_HOME) if _HOME else Path(__file__).resolve().parent) / "config.json"

_CONFIG_DEFAULTS: dict = {
    "watch_directory": str(Path("data").resolve()),
    "auto_load": True,
    "refresh_interval_s": 5,
    "ihm_ip": "192.168.8.10",
    "ihm_port": 502,
    "ihm_timeout": 3,
    "ihm_registers": [],
    "ftp_port": 21,
    "ftp_user": "",
    "ftp_password": "",
    "ftp_remote_dir": "/",
    "ftp_remote_filename": "",
    "realtime_interval_ms": 100,
    "realtime_bit_name": "teste_ativo_bit",
    "realtime_stop_bit_name": "teste_parada_bit",
    "realtime_forca_name": "forca_atual",
    "realtime_deslocamento_name": "deslocamento_atual",
    "clp_ip": "",
    "clp_port": 502,
    "clp_timeout": 3,
    "plc_family": "dvp",
    "forca_clp_kgf": True,
    "control_registers": [],
    "control_pulse_ms": 300,
    "area_seccao_mm2": 0.0,
    "comprimento_inicial_mm": 0.0,
    "flexao_registers": [],
    "flexao_separados": [],
    "flexao_largura_mm": 0.0,
    "flexao_espessura_mm": 0.0,
    "flexao_span_mm": 0.0,
    "flexao_norma": "ISO 178",
    "flexao_habilitada": True,
    "backup_ativo": False,
    "backup_dir": "",
    "backup_intervalo_h": 24.0,
    "backup_manter": 30,
}


def _load_config() -> dict:
    if _CONFIG_FILE.exists():
        try:
            saved = json.loads(_CONFIG_FILE.read_text(encoding="utf-8"))
            return {**_CONFIG_DEFAULTS, **saved}
        except Exception as exc:
            print(f"[config] Erro ao ler config.json: {exc}", flush=True)
    return dict(_CONFIG_DEFAULTS)


def _save_config(cfg: dict) -> None:
    try:
        _CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:
        print(f"[config] Erro ao salvar config.json: {exc}", flush=True)


_config: dict = _load_config()

_watcher = DirectoryWatcher(callback=lambda p: _load_csv(p))

_backup = BackupAgendado(lambda: _config, Path(engine.url.database).resolve(), _CONFIG_FILE)


# ---------------------------------------------------------------------------
# CLP — conexão e registradores de controle
# ---------------------------------------------------------------------------

# Roles de leitura usados na aquisição/status
_READ_ROLES = (
    "forca_atual", "deslocamento_atual", "material_integro_bit", "ruptura_bit",
    "forca_maxima", "tensao_maxima", "deslocamento_maximo",
    "emergencia", "limite_superior", "limite_inferior",
)
# Roles que são bits (coil/entrada) — devolvidos como bool no status/stream
_BIT_ROLES = ("material_integro_bit", "ruptura_bit", "emergencia", "limite_superior", "limite_inferior")
# Roles extras exibidos no painel (além de força/deslocamento/ruptura)
_EXTRA_ROLES = ("forca_maxima", "tensao_maxima", "deslocamento_maximo",
                "emergencia", "limite_superior", "limite_inferior")


def _clp_conn() -> tuple[str, int, int]:
    """Retorna (ip, port, timeout) do CLP, com fallback para a config da IHM."""
    ip      = _config.get("clp_ip") or _config.get("ihm_ip", "")
    port    = int(_config.get("clp_port") or _config.get("ihm_port", 502))
    timeout = int(_config.get("clp_timeout") or _config.get("ihm_timeout", 3))
    return ip, port, timeout


def _sim_enabled() -> bool:
    """Simulador ligado: usa valores gerados em vez de conectar no CLP real."""
    return bool(_config.get("simulator_enabled", False))


def _make_reader(ip: str, port: int, timeout: int, regs: list[dict]):
    """RealtimeModbusReader real, ou o simulado quando o simulador está ativo."""
    return SimReader(regs) if _sim_enabled() else RealtimeModbusReader(ip, port, timeout, regs)


N_POR_KGF = 9.80665
# Registradores de força lidos (role ou nome) e o setpoint de limite de força
_FORCA_LIDA = ("forca_atual", "forca_maxima")
_FORCA_ESCRITA = ("limite_forca",)


def _forca_em_newton(r: dict) -> dict:
    """Com a força do CLP em kgf (forca_clp_kgf), ajusta a escala dos registradores
    de força para o software trabalhar sempre em N: leitura × 9,80665 e escrita do
    limite de força ÷ 9,80665 (a escrita também multiplica pela escala)."""
    if not _config.get("forca_clp_kgf", True):
        return r
    chaves = {r.get("role"), r.get("name")}
    if chaves & {*_FORCA_LIDA, _config.get("realtime_forca_name", "forca_atual")}:
        fator = N_POR_KGF
    elif chaves & set(_FORCA_ESCRITA):
        fator = 1 / N_POR_KGF
    else:
        return r
    return {**r, "scale": float(r.get("scale", 1.0)) * fator}


def _resolve_registers(regs: list[dict]) -> list[dict]:
    """Converte os dispositivos Delta (D412, M5, X0...) em endereços Modbus conforme
    a família do CLP. Registradores com dispositivo inválido são ignorados (com log)."""
    family = _config.get("plc_family", "dvp")
    out: list[dict] = []
    for r in regs or []:
        try:
            out.append(_forca_em_newton(resolve_register(r, family)))
        except ValueError as exc:
            print(f"[config] Registrador '{r.get('name')}' ignorado: {exc}", flush=True)
    return out


def _control_registers() -> list[dict]:
    return _resolve_registers(_config.get("control_registers", []))


def _make_controller():
    if _sim_enabled():
        return SimController(_control_registers())
    ip, port, timeout = _clp_conn()
    return ModbusController(ip, port, timeout, _control_registers())


def _read_registers_by_role() -> list[dict]:
    return [r for r in _control_registers() if r.get("role") in _READ_ROLES]


def _role_to_name() -> dict[str, str]:
    return {r["role"]: r["name"] for r in _control_registers() if r.get("role") and r.get("name")}


# ---------------------------------------------------------------------------
# CSV loading helper (called at startup and by watcher)
# ---------------------------------------------------------------------------

def _fetch_ihm_params() -> dict | None:
    """Lê registradores de configuração da IHM via Modbus. Registros coil (bits de
    estado transiente) são excluídos — não fazem parte dos parâmetros do ensaio."""
    ip      = _config.get("ihm_ip", "")
    port    = int(_config.get("ihm_port", 502))
    timeout = int(_config.get("ihm_timeout", 3))
    regs    = [r for r in _resolve_registers(_config.get("ihm_registers", []))
               if r.get("data_type", "uint16") not in ("coil", "input")]
    if not ip or not regs:
        return None
    return capture_registers(ip, port, timeout, regs)


def _save_ihm_params(filename: str, db, params: dict) -> None:
    record = ParametrosIHMDB(
        ensaio_filename=filename,
        ihm_ip=_config.get("ihm_ip", ""),
        params_json=json.dumps(params),
    )
    db.add(record)
    db.commit()
    print(f"[modbus] Parâmetros capturados para {filename}: {params}", flush=True)


def _load_csv(filepath: str) -> tuple[bool, str]:
    """Retorna (sucesso, mensagem). Em caso de falha a mensagem descreve o motivo."""
    db = SessionLocal()
    try:
        path = Path(filepath)
        if not path.exists():
            return False, f"Arquivo não encontrado: {path.name}"

        # Skip if already in database
        if db.query(EnsaioDB).filter(EnsaioDB.filename == path.name).first():
            return True, "já importado"

        metadata, df = parse_csv(filepath)

        n_validas = int(df["Forca_N"].dropna().shape[0])
        if n_validas < 10:
            msg = (
                f"Apenas {n_validas} amostra(s) válida(s) após filtrar lapsos temporais. "
                "O ensaio pode estar incompleto ou o arquivo foi coletado antes do início do teste."
            )
            print(f"[loader] Ignorando {path.name}: {msg}", flush=True)
            return False, msg

        # Busca parâmetros da IHM ANTES de calcular KPIs (area_seccao e comprimento_inicial
        # entram diretamente nas fórmulas σ = F/A, ε = ΔL/L₀, A% = (d/L₀)×100)
        ihm_params = _fetch_ihm_params()
        if ihm_params is None and _config.get("ihm_ip"):
            print(f"[modbus] IHM inacessível — parâmetros não capturados para {path.name}", flush=True)

        persist_ensaio(
            db, metadata, df,
            filename=path.name,
            params=ihm_params,
            filepath=str(path.resolve()),
            source_ip=_config.get("ihm_ip", ""),
        )
        print(f"[loader] Loaded: {path.name}", flush=True)
        return True, "ok"

    except Exception as exc:
        msg = f"{type(exc).__name__}: {exc}"
        print(f"[loader] Error loading {filepath}: {msg}", flush=True)
        return False, msg
    finally:
        db.close()


# ---------------------------------------------------------------------------
# IHM helpers (mantidos para compatibilidade com chamadas externas)
# ---------------------------------------------------------------------------

def _capture_ihm_params(filename: str, db) -> None:
    params = _fetch_ihm_params()
    if params is None:
        print(f"[modbus] IHM inacessível — parâmetros não capturados para {filename}", flush=True)
        return
    _save_ihm_params(filename, db, params)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    watch_dir = _config["watch_directory"]
    if Path(watch_dir).exists():
        for csv_file in sorted(Path(watch_dir).glob("*.csv")):
            _load_csv(str(csv_file))
        _watcher.start(watch_dir)
    _backup.start()
    yield
    _backup.stop()
    _watcher.stop()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

# Na instalação do cliente a documentação da API (/docs, /redoc) fica desligada.
_api_docs = {} if not _HOME else {"docs_url": None, "redoc_url": None, "openapi_url": None}
app = FastAPI(title="Analisador de Ensaios de Tração", version="1.0.0", lifespan=lifespan, **_api_docs)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _clientes_por_id(db) -> dict[int, str]:
    return {c.id: c.nome for c in db.query(ClienteDB.id, ClienteDB.nome).all()}


def _ensaio_summary_fields(r: EnsaioDB, clientes: dict[int, str]) -> dict:
    return dict(
        id=r.id,
        nome=r.nome,
        filename=r.filename,
        data_ensaio=r.data_ensaio,
        num_amostras=r.num_amostras,
        forca_max_N=r.forca_max_N,
        tensao_max_MPa=r.tensao_max_MPa,
        created_at=r.created_at,
        cliente_id=r.cliente_id,
        cliente_nome=clientes.get(r.cliente_id, "") if r.cliente_id else "",
        amostra=r.amostra or "",
        norma=r.norma or "",
        operador=r.operador or "",
    )


def _setup_of(r) -> dict:
    try:
        return json.loads(r.setup_json) if getattr(r, "setup_json", None) else {}
    except ValueError:
        return {}


@app.get("/api/ensaios", response_model=list[EnsaioSummary])
def list_ensaios(cliente_id: int | None = None, db: Session = Depends(get_db)):
    # Sem carregar data_json (a curva inteira) só para montar a lista
    q = db.query(EnsaioDB).options(defer(EnsaioDB.data_json))
    if cliente_id is not None:
        q = q.filter(EnsaioDB.cliente_id == cliente_id)
    rows = q.order_by(EnsaioDB.created_at.desc()).all()
    clientes = _clientes_por_id(db)
    return [EnsaioSummary(**_ensaio_summary_fields(r, clientes)) for r in rows]


@app.get("/api/ensaios/{id}", response_model=EnsaioDetail)
def get_ensaio(id: int, db: Session = Depends(get_db)):
    r = db.query(EnsaioDB).filter(EnsaioDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    return EnsaioDetail(
        **_ensaio_summary_fields(r, _clientes_por_id(db)),
        metadata_version=r.metadata_version,
        metadata_equipment_id=r.metadata_equipment_id,
        metadata_code=r.metadata_code,
        alonga_ruptura_pct=r.alonga_ruptura_pct,
        tempo_ruptura_s=r.tempo_ruptura_s,
        observacoes=r.observacoes or "",
        setup=_setup_of(r),
    )


@app.patch("/api/ensaios/{id}", response_model=EnsaioDetail)
def update_ensaio(id: int, body: EnsaioUpdate, db: Session = Depends(get_db)):
    r = db.query(EnsaioDB).filter(EnsaioDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    if body.cliente_id is not None:
        if not db.query(ClienteDB).filter(ClienteDB.id == body.cliente_id).first():
            raise HTTPException(status_code=422, detail="Cliente não encontrado")
        r.cliente_id = body.cliente_id
    if body.limpar_cliente:
        r.cliente_id = None
    for campo in ("nome", "amostra", "norma", "operador", "observacoes"):
        v = getattr(body, campo)
        if v is not None:
            setattr(r, campo, v.strip() if campo != "observacoes" else v)
    db.commit()
    return get_ensaio(id, db)


@app.get("/api/ensaios/{id}/qualidade")
def get_qualidade(id: int, db: Session = Depends(get_db)):
    r = db.query(EnsaioDB).filter(EnsaioDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    df = pd.read_json(io.StringIO(r.data_json))
    ihm_params = _load_ihm_params_for(r.filename, db)
    kpis = calculate_kpis(df, ihm_params=ihm_params)
    itens = avaliar_qualidade(df, kpis, ihm_params)
    return {"status": resumo_status(itens), "itens": itens}


def _load_ihm_params_for(ensaio_filename: str, db) -> dict | None:
    rec = (
        db.query(ParametrosIHMDB)
        .filter(ParametrosIHMDB.ensaio_filename == ensaio_filename)
        .order_by(ParametrosIHMDB.captured_at.desc())
        .first()
    )
    return json.loads(rec.params_json) if rec else None


@app.get("/api/ensaios/{id}/kpis")
def get_kpis(id: int, db: Session = Depends(get_db)):
    r = db.query(EnsaioDB).filter(EnsaioDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    df = pd.read_json(io.StringIO(r.data_json))
    ihm_params = _load_ihm_params_for(r.filename, db)
    return JSONResponse(content=calculate_kpis(df, ihm_params=ihm_params))


@app.get("/api/ensaios/{id}/curvas")
def get_curvas(id: int, db: Session = Depends(get_db)):
    r = db.query(EnsaioDB).filter(EnsaioDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    df = pd.read_json(io.StringIO(r.data_json))
    return JSONResponse(content=format_chart_data(df))


@app.get("/api/ensaios/{id}/parametros_ihm", response_model=ParametrosIHM | None)
def get_parametros_ihm(id: int, db: Session = Depends(get_db)):
    ensaio = db.query(EnsaioDB).filter(EnsaioDB.id == id).first()
    if not ensaio:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    rec = (
        db.query(ParametrosIHMDB)
        .filter(ParametrosIHMDB.ensaio_filename == ensaio.filename)
        .order_by(ParametrosIHMDB.captured_at.desc())
        .first()
    )
    if not rec:
        return None
    return ParametrosIHM(
        id=rec.id,
        ensaio_filename=rec.ensaio_filename,
        captured_at=rec.captured_at,
        ihm_ip=rec.ihm_ip,
        params=json.loads(rec.params_json),
    )


@app.delete("/api/ensaios/{id}", status_code=204)
def delete_ensaio(id: int, db: Session = Depends(get_db)):
    r = db.query(EnsaioDB).filter(EnsaioDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    db.delete(r)
    db.commit()


@app.post("/api/ensaios/{id}/reimport")
def reimport_ensaio(id: int, db: Session = Depends(get_db)):
    """Apaga o ensaio do banco e o re-importa a partir do arquivo CSV original."""
    r = db.query(EnsaioDB).filter(EnsaioDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    filepath = r.filepath
    if not filepath or not Path(filepath).exists():
        raise HTTPException(status_code=422, detail=f"Arquivo não encontrado: {filepath}")
    cadastro = _cadastro_de(db, r)
    db.delete(r)
    db.commit()
    ok, msg = _load_csv(filepath)
    if not ok:
        raise HTTPException(status_code=422, detail=f"Falha ao reimportar: {msg}")
    new_r = db.query(EnsaioDB).filter(EnsaioDB.filename == Path(filepath).name).first()
    if not new_r:
        raise HTTPException(status_code=500, detail="Falha ao reimportar — erro desconhecido")
    _restaurar_cadastro(db, new_r, cadastro)
    return {"id": new_r.id, "nome": new_r.nome, "num_amostras": new_r.num_amostras}


_CAMPOS_CADASTRO = ("nome", "cliente_id", "amostra", "norma", "operador", "observacoes", "setup_json")


def _cadastro_de(db, r: EnsaioDB) -> dict:
    """Cadastro do teste que precisa sobreviver a uma reimportação do CSV. Os
    relatórios do ensaio ficam marcados com o id negativo até a reimportação
    (o SQLite pode reaproveitar ids apagados)."""
    db.query(RelatorioDB).filter(RelatorioDB.ensaio_id == r.id).update({RelatorioDB.ensaio_id: -r.id})
    return {"id": r.id, **{c: getattr(r, c) for c in _CAMPOS_CADASTRO}}


def _restaurar_cadastro(db, new_r: EnsaioDB, cadastro: dict) -> None:
    for c in _CAMPOS_CADASTRO:
        if cadastro.get(c) not in (None, ""):
            setattr(new_r, c, cadastro[c])
    # Relatórios salvos continuam apontando para o ensaio reimportado
    db.query(RelatorioDB).filter(RelatorioDB.ensaio_id == -cadastro["id"]).update(
        {RelatorioDB.ensaio_id: new_r.id})
    db.commit()


@app.post("/api/reimport-all")
def reimport_all(db: Session = Depends(get_db)):
    """Apaga todos os ensaios do banco e os re-importa a partir dos arquivos CSV."""
    rows = db.query(EnsaioDB).all()
    filepaths = [r.filepath for r in rows if r.filepath and Path(r.filepath).exists()]
    cadastros = {Path(r.filepath).name: _cadastro_de(db, r) for r in rows
                 if r.filepath and Path(r.filepath).exists()}
    for r in rows:
        if r.filepath and Path(r.filepath).exists():
            db.delete(r)
    db.commit()
    results = []
    for fp in filepaths:
        ok, msg = _load_csv(fp)
        new_r = db.query(EnsaioDB).filter(EnsaioDB.filename == Path(fp).name).first()
        if ok and new_r and Path(fp).name in cadastros:
            _restaurar_cadastro(db, new_r, cadastros[Path(fp).name])
        results.append({"file": Path(fp).name, "ok": ok, "msg": msg})
    return {"reimported": len([r for r in results if r["ok"]]), "details": results}


@app.post("/api/relatorio")
def generate_report(req: ReportRequest, db: Session = Depends(get_db)):
    r = db.query(EnsaioDB).filter(EnsaioDB.id == req.ensaio_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    df = pd.read_json(io.StringIO(r.data_json))
    ihm_params = _load_ihm_params_for(r.filename, db)
    kpis = calculate_kpis(df, ihm_params=ihm_params)

    comparacao_series = None
    if req.include_comparativo and req.comparacao_ids:
        comparacao_series = []
        for cid in req.comparacao_ids:
            cr = db.query(EnsaioDB).filter(EnsaioDB.id == cid).first()
            if cr:
                try:
                    cdf = pd.read_json(io.StringIO(cr.data_json))
                    comparacao_series.append((cr.nome, cdf))
                except Exception as exc:
                    print(f"[relatorio] falha ao carregar ensaio {cid} para comparativo: {exc}", flush=True)

    html = generate_html_report(r, df, kpis, req, comparacao_series=comparacao_series)

    # Guarda o relatório gerado para abrir/buscar depois
    cliente_id = req.cliente_id or r.cliente_id
    cliente_nome = req.cliente.nome.strip()
    if not cliente_nome and cliente_id:
        c = db.query(ClienteDB).filter(ClienteDB.id == cliente_id).first()
        cliente_nome = c.nome if c else ""
    req_dump = req.model_dump()
    # A foto da amostra pesa e já está no HTML; o logo fica para reaproveitar
    # no próximo relatório.
    req_dump.get("amostra", {}).pop("imagem_data_url", None)
    rel = RelatorioDB(
        ensaio_id=r.id,
        cliente_id=cliente_id,
        numero=req.empresa.numero_relatorio.strip(),
        titulo=r.nome,
        cliente_nome=cliente_nome,
        request_json=json.dumps(req_dump, ensure_ascii=False),
        html=html,
    )
    db.add(rel)
    db.commit()
    return HTMLResponse(content=html, headers={"X-Relatorio-Id": str(rel.id)})


@app.get("/api/ensaios/{id}/campos-relatorio")
def campos_relatorio(id: int, db: Session = Depends(get_db)):
    """Campos do relatório preenchidos automaticamente a partir do ensaio (setup,
    parâmetros da IHM, cliente cadastrado e último relatório gerado)."""
    r = db.query(EnsaioDB).filter(EnsaioDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    setup = _setup_of(r)
    ihm = _load_ihm_params_for(r.filename, db) or {}
    df = pd.read_json(io.StringIO(r.data_json))
    kpis = calculate_kpis(df, ihm_params=ihm or None)

    def _n(v, d=2):
        return "" if v in (None, "") else f"{float(v):.{d}f}".replace(".", ",")

    velocidade = setup.get("velocidade") or kpis.get("velocidade_ihm")
    l0 = setup.get("comprimento_inicial") or ihm.get("comprimento_inicial") or kpis.get("comprimento_inicial_mm")
    condicoes = {
        "data_realizacao": r.data_ensaio or "",
        "comprimento_inicial_mm": _n(l0),
        "velocidade_ensaio": _n(velocidade),
        "norma_referencia": r.norma or "",
        "num_corpos_prova": "1",
    }
    norma = next((n for n in listar_normas() if n["codigo"] == (r.norma or "")), None)
    if norma:
        condicoes["tipo_corpo_prova"] = norma.get("corpo_prova") or ""
        if norma.get("distancia_garras_mm"):
            condicoes["distancia_garras_mm"] = _n(norma["distancia_garras_mm"], 0)

    cliente = None
    if r.cliente_id:
        c = db.query(ClienteDB).filter(ClienteDB.id == r.cliente_id).first()
        if c:
            cliente = {
                "nome": c.nome, "contato": c.contato, "email_cliente": c.email,
                "telefone_cliente": c.telefone, "endereco": c.endereco, "bairro": c.bairro,
                "cidade_uf": c.cidade_uf, "cep": c.cep,
            }

    # Dados da empresa e assinaturas costumam se repetir: reaproveita o último relatório
    ultimo = db.query(RelatorioDB).order_by(RelatorioDB.created_at.desc()).first()
    anterior: dict = {}
    if ultimo and ultimo.request_json:
        try:
            anterior = json.loads(ultimo.request_json)
        except ValueError:
            anterior = {}
    ano = time.strftime("%Y")
    n_ano = db.query(RelatorioDB).filter(RelatorioDB.created_at >= f"{ano}-01-01").count()

    return {
        "cliente_id": r.cliente_id,
        "cliente": cliente,
        "amostra": {"id_interno": r.amostra or "", "id_cliente": ""},
        "condicoes": condicoes,
        "empresa": {k: v for k, v in (anterior.get("empresa") or {}).items() if k != "numero_relatorio"},
        "numero_relatorio_sugerido": f"{n_ano + 1:04d}/{ano}",
        "assinaturas": anterior.get("assinaturas") or [],
        "equipamentos": (anterior.get("condicoes") or {}).get("equipamentos", ""),
    }


# ---------------------------------------------------------------------------
# Relatórios salvos
# ---------------------------------------------------------------------------

def _relatorio_summary(rel: RelatorioDB) -> RelatorioSummary:
    return RelatorioSummary(
        id=rel.id, ensaio_id=rel.ensaio_id, cliente_id=rel.cliente_id,
        numero=rel.numero or "", titulo=rel.titulo or "",
        cliente_nome=rel.cliente_nome or "", created_at=rel.created_at,
    )


@app.get("/api/relatorios", response_model=list[RelatorioSummary])
def list_relatorios(cliente_id: int | None = None, ensaio_id: int | None = None,
                    db: Session = Depends(get_db)):
    q = db.query(RelatorioDB).options(defer(RelatorioDB.html), defer(RelatorioDB.request_json))
    if cliente_id is not None:
        q = q.filter(RelatorioDB.cliente_id == cliente_id)
    if ensaio_id is not None:
        q = q.filter(RelatorioDB.ensaio_id == ensaio_id)
    return [_relatorio_summary(x) for x in q.order_by(RelatorioDB.created_at.desc()).all()]


@app.get("/api/relatorios/{id}/html")
def get_relatorio_html(id: int, download: bool = False, db: Session = Depends(get_db)):
    rel = db.query(RelatorioDB).filter(RelatorioDB.id == id).first()
    if not rel:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="relatorio_{rel.id}.html"'
    return HTMLResponse(content=rel.html or "", headers=headers)


@app.delete("/api/relatorios/{id}", status_code=204)
def delete_relatorio(id: int, db: Session = Depends(get_db)):
    rel = db.query(RelatorioDB).filter(RelatorioDB.id == id).first()
    if not rel:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    db.delete(rel)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Clientes
# ---------------------------------------------------------------------------

def _cliente_out(c: ClienteDB, db) -> Cliente:
    return Cliente(
        id=c.id, created_at=c.created_at,
        **{k: getattr(c, k) or "" for k in ClienteIn.model_fields},
        num_ensaios=db.query(EnsaioDB).filter(EnsaioDB.cliente_id == c.id).count(),
        num_relatorios=db.query(RelatorioDB).filter(RelatorioDB.cliente_id == c.id).count(),
    )


@app.get("/api/clientes", response_model=list[Cliente])
def list_clientes(db: Session = Depends(get_db)):
    return [_cliente_out(c, db) for c in db.query(ClienteDB).order_by(ClienteDB.nome).all()]


@app.post("/api/clientes", response_model=Cliente, status_code=201)
def create_cliente(body: ClienteIn, db: Session = Depends(get_db)):
    if not body.nome.strip():
        raise HTTPException(status_code=422, detail="Informe o nome do cliente.")
    c = ClienteDB(**{k: (v.strip() if isinstance(v, str) else v) for k, v in body.model_dump().items()})
    db.add(c)
    db.commit()
    db.refresh(c)
    return _cliente_out(c, db)


@app.put("/api/clientes/{id}", response_model=Cliente)
def update_cliente(id: int, body: ClienteIn, db: Session = Depends(get_db)):
    c = db.query(ClienteDB).filter(ClienteDB.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    if not body.nome.strip():
        raise HTTPException(status_code=422, detail="Informe o nome do cliente.")
    for k, v in body.model_dump().items():
        setattr(c, k, v.strip() if isinstance(v, str) else v)
    db.commit()
    return _cliente_out(c, db)


@app.delete("/api/clientes/{id}", status_code=204)
def delete_cliente(id: int, db: Session = Depends(get_db)):
    """Remove o cliente; ensaios e relatórios dele continuam, só sem cliente."""
    c = db.query(ClienteDB).filter(ClienteDB.id == id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    for model in (EnsaioDB, EnsaioFlexaoDB, RelatorioDB):
        db.query(model).filter(model.cliente_id == id).update({model.cliente_id: None})
    db.delete(c)
    db.commit()
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Busca inteligente (clientes, testes e relatórios)
# ---------------------------------------------------------------------------

def _norm(texto: str) -> str:
    """Minúsculas e sem acento, para 'tracao' achar 'Tração'."""
    t = unicodedata.normalize("NFKD", texto or "")
    return "".join(ch for ch in t if not unicodedata.combining(ch)).lower()


def _pontuar(termos: list[str], titulo: str, campos: str) -> int:
    """0 se algum termo não aparece; senão, mais pontos para termos no título e
    para palavras que começam com o termo."""
    t_norm, c_norm = _norm(titulo), _norm(campos)
    total = 0
    for termo in termos:
        if termo in t_norm:
            total += 3 + (2 if any(w.startswith(termo) for w in t_norm.split()) else 0)
        elif termo in c_norm:
            total += 1 + (1 if any(w.startswith(termo) for w in c_norm.split()) else 0)
        else:
            return 0
    return total


@app.get("/api/busca")
def busca(q: str = "", tipo: str = "todos", cliente_id: int | None = None,
          limite: int = 50, db: Session = Depends(get_db)):
    """Busca por várias palavras ao mesmo tempo (todas precisam aparecer), sem
    diferenciar acento e maiúscula, em clientes, ensaios (tração e flexão) e
    relatórios. tipo: todos | cliente | teste | relatorio."""
    termos = [_norm(t) for t in q.split() if t.strip()]
    clientes = {c.id: c for c in db.query(ClienteDB).all()}
    res: list[dict] = []

    def _add(score, item):
        if score or not termos:
            item["score"] = score
            res.append(item)

    if tipo in ("todos", "cliente"):
        for c in clientes.values():
            if cliente_id is not None and c.id != cliente_id:
                continue
            campos = " ".join([c.documento, c.contato, c.email, c.telefone, c.cidade_uf, c.observacoes or ""])
            _add(_pontuar(termos, c.nome, campos), {
                "tipo": "cliente", "id": c.id, "titulo": c.nome,
                "subtitulo": " · ".join(x for x in (c.contato, c.cidade_uf) if x),
                "data": c.created_at.isoformat() if c.created_at else None,
            })

    if tipo in ("todos", "teste"):
        for modo, model in (("tracao", EnsaioDB), ("flexao", EnsaioFlexaoDB)):
            q_ens = db.query(model).options(defer(model.data_json))
            if cliente_id is not None:
                q_ens = q_ens.filter(model.cliente_id == cliente_id)
            for e in q_ens.all():
                cli = clientes.get(e.cliente_id)
                titulo = e.nome or e.filename
                campos = " ".join(str(x) for x in (
                    e.filename, e.data_ensaio, e.amostra or "", e.norma or "",
                    e.operador or "", e.observacoes or "", cli.nome if cli else "",
                    "tracao" if modo == "tracao" else "flexao",
                ))
                _add(_pontuar(termos, titulo, campos), {
                    "tipo": "teste", "modo": modo, "id": e.id, "titulo": titulo,
                    "subtitulo": " · ".join(x for x in (
                        "Tração" if modo == "tracao" else "Flexão",
                        cli.nome if cli else "", e.amostra or "", e.norma or "",
                        ("Fmáx " + f"{e.forca_max_N / 1000:.2f}".replace(".", ",") + " kN") if e.forca_max_N else "",
                    ) if x),
                    "data": e.created_at.isoformat() if e.created_at else None,
                    "cliente_id": e.cliente_id,
                })

    if tipo in ("todos", "relatorio"):
        q_rel = db.query(RelatorioDB).options(defer(RelatorioDB.html), defer(RelatorioDB.request_json))
        if cliente_id is not None:
            q_rel = q_rel.filter(RelatorioDB.cliente_id == cliente_id)
        for rel in q_rel.all():
            titulo = f"Relatório {rel.numero}" if rel.numero else f"Relatório #{rel.id}"
            campos = " ".join([rel.titulo or "", rel.cliente_nome or "", "relatorio",
                               rel.created_at.strftime("%d/%m/%Y") if rel.created_at else ""])
            _add(_pontuar(termos, titulo, campos), {
                "tipo": "relatorio", "id": rel.id, "titulo": titulo,
                "subtitulo": " · ".join(x for x in (rel.cliente_nome, rel.titulo) if x),
                "data": rel.created_at.isoformat() if rel.created_at else None,
                "ensaio_id": rel.ensaio_id, "cliente_id": rel.cliente_id,
            })

    res.sort(key=lambda x: (-x["score"], x["data"] and -_ts(x["data"]) or 0))
    return {"total": len(res), "resultados": res[:max(1, min(limite, 500))]}


def _ts(iso: str) -> float:
    from datetime import datetime as _dt
    try:
        return _dt.fromisoformat(iso).timestamp()
    except ValueError:
        return 0.0


@app.get("/api/backup")
def backup_status():
    return _backup.status()


@app.post("/api/backup/agora")
def backup_agora():
    try:
        return _backup.executar()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha no backup: {exc}")


@app.get("/api/normas")
def get_normas(tipo: str | None = None):
    return listar_normas(tipo)


def exigir_tecnico(x_config_token: str | None = Header(default=None)) -> None:
    """Rotas que mudam configuração/registradores exigem o token da senha."""
    if not acesso.token_valido(x_config_token):
        raise HTTPException(status_code=401, detail="Senha das Configurações necessária.")


class _SenhaIn(BaseModel):
    senha: str


class _TrocaSenhaIn(BaseModel):
    atual: str
    nova: str


@app.post("/api/config/login")
def config_login(body: _SenhaIn):
    if not acesso.confere(body.senha, _config):
        time.sleep(1)  # atrasa tentativas por força bruta
        raise HTTPException(status_code=401, detail="Senha incorreta.")
    return {"token": acesso.novo_token()}


@app.post("/api/config/logout")
def config_logout(x_config_token: str | None = Header(default=None)):
    acesso.encerrar(x_config_token)
    return {"ok": True}


@app.get("/api/config/sessao")
def config_sessao(x_config_token: str | None = Header(default=None)):
    return {"ok": acesso.token_valido(x_config_token)}


@app.post("/api/config/senha", dependencies=[Depends(exigir_tecnico)])
def config_trocar_senha(body: _TrocaSenhaIn):
    if not acesso.confere(body.atual, _config):
        raise HTTPException(status_code=401, detail="Senha atual incorreta.")
    if len(body.nova) < 4:
        raise HTTPException(status_code=422, detail="A senha nova precisa ter ao menos 4 caracteres.")
    _config["senha_config"] = acesso.hash_senha(body.nova)
    _save_config(_config)
    return {"ok": True}


@app.get("/api/config")
def get_config():
    return JSONResponse(content={k: v for k, v in _config.items() if k != "senha_config"})


@app.put("/api/config", dependencies=[Depends(exigir_tecnico)])
def update_config(body: ConfigModel):
    _config.update(body.model_dump())
    _save_config(_config)
    if body.auto_load:
        _watcher.start(body.watch_directory)
        for csv_file in sorted(Path(body.watch_directory).glob("*.csv")):
            _load_csv(str(csv_file))
    else:
        _watcher.stop()
    return JSONResponse(content={k: v for k, v in _config.items() if k != "senha_config"})


@app.post("/api/scan")
def scan_directory():
    watch_dir = _config["watch_directory"]
    loaded: list[str] = []
    if Path(watch_dir).exists():
        for csv_file in sorted(Path(watch_dir).glob("*.csv")):
            _load_csv(str(csv_file))
            loaded.append(csv_file.name)
    return {"scanned": loaded}


@app.post("/api/ftp/fetch_csv")
def fetch_csv_via_ftp(db: Session = Depends(get_db)):
    """Baixa o arquivo CSV da IHM via FTP e importa o ensaio."""
    from datetime import datetime as _dt

    host          = _config.get("ihm_ip", "")
    ftp_port      = int(_config.get("ftp_port", 21))
    user          = _config.get("ftp_user", "")
    password      = _config.get("ftp_password", "")
    remote_dir    = _config.get("ftp_remote_dir", "/")
    remote_fname  = _config.get("ftp_remote_filename", "")

    if not host:
        raise HTTPException(status_code=400, detail="IP da IHM não configurado — preencha o campo 'IP da IHM' em Configurações → Conexão IHM.")
    if not remote_fname:
        raise HTTPException(status_code=400, detail="Nome do arquivo remoto não configurado — preencha o campo 'Nome do arquivo remoto' em Configurações → FTP.")

    ts = _dt.now().strftime("%Y%m%d_%H%M%S")
    filename = f"FTP_{ts}_{remote_fname}"
    watch_dir = Path(_config["watch_directory"])
    watch_dir.mkdir(parents=True, exist_ok=True)
    dest = watch_dir / filename

    try:
        ftp_download_csv(host, ftp_port, user, password, remote_dir, remote_fname, dest)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    ok, msg = _load_csv(str(dest))
    if not ok:
        raise HTTPException(status_code=422, detail=f"Arquivo recebido mas falhou ao importar: {msg}")

    rec = db.query(EnsaioDB).filter(EnsaioDB.filename == filename).first()
    if not rec:
        raise HTTPException(status_code=500, detail="Arquivo recebido mas falhou ao importar: erro desconhecido")

    return {
        "status": "ok",
        "bytes_received": dest.stat().st_size,
        "filename": filename,
        "ensaio_id": rec.id,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/clp/conexao")
def clp_conexao():
    """Indicador de conexão: tenta ler a força atual (prova que a IHM/CLP responde
    em Modbus); sem esse registrador mapeado, testa só a porta TCP."""
    ip, port, timeout = _clp_conn()
    if _sim_enabled():
        return {"online": True, "ip": ip or "simulador", "port": port, "simulador": True,
                "latencia_ms": 0, "motivo": ""}
    if not ip:
        return {"online": False, "ip": "", "port": port, "simulador": False,
                "latencia_ms": None, "motivo": "IP não configurado"}
    t0 = time.perf_counter()
    forca = [r for r in _read_registers_by_role() if r.get("role") == "forca_atual"]
    motivo = ""
    if forca:
        data = capture_registers(ip, port, min(timeout, 2), forca)
        online = data is not None and data.get(forca[0]["name"]) is not None
        if not online:
            motivo = "sem resposta Modbus" if data is None else "registrador de força sem leitura"
    else:
        try:
            with socket.create_connection((ip, port), timeout=min(timeout, 2)):
                online = True
        except OSError as exc:
            online, motivo = False, str(exc)
    return {
        "online": online, "ip": ip, "port": port, "simulador": False,
        "latencia_ms": round((time.perf_counter() - t0) * 1000) if online else None,
        "motivo": motivo,
    }


# ---------------------------------------------------------------------------
# Controle da máquina — escrita de comandos/setpoints no CLP
# ---------------------------------------------------------------------------

def _aplicar_cadastro(db, rec, info: dict | None) -> None:
    """Preenche automaticamente o ensaio recém-gravado com o cadastro informado no
    Controle (cliente, amostra, norma, operador e setup usado)."""
    if not info:
        return
    try:
        cid = info.get("cliente_id")
        if cid and db.query(ClienteDB).filter(ClienteDB.id == cid).first():
            rec.cliente_id = cid
        for campo in ("amostra", "norma", "operador"):
            if info.get(campo) and hasattr(rec, campo):
                setattr(rec, campo, info[campo])
        if info.get("setup") and hasattr(rec, "setup_json"):
            rec.setup_json = json.dumps(info["setup"])
        db.commit()
    except Exception as exc:
        print(f"[control] Falha ao gravar cadastro do ensaio: {exc}", flush=True)

def _apply_setpoints(ctrl: ModbusController, *, velocidade, deslocamento, limite_forca) -> dict:
    """Escreve apenas os setpoints numéricos (ignora os None e os roles não configurados).

    O sentido NÃO é escrito aqui — ele é disparado como pulso momentâneo por
    :func:`_pulse_sentido`, pois travar o coil de sentido em nível alto mantém a
    máquina/CLP em estado ativo (e faz o CLP sobrescrever os registradores)."""
    applied: dict = {}
    for role, value in (
        ("limite_forca", limite_forca),
        ("velocidade", velocidade),
        ("deslocamento_programado", deslocamento),
    ):
        if value is not None and ctrl.resolve(role) is not None:
            ctrl.write_named(role, value)
            applied[role] = value
    return applied


def _pulse_sentido(ctrl: ModbusController, sentido: str | None, pulse_ms: int) -> str | None:
    """Dispara o coil de sentido como pulso momentâneo (escreve 1 e volta a 0).

    O CLP retém o sentido internamente na borda de subida do pulso, então o bit
    não pode ficar acionado para sempre. Retorna o sentido aplicado ou None."""
    if sentido not in ("cima", "baixo"):
        return None
    role = "sentido_cima" if sentido == "cima" else "sentido_baixo"
    if ctrl.resolve(role) is None:
        return None
    ctrl.pulse(role, pulse_ms)
    return sentido


@app.post("/api/control/start")
def control_start(req: ControlStartRequest):
    ip, port, timeout = _clp_conn()
    if not ip:
        raise HTTPException(status_code=400, detail="IP do CLP não configurado — preencha em Configurações → Controle (CLP).")
    if req.sentido not in ("cima", "baixo"):
        raise HTTPException(status_code=422, detail="Sentido inválido — use 'cima' ou 'baixo'.")
    if req.limite_forca is not None and req.limite_forca <= 0:
        raise HTTPException(status_code=422, detail="Limite de força deve ser maior que zero.")

    ctrl = _make_controller()
    if ctrl.resolve("iniciar") is None:
        raise HTTPException(status_code=400, detail="Registrador 'iniciar' não configurado em Controle (CLP).")
    if not ctrl.connect():
        raise HTTPException(status_code=502, detail=f"CLP inacessível em {ip}:{port}.")

    pulse_ms = int(_config.get("control_pulse_ms", 300))
    try:
        applied = _apply_setpoints(
            ctrl, velocidade=req.velocidade,
            deslocamento=req.deslocamento, limite_forca=req.limite_forca,
        )
        # Persiste área/L0 do setup para a próxima aquisição derivar tensão/deformação
        if req.area_seccao is not None:
            _config["area_seccao_mm2"] = req.area_seccao
        if req.comprimento_inicial is not None:
            _config["comprimento_inicial_mm"] = req.comprimento_inicial
        _config["proximo_ensaio"] = {
            "cliente_id": req.cliente_id, "amostra": req.amostra.strip(),
            "norma": req.norma.strip(), "operador": req.operador.strip(),
            "setup": {
                "sentido": req.sentido, "velocidade": req.velocidade,
                "deslocamento": req.deslocamento, "limite_forca": req.limite_forca,
                "area_seccao": req.area_seccao, "comprimento_inicial": req.comprimento_inicial,
            },
        }
        _save_config(_config)

        # Setpoints escritos → pulso de sentido (momentâneo) → pulso de início.
        sent = _pulse_sentido(ctrl, req.sentido, pulse_ms)
        if sent:
            applied["sentido"] = sent
        ctrl.pulse("iniciar", pulse_ms)
        return {"status": "started", "sentido": req.sentido, "setpoints": applied}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao iniciar ensaio: {exc}")
    finally:
        ctrl.close()


@app.post("/api/control/stop")
def control_stop():
    ip, port, timeout = _clp_conn()
    if not ip:
        raise HTTPException(status_code=400, detail="IP do CLP não configurado.")
    ctrl = _make_controller()
    if ctrl.resolve("parar") is None:
        raise HTTPException(status_code=400, detail="Registrador 'parar' não configurado em Controle (CLP).")
    if not ctrl.connect():
        raise HTTPException(status_code=502, detail=f"CLP inacessível em {ip}:{port}.")
    pulse_ms = int(_config.get("control_pulse_ms", 300))
    try:
        ctrl.pulse("parar", pulse_ms)
        # Segurança: zera os sentidos
        for role in ("sentido_cima", "sentido_baixo"):
            if ctrl.resolve(role) is not None:
                ctrl.write_named(role, 0)
        return {"status": "stopped"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao parar ensaio: {exc}")
    finally:
        ctrl.close()


def _pulse_command(make_controller, role: str, label: str) -> dict:
    """Conecta, pulsa um coil de comando momentâneo (role) e fecha. Usado por
    comandos como zerar deslocamento e zerar célula de carga."""
    ip, port, timeout = _clp_conn()
    if not ip:
        raise HTTPException(status_code=400, detail="IP do CLP não configurado em Configurações → Controle (CLP).")
    ctrl = make_controller()
    if ctrl.resolve(role) is None:
        raise HTTPException(status_code=400, detail=f"Registrador '{role}' não configurado em Controle (CLP).")
    if not ctrl.connect():
        raise HTTPException(status_code=502, detail=f"CLP inacessível em {ip}:{port}.")
    pulse_ms = int(_config.get("control_pulse_ms", 300))
    try:
        ctrl.pulse(role, pulse_ms)
        return {"status": "ok", "comando": role}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao {label}: {exc}")
    finally:
        ctrl.close()


@app.post("/api/control/zerar-deslocamento")
def control_zerar_deslocamento():
    """Pulsa o bit que zera o deslocamento (limpa o resíduo antes de um novo ensaio)."""
    return _pulse_command(_make_controller, "zerar_deslocamento", "zerar o deslocamento")


@app.post("/api/control/zerar-celula")
def control_zerar_celula():
    """Pulsa o bit que zera a célula de carga — isso também para o ensaio em curso."""
    return _pulse_command(_make_controller, "zerar_celula", "zerar a célula de carga")


@app.post("/api/control/probe", dependencies=[Depends(exigir_tecnico)])
def control_probe(req: RegisterProbeRequest):
    """Testa um registrador isolado (leitura/escrita) contra a IHM/CLP e devolve
    o que foi/voltou no fio. Útil para descobrir tipo, endereço e ordem de palavra
    sem mexer no mapa de controle salvo."""
    ip, port, timeout = _clp_conn()
    if not ip:
        raise HTTPException(status_code=400, detail="IP do CLP/IHM não configurado em Configurações → Controle (CLP).")
    if req.direction not in ("read", "write"):
        raise HTTPException(status_code=422, detail="direction deve ser 'read' ou 'write'.")
    if req.direction == "write" and req.value is None:
        raise HTTPException(status_code=422, detail="Informe um valor para escrita.")
    reg = {
        "name": req.name,
        "address": req.address,
        "device": req.device,
        "data_type": req.data_type,
        "scale": req.scale,
        "word_order": req.word_order,
    }
    try:
        reg = resolve_register(reg, _config.get("plc_family", "dvp"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if _sim_enabled():
        decoded = SIM.value_for_register(reg)
        return {
            "ok": True, "direction": req.direction, "address": req.address,
            "name": req.name, "data_type": req.data_type, "word_order": req.word_order,
            "scale": req.scale, "ip": "simulador", "port": 0,
            "sent_words": None, "read_words": None, "decoded": decoded,
            "as_float": float(decoded) if isinstance(decoded, (int, float)) else None,
            "as_int": int(decoded) if isinstance(decoded, (int, float)) else None,
            "error": None,
        }
    return probe_register(ip, port, timeout, reg, direction=req.direction, value=req.value)


@app.post("/api/control/setpoints")
def control_setpoints(req: ControlSetpointsRequest):
    ip, port, timeout = _clp_conn()
    if not ip:
        raise HTTPException(status_code=400, detail="IP do CLP não configurado.")
    if req.limite_forca is not None and req.limite_forca <= 0:
        raise HTTPException(status_code=422, detail="Limite de força deve ser maior que zero.")
    ctrl = _make_controller()
    if not ctrl.connect():
        raise HTTPException(status_code=502, detail=f"CLP inacessível em {ip}:{port}.")
    try:
        applied = _apply_setpoints(
            ctrl, velocidade=req.velocidade,
            deslocamento=req.deslocamento, limite_forca=req.limite_forca,
        )
        sent = _pulse_sentido(ctrl, req.sentido, int(_config.get("control_pulse_ms", 300)))
        if sent:
            applied["sentido"] = sent
        return {"status": "ok", "setpoints": applied}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao escrever setpoints: {exc}")
    finally:
        ctrl.close()


@app.get("/api/control/status", response_model=ControlStatus)
def control_status():
    ip, port, timeout = _clp_conn()
    regs = _read_registers_by_role()
    if not regs or (not ip and not _sim_enabled()):
        return ControlStatus(online=False)
    data = sim_capture(regs) if _sim_enabled() else capture_registers(ip, port, timeout, regs)
    if data is None:
        return ControlStatus(online=False)
    rn = _role_to_name()
    def _val(role):
        name = rn.get(role)
        return data.get(name) if name else None
    integro = _val("material_integro_bit")
    ruptura = _val("ruptura_bit")
    return ControlStatus(
        online=True,
        forca_atual=_val("forca_atual"),
        deslocamento_atual=_val("deslocamento_atual"),
        material_integro=bool(integro) if integro is not None else None,
        ruptura=bool(ruptura) if ruptura is not None else None,
        ativo=None,
        **_extras(data, rn),
    )


def _extras(data: dict, rn: dict[str, str]) -> dict:
    """Valores extras da tela de ensaio (máximos do CLP, emergência e fins de curso)."""
    out: dict = {}
    for role in _EXTRA_ROLES:
        name = rn.get(role)
        v = data.get(name) if name else None
        out[role] = (bool(v) if v is not None else None) if role in _BIT_ROLES else v
    return out


# ---------------------------------------------------------------------------
# Aquisição do CLP — SSE stream com gravação direta no banco
# ---------------------------------------------------------------------------

@app.get("/api/control/stream")
async def control_stream(request: Request):
    """Stream SSE que lê força/deslocamento do CLP, acumula as amostras e, ao
    detectar ruptura (bit de ruptura, se mapeado), grava o ensaio direto no banco
    e emite {"saved_ensaio_id": N}. Se o cliente desconectar (ex.: botão Parar)
    depois de coletar dados, o ensaio também é gravado."""
    ip, port, timeout = _clp_conn()
    interval_ms = max(50, int(_config.get("realtime_interval_ms", 100)))
    regs = _read_registers_by_role()
    rn = _role_to_name()
    forca_name   = rn.get("forca_atual")
    desl_name    = rn.get("deslocamento_atual")
    integro_name = rn.get("material_integro_bit")
    ruptura_name = rn.get("ruptura_bit")

    if not forca_name or (not ip and not _sim_enabled()):
        async def _err():
            yield f"data: {json.dumps({'error': 'clp_nao_configurado'})}\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    reader = _make_reader(ip, port, timeout, regs)
    loop   = asyncio.get_event_loop()
    area = float(_config.get("area_seccao_mm2", 0) or 0)
    l0   = float(_config.get("comprimento_inicial_mm", 0) or 0)

    def _persist(samples: list[dict]) -> int | None:
        if len(samples) < 10:
            return None
        db = SessionLocal()
        try:
            filename = f"CLP_{time.strftime('%Y%m%d_%H%M%S')}.csv"
            metadata, df = build_ensaio_dataframe(samples, area, l0, filename=filename)
            if int(df["Forca_N"].dropna().shape[0]) < 10:
                return None
            params = {"area_seccao": area, "comprimento_inicial": l0} if (area > 0 and l0 > 0) else None
            rec = persist_ensaio(db, metadata, df, filename=filename, params=params, source_ip=ip)
            _aplicar_cadastro(db, rec, _config.get("proximo_ensaio"))
            return rec.id
        except Exception as exc:
            print(f"[control] Falha ao persistir ensaio: {exc}", flush=True)
            return None
        finally:
            db.close()

    async def generate():
        samples: list[dict] = []
        t_start: float | None = None
        last_ruptura = False
        saved = False
        try:
            connected = await loop.run_in_executor(None, reader.connect)
            if not connected:
                yield f"data: {json.dumps({'error': 'clp_offline'})}\n\n"
                return

            while True:
                if await request.is_disconnected():
                    break

                data = await loop.run_in_executor(None, reader.read)
                if data is None:
                    yield f"data: {json.dumps({'error': 'reconnecting'})}\n\n"
                    await asyncio.sleep(1.0)
                    await loop.run_in_executor(None, reader.connect)
                    continue

                forca   = data.get(forca_name)
                desl    = data.get(desl_name) if desl_name else None
                integro = bool(data.get(integro_name, 0)) if integro_name else None
                ruptura = bool(data.get(ruptura_name, 0)) if ruptura_name else False

                if t_start is None and forca is not None:
                    t_start = time.time()
                elapsed_ms = int((time.time() - t_start) * 1000) if t_start else 0

                if forca is not None:
                    samples.append({"t_ms": elapsed_ms, "forca": forca, "deslocamento": desl or 0.0})

                # Borda de subida na ruptura → grava e encerra
                if ruptura and not last_ruptura:
                    saved = True
                    saved_id = await loop.run_in_executor(None, _persist, samples)
                    yield f"data: {json.dumps({'ruptura': True, 'saved_ensaio_id': saved_id})}\n\n"
                    break
                last_ruptura = ruptura

                payload = json.dumps({
                    "recording":        t_start is not None,
                    "forca":            forca,
                    "deslocamento":     desl,
                    "material_integro": integro,
                    "ruptura":          ruptura,
                    "t_ms":             elapsed_ms,
                    **_extras(data, rn),
                })
                yield f"data: {payload}\n\n"
                await asyncio.sleep(interval_ms / 1000)
        except asyncio.CancelledError:
            pass
        finally:
            # Síncrono de propósito: na desconexão a task está cancelada e um await aqui
            # seria interrompido antes de gravar.
            reader.close()
            # Parado pelo usuário (ou sem bit de ruptura mapeado): grava o que foi coletado.
            if not saved and samples:
                _persist(samples)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Tempo Real — SSE stream
# ---------------------------------------------------------------------------

@app.get("/api/realtime/stream")
async def realtime_stream(request: Request):
    ip           = _config.get("ihm_ip", "")
    port         = int(_config.get("ihm_port", 502))
    timeout      = int(_config.get("ihm_timeout", 3))
    interval_ms   = max(50, int(_config.get("realtime_interval_ms", 100)))
    bit_name      = _config.get("realtime_bit_name", "teste_ativo_bit")
    stop_bit_name = _config.get("realtime_stop_bit_name", "teste_parada_bit")
    forca_name    = _config.get("realtime_forca_name", "forca_atual")
    desl_name     = _config.get("realtime_deslocamento_name", "deslocamento_atual")

    all_regs = _resolve_registers(_config.get("ihm_registers", []))
    rt_regs  = [r for r in all_regs if r["name"] in (bit_name, stop_bit_name, forca_name, desl_name)]

    reader = RealtimeModbusReader(ip, port, timeout, rt_regs)
    loop   = asyncio.get_event_loop()

    async def generate():
        try:
            connected = await loop.run_in_executor(None, reader.connect)
            if not connected:
                yield f"data: {json.dumps({'error': 'ihm_offline'})}\n\n"
                return

            t_start:       float | None = None
            last_bit:      bool         = False
            last_stop_bit: bool         = False
            recording:     bool         = False

            while True:
                if await request.is_disconnected():
                    break

                data = await loop.run_in_executor(None, reader.read)

                if data is None:
                    yield f"data: {json.dumps({'error': 'reconnecting'})}\n\n"
                    await asyncio.sleep(1.0)
                    await loop.run_in_executor(None, reader.connect)
                    continue

                bit      = bool(data.get(bit_name, 0))
                stop_bit = bool(data.get(stop_bit_name, 0))
                forca    = data.get(forca_name)
                desl     = data.get(desl_name)

                # Borda de subida no bit de início
                if bit and not last_bit and not recording:
                    t_start   = time.time()
                    recording = True
                last_bit = bit

                # Borda de subida no bit de parada
                if stop_bit and not last_stop_bit and recording:
                    yield f"data: {json.dumps({'stopped': True})}\n\n"
                    break
                last_stop_bit = stop_bit

                elapsed_ms = int((time.time() - t_start) * 1000) if (recording and t_start) else 0

                payload = json.dumps({
                    "recording":    recording,
                    "bit":          bit,
                    "forca":        forca,
                    "deslocamento": desl,
                    "t_ms":         elapsed_ms,
                })
                yield f"data: {payload}\n\n"

                await asyncio.sleep(interval_ms / 1000)
        except asyncio.CancelledError:
            pass
        finally:
            await loop.run_in_executor(None, reader.close)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":       "keep-alive",
        },
    )


# ---------------------------------------------------------------------------
# Flexão — listagem, KPIs, curvas, controle e aquisição (módulo separado)
# ---------------------------------------------------------------------------

_FLEXAO_READ_ROLES = ("forca_atual", "deslocamento_atual", "fim_ensaio_bit")


def _flexao_registers() -> list[dict]:
    """A flexão roda na mesma máquina: por padrão usa os registradores da tração.
    Os papéis listados em flexao_separados usam o registrador próprio da flexão
    (flexao_registers), e papéis que só a flexão tem (ex.: fim_ensaio_bit) entram sempre."""
    proprios = {r.get("role"): r for r in _resolve_registers(_config.get("flexao_registers", []))
                if r.get("role")}
    separados = set(_config.get("flexao_separados") or [])
    tracao = _control_registers()
    papeis_tracao = {r.get("role") for r in tracao if r.get("role")}
    regs = [proprios[r["role"]] if r.get("role") in separados and r.get("role") in proprios else r
            for r in tracao]
    regs += [r for role, r in proprios.items() if role not in papeis_tracao]
    return regs


def _flexao_make_controller():
    if _sim_enabled():
        return SimController(_flexao_registers())
    ip, port, timeout = _clp_conn()
    return ModbusController(ip, port, timeout, _flexao_registers())


def _flexao_read_registers_by_role() -> list[dict]:
    return [r for r in _flexao_registers() if r.get("role") in _FLEXAO_READ_ROLES]


def _flexao_role_to_name() -> dict[str, str]:
    return {r["role"]: r["name"] for r in _flexao_registers() if r.get("role") and r.get("name")}


@app.get("/api/flexao/ensaios", response_model=list[EnsaioFlexaoSummary])
def list_ensaios_flexao(db: Session = Depends(get_db)):
    rows = db.query(EnsaioFlexaoDB).order_by(EnsaioFlexaoDB.created_at.desc()).all()
    return [
        EnsaioFlexaoSummary(
            id=r.id, nome=r.nome, filename=r.filename,
            data_ensaio=r.data_ensaio, num_amostras=r.num_amostras,
            forca_max_N=r.forca_max_N, tensao_flexao_max_MPa=r.tensao_flexao_max_MPa,
            modulo_flexao_MPa=r.modulo_flexao_MPa, created_at=r.created_at,
        )
        for r in rows
    ]


@app.get("/api/flexao/ensaios/{id}", response_model=EnsaioFlexaoDetail)
def get_ensaio_flexao(id: int, db: Session = Depends(get_db)):
    r = db.query(EnsaioFlexaoDB).filter(EnsaioFlexaoDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio de flexão não encontrado")
    return EnsaioFlexaoDetail(
        id=r.id, nome=r.nome, filename=r.filename,
        data_ensaio=r.data_ensaio, num_amostras=r.num_amostras,
        forca_max_N=r.forca_max_N, tensao_flexao_max_MPa=r.tensao_flexao_max_MPa,
        modulo_flexao_MPa=r.modulo_flexao_MPa, created_at=r.created_at,
        metadata_version=r.metadata_version,
        metadata_equipment_id=r.metadata_equipment_id, metadata_code=r.metadata_code,
        deflexao_max_mm=r.deflexao_max_mm, tempo_ensaio_s=r.tempo_ensaio_s,
        largura_mm=r.largura_mm or 0.0, espessura_mm=r.espessura_mm or 0.0,
        span_mm=r.span_mm or 0.0, norma=r.norma or "",
    )


def _flexao_geom(r: EnsaioFlexaoDB) -> dict:
    return {
        "largura_mm": r.largura_mm, "espessura_mm": r.espessura_mm,
        "span_mm": r.span_mm, "norma": r.norma,
    }


@app.get("/api/flexao/ensaios/{id}/kpis")
def get_kpis_flexao(id: int, db: Session = Depends(get_db)):
    r = db.query(EnsaioFlexaoDB).filter(EnsaioFlexaoDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio de flexão não encontrado")
    df = pd.read_json(io.StringIO(r.data_json))
    return JSONResponse(content=calculate_kpis_flexao(df, geom=_flexao_geom(r)))


@app.get("/api/flexao/ensaios/{id}/qualidade")
def get_qualidade_flexao(id: int, db: Session = Depends(get_db)):
    r = db.query(EnsaioFlexaoDB).filter(EnsaioFlexaoDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio de flexão não encontrado")
    df = pd.read_json(io.StringIO(r.data_json))
    itens = avaliar_qualidade_flexao(df, calculate_kpis_flexao(df, geom=_flexao_geom(r)))
    return {"status": resumo_status(itens), "itens": itens}


@app.get("/api/flexao/ensaios/{id}/curvas")
def get_curvas_flexao(id: int, db: Session = Depends(get_db)):
    r = db.query(EnsaioFlexaoDB).filter(EnsaioFlexaoDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio de flexão não encontrado")
    df = pd.read_json(io.StringIO(r.data_json))
    return JSONResponse(content=format_chart_data_flexao(df))


@app.delete("/api/flexao/ensaios/{id}", status_code=204)
def delete_ensaio_flexao(id: int, db: Session = Depends(get_db)):
    r = db.query(EnsaioFlexaoDB).filter(EnsaioFlexaoDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio de flexão não encontrado")
    db.delete(r)
    db.commit()


@app.post("/api/flexao/control/start")
def flexao_control_start(req: FlexaoControlStartRequest):
    if not _config.get("flexao_habilitada", True):
        raise HTTPException(status_code=403, detail="Flexão desabilitada nesta máquina (Configurações → Geral).")
    ip, port, timeout = _clp_conn()
    if not ip:
        raise HTTPException(status_code=400, detail="IP do CLP não configurado — preencha em Configurações → Controle (CLP).")
    if req.limite_forca is not None and req.limite_forca <= 0:
        raise HTTPException(status_code=422, detail="Limite de força deve ser maior que zero.")

    ctrl = _flexao_make_controller()
    if ctrl.resolve("iniciar") is None:
        raise HTTPException(status_code=400, detail="Registrador 'iniciar' de flexão não configurado.")
    if not ctrl.connect():
        raise HTTPException(status_code=502, detail=f"CLP inacessível em {ip}:{port}.")

    pulse_ms = int(_config.get("control_pulse_ms", 300))
    try:
        applied = _apply_setpoints(
            ctrl, velocidade=req.velocidade,
            deslocamento=req.deslocamento, limite_forca=req.limite_forca,
        )
        # Persiste geometria do setup para a próxima aquisição derivar σf/εf.
        for cfg_key, val in (
            ("flexao_largura_mm", req.largura_mm),
            ("flexao_espessura_mm", req.espessura_mm),
            ("flexao_span_mm", req.span_mm),
            ("flexao_norma", req.norma),
        ):
            if val is not None:
                _config[cfg_key] = val
        _config["proximo_ensaio_flexao"] = {
            "cliente_id": req.cliente_id, "amostra": req.amostra.strip(),
            "operador": req.operador.strip(),
        }
        _save_config(_config)

        # Setpoints escritos → pulso de sentido (momentâneo) → pulso de início.
        sent = _pulse_sentido(ctrl, req.sentido, pulse_ms)
        if sent:
            applied["sentido"] = sent
        ctrl.pulse("iniciar", pulse_ms)
        return {"status": "started", "sentido": req.sentido, "setpoints": applied}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao iniciar ensaio de flexão: {exc}")
    finally:
        ctrl.close()


@app.post("/api/flexao/control/stop")
def flexao_control_stop():
    ip, port, timeout = _clp_conn()
    if not ip:
        raise HTTPException(status_code=400, detail="IP do CLP não configurado.")
    ctrl = _flexao_make_controller()
    if ctrl.resolve("parar") is None:
        raise HTTPException(status_code=400, detail="Registrador 'parar' de flexão não configurado.")
    if not ctrl.connect():
        raise HTTPException(status_code=502, detail=f"CLP inacessível em {ip}:{port}.")
    pulse_ms = int(_config.get("control_pulse_ms", 300))
    try:
        ctrl.pulse("parar", pulse_ms)
        for role in ("sentido_cima", "sentido_baixo"):
            if ctrl.resolve(role) is not None:
                ctrl.write_named(role, 0)
        return {"status": "stopped"}
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao parar ensaio de flexão: {exc}")
    finally:
        ctrl.close()


@app.post("/api/flexao/control/zerar-deslocamento")
def flexao_control_zerar_deslocamento():
    """Pulsa o bit que zera o deslocamento do ensaio de flexão."""
    return _pulse_command(_flexao_make_controller, "zerar_deslocamento", "zerar o deslocamento")


@app.post("/api/flexao/control/zerar-celula")
def flexao_control_zerar_celula():
    """Pulsa o bit que zera a célula de carga da flexão — também para o ensaio."""
    return _pulse_command(_flexao_make_controller, "zerar_celula", "zerar a célula de carga")


@app.get("/api/flexao/control/status", response_model=ControlStatus)
def flexao_control_status():
    ip, port, timeout = _clp_conn()
    regs = _flexao_read_registers_by_role()
    if not regs or (not ip and not _sim_enabled()):
        return ControlStatus(online=False)
    data = sim_capture(regs) if _sim_enabled() else capture_registers(ip, port, timeout, regs)
    if data is None:
        return ControlStatus(online=False)
    rn = _flexao_role_to_name()
    def _val(role):
        name = rn.get(role)
        return data.get(name) if name else None
    fim = _val("fim_ensaio_bit")
    return ControlStatus(
        online=True,
        forca_atual=_val("forca_atual"),
        deslocamento_atual=_val("deslocamento_atual"),
        material_integro=(not bool(fim)) if fim is not None else None,
        ruptura=bool(fim) if fim is not None else None,
        ativo=None,
    )


@app.get("/api/flexao/control/stream")
async def flexao_control_stream(request: Request):
    """Stream SSE de força/deflexão do CLP; ao detectar fim do ensaio (fim_ensaio_bit)
    — ou desconexão após coletar dados — grava o ensaio de flexão no banco."""
    ip, port, timeout = _clp_conn()
    interval_ms = max(50, int(_config.get("realtime_interval_ms", 100)))
    regs = _flexao_read_registers_by_role()
    rn = _flexao_role_to_name()
    forca_name = rn.get("forca_atual")
    desl_name  = rn.get("deslocamento_atual")
    fim_name   = rn.get("fim_ensaio_bit")

    if not forca_name or (not ip and not _sim_enabled()):
        async def _err():
            yield f"data: {json.dumps({'error': 'clp_nao_configurado'})}\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    reader = _make_reader(ip, port, timeout, regs)
    loop   = asyncio.get_event_loop()
    geom = {
        "largura_mm":   float(_config.get("flexao_largura_mm", 0) or 0),
        "espessura_mm": float(_config.get("flexao_espessura_mm", 0) or 0),
        "span_mm":      float(_config.get("flexao_span_mm", 0) or 0),
        "norma":        _config.get("flexao_norma", "ISO 178"),
    }

    def _persist(samples: list[dict]) -> int | None:
        if len(samples) < 10:
            return None
        db = SessionLocal()
        try:
            filename = f"FLEXAO_{time.strftime('%Y%m%d_%H%M%S')}.csv"
            metadata, df = build_ensaio_flexao_dataframe(
                samples, geom["largura_mm"], geom["espessura_mm"], geom["span_mm"],
                filename=filename,
            )
            if int(df["Forca_N"].dropna().shape[0]) < 10:
                return None
            rec = persist_ensaio_flexao(db, metadata, df, filename=filename, geom=geom, source_ip=ip)
            _aplicar_cadastro(db, rec, _config.get("proximo_ensaio_flexao"))
            return rec.id
        except Exception as exc:
            print(f"[flexao.control] Falha ao persistir ensaio: {exc}", flush=True)
            return None
        finally:
            db.close()

    async def generate():
        samples: list[dict] = []
        t_start: float | None = None
        last_fim = False
        saved = False
        try:
            if not await loop.run_in_executor(None, reader.connect):
                yield f"data: {json.dumps({'error': 'clp_offline'})}\n\n"
                return

            while True:
                if await request.is_disconnected():
                    break
                data = await loop.run_in_executor(None, reader.read)
                if data is None:
                    yield f"data: {json.dumps({'error': 'reconnecting'})}\n\n"
                    await asyncio.sleep(1.0)
                    await loop.run_in_executor(None, reader.connect)
                    continue

                forca = data.get(forca_name)
                desl  = data.get(desl_name) if desl_name else None
                fim   = bool(data.get(fim_name, 0)) if fim_name else False

                if t_start is None and forca is not None:
                    t_start = time.time()
                elapsed_ms = int((time.time() - t_start) * 1000) if t_start else 0

                if forca is not None:
                    samples.append({"t_ms": elapsed_ms, "forca": forca, "deslocamento": desl or 0.0})

                if fim and not last_fim:
                    saved = True
                    saved_id = await loop.run_in_executor(None, _persist, samples)
                    yield f"data: {json.dumps({'fim_ensaio': True, 'saved_ensaio_id': saved_id})}\n\n"
                    break
                last_fim = fim

                payload = json.dumps({
                    "recording":    t_start is not None,
                    "forca":        forca,
                    "deslocamento": desl,
                    "fim_ensaio":   fim,
                    "t_ms":         elapsed_ms,
                })
                yield f"data: {payload}\n\n"
                await asyncio.sleep(interval_ms / 1000)
        except asyncio.CancelledError:
            pass
        finally:
            # Síncrono de propósito: na desconexão a task está cancelada e um await aqui
            # seria interrompido antes de gravar.
            reader.close()
            # Parado pelo usuário (ou o bit de fim não subiu): grava o que foi coletado.
            if not saved and samples:
                _persist(samples)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",
            "Connection":        "keep-alive",
        },
    )


# Serve frontend dist (built with `npm run build` in frontend/)
_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")
else:
    print(f"[main] dist não encontrado em {_dist}", flush=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
