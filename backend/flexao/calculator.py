"""Cálculos do ensaio de flexão a 3 pontos.

Geometria do corpo de prova (entradas do ensaio):
    b = largura (mm)
    h = espessura/altura (mm)
    L = distância entre apoios / span (mm)

Fórmulas (idênticas em ISO 178 e ASTM D790 para flexão a 3 pontos):

    σf = 3 · F · L / (2 · b · h²)        tensão de flexão (MPa, com F em N e mm)
    εf = 6 · s · h / L²                  deformação de flexão (adimensional; s = deflexão)
    Ef = (L³ / (4 · b · h³)) · (ΔF/Δs)   módulo de flexão (MPa)

O módulo também é calculado por dois caminhos:
  • regressão linear de σf×εf na região elástica detectada (``modulo_flexao_MPa``);
  • módulo cordal entre dois pontos de deformação definidos pela norma
    (``modulo_cordal_MPa``) — ISO 178 usa εf1=0,0005 e εf2=0,0025.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Fases consideradas "carregamento" (pré-pico) para taxas/energia/regressão.
_LOADING = frozenset([
    "acomodacao", "elastico_linear", "pos_escoamento", "carregamento",
])
_ELASTIC = "elastico_linear"

# Parâmetros por norma. ``eps1``/``eps2`` definem os pontos do módulo cordal.
NORMAS_FLEXAO: dict[str, dict] = {
    "ISO 178":   {"label": "ISO 178:2019",  "eps1": 0.0005, "eps2": 0.0025},
    "ASTM D790": {"label": "ASTM D790-17",  "eps1": 0.0,    "eps2": 0.0025},
}
NORMA_PADRAO = "ISO 178"


def _norma_cfg(norma: str | None) -> dict:
    return NORMAS_FLEXAO.get(norma or NORMA_PADRAO, NORMAS_FLEXAO[NORMA_PADRAO])


def sigma_flexao(forca_N: float, L: float, b: float, h: float) -> float:
    """σf = 3·F·L / (2·b·h²) — MPa."""
    if b <= 0 or h <= 0:
        return 0.0
    return 3.0 * forca_N * L / (2.0 * b * h * h)


def epsilon_flexao(deflexao_mm: float, L: float, h: float) -> float:
    """εf = 6·s·h / L² — adimensional."""
    if L <= 0:
        return 0.0
    return 6.0 * deflexao_mm * h / (L * L)


def calculate_kpis(df: pd.DataFrame, geom: dict | None = None) -> dict:
    """KPIs de flexão a partir de um DataFrame já com colunas derivadas.

    ``geom`` carrega ``largura_mm``/``espessura_mm``/``span_mm``/``norma`` quando
    disponíveis (usados para o módulo cordal e o relatório). As colunas σf/εf já
    vêm calculadas por :func:`acquisition.build_ensaio_flexao_dataframe`.
    """
    valid_forca = df["Forca_N"].dropna()
    if valid_forca.empty:
        raise ValueError(
            f"Ensaio de flexão sem dados de força válidos ({len(df)} amostras) — incompleto ou corrompido"
        )

    geom = geom or {}
    norma = geom.get("norma")
    ncfg = _norma_cfg(norma)

    peak_loc = df["Forca_N"].idxmax()
    peak_row = df.loc[peak_loc]

    forca_max          = float(df["Forca_N"].max())
    tensao_flexao_max  = float(df["Tensao_Flexao"].max())
    deflexao_max       = float(df["Deslocamento"].max())
    deflexao_pico      = float(peak_row["Deslocamento"])
    deform_flexao_max  = float(df["Deform_Flexao"].max())
    tempo_ensaio       = float(df["elapsed_seconds"].max())
    tempo_pico         = float(peak_row["elapsed_seconds"])

    loading_df = df[df["fase"].isin(_LOADING)]
    elastic_df = df[df["fase"] == _ELASTIC]

    # ── Módulo de flexão via regressão na região elástica (σf×εf) ────────────
    modulo_flexao_MPa: float | None = None
    if len(elastic_df) >= 3:
        eps = elastic_df["Deform_Flexao"].to_numpy(dtype=float)
        sig = elastic_df["Tensao_Flexao"].to_numpy(dtype=float)
        valid = np.isfinite(eps) & np.isfinite(sig)
        if valid.sum() >= 3 and float(np.std(eps[valid])) > 0:
            coeffs = np.polyfit(eps[valid], sig[valid], 1)
            modulo_flexao_MPa = float(coeffs[0])

    # ── Módulo cordal entre εf1 e εf2 da norma — Ef = (σf2 − σf1)/(εf2 − εf1) ─
    modulo_cordal_MPa: float | None = None
    eps1, eps2 = ncfg["eps1"], ncfg["eps2"]
    if eps2 > eps1:
        eps_all = df["Deform_Flexao"].to_numpy(dtype=float)
        sig_all = df["Tensao_Flexao"].to_numpy(dtype=float)
        order = np.argsort(eps_all)
        eps_s, sig_s = eps_all[order], sig_all[order]
        if eps_s.size >= 2 and eps_s[0] <= eps2 and eps_s[-1] >= eps1:
            sig1 = float(np.interp(eps1, eps_s, sig_s))
            sig2 = float(np.interp(eps2, eps_s, sig_s))
            modulo_cordal_MPa = (sig2 - sig1) / (eps2 - eps1)

    # ── Rigidez ΔF/Δs e taxa de carregamento ────────────────────────────────
    rigidez = 0.0
    taxa_carregamento = 0.0
    if len(loading_df) > 1:
        ds = loading_df["Deslocamento"].max() - loading_df["Deslocamento"].min()
        dF = loading_df["Forca_N"].max() - loading_df["Forca_N"].min()
        rigidez = dF / ds if ds > 0 else 0.0
        dt = loading_df["elapsed_seconds"].max() - loading_df["elapsed_seconds"].min()
        taxa_carregamento = dF / dt if dt > 0 else 0.0

    # ── Energia até o pico = ∫ F ds ──────────────────────────────────────────
    loading_for_energy = loading_df.sort_values("Deslocamento")
    _trapz = getattr(np, "trapezoid", None) or getattr(np, "trapz")
    energia = float(
        _trapz(
            loading_for_energy["Forca_N"].values,
            loading_for_energy["Deslocamento"].values,
        )
    ) if len(loading_for_energy) > 1 else 0.0

    # ── Tensão de escoamento de flexão: queda do módulo local > 10% ──────────
    tensao_escoamento = None
    if modulo_flexao_MPa and modulo_flexao_MPa > 0:
        threshold = modulo_flexao_MPa * 0.90
        for _, row in loading_df.iterrows():
            if 0 < row["Modulo_Flexao"] < threshold:
                tensao_escoamento = float(row["Tensao_Flexao"])
                break

    # CV do módulo na região elástica (estabilidade da reta)
    cv_modulo = 0.0
    if len(elastic_df) > 1 and elastic_df["Modulo_Flexao"].mean() != 0:
        cv_modulo = float(
            elastic_df["Modulo_Flexao"].std() / elastic_df["Modulo_Flexao"].mean()
        )

    modulo_final = modulo_cordal_MPa or modulo_flexao_MPa or 0.0

    return {
        "forca_max_N": forca_max,
        "forca_max_kN": forca_max / 1000,
        "tensao_flexao_max_MPa": tensao_flexao_max,
        "resistencia_flexao_MPa": tensao_flexao_max,           # σfM (alias para relatório)
        "modulo_flexao_MPa": modulo_final,
        "modulo_flexao_GPa": modulo_final / 1000,
        "modulo_regressao_MPa": modulo_flexao_MPa,
        "modulo_cordal_MPa": modulo_cordal_MPa,
        "deflexao_max_mm": deflexao_max,
        "deflexao_pico_mm": deflexao_pico,
        "deform_flexao_max_pct": deform_flexao_max * 100.0,
        "tempo_ensaio_s": tempo_ensaio,
        "tempo_pico_s": tempo_pico,
        "rigidez_N_mm": rigidez,
        "taxa_carregamento_N_s": taxa_carregamento,
        "energia_J": energia,
        "tensao_escoamento_MPa": tensao_escoamento,
        "cv_modulo": cv_modulo,
        "norma": ncfg["label"],
        "largura_mm": geom.get("largura_mm"),
        "espessura_mm": geom.get("espessura_mm"),
        "span_mm": geom.get("span_mm"),
    }


def _break_cutoff(df: pd.DataFrame) -> int:
    """Índice (inclusivo) até onde plotar: primeira queda abrupta de força (>50%
    de Fmax num passo) após o pico. Sem queda (ensaio que não rompe) → último ponto."""
    forca = df["Forca_N"].values.astype(float)
    n = len(forca)
    if n < 2:
        return n - 1
    peak_pos = int(np.argmax(forca))
    fmax = float(forca[peak_pos])
    if fmax <= 0:
        return n - 1
    threshold = fmax * 0.50
    for i in range(peak_pos + 1, n):
        if forca[i - 1] - forca[i] > threshold:
            return i
    return n - 1


def format_chart_data(df: pd.DataFrame) -> dict:
    def safe_records(sub: pd.DataFrame, fields: list[str]) -> list[dict]:
        out = []
        for _, row in sub.iterrows():
            record = {}
            for f in fields:
                val = row.get(f, None)
                record[f] = None if (isinstance(val, float) and np.isnan(val)) else val
            out.append(record)
        return out

    cutoff = _break_cutoff(df)
    df_plot = df.iloc[:cutoff + 1].copy()

    for _col in ["Tensao_Flexao", "Forca_N", "Deslocamento", "Deform_Flexao", "Modulo_Flexao"]:
        if _col in df_plot.columns:
            df_plot[_col] = df_plot[_col].ffill()

    peak_loc = df_plot["Forca_N"].idxmax()
    peak_row = df_plot.loc[peak_loc]
    elastic_df = df_plot[df_plot["fase"] == _ELASTIC]

    Ef_regressao: float | None = None
    if len(elastic_df) >= 3:
        eps_el = elastic_df["Deform_Flexao"].values.astype(float)
        sig_el = elastic_df["Tensao_Flexao"].values.astype(float)
        valid = np.isfinite(eps_el) & np.isfinite(sig_el) & (eps_el > 0)
        if valid.sum() >= 3 and float(np.std(eps_el[valid])) > 0:
            coeffs = np.polyfit(eps_el[valid], sig_el[valid], 1)
            Ef_regressao = float(coeffs[0])

    return {
        "stress_strain": safe_records(
            df_plot, ["Deform_Flexao", "Tensao_Flexao", "fase", "elapsed_seconds"]
        ),
        "force_displacement": safe_records(
            df_plot, ["Deslocamento", "Forca_N", "fase", "elapsed_seconds"]
        ),
        "force_time": safe_records(df_plot, ["elapsed_seconds", "Forca_N", "fase"]),
        "flexural_modulus_time": safe_records(
            elastic_df if len(elastic_df) > 0 else df_plot,
            ["elapsed_seconds", "Modulo_Flexao", "fase"],
        ),
        "stress_time": safe_records(
            df_plot, ["elapsed_seconds", "Tensao_Flexao", "fase"]
        ),
        "peak": {
            "elapsed_seconds": float(peak_row["elapsed_seconds"]),
            "Forca_N": float(peak_row["Forca_N"]),
            "Deform_Flexao": float(peak_row["Deform_Flexao"]),
            "Tensao_Flexao": float(peak_row["Tensao_Flexao"]),
            "Deslocamento": float(peak_row["Deslocamento"]),
        },
        "Ef_regressao": Ef_regressao,
    }
