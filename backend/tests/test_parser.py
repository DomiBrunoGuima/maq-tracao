"""Unit tests for the CSV parser, rupture detection, and energy calculation."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

# Allow running tests from the project root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.calculator import calculate_kpis, format_chart_data
from backend.parser import parse_csv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CSV_CONTENT = (
    "HISTORY V1.0\tMAQ-TEST-001\tTEST01\n"
    "\n"
    "TIME\tDATA\tTensao_Pa\tModulo_Elast\tTensao_Max\tDeform_Along\tAlonga_Ruptura\tDeslocamento\tForca_N\tChecksum\n"
    "TIME\tDATA\t1\t1\t1\t1\t1\t1\t1\tChecksum\n"
    # Loading phase
    "08:00:00\t01/06/2026\t5.00\t100.00\t5.00\t0.05\t5.00\t5.00\t2500.00\tabc001\n"
    "08:00:01\t01/06/2026\t15.00\t200.00\t15.00\t0.10\t10.00\t10.00\t7500.00\tabc002\n"
    # Rupture
    "08:00:02\t01/06/2026\t30.00\t250.00\t30.00\t0.20\t20.00\t20.00\t15000.00\tabc003\n"
    # Post-rupture
    "08:00:03\t01/06/2026\t28.00\t240.00\t30.00\t0.20\t20.00\t20.00\t14000.00\tabc004\n"
    "08:00:04\t01/06/2026\t27.50\t238.00\t30.00\t0.20\t20.00\t20.00\t13750.00\tabc005\n"
)


def _write_test_csv(tmp_path: Path) -> Path:
    csv_file = tmp_path / "TEST01.csv"
    with open(csv_file, "w", encoding="utf-16") as f:
        f.write(_CSV_CONTENT)
    return csv_file


# ---------------------------------------------------------------------------
# Tests: parsing
# ---------------------------------------------------------------------------

def test_basic_parsing(tmp_path):
    csv_file = _write_test_csv(tmp_path)
    metadata, df = parse_csv(csv_file)

    assert metadata.version == "HISTORY V1.0"
    assert metadata.equipment_id == "MAQ-TEST-001"
    assert metadata.code == "TEST01"
    assert metadata.filename == "TEST01"

    assert len(df) == 5
    assert set(["TIME", "DATA", "Tensao_Pa", "Forca_N", "fase", "elapsed_seconds"]).issubset(
        df.columns
    )


def test_numeric_columns(tmp_path):
    csv_file = _write_test_csv(tmp_path)
    _, df = parse_csv(csv_file)

    assert df["Forca_N"].dtype in (float, np.float64)
    assert df["Tensao_Pa"].dtype in (float, np.float64)
    assert df["Forca_N"].iloc[0] == pytest.approx(2500.0)
    assert df["Forca_N"].iloc[2] == pytest.approx(15000.0)  # rupture


def test_elapsed_seconds(tmp_path):
    csv_file = _write_test_csv(tmp_path)
    _, df = parse_csv(csv_file)

    assert df["elapsed_seconds"].iloc[0] == pytest.approx(0.0)
    assert df["elapsed_seconds"].iloc[1] == pytest.approx(1.0)
    assert df["elapsed_seconds"].iloc[4] == pytest.approx(4.0)


def test_rupture_detection(tmp_path):
    csv_file = _write_test_csv(tmp_path)
    _, df = parse_csv(csv_file)

    # Rupture must be at the row with max Forca_N
    rupture_rows = df[df["fase"] == "ruptura"]
    assert len(rupture_rows) == 1
    assert rupture_rows.iloc[0]["Forca_N"] == pytest.approx(15000.0)

    # Everything after rupture is post-rupture
    post = df[df["fase"] == "pos_ruptura"]
    assert len(post) == 2
    assert (post["Forca_N"] < 15000.0).all()


# ---------------------------------------------------------------------------
# Tests: KPI calculation
# ---------------------------------------------------------------------------

def test_kpi_forca_max(tmp_path):
    csv_file = _write_test_csv(tmp_path)
    _, df = parse_csv(csv_file)
    kpis = calculate_kpis(df)

    assert kpis["forca_max_N"] == pytest.approx(15000.0)
    assert kpis["forca_max_kN"] == pytest.approx(15.0)


def test_kpi_tensao_max(tmp_path):
    csv_file = _write_test_csv(tmp_path)
    _, df = parse_csv(csv_file)
    kpis = calculate_kpis(df)

    assert kpis["tensao_max_MPa"] == pytest.approx(30.0)


def test_energy_absorbed(tmp_path):
    """Energy = trapz(F, d) over the loading + rupture phase."""
    csv_file = _write_test_csv(tmp_path)
    _, df = parse_csv(csv_file)
    kpis = calculate_kpis(df)

    # Manual: loading d=[5,10,20], F=[2500,7500,15000]
    # trapz([2500,7500,15000], [5,10,20]) = (7500+2500)/2*5 + (15000+7500)/2*10
    #                                     = 25000 + 112500 = 137500
    assert kpis["energia_J"] == pytest.approx(137500.0, rel=0.01)


def test_kpi_required_fields(tmp_path):
    csv_file = _write_test_csv(tmp_path)
    _, df = parse_csv(csv_file)
    kpis = calculate_kpis(df)

    required = [
        "forca_max_N", "forca_max_kN", "tensao_max_MPa",
        "modulo_elasticidade_MPa", "modulo_elasticidade_GPa",
        "alonga_ruptura_pct", "deslocamento_max_mm",
        "tempo_ruptura_s", "taxa_carregamento_N_s",
        "rigidez_N_mm", "energia_J", "cv_modulo",
    ]
    for field in required:
        assert field in kpis, f"KPI field missing: {field}"


# ---------------------------------------------------------------------------
# Tests: chart data
# ---------------------------------------------------------------------------

def test_chart_data_structure(tmp_path):
    csv_file = _write_test_csv(tmp_path)
    _, df = parse_csv(csv_file)
    charts = format_chart_data(df)

    assert "stress_strain" in charts
    assert "force_displacement" in charts
    assert "force_time" in charts
    assert "elastic_modulus_time" in charts
    assert "stress_time" in charts
    assert "rupture" in charts

    assert len(charts["stress_strain"]) == 5
    assert charts["rupture"]["Forca_N"] == pytest.approx(15000.0)
