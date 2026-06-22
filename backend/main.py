from __future__ import annotations

import asyncio
import io
import json
import time
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .acquisition import build_ensaio_dataframe, persist_ensaio
from .calculator import calculate_kpis, format_chart_data
from .database import EnsaioDB, EnsaioFlexaoDB, ParametrosIHMDB, SessionLocal, get_db
from .flexao.acquisition import build_ensaio_flexao_dataframe, persist_ensaio_flexao
from .flexao.calculator import calculate_kpis as calculate_kpis_flexao
from .flexao.calculator import format_chart_data as format_chart_data_flexao
from .models import (
    ConfigModel,
    ControlSetpointsRequest,
    ControlStartRequest,
    ControlStatus,
    EnsaioDetail,
    EnsaioFlexaoDetail,
    EnsaioFlexaoSummary,
    EnsaioSummary,
    FlexaoControlStartRequest,
    ParametrosIHM,
    ReportRequest,
)
from .ftp_client import download_csv as ftp_download_csv
from .modbus_client import ModbusController, RealtimeModbusReader, capture_registers
from .parser import parse_csv
from .report import generate_html_report
from .watcher import DirectoryWatcher

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

_CONFIG_FILE = Path(__file__).resolve().parent / "config.json"

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
    "control_registers": [],
    "control_pulse_ms": 300,
    "area_seccao_mm2": 0.0,
    "comprimento_inicial_mm": 0.0,
    "flexao_registers": [],
    "flexao_largura_mm": 0.0,
    "flexao_espessura_mm": 0.0,
    "flexao_span_mm": 0.0,
    "flexao_norma": "ISO 178",
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


# ---------------------------------------------------------------------------
# CLP — conexão e registradores de controle
# ---------------------------------------------------------------------------

# Roles de leitura usados na aquisição/status
_READ_ROLES = ("forca_atual", "deslocamento_atual", "material_integro_bit", "ruptura_bit")


def _clp_conn() -> tuple[str, int, int]:
    """Retorna (ip, port, timeout) do CLP, com fallback para a config da IHM."""
    ip      = _config.get("clp_ip") or _config.get("ihm_ip", "")
    port    = int(_config.get("clp_port") or _config.get("ihm_port", 502))
    timeout = int(_config.get("clp_timeout") or _config.get("ihm_timeout", 3))
    return ip, port, timeout


def _control_registers() -> list[dict]:
    return _config.get("control_registers", []) or []


def _make_controller() -> ModbusController:
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
    regs    = [r for r in _config.get("ihm_registers", [])
               if r.get("data_type", "uint16") != "coil"]
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
    yield
    _watcher.stop()


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="Analisador de Ensaios de Tração", version="1.0.0", lifespan=lifespan)

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

@app.get("/api/ensaios", response_model=list[EnsaioSummary])
def list_ensaios(db: Session = Depends(get_db)):
    rows = db.query(EnsaioDB).order_by(EnsaioDB.created_at.desc()).all()
    return [
        EnsaioSummary(
            id=r.id,
            nome=r.nome,
            filename=r.filename,
            data_ensaio=r.data_ensaio,
            num_amostras=r.num_amostras,
            forca_max_N=r.forca_max_N,
            tensao_max_MPa=r.tensao_max_MPa,
            created_at=r.created_at,
        )
        for r in rows
    ]


