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

from .calculator import calculate_kpis, format_chart_data
from .database import EnsaioDB, ParametrosIHMDB, SessionLocal, get_db
from .models import ConfigModel, EnsaioDetail, EnsaioSummary, ParametrosIHM, ReportRequest
from .ftp_client import download_csv as ftp_download_csv
from .modbus_client import RealtimeModbusReader, capture_registers
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


def _load_csv(filepath: str) -> None:
    db = SessionLocal()
    try:
        path = Path(filepath)
        if not path.exists():
            return

        # Skip if already in database
        if db.query(EnsaioDB).filter(EnsaioDB.filename == path.name).first():
            return

        metadata, df = parse_csv(filepath)

        # Busca parâmetros da IHM ANTES de calcular KPIs (area_seccao e comprimento_inicial
        # entram diretamente nas fórmulas σ = F/A, ε = ΔL/L₀, A% = (d/L₀)×100)
        ihm_params = _fetch_ihm_params()
        kpis = calculate_kpis(df, ihm_params=ihm_params)

        data_ensaio = df["DATA"].iloc[0].strip() if len(df) > 0 else "01/01/2026"

        # Serialize df, converting timestamps to ISO strings
        df_for_json = df.copy()
        if "timestamp" in df_for_json.columns:
            df_for_json["timestamp"] = df_for_json["timestamp"].astype(str)

        record = EnsaioDB(
            nome=f"{path.stem} — {data_ensaio}",
            filename=path.name,
            data_ensaio=data_ensaio,
            num_amostras=len(df),
            forca_max_N=kpis["forca_max_N"],
            tensao_max_MPa=kpis["tensao_max_MPa"],
            alonga_ruptura_pct=kpis["alonga_ruptura_pct"],
            tempo_ruptura_s=kpis["tempo_ruptura_s"],
            metadata_version=metadata.version,
            metadata_equipment_id=metadata.equipment_id,
            metadata_code=metadata.code,
            filepath=str(path.resolve()),
            data_json=df_for_json.to_json(orient="records"),
        )
        db.add(record)
        db.commit()
        print(f"[loader] Loaded: {path.name}", flush=True)

        if ihm_params is not None:
            _save_ihm_params(path.name, db, ihm_params)
        elif _config.get("ihm_ip"):
            print(f"[modbus] IHM inacessível — parâmetros não capturados para {path.name}", flush=True)

    except Exception as exc:
        print(f"[loader] Error loading {filepath}: {exc}")
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


@app.post("/api/relatorio")
def generate_report(req: ReportRequest, db: Session = Depends(get_db)):
    r = db.query(EnsaioDB).filter(EnsaioDB.id == req.ensaio_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    df = pd.read_json(io.StringIO(r.data_json))
    ihm_params = _load_ihm_params_for(r.filename, db)
    kpis = calculate_kpis(df, ihm_params=ihm_params)
    html = generate_html_report(r, df, kpis, req)
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

    _load_csv(str(dest))

    rec = db.query(EnsaioDB).filter(EnsaioDB.filename == filename).first()
    if not rec:
        raise HTTPException(status_code=500, detail="Arquivo recebido mas falhou ao importar")

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


# Serve frontend dist (built with `npm run build` in frontend/)
_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="static")
else:
    print(f"[main] dist não encontrado em {_dist}", flush=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
