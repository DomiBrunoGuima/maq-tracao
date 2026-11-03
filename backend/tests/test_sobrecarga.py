"""Proteção de sobrecarga: limite da célula de carga em kgf e pulso de parada."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.sobrecarga import N_POR_KGF, MonitorSobrecarga


class Relogio:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def _monitor(cfg, relogio=None):
    return MonitorSobrecarga(lambda: cfg, agora=relogio or Relogio())


def test_desligado_nao_dispara():
    pulsos = []
    m = _monitor({"sobrecarga_ativa": False, "sobrecarga_limite_kgf": 10})
    assert m.verificar(1000 * N_POR_KGF, lambda: pulsos.append(1)) is False
    m = _monitor({"sobrecarga_ativa": True, "sobrecarga_limite_kgf": 0})
    assert m.verificar(1000 * N_POR_KGF, lambda: pulsos.append(1)) is False
    assert pulsos == []


def test_dispara_no_limite_e_trava_ate_reconhecer():
    pulsos = []
    rel = Relogio()
    m = _monitor({"sobrecarga_ativa": True, "sobrecarga_limite_kgf": 500}, rel)

    assert m.verificar(499 * N_POR_KGF, lambda: pulsos.append(1)) is False
    assert m.estado()["ativo"] is False

    assert m.verificar(500 * N_POR_KGF, lambda: pulsos.append(1)) is True
    e = m.estado()
    assert e["ativo"] and e["pulso_enviado"] and e["limite_kgf"] == 500
    assert e["forca_max_kgf"] == 500
    assert pulsos == [1]

    # Ainda acima do limite logo em seguida: não repete o pulso antes de 2 s
    rel.t = 1.0
    m.verificar(520 * N_POR_KGF, lambda: pulsos.append(1))
    assert pulsos == [1]
    rel.t = 2.5
    m.verificar(510 * N_POR_KGF, lambda: pulsos.append(1))
    assert pulsos == [1, 1]
    assert m.estado()["forca_max_kgf"] == 520

    # A força caiu, mas o alarme continua até o operador reconhecer
    m.verificar(0.0, lambda: pulsos.append(1))
    assert m.estado()["ativo"] is True
    assert m.reconhecer()["ativo"] is False


def test_compressao_usa_modulo_da_forca():
    pulsos = []
    m = _monitor({"sobrecarga_ativa": True, "sobrecarga_limite_kgf": 100})
    assert m.verificar(-150 * N_POR_KGF, lambda: pulsos.append(1)) is True
    assert pulsos == [1]


def test_falha_no_pulso_fica_registrada():
    def falha():
        raise RuntimeError("CLP inacessível")

    m = _monitor({"sobrecarga_ativa": True, "sobrecarga_limite_kgf": 1})
    assert m.verificar(100.0, falha) is True
    e = m.estado()
    assert e["ativo"] and not e["pulso_enviado"] and "inacessível" in e["erro"]


class FakeCtrl:
    def __init__(self, regs, log):
        self.by_role = {r["role"]: r for r in regs if r.get("role")}
        self.log = log

    def resolve(self, role):
        return self.by_role.get(role)

    def connect(self):
        return True

    def close(self):
        pass

    def pulse(self, role, ms=300):
        self.log.append(("pulse", role))

    def write_named(self, role, value):
        self.log.append(("write", role, value))


def _cfg_maquina(main, extra_regs=()):
    return {
        **main._config,
        "simulator_enabled": False, "clp_ip": "10.0.0.1",
        "forca_clp_kgf": True,
        "sobrecarga_ativa": True, "sobrecarga_limite_kgf": 200.0,
        "control_registers": [
            {"name": "forca_atual", "role": "forca_atual", "address": 40079, "data_type": "float32"},
            {"name": "parar", "role": "parar", "address": 4001, "data_type": "coil", "writable": True},
            {"name": "sentido_cima", "role": "sentido_cima", "address": 3999, "data_type": "coil", "writable": True},
            *extra_regs,
        ],
    }


def test_status_dispara_pulso_de_parada(monkeypatch):
    from fastapi.testclient import TestClient
    from backend import main

    log: list = []
    monkeypatch.setattr(main, "_config", _cfg_maquina(main))
    monkeypatch.setattr(main, "_sobrecarga", MonitorSobrecarga(lambda: main._config))
    monkeypatch.setattr(main, "_make_controller", lambda: FakeCtrl(main._control_registers(), log))
    # A IHM devolve 250 kgf; o software converte para N (× 9,80665) antes de comparar
    monkeypatch.setattr(main, "capture_registers",
                        lambda ip, port, timeout, regs: {"forca_atual": 250 * N_POR_KGF})
    cli = TestClient(main.app)

    s = cli.get("/api/control/status").json()
    assert s["sobrecarga"]["ativo"] is True
    assert ("pulse", "parar") in log and ("write", "sentido_cima", 0) in log

    # Com o alarme ativo, não deixa iniciar outro ensaio
    r = cli.post("/api/control/start", json={"sentido": "cima"})
    assert r.status_code == 409

    assert cli.post("/api/sobrecarga/reconhecer").json()["ativo"] is False


def test_usa_registrador_proprio_quando_mapeado(monkeypatch):
    from backend import main

    log: list = []
    extra = ({"name": "alarme", "role": "parada_sobrecarga", "address": 4040, "data_type": "coil", "writable": True},)
    monkeypatch.setattr(main, "_config", _cfg_maquina(main, extra))
    monkeypatch.setattr(main, "_make_controller", lambda: FakeCtrl(main._control_registers(), log))
    main._parada_sobrecarga(main._make_controller)()
    assert ("pulse", "parada_sobrecarga") in log and ("pulse", "parar") not in log
