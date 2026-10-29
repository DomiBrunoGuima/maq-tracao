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


@pytest.mark.parametrize("device,expected", [
    ("D600", (600, "holding")),
    ("M101", (101, "coil")),
    ("X10",  (8, "input")),
])
def test_direto_device_addresses(device, expected):
    assert device_to_modbus(device, "direto") == expected


def test_write_multiplies_by_scale():
    from backend.modbus_client import ModbusController

    class _Resp:
        def isError(self):
            return False

    class _Cli:
        def __init__(self):
            self.sent = None
        def write_registers(self, address, values):
            self.sent = values
            return _Resp()
        def write_register(self, address, value):
            self.sent = [value]
            return _Resp()

    ctrl = ModbusController("x", 502, 1, [])
    ctrl._client = _Cli()
    ctrl.write_register({"address": 0, "data_type": "uint16", "scale": 10}, 5)
    assert ctrl._client.sent == [50]
    ctrl.write_register({"address": 0, "data_type": "float32", "scale": 2, "word_order": "little"}, 1.5)
    lo, hi = ctrl._client.sent
    assert _decode_float32(hi, lo) == pytest.approx(3.0)


def test_flexao_usa_registradores_da_tracao(monkeypatch):
    from backend import main

    cfg = {
        **main._config,
        "control_registers": [
            {"name": "zerar_desl", "role": "zerar_deslocamento", "address": 4019, "data_type": "coil"},
            {"name": "tara", "role": "zerar_celula", "address": 4020, "data_type": "coil"},
        ],
        "flexao_registers": [
            {"name": "zerar_deslocamento", "role": "zerar_deslocamento", "address": 0, "data_type": "coil"},
            {"name": "fim_ensaio_bit", "role": "fim_ensaio_bit", "address": 4010, "data_type": "coil"},
        ],
    }
    monkeypatch.setattr(main, "_config", cfg)
    regs = {r["role"]: r["address"] for r in main._flexao_registers()}
    assert regs == {"zerar_deslocamento": 4019, "zerar_celula": 4020, "fim_ensaio_bit": 4010}

    # Separado: a flexão passa a usar o registrador próprio para esse papel
    cfg["flexao_registers"][0]["address"] = 4004
    cfg["flexao_separados"] = ["zerar_deslocamento"]
    regs = {r["role"]: r["address"] for r in main._flexao_registers()}
    assert regs == {"zerar_deslocamento": 4004, "zerar_celula": 4020, "fim_ensaio_bit": 4010}


def test_configuracoes_exigem_senha(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from backend import acesso, main

    monkeypatch.setattr(main, "_CONFIG_FILE", tmp_path / "config.json")
    cfg = {k: v for k, v in main._config.items() if k != "senha_config"}
    monkeypatch.setattr(main, "_config", cfg)
    cli = TestClient(main.app)

    corpo = {**cfg, "auto_load": False}
    assert cli.put("/api/config", json=corpo).status_code == 401
    assert cli.post("/api/config/login", json={"senha": "errada"}).status_code == 401

    token = cli.post("/api/config/login", json={"senha": acesso.SENHA_PADRAO}).json()["token"]
    h = {"X-Config-Token": token}
    assert cli.put("/api/config", json=corpo, headers=h).status_code == 200

    assert cli.post("/api/config/senha", json={"atual": acesso.SENHA_PADRAO, "nova": "nova123"},
                    headers=h).status_code == 200
    assert "senha_config" not in cli.get("/api/config").json()
    assert cli.post("/api/config/login", json={"senha": acesso.SENHA_PADRAO}).status_code == 401
    assert cli.post("/api/config/login", json={"senha": "nova123"}).status_code == 200


def test_flexao_desabilitada_bloqueia_inicio(monkeypatch):
    from fastapi.testclient import TestClient
    from backend import main

    monkeypatch.setattr(main, "_config", {**main._config, "flexao_habilitada": False})
    r = TestClient(main.app).post("/api/flexao/control/start", json={})
    assert r.status_code == 403
    assert "desabilitada" in r.json()["detail"]


def test_forca_do_clp_em_kgf_vira_newton(monkeypatch):
    from backend import main

    regs = [
        {"name": "forca", "role": "forca_atual", "address": 40050, "data_type": "float32", "scale": 1.0},
        {"name": "fmax", "role": "forca_maxima", "address": 40052, "data_type": "float32"},
        {"name": "limite_forca", "role": "limite_forca", "address": 40008, "data_type": "float32"},
        {"name": "desl", "role": "deslocamento_atual", "address": 40040, "data_type": "float32", "scale": 1.0},
    ]
    monkeypatch.setattr(main, "_config", {**main._config, "plc_family": "direto",
                                          "forca_clp_kgf": True, "control_registers": regs})
    escala = {r["role"]: r["scale"] for r in main._control_registers()}
    assert escala["forca_atual"] == pytest.approx(9.80665)
    assert escala["forca_maxima"] == pytest.approx(9.80665)
    assert escala["limite_forca"] == pytest.approx(1 / 9.80665)
    assert escala["deslocamento_atual"] == 1.0
    assert regs[0]["scale"] == 1.0  # a config não é alterada

    main._config["forca_clp_kgf"] = False
    assert all(r.get("scale", 1.0) == 1.0 for r in main._control_registers())
