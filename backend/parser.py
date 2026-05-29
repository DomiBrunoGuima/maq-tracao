from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


# ──────────────────────────────────────────────────────────────────────────────
# Pre-contact trim
# ──────────────────────────────────────────────────────────────────────────────

def _trim_precontact(df: pd.DataFrame) -> pd.DataFrame:
    forca = df["Forca_N"].values.astype(float)
    fmax = float(np.nanmax(forca)) if len(forca) > 0 else 0.0
    if fmax <= 0:
        return df
    threshold = fmax * 0.005
    n = len(forca)
    i_contact = None
    for i in range(n - 2):
        if forca[i] > threshold and forca[i + 1] > threshold and forca[i + 2] > threshold:
            i_contact = i
            break
    if i_contact is None or i_contact == 0:
        return df
    df = df.iloc[i_contact:].reset_index(drop=True)
    # Re-reference both axes to contact point
    if "elapsed_seconds" in df.columns:
        df["elapsed_seconds"] = df["elapsed_seconds"] - df["elapsed_seconds"].iloc[0]
    if "Deslocamento" in df.columns:
        df["Deslocamento"] = df["Deslocamento"] - float(df["Deslocamento"].iloc[0])
    print(f"[trim] cortados {i_contact} pontos pré-contato; Fmax={fmax:.1f}N threshold={threshold:.2f}N", flush=True)
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Linear elastic region detection
# ──────────────────────────────────────────────────────────────────────────────

