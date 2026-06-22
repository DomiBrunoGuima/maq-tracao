"""Aquisição do ensaio de flexão: converte amostras (força + deflexão) lidas do CLP
num DataFrame com as colunas de flexão derivadas e persiste o ensaio no banco.

Deriva, a partir de Força (N), Deflexão s (mm) e geometria b/h/L (mm):

    σf = 3·F·L / (2·b·h²)   (MPa)
    εf = 6·s·h / L²         (adimensional)
    Ef = dσf/dεf            (módulo local, MPa)
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

import numpy as np
import pandas as pd

from ..database import EnsaioFlexaoDB, ParametrosIHMDB
from .calculator import calculate_kpis, epsilon_flexao, sigma_flexao
from .parser import COLUMN_NAMES, detect_stages

logger_prefix = "[flexao.acquisition]"


@dataclass
class FlexaoMetadata:
    version: str
    equipment_id: str
    code: str
    filename: str


def build_ensaio_flexao_dataframe(
    samples: list[dict],
    largura_mm: float,
    espessura_mm: float,
    span_mm: float,
    *,
    equipment_id: str = "CLP",
    code: str = "",
    filename: str = "",
) -> tuple[FlexaoMetadata, pd.DataFrame]:
    """Monta o DataFrame de um ensaio de flexão a partir das amostras do CLP.

    Cada amostra é um dict com ``forca`` (N) e ``deslocamento`` (deflexão, mm); o
    instante vem de ``elapsed_seconds`` ou ``t_ms``.
    """
    now = datetime.now()

    rows: list[dict] = []
    for i, s in enumerate(samples):
        forca = s.get("forca")
        desl  = s.get("deslocamento")
        if forca is None or desl is None:
            continue
        if s.get("elapsed_seconds") is not None:
            elapsed = float(s["elapsed_seconds"])
        else:
            elapsed = float(s.get("t_ms", i * 100)) / 1000.0
        rows.append({"elapsed_seconds": elapsed, "Forca_N": float(forca), "Deslocamento": float(desl)})

    df = pd.DataFrame(rows, columns=["elapsed_seconds", "Forca_N", "Deslocamento"])

    df["timestamp"] = now + pd.to_timedelta(df["elapsed_seconds"], unit="s")
    df["DATA"] = df["timestamp"].dt.strftime("%d/%m/%Y")
    df["TIME"] = df["timestamp"].dt.strftime("%H:%M:%S")

    b = float(largura_mm) if largura_mm and largura_mm > 0 else 1.0
    h = float(espessura_mm) if espessura_mm and espessura_mm > 0 else 1.0
    L = float(span_mm) if span_mm and span_mm > 0 else 1.0
    if b == 1.0 or h == 1.0 or L == 1.0:
        print(f"{logger_prefix} AVISO: geometria b={largura_mm} h={espessura_mm} "
              f"L={span_mm} inválida — colunas de flexão em unidades cruas.", flush=True)

    # σf = 3FL/2bh²  ; εf = 6sh/L²
    df["Tensao_Flexao"] = 3.0 * df["Forca_N"] * L / (2.0 * b * h * h)
    df["Deform_Flexao"] = 6.0 * df["Deslocamento"] * h / (L * L)

    # Módulo local Ef = dσf/dεf
    if len(df) >= 2:
        sig = df["Tensao_Flexao"].to_numpy(dtype=float)
        eps = df["Deform_Flexao"].to_numpy(dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            modulo = np.gradient(sig, eps)
        df["Modulo_Flexao"] = np.where(np.isfinite(modulo), modulo, 0.0)
    else:
        df["Modulo_Flexao"] = 0.0

    for col in COLUMN_NAMES:
        if col not in df.columns:
            df[col] = np.nan

    df["fase"] = detect_stages(df)

    metadata = FlexaoMetadata(
        version="FLEXAO V1.0",
        equipment_id=equipment_id,
        code=code,
        filename=filename or (equipment_id or "CLP"),
    )
    return metadata, df


def persist_ensaio_flexao(
    db,
    metadata: FlexaoMetadata,
    df: pd.DataFrame,
    *,
    filename: str,
    geom: dict,
    filepath: str = "",
    source_ip: str = "",
) -> EnsaioFlexaoDB:
    """Calcula KPIs de flexão e grava o ensaio (e a geometria) no banco."""
    kpis = calculate_kpis(df, geom=geom)

    data_ensaio = df["DATA"].iloc[0].strip() if len(df) > 0 and pd.notna(df["DATA"].iloc[0]) else \
        datetime.now().strftime("%d/%m/%Y")

    df_for_json = df.copy()
    if "timestamp" in df_for_json.columns:
        df_for_json["timestamp"] = df_for_json["timestamp"].astype(str)

    nome_stem = filename[:-4] if filename.lower().endswith(".csv") else filename
    record = EnsaioFlexaoDB(
        nome=f"{nome_stem} — {data_ensaio}",
        filename=filename,
        data_ensaio=data_ensaio,
        num_amostras=len(df),
        forca_max_N=kpis["forca_max_N"],
        tensao_flexao_max_MPa=kpis["tensao_flexao_max_MPa"],
        modulo_flexao_MPa=kpis["modulo_flexao_MPa"],
        deflexao_max_mm=kpis["deflexao_max_mm"],
        tempo_ensaio_s=kpis["tempo_ensaio_s"],
        largura_mm=float(geom.get("largura_mm") or 0),
        espessura_mm=float(geom.get("espessura_mm") or 0),
        span_mm=float(geom.get("span_mm") or 0),
        norma=str(geom.get("norma") or ""),
        metadata_version=metadata.version,
        metadata_equipment_id=metadata.equipment_id,
        metadata_code=metadata.code,
        filepath=filepath,
        data_json=df_for_json.to_json(orient="records"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    db.add(ParametrosIHMDB(
        ensaio_filename=filename,
        ihm_ip=source_ip,
        params_json=json.dumps(geom),
    ))
    db.commit()

    print(f"{logger_prefix} Ensaio gravado: {filename} ({len(df)} amostras, "
          f"Fmax={kpis['forca_max_N']:.1f}N, σfM={kpis['tensao_flexao_max_MPa']:.1f}MPa)", flush=True)
    return record
