"""Testes do módulo de flexão: fórmulas, builder de DataFrame, KPIs e fases."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.flexao.acquisition import build_ensaio_flexao_dataframe
from backend.flexao.calculator import (
    calculate_kpis,
    epsilon_flexao,
    format_chart_data,
    sigma_flexao,
)

# Geometria do corpo de prova (típica ISO 178: L/h = 16)
B, H, L = 10.0, 4.0, 64.0


# ---------------------------------------------------------------------------
# Fórmulas
# ---------------------------------------------------------------------------

def test_sigma_flexao():
    # σf = 3·F·L / (2·b·h²) = 3·100·64 / (2·10·16) = 60 MPa
    assert sigma_flexao(100.0, L, B, H) == pytest.approx(60.0)


def test_epsilon_flexao():
    # εf = 6·s·h / L² = 6·2·4 / 4096
    assert epsilon_flexao(2.0, L, H) == pytest.approx(48.0 / 4096.0)


def test_geometria_invalida_nao_explode():
    assert sigma_flexao(100.0, L, 0.0, H) == 0.0
    assert epsilon_flexao(2.0, 0.0, H) == 0.0


# ---------------------------------------------------------------------------
# Builder + KPIs
# ---------------------------------------------------------------------------

def _synthetic_samples(n: int = 40):
    """Curva de flexão sintética: rampa linear de força até o pico e depois queda
    abrupta (ruptura). Deflexão proporcional ao tempo."""
    samples = []
    for i in range(n):
        s = i * 0.5                       # deflexão em mm
        if i < n - 2:
            forca = 50.0 * i              # rampa linear
        else:
            forca = 5.0                   # queda abrupta → ruptura
        samples.append({"t_ms": i * 100, "forca": forca, "deslocamento": s})
    return samples


def test_build_dataframe_colunas():
    _, df = build_ensaio_flexao_dataframe(_synthetic_samples(), B, H, L)
    for col in ("Forca_N", "Deslocamento", "Tensao_Flexao", "Deform_Flexao", "Modulo_Flexao", "fase"):
        assert col in df.columns
    assert len(df) >= 10


def test_kpis_flexao():
    metadata, df = build_ensaio_flexao_dataframe(_synthetic_samples(), B, H, L)
    geom = {"largura_mm": B, "espessura_mm": H, "span_mm": L, "norma": "ISO 178"}
    kpis = calculate_kpis(df, geom=geom)

    fmax = df["Forca_N"].max()
    assert kpis["forca_max_N"] == pytest.approx(fmax)
    # σfM coerente com a fórmula aplicada ao Fmax
    assert kpis["tensao_flexao_max_MPa"] == pytest.approx(sigma_flexao(fmax, L, B, H), rel=1e-3)
    assert kpis["modulo_flexao_MPa"] > 0
    assert kpis["norma"] == "ISO 178:2019"


def test_kpis_campos_obrigatorios():
    _, df = build_ensaio_flexao_dataframe(_synthetic_samples(), B, H, L)
    kpis = calculate_kpis(df, geom={"largura_mm": B, "espessura_mm": H, "span_mm": L})
    required = [
        "forca_max_N", "tensao_flexao_max_MPa", "resistencia_flexao_MPa",
        "modulo_flexao_MPa", "modulo_flexao_GPa", "deflexao_max_mm",
        "deform_flexao_max_pct", "tempo_ensaio_s", "rigidez_N_mm",
        "energia_J", "cv_modulo", "norma",
    ]
    for f in required:
        assert f in kpis, f"KPI ausente: {f}"


# ---------------------------------------------------------------------------
# Fases
# ---------------------------------------------------------------------------

def test_deteccao_ruptura():
    _, df = build_ensaio_flexao_dataframe(_synthetic_samples(), B, H, L)
    # Último ponto é queda abrupta → ruptura
    assert df["fase"].iloc[-1] == "ruptura"
    assert (df["fase"] == "elastico_linear").any()


def test_fim_ensaio_sem_ruptura():
    # Rampa monotônica sem queda → fim_ensaio (não rompe)
    samples = [{"t_ms": i * 100, "forca": 20.0 * i, "deslocamento": i * 0.5} for i in range(40)]
    _, df = build_ensaio_flexao_dataframe(samples, B, H, L)
    assert df["fase"].iloc[-1] == "fim_ensaio"


# ---------------------------------------------------------------------------
# Curvas
# ---------------------------------------------------------------------------

def test_chart_data_structure():
    _, df = build_ensaio_flexao_dataframe(_synthetic_samples(), B, H, L)
    charts = format_chart_data(df)
    for key in ("stress_strain", "force_displacement", "force_time",
                "flexural_modulus_time", "stress_time", "peak", "Ef_regressao"):
        assert key in charts
    assert charts["peak"]["Forca_N"] == pytest.approx(df["Forca_N"].max())