@app.get("/api/ensaios/{id}", response_model=EnsaioDetail)
def get_ensaio(id: int, db: Session = Depends(get_db)):
    r = db.query(EnsaioDB).filter(EnsaioDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    return EnsaioDetail(
        id=r.id, nome=r.nome, filename=r.filename,
        data_ensaio=r.data_ensaio, num_amostras=r.num_amostras,
        forca_max_N=r.forca_max_N, tensao_max_MPa=r.tensao_max_MPa,
        created_at=r.created_at, metadata_version=r.metadata_version,
        metadata_equipment_id=r.metadata_equipment_id,
        metadata_code=r.metadata_code,
        alonga_ruptura_pct=r.alonga_ruptura_pct,
        tempo_ruptura_s=r.tempo_ruptura_s,
    )


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
    db.delete(r)
    db.commit()
    ok, msg = _load_csv(filepath)
    if not ok:
        raise HTTPException(status_code=422, detail=f"Falha ao reimportar: {msg}")
    new_r = db.query(EnsaioDB).filter(EnsaioDB.filename == Path(filepath).name).first()
    if not new_r:
        raise HTTPException(status_code=500, detail="Falha ao reimportar — erro desconhecido")
    return {"id": new_r.id, "nome": new_r.nome, "num_amostras": new_r.num_amostras}


@app.post("/api/reimport-all")
def reimport_all(db: Session = Depends(get_db)):
    """Apaga todos os ensaios do banco e os re-importa a partir dos arquivos CSV."""
    rows = db.query(EnsaioDB).all()
    filepaths = [r.filepath for r in rows if r.filepath and Path(r.filepath).exists()]
    for r in rows:
        db.delete(r)
    db.commit()
    results = []
    for fp in filepaths:
        ok, msg = _load_csv(fp)
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
    return HTMLResponse(content=html)


@app.get("/api/config")
def get_config():
    return JSONResponse(content=_config)


@app.put("/api/config")
def update_config(body: ConfigModel):
    _config.update(body.model_dump())
    _save_config(_config)
    if body.auto_load:
        _watcher.start(body.watch_directory)
        for csv_file in sorted(Path(body.watch_directory).glob("*.csv")):
            _load_csv(str(csv_file))
    else:
        _watcher.stop()
    return JSONResponse(content=_config)


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


# ---------------------------------------------------------------------------
# Controle da máquina — escrita de comandos/setpoints no CLP
# ---------------------------------------------------------------------------

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
        if req.area_seccao is not None or req.comprimento_inicial is not None:
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
    if not ip or not regs:
        return ControlStatus(online=False)
    data = capture_registers(ip, port, timeout, regs)
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
    )


# ---------------------------------------------------------------------------
# Aquisição do CLP — SSE stream com gravação direta no banco
# ---------------------------------------------------------------------------

@app.get("/api/control/stream")
async def control_stream(request: Request):
    """Stream SSE que lê força/deslocamento do CLP, acumula as amostras e, ao
    detectar ruptura (M31) — ou desconexão do cliente após coletar dados —, grava
    o ensaio direto no banco e emite {"saved_ensaio_id": N}."""
    ip, port, timeout = _clp_conn()
    interval_ms = max(50, int(_config.get("realtime_interval_ms", 100)))
    regs = _read_registers_by_role()
    rn = _role_to_name()
    forca_name   = rn.get("forca_atual")
    desl_name    = rn.get("deslocamento_atual")
    integro_name = rn.get("material_integro_bit")
    ruptura_name = rn.get("ruptura_bit")

    if not ip or not forca_name:
        async def _err():
            yield f"data: {json.dumps({'error': 'clp_nao_configurado'})}\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    reader = RealtimeModbusReader(ip, port, timeout, regs)
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

    all_regs = _config.get("ihm_registers", [])
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
    return _config.get("flexao_registers", []) or []


def _flexao_make_controller() -> ModbusController:
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


@app.get("/api/flexao/control/status", response_model=ControlStatus)
def flexao_control_status():
    ip, port, timeout = _clp_conn()
    regs = _flexao_read_registers_by_role()
    if not ip or not regs:
        return ControlStatus(online=False)
    data = capture_registers(ip, port, timeout, regs)
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

    if not ip or not forca_name:
        async def _err():
            yield f"data: {json.dumps({'error': 'clp_nao_configurado'})}\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    reader = RealtimeModbusReader(ip, port, timeout, regs)
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
            await loop.run_in_executor(None, reader.close)

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
