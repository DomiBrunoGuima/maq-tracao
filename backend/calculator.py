from __future__ import annotations

import numpy as np
import pandas as pd

_LOADING = frozenset([
    "elastico_linear", "escoamento_superior", "patamar_escoamento",
    "encruamento", "ruptura",
    "carregamento",  # retrocompatibilidade
])
_PRE_UTS = frozenset([
    "elastico_linear", "escoamento_superior", "patamar_escoamento", "encruamento",
    "carregamento",
])


def calculate_kpis(df: pd.DataFrame, ihm_params: dict | None = None) -> dict:
    rupture_loc = df["Forca_N"].idxmax()
    rupture_row = df.loc[rupture_loc]

    loading_df = df[df["fase"].isin(_LOADING)]
    n_loading = max(len(loading_df), 1)
    elastic_end = max(1, int(n_loading * 0.30))
    elastic_df = loading_df.iloc[:elastic_end]

    forca_max = float(df["Forca_N"].max())
    tensao_max = float(df["Tensao_Max"].max())
    alonga_ruptura = float(rupture_row["Alonga_Ruptura"])
    deslocamento_max = float(df["Deslocamento"].max())
    deslocamento_ruptura = float(rupture_row["Deslocamento"])
    tempo_ruptura = float(rupture_row["elapsed_seconds"])

    modulo_medio = float(elastic_df["Modulo_Elast"].mean()) if len(elastic_df) > 0 else 0.0

    loading_only = df[df["fase"].isin(_PRE_UTS)]
    if len(loading_only) > 1:
        dt = loading_only["elapsed_seconds"].max() - loading_only["elapsed_seconds"].min()
        dF = loading_only["Forca_N"].max() - loading_only["Forca_N"].min()
        taxa_carregamento = dF / dt if dt > 0 else 0.0
    else:
        taxa_carregamento = 0.0

    if len(loading_only) > 1:
        dd = loading_only["Deslocamento"].max() - loading_only["Deslocamento"].min()
        dF2 = loading_only["Forca_N"].max() - loading_only["Forca_N"].min()
        rigidez = dF2 / dd if dd > 0 else 0.0
    else:
        rigidez = 0.0

    loading_for_energy = df[df["fase"].isin(_LOADING)].sort_values("Deslocamento")
    _trapz = getattr(np, "trapezoid", None) or getattr(np, "trapz")
    energia = float(
        _trapz(
            loading_for_energy["Forca_N"].values,
            loading_for_energy["Deslocamento"].values,
        )
    ) if len(loading_for_energy) > 1 else 0.0

    # Yield point: first point where Modulo_Elast drops > 10% below elastic mean
    tensao_escoamento = None
    if modulo_medio > 0:
        threshold = modulo_medio * 0.90
        for _, row in loading_df.iterrows():
            if row["Modulo_Elast"] < threshold:
                tensao_escoamento = float(row["Tensao_Pa"])
                break

    cv_modulo = 0.0
    if len(elastic_df) > 1 and elastic_df["Modulo_Elast"].mean() != 0:
        cv_modulo = float(
            elastic_df["Modulo_Elast"].std() / elastic_df["Modulo_Elast"].mean()
        )

    # ── Área da seção e comprimento inicial ─────────────────────────────────
    # Prioridade 1: registrador da IHM (valor configurado diretamente na máquina)
    # Prioridade 2: back-cálculo pela série CSV (F/σ e ΔL/ε)
    area_mm2: float | None = None
    comprimento_inicial_mm: float | None = None

    if ihm_params:
        v = ihm_params.get("area_seccao")
        if v is not None:
            area_mm2 = float(v)
        v = ihm_params.get("comprimento_inicial")
        if v is not None:
            comprimento_inicial_mm = float(v)

    if area_mm2 is None:
        mask_stress = loading_df["Tensao_Pa"] > 0.5
        if mask_stress.sum() >= 3:
            a_series = loading_df.loc[mask_stress, "Forca_N"] / loading_df.loc[mask_stress, "Tensao_Pa"]
            area_mm2 = float(a_series.median())

    if comprimento_inicial_mm is None:
        mask_strain = loading_df["Deform_Along"] > 0.0001
        if mask_strain.sum() >= 3:
            l0_series = loading_df.loc[mask_strain, "Deslocamento"] / loading_df.loc[mask_strain, "Deform_Along"]
            comprimento_inicial_mm = float(l0_series.median())

    # ── σmáx = Fmáx / A  (fórmula da imagem) ────────────────────────────────
    tensao_max_calc_MPa: float | None = (forca_max / area_mm2) if area_mm2 else None

    # ── A% = ((Lf − L0) / L0) × 100  ────────────────────────────────────────
    # Lf = L0 + deslocamento_ruptura  →  A% = (d_ruptura / L0) × 100
    alonga_calc_pct: float | None = (
        (deslocamento_ruptura / comprimento_inicial_mm) * 100
        if comprimento_inicial_mm else None
    )

    # ── E via regressão linear na região elástica  ───────────────────────────
    # Se A e L0 da IHM estiverem disponíveis, recalcula σ e ε diretamente de
    # Forca_N e Deslocamento para máxima precisão
    modulo_regressao_MPa: float | None = None
    if len(elastic_df) >= 3:
        if area_mm2 and comprimento_inicial_mm:
            sigma_el = elastic_df["Forca_N"].values / area_mm2
            eps_el   = elastic_df["Deslocamento"].values / comprimento_inicial_mm
        else:
            sigma_el = elastic_df["Tensao_Pa"].values
            eps_el   = elastic_df["Deform_Along"].values
        if float(np.std(eps_el)) > 0:
            coeffs = np.polyfit(eps_el, sigma_el, 1)
            modulo_regressao_MPa = float(coeffs[0])

    # ── Velocidade programada da IHM (se disponível) ─────────────────────────
    # A escala é aplicada pelo capture_registers via o campo scale do registrador.
    velocidade_ihm: float | None = None
    if ihm_params:
        for k in ("velocidade_processamento", "velocidade_programa", "velocidade_pro",
                  "velocidade_programada"):
            if ihm_params.get(k) is not None:
                velocidade_ihm = float(ihm_params[k])
                break

    return {
        "forca_max_N": forca_max,
        "forca_max_kN": forca_max / 1000,
        "tensao_max_MPa": tensao_max,
        "modulo_elasticidade_MPa": modulo_medio,
        "modulo_elasticidade_GPa": modulo_medio / 1000,
        "alonga_ruptura_pct": alonga_ruptura,
        "deslocamento_max_mm": deslocamento_max,
        "tempo_ruptura_s": tempo_ruptura,
        "taxa_carregamento_N_s": taxa_carregamento,
        "rigidez_N_mm": rigidez,
        "energia_J": energia,
        "tensao_escoamento_MPa": tensao_escoamento,
        "cv_modulo": cv_modulo,
        "area_secao_mm2": area_mm2,
        "comprimento_inicial_mm": comprimento_inicial_mm,
        "tensao_max_calc_MPa": tensao_max_calc_MPa,
        "alonga_calc_pct": alonga_calc_pct,
        "modulo_regressao_MPa": modulo_regressao_MPa,
        "velocidade_ihm": velocidade_ihm,
    }


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

    rupture_loc = df["Forca_N"].idxmax()
    rupture_row = df.loc[rupture_loc]

    return {
        "stress_strain": safe_records(
            df,
            ["Deform_Along", "Tensao_Pa", "fase", "elapsed_seconds"],
        ),
        "force_displacement": safe_records(
            df, ["Deslocamento", "Forca_N", "fase", "elapsed_seconds"]
        ),
        "force_time": safe_records(df, ["elapsed_seconds", "Forca_N", "fase"]),
        "elastic_modulus_time": safe_records(
            df, ["elapsed_seconds", "Modulo_Elast", "fase"]
        ),
        "stress_time": safe_records(
            df, ["elapsed_seconds", "Tensao_Pa", "fase"]
        ),
        "rupture": {
            "elapsed_seconds": float(rupture_row["elapsed_seconds"]),
            "Forca_N": float(rupture_row["Forca_N"]),
            "Deform_Along": float(rupture_row["Deform_Along"]),
            "Tensao_Pa": float(rupture_row["Tensao_Pa"]),
            "Deslocamento": float(rupture_row["Deslocamento"]),
        },
    }
