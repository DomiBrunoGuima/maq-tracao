"""Aquisição direta do CLP: converte amostras (força + deslocamento) lidas dos
registradores Modbus num DataFrame compatível com o pipeline de análise (que antes
consumia o CSV gerado pela IHM) e persiste o ensaio direto no banco.

A IHM calculava as colunas de tensão/módulo/deformação. Sem ela, derivamos essas
colunas aqui a partir de Força (N), Deslocamento (mm), Área da seção (mm²) e
Comprimento inicial L0 (mm):

    σ  = F / A            (MPa, pois N/mm² = MPa)
    ε  = ΔL / L0          (adimensional)
    A% = (ΔL / L0) × 100  (alongamento %)
    E  = dσ/dε            (módulo local, MPa)
"""
from __future__ import annotations

import json
from datetime import datetime

import numpy as np
import pandas as pd

from .calculator import calculate_kpis
from .database import EnsaioDB, ParametrosIHMDB
from .parser import COLUMN_NAMES, EnsaioMetadata, _detect_stages, _trim_precontact

logger_prefix = "[acquisition]"


def build_ensaio_dataframe(
    samples: list[dict],
    area_mm2: float,
    l0_mm: float,
    *,
    equipment_id: str = "CLP",
    code: str = "",
    filename: str = "",
) -> tuple[EnsaioMetadata, pd.DataFrame]:
    """Monta o DataFrame de um ensaio a partir das amostras capturadas do CLP.

    Cada amostra é um dict com pelo menos ``forca`` (N) e ``deslocamento`` (mm); o
    instante vem de ``elapsed_seconds`` ou ``t_ms``. O DataFrame resultante contém
    todas as colunas que ``calculate_kpis``/``format_chart_data`` esperam, incluindo
    ``fase`` (via :func:`parser._detect_stages`).
    """
    now = datetime.now()

    rows: list[dict] = []
    for i, s in enumerate(samples):
        forca = s.get("forca")
        desl  = s.get("deslocamento")
        if forca is None or desl is None:
            continue
        if "elapsed_seconds" in s and s["elapsed_seconds"] is not None:
            elapsed = float(s["elapsed_seconds"])
        else:
            elapsed = float(s.get("t_ms", i * 100)) / 1000.0
        rows.append({"elapsed_seconds": elapsed, "Forca_N": float(forca), "Deslocamento": float(desl)})

    df = pd.DataFrame(rows, columns=["elapsed_seconds", "Forca_N", "Deslocamento"])

    # Colunas textuais de data/hora (DATA usada para nome/data do ensaio)
    df["timestamp"] = now + pd.to_timedelta(df["elapsed_seconds"], unit="s")
    df["DATA"] = df["timestamp"].dt.strftime("%d/%m/%Y")
    df["TIME"] = df["timestamp"].dt.strftime("%H:%M:%S")

    # Corta pré-contato ANTES de derivar — o trim re-referencia elapsed_seconds e
    # Deslocamento (zera no ponto de contato), então tensão/deformação devem usar os
    # valores já re-referenciados para ficarem consistentes.
    df = _trim_precontact(df).reset_index(drop=True)

    # Sem área/L0 não há como derivar tensão/deformação em unidades físicas — usamos
    # 1.0 (unidades cruas) e avisamos, para não perder os dados do ensaio.
    area = float(area_mm2) if area_mm2 and area_mm2 > 0 else 1.0
    l0   = float(l0_mm) if l0_mm and l0_mm > 0 else 1.0
    if area == 1.0 or l0 == 1.0:
        print(f"{logger_prefix} AVISO: área={area_mm2} L0={l0_mm} inválidos — "
              "colunas de tensão/deformação em unidades cruas.", flush=True)

    df["Tensao_Pa"]      = df["Forca_N"] / area               # MPa
    df["Tensao_Max"]     = df["Tensao_Pa"]                     # instantâneo (máx via .max())
    df["Deform_Along"]   = df["Deslocamento"] / l0             # ε adimensional
    df["Alonga_Ruptura"] = (df["Deslocamento"] / l0) * 100.0   # A%

    # Módulo local E = dσ/dε (gradiente ponto a ponto, MPa)
    if len(df) >= 2:
        sig = df["Tensao_Pa"].to_numpy(dtype=float)
        eps = df["Deform_Along"].to_numpy(dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            modulo = np.gradient(sig, eps)
        modulo = np.where(np.isfinite(modulo), modulo, 0.0)
        df["Modulo_Elast"] = modulo
    else:
        df["Modulo_Elast"] = 0.0

    # Garante a presença de todas as colunas esperadas pelo pipeline
    for col in COLUMN_NAMES:
        if col not in df.columns:
            df[col] = np.nan

    # Classifica fases (mesma lógica do parser de CSV)
    df["fase"] = _detect_stages(df)

    metadata = EnsaioMetadata(
        version="CLP V1.0",
        equipment_id=equipment_id,
        code=code,
        filename=filename or (equipment_id or "CLP"),
    )
    return metadata, df


def persist_ensaio(
    db,
    metadata: EnsaioMetadata,
    df: pd.DataFrame,
    *,
    filename: str,
    params: dict | None = None,
    filepath: str = "",
    source_ip: str = "",
) -> EnsaioDB:
    """Calcula KPIs e grava o ensaio (e parâmetros) no banco. Reutilizável pelos
    caminhos de CSV e de aquisição direta do CLP."""
    kpis = calculate_kpis(df, ihm_params=params)

    data_ensaio = df["DATA"].iloc[0].strip() if len(df) > 0 and pd.notna(df["DATA"].iloc[0]) else \
        datetime.now().strftime("%d/%m/%Y")

    df_for_json = df.copy()
    if "timestamp" in df_for_json.columns:
        df_for_json["timestamp"] = df_for_json["timestamp"].astype(str)

    nome_stem = filename[:-4] if filename.lower().endswith(".csv") else filename
    record = EnsaioDB(
        nome=f"{nome_stem} — {data_ensaio}",
        filename=filename,
        data_ensaio=data_ensaio,
        num_amostras=len(df),
        forca_max_N=kpis["forca_max_N"],
        tensao_max_MPa=kpis["tensao_max_MPa"],
        alonga_ruptura_pct=kpis["alonga_ruptura_pct"],
        tempo_ruptura_s=kpis["tempo_ruptura_s"],
        metadata_version=metadata.version,
        metadata_equipment_id=metadata.equipment_id,
        metadata_code=metadata.code,
        filepath=filepath,
        data_json=df_for_json.to_json(orient="records"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    if params:
        db.add(ParametrosIHMDB(
            ensaio_filename=filename,
            ihm_ip=source_ip,
            params_json=json.dumps(params),
        ))
        db.commit()

    print(f"{logger_prefix} Ensaio gravado: {filename} ({len(df)} amostras, "
          f"Fmax={kpis['forca_max_N']:.1f}N)", flush=True)
    return record
