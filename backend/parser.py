from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


def _detect_stages(df: pd.DataFrame) -> pd.Series:
    """Classifica cada ponto em uma das 6 etapas do ensaio de tração."""
    n = len(df)
    stages = pd.Series("encruamento", index=df.index)
    if n < 8:
        return stages

    sig   = df["Tensao_Pa"].values.astype(float)
    forca = df["Forca_N"].values.astype(float)

    uts_pos = int(np.argmax(forca))

    if uts_pos < n - 1:
        stages.iloc[uts_pos + 1 :] = "estriccao"
        stages.iloc[-1] = "ruptura"
    else:
        stages.iloc[-1] = "ruptura"

    n_load = uts_pos + 1
    if n_load < 8:
        return stages

    # Smooth loading stress
    w = max(3, n_load // 12)
    sig_s = np.convolve(sig[:n_load], np.ones(w) / w, mode="same")

    # ── Upper yield: first local max with significant drop after it ───────────
    search_end = int(n_load * 0.65)
    uy_pos = None
    for i in range(2, search_end - 1):
        drop = sig_s[i] - float(np.min(sig_s[i + 1 : min(i + 5, search_end)]))
        if sig_s[i] > sig_s[i - 1] and drop > sig_s[i] * 0.02:
            uy_pos = i
            break

    if uy_pos is None:
        # Sem escoamento distinto: elástico = primeiros 25%, resto = encruamento
        stages.iloc[: int(n_load * 0.25)] = "elastico_linear"
        return stages

    hw = max(2, n_load // 30)
    uy_s = max(1, uy_pos - hw)
    uy_e = min(n_load - 1, uy_pos + hw)

    # ── Elástico Linear: tudo antes do início do escoamento superior ──────────
    stages.iloc[: uy_s] = "elastico_linear"
    stages.iloc[uy_s : uy_e + 1] = "escoamento_superior"

    # ── Patamar: após escoamento superior, σ ≈ constante ─────────────────────
    post = sig_s[uy_e + 1 :]
    if len(post) < 3:
        return stages

    lower_yield = float(np.min(post[: max(3, len(post) // 4)]))
    thresh = lower_yield * 1.12
    plat_end_rel = 0
    tolerance = max(3, n_load // 15)
    for i, s in enumerate(post):
        if s <= thresh:
            plat_end_rel = i
        elif i > plat_end_rel + tolerance:
            break

    plat_end_abs = uy_e + 1 + plat_end_rel
    stages.iloc[uy_e + 1 : plat_end_abs + 1] = "patamar_escoamento"
    # encruamento: plat_end_abs + 1 → uts_pos (já é o default)

    return stages

COLUMN_NAMES = [
    "TIME",
    "DATA",
    "Tensao_Pa",
    "Modulo_Elast",
    "Tensao_Max",
    "Deform_Along",
    "Alonga_Ruptura",
    "Deslocamento",
    "Forca_N",
    "Checksum",
]

NUMERIC_COLS = [
    "Tensao_Pa",
    "Modulo_Elast",
    "Tensao_Max",
    "Deform_Along",
    "Alonga_Ruptura",
    "Deslocamento",
    "Forca_N",
]


@dataclass
class EnsaioMetadata:
    version: str
    equipment_id: str
    code: str
    filename: str


def _clean_header_line(line: str) -> str:
    """Remove UTF-16 artifacts: spaces between every character."""
    # If every other char is a space: "T I M E" → "TIME"
    stripped = line.strip()
    if re.fullmatch(r"(\S )+\S?", stripped):
        stripped = stripped.replace(" ", "")
    return stripped


def parse_csv(filepath: str | Path) -> tuple[EnsaioMetadata, pd.DataFrame]:
    filepath = Path(filepath)

    # Read the whole file to extract metadata from the header
    with open(filepath, encoding="utf-16") as f:
        raw_lines = f.readlines()

    # Line 0: "HISTORY V1.0\t{equip_id}\t{code}"
    meta_parts = raw_lines[0].strip().split("\t") if raw_lines else []
    metadata = EnsaioMetadata(
        version=meta_parts[0].strip() if len(meta_parts) > 0 else "HISTORY V1.0",
        equipment_id=meta_parts[1].strip() if len(meta_parts) > 1 else "",
        code=meta_parts[2].strip() if len(meta_parts) > 2 else "",
        filename=filepath.stem,
    )

    # Data rows start at line index 4 (0=meta, 1=empty, 2=col names, 3=channel markers)
    df = pd.read_csv(
        filepath,
        encoding="utf-16",
        sep="\t",
        skiprows=4,
        header=None,
        names=COLUMN_NAMES,
        dtype=str,
        on_bad_lines="skip",
    )

    # Drop completely empty rows
    df = df.dropna(how="all")

    # Convert numeric columns
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Forca_N"])
    df = df.reset_index(drop=True)

    # Build full timestamp
    df["timestamp"] = pd.to_datetime(
        df["DATA"].str.strip() + " " + df["TIME"].str.strip(),
        format="%d/%m/%Y %H:%M:%S",
        errors="coerce",
    )

    # Sort by timestamp and keep only the monotonically increasing sequence.
    # The IHM occasionally writes rows out of order or appends old records at
    # the end of the file; sorting + deduplication fixes the chart X-axis.
    valid_ts = df["timestamp"].notna()
    if valid_ts.any():
        df = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
        # Drop rows whose timestamp goes backwards relative to the running max
        # (handles old data spliced into the middle/end of the file).
        ts_max = df["timestamp"].cummax()
        df = df[df["timestamp"] >= ts_max].reset_index(drop=True)

    # Elapsed seconds from first valid timestamp
    t0 = df["timestamp"].dropna().iloc[0] if not df["timestamp"].dropna().empty else None
    if t0 is not None:
        df["elapsed_seconds"] = (df["timestamp"] - t0).dt.total_seconds()
    else:
        df["elapsed_seconds"] = np.arange(len(df), dtype=float)

    df["fase"] = _detect_stages(df)

    return metadata, df
