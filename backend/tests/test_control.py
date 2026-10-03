"""Testes do controle/aquisição via CLP: codecs Modbus de 32 bits e a montagem
do DataFrame de ensaio a partir de amostras de força/deslocamento."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.acquisition import build_ensaio_dataframe
from backend.calculator import calculate_kpis, format_chart_data
from backend.modbus_client import (
    _decode_float32,
    _decode_int32,
    encode_float32,
    encode_int32,
)


# ---------------------------------------------------------------------------
# Codecs round-trip
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("value", [0.0, 1.0, -1.0, 3.14159, 12345.678, -987.6])
def test_float32_roundtrip(value):
    hi, lo = encode_float32(value)
    decoded = _decode_float32(hi, lo)
    assert decoded == pytest.approx(value, rel=1e-5, abs=1e-3)


@pytest.mark.parametrize("value", [0, 1, -1, 100000, -50000, 2_000_000_000])
def test_int32_roundtrip(value):
    hi, lo = encode_int32(value)
    assert _decode_int32(hi, lo) == value


def test_int32_words_are_16bit():
    hi, lo = encode_int32(70000)  # > 16 bits, garante split correto HI/LO
    assert 0 <= hi <= 0xFFFF and 0 <= lo <= 0xFFFF
    assert _decode_int32(hi, lo) == 70000


# ---------------------------------------------------------------------------
# build_ensaio_dataframe
# ---------------------------------------------------------------------------

def _ramp_samples(n_load=100, n_drop=20):
    """Rampa linear de tração até a ruptura (queda abrupta de força)."""
    samples = []
    for i in range(n_load + n_drop):
        if i < n_load:
            f = 50.0 * i        # 0..(n_load-1)*50 N
            d = 0.05 * i        # mm
        else:
            f = max(50.0 * (n_load - 1) - (i - n_load + 1) * 1500.0, 0.0)
            d = 0.05 * (n_load - 1) + (i - n_load + 1) * 0.05
        samples.append({"t_ms": i * 100, "forca": f, "deslocamento": d})
    return samples


def test_build_dataframe_columns_and_derivations():
    area, l0 = 20.0, 50.0
    meta, df = build_ensaio_dataframe(_ramp_samples(), area, l0, filename="CLP_x.csv")

    for col in ["Forca_N", "Deslocamento", "Tensao_Pa", "Tensao_Max",
                "Deform_Along", "Alonga_Ruptura", "Modulo_Elast",
                "elapsed_seconds", "fase", "DATA", "TIME"]:
        assert col in df.columns, f"coluna ausente: {col}"

    assert meta.version == "CLP V1.0"
    fmax = df["Forca_N"].max()
    # σ = F/A
    assert df["Tensao_Pa"].max() == pytest.approx(fmax / area, rel=1e-6)
    # ε e A% coerentes com d/L0 na ruptura
    idx = df["Forca_N"].idxmax()
    d_rup = df.loc[idx, "Deslocamento"]
    assert df.loc[idx, "Deform_Along"] == pytest.approx(d_rup / l0, rel=1e-6)
    assert df.loc[idx, "Alonga_Ruptura"] == pytest.approx(d_rup / l0 * 100, rel=1e-6)


def test_build_dataframe_feeds_pipeline():
    area, l0 = 20.0, 50.0
    _, df = build_ensaio_dataframe(_ramp_samples(), area, l0, filename="CLP_y.csv")
    kpis = calculate_kpis(df, ihm_params={"area_seccao": area, "comprimento_inicial": l0})
    assert kpis["forca_max_N"] > 0
    assert kpis["tensao_max_MPa"] == pytest.approx(kpis["forca_max_N"] / area, rel=1e-4)
    chart = format_chart_data(df)
    assert {"stress_strain", "force_displacement", "rupture"} <= set(chart.keys())


def test_build_dataframe_without_area_uses_raw_units():
    # área/L0 inválidos não devem quebrar a montagem (unidades cruas)
    _, df = build_ensaio_dataframe(_ramp_samples(), 0.0, 0.0, filename="CLP_z.csv")
    assert len(df) > 10
    # com área=1, tensão == força
    assert df["Tensao_Pa"].max() == pytest.approx(df["Forca_N"].max(), rel=1e-6)


def test_build_dataframe_skips_incomplete_samples():
    samples = [{"t_ms": i * 100, "forca": None, "deslocamento": None} for i in range(5)]
    samples += _ramp_samples()
    _, df = build_ensaio_dataframe(samples, 20.0, 50.0, filename="CLP_w.csv")
    assert df["Forca_N"].notna().all()


# ---------------------------------------------------------------------------
# Dispositivos Delta → endereço Modbus
# ---------------------------------------------------------------------------

from backend.modbus_client import device_to_modbus, resolve_register  # noqa: E402


@pytest.mark.parametrize("device,expected", [
    ("D412",  (0x1000 + 412, "holding")),
    ("D3004", (0x1000 + 3004, "holding")),
    ("D4096", (0x9000, "holding")),
    ("M5",    (0x0800 + 5, "coil")),
    ("M101",  (0x0800 + 101, "coil")),
    ("M1536", (0xB000, "coil")),
    ("X0",    (0x0400, "input")),
    ("X10",   (0x0400 + 8, "input")),   # X é octal no DVP
    ("Y1",    (0x0501, "coil")),
])
def test_dvp_device_addresses(device, expected):
    assert device_to_modbus(device, "dvp") == expected


@pytest.mark.parametrize("device,expected", [
    ("D412",  (412, "holding")),
    ("M101",  (101, "coil")),
    ("X0.2",  (0x6002, "input")),
    ("X1.0",  (0x6010, "input")),
])
def test_as_device_addresses(device, expected):
    assert device_to_modbus(device, "as") == expected


@pytest.mark.parametrize("device", ["X8", "Z1", "D", "Dabc"])
def test_invalid_devices(device):
    with pytest.raises(ValueError):
        device_to_modbus(device, "dvp")


def test_resolve_register_device_overrides_address():
    reg = {"name": "desl", "device": "d600", "address": 40039, "data_type": "float32"}
    out = resolve_register(reg, "dvp")
    assert out["address"] == 0x1000 + 600
    assert out["data_type"] == "float32"
    assert reg["address"] == 40039  # não altera o original


def test_resolve_register_input_is_readonly():
    out = resolve_register({"name": "emg", "device": "X0", "data_type": "coil", "writable": True})
    assert out["data_type"] == "input" and out["writable"] is False


def test_resolve_register_without_device_is_unchanged():
    reg = {"name": "x", "address": 123, "data_type": "uint16"}
    assert resolve_register(reg) is reg