def _find_linear_region(disp: np.ndarray, forca: np.ndarray) -> tuple[int, int]:
    """
    Detects the true linear elastic region via local stiffness stability.
    Returns (i_start, i_end) as indices within the loading subarray.
    The toe/accommodation region is [0, i_start-1].
    Fallback: (0, n//4) if detection fails.
    """
    n = len(disp)
    if n < 10:
        return 0, max(1, n // 4)

    # 5-point local stiffness dF/dd
    W = 5
    k = np.zeros(n)
    for i in range(n):
        i0 = max(0, i - W // 2)
        i1 = min(n, i + W // 2 + 1)
        dd = float(disp[i1 - 1] - disp[i0])
        dF = float(forca[i1 - 1] - forca[i0])
        k[i] = dF / dd if dd > 1e-6 else 0.0

    k_max = float(np.nanmax(k))
    if k_max <= 0:
        return 0, max(1, n // 4)

    # Sliding CV of stiffness (window ≈ 10% of n, minimum 5)
    CV_W = max(5, min(10, n // 10))
    cv_k = np.full(n, 999.0)
    for i in range(n):
        i0 = max(0, i - CV_W // 2)
        i1 = min(n, i + CV_W // 2 + 1)
        seg = k[i0:i1]
        m = float(np.mean(seg))
        if m > k_max * 0.1:
            cv_k[i] = float(np.std(seg)) / m

    # Linear mask: high stiffness (>50% k_max) AND stable (CV < 20%)
    lin = (k > 0.5 * k_max) & (cv_k < 0.20)

    # Find first sustained linear run (at least 5% of n, minimum 3 points)
    MIN_RUN = max(3, n // 20)
    i_start = None
    i = 0
    while i < n:
        if lin[i]:
            j = i
            while j < n and lin[j]:
                j += 1
            if j - i >= MIN_RUN:
                i_start = i
                break
        i += 1

    if i_start is None:
        return 0, max(1, n // 4)

    # Find end: stiffness drops below 80% of k_max for more than `grace` steps
    grace = max(3, n // 30)
    i_end = i_start
    dip = 0
    for i in range(i_start, n):
        if k[i] >= k_max * 0.80:
            i_end = i
            dip = 0
        else:
            dip += 1
            if dip > grace:
                break

    # Ensure at least 5 points in elastic region
    if i_end - i_start < 4:
        i_end = min(i_start + max(5, n // 8), n - 1)

    return i_start, i_end


# ──────────────────────────────────────────────────────────────────────────────
# Stage detection
# ──────────────────────────────────────────────────────────────────────────────

def _detect_stages(df: pd.DataFrame) -> pd.Series:
    """Classifica cada ponto em uma das etapas do ensaio de tração."""
    n = len(df)
    stages = pd.Series("encruamento", index=df.index)
    if n < 8:
        print(f"[stages] n={n} < 8, retornando encruamento total", flush=True)
        return stages

    sig   = df["Tensao_Pa"].values.astype(float)
    forca = df["Forca_N"].values.astype(float)
    disp  = df["Deslocamento"].values.astype(float)

    uts_pos = int(np.argmax(forca))

    if uts_pos < n - 1:
        stages.iloc[uts_pos + 1:] = "estriccao"
        stages.iloc[-1] = "ruptura"
    else:
        stages.iloc[-1] = "ruptura"

    n_load = uts_pos + 1
    if n_load < 8:
        print(f"[stages] n={n} uts_pos={uts_pos} n_load={n_load} < 8", flush=True)
        return stages

    # ── Detect true elastic linear region ────────────────────────────────────
    i_el_start, i_el_end = _find_linear_region(disp[:n_load], forca[:n_load])

    # Accommodation: toe region before elastic start
    if i_el_start > 0:
        stages.iloc[:i_el_start] = "acomodacao"

    stages.iloc[i_el_start:i_el_end + 1] = "elastico_linear"

    # ── Yield / plateau / encruamento in the post-elastic region ─────────────
    post_start = i_el_end + 1
    post_n = uts_pos - i_el_end  # points from post_start up to (not including) uts_pos

    uy_pos_abs = None
    plat_end_abs = None

    if post_n >= 8:
        sig_post = sig[post_start:n_load]
        w = max(3, post_n // 12)
        sig_s = np.convolve(sig_post, np.ones(w) / w, mode="same")
        search_end = int(post_n * 0.65)

        uy_pos_rel = None
        for i in range(2, max(3, search_end - 1)):
            lo = float(np.min(sig_s[i + 1: min(i + 5, search_end)]))
            drop = sig_s[i] - lo
            if sig_s[i] > sig_s[i - 1] and drop > sig_s[i] * 0.015:
                uy_pos_rel = i
                break

        if uy_pos_rel is not None:
            uy_pos_abs = post_start + uy_pos_rel
            hw = max(2, post_n // 30)
            uy_s = max(post_start, uy_pos_abs - hw)
            uy_e = min(n_load - 1, uy_pos_abs + hw)
            stages.iloc[uy_s:uy_e + 1] = "escoamento_superior"

            # Patamar de escoamento
            plat_rel_start = uy_e + 1 - post_start
            if plat_rel_start < len(sig_s) - 2:
                post2 = sig_s[plat_rel_start:]
                lower_yield = float(np.min(post2[:max(3, len(post2) // 4)]))
                thresh = lower_yield * 1.12
                plat_end_rel = 0
                tolerance = max(3, post_n // 15)
                for i2, s in enumerate(post2):
                    if s <= thresh:
                        plat_end_rel = i2
                    elif i2 > plat_end_rel + tolerance:
                        break
                plat_end_abs = uy_e + 1 + plat_end_rel
                stages.iloc[uy_e + 1:plat_end_abs + 1] = "patamar_escoamento"
                # encruamento: plat_end_abs+1 → uts_pos (already default)

    # ── Debug: phase coverage ─────────────────────────────────────────────────
    counts = {p: int((stages.values == p).sum()) for p in [
        "acomodacao", "elastico_linear", "escoamento_superior",
        "patamar_escoamento", "encruamento", "estriccao", "ruptura",
    ]}
    total_assigned = sum(counts.values())
    coverage = (
        f"acomod[0:{i_el_start}] "
        f"elast[{i_el_start}:{i_el_end+1}] "
        f"uy_abs={uy_pos_abs} "
        f"plat_end={plat_end_abs} "
        f"encruamento→{uts_pos} "
        f"estriccao[{uts_pos+1}:{n-1}]"
    )
    print(
        f"[stages] n={n} uts={uts_pos} el=({i_el_start},{i_el_end}) | {coverage}",
        flush=True,
    )
    print(f"[stages] counts={counts} total={total_assigned}/{n}", flush=True)
    if total_assigned != n:
        print(f"[stages] AVISO ANTI-GAP: {n - total_assigned} pontos sem fase!", flush=True)

    return stages


# ──────────────────────────────────────────────────────────────────────────────
# CSV column names
# ──────────────────────────────────────────────────────────────────────────────

COLUMN_NAMES = [
    "TIME", "DATA", "Tensao_Pa", "Modulo_Elast", "Tensao_Max",
    "Deform_Along", "Alonga_Ruptura", "Deslocamento", "Forca_N", "Checksum",
]

NUMERIC_COLS = [
    "Tensao_Pa", "Modulo_Elast", "Tensao_Max",
    "Deform_Along", "Alonga_Ruptura", "Deslocamento", "Forca_N",
]


@dataclass
class EnsaioMetadata:
    version: str
    equipment_id: str
    code: str
    filename: str


def _clean_header_line(line: str) -> str:
    stripped = line.strip()
    if re.fullmatch(r"(\S )+\S?", stripped):
        stripped = stripped.replace(" ", "")
    return stripped


def parse_csv(filepath: str | Path) -> tuple[EnsaioMetadata, pd.DataFrame]:
    filepath = Path(filepath)

    with open(filepath, encoding="utf-16") as f:
        raw_lines = f.readlines()

    meta_parts = raw_lines[0].strip().split("\t") if raw_lines else []
    metadata = EnsaioMetadata(
        version=meta_parts[0].strip() if len(meta_parts) > 0 else "HISTORY V1.0",
        equipment_id=meta_parts[1].strip() if len(meta_parts) > 1 else "",
        code=meta_parts[2].strip() if len(meta_parts) > 2 else "",
        filename=filepath.stem,
    )

    df = pd.read_csv(
        filepath, encoding="utf-16", sep="\t", skiprows=4,
        header=None, names=COLUMN_NAMES, dtype=str, on_bad_lines="skip",
    )

    df = df.dropna(how="all")
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Forca_N"])
    df = df.drop(columns=["Checksum"], errors="ignore")
    df = df.reset_index(drop=True)

    df["timestamp"] = pd.to_datetime(
        df["DATA"].str.strip() + " " + df["TIME"].str.strip(),
        format="%d/%m/%Y %H:%M:%S", errors="coerce",
    )

    valid_ts = df["timestamp"].notna()
    if valid_ts.any():
        df = df.sort_values("timestamp", kind="stable").reset_index(drop=True)
        ts_max = df["timestamp"].cummax()
        df = df[df["timestamp"] >= ts_max].reset_index(drop=True)

    t0 = df["timestamp"].dropna().iloc[0] if not df["timestamp"].dropna().empty else None
    if t0 is not None:
        df["elapsed_seconds"] = (df["timestamp"] - t0).dt.total_seconds()
    else:
        df["elapsed_seconds"] = np.arange(len(df), dtype=float)

    df = _trim_precontact(df)
    df["fase"] = _detect_stages(df)

    return metadata, df
