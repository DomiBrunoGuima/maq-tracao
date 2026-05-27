from __future__ import annotations

import io
import json
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session

from .calculator import calculate_kpis, format_chart_data
from .database import EnsaioDB, ParametrosIHMDB, SessionLocal, get_db
from .models import ConfigModel, EnsaioDetail, EnsaioSummary, ParametrosIHM, ReportRequest
from .ftp_client import download_csv as ftp_download_csv
from .modbus_client import capture_registers
from .parser import parse_csv
from .report import generate_html_report
from .watcher import DirectoryWatcher

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

_config: dict = {
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
}

_watcher = DirectoryWatcher(callback=lambda p: _load_csv(p))


# ---------------------------------------------------------------------------
# CSV loading helper (called at startup and by watcher)
# ---------------------------------------------------------------------------

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
        kpis = calculate_kpis(df)

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
            kpis_json=json.dumps(kpis),
        )
        db.add(record)
        db.commit()
        print(f"[loader] Loaded: {path.name}")

        # Captura parâmetros da IHM via Modbus (falha silenciosa)
        _capture_ihm_params(path.name, db)

    except Exception as exc:
        print(f"[loader] Error loading {filepath}: {exc}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# IHM Modbus capture
# ---------------------------------------------------------------------------

def _capture_ihm_params(filename: str, db) -> None:
    ip      = _config.get("ihm_ip", "")
    port    = int(_config.get("ihm_port", 502))
    timeout = int(_config.get("ihm_timeout", 3))
    regs    = _config.get("ihm_registers", [])

    if not ip:
        return

    params = capture_registers(ip, port, timeout, regs)
    if params is None:
        print(f"[modbus] IHM inacessível — parâmetros não capturados para {filename}")
        return

    record = ParametrosIHMDB(
        ensaio_filename=filename,
        ihm_ip=ip,
        params_json=json.dumps(params),
    )
    db.add(record)
    db.commit()
    print(f"[modbus] Parâmetros capturados para {filename}: {params}")


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


@app.get("/api/ensaios/{id}/kpis")
def get_kpis(id: int, db: Session = Depends(get_db)):
    r = db.query(EnsaioDB).filter(EnsaioDB.id == id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Ensaio não encontrado")
    df = pd.read_json(io.StringIO(r.data_json))
    return JSONResponse(content=calculate_kpis(df))


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
    kpis = json.loads(r.kpis_json)
    html = generate_html_report(r, df, kpis, req)
    return HTMLResponse(content=html)


@app.get("/api/config")
def get_config():
    return JSONResponse(content=_config)


@app.put("/api/config")
def update_config(body: ConfigModel):
    _config.update(body.model_dump())
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
        raise HTTPException(status_code=400, detail="IP da IHM não configurado")
    if not remote_fname:
        raise HTTPException(status_code=400, detail="Nome do arquivo remoto não configurado")

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
