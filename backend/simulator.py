"""Simulador in-process da IHM/CLP.

Permite iniciar e finalizar um ensaio completo **sem hardware**: modela um ensaio
de tração/flexão (curva força×deslocamento com região elástica, encruamento e
ruptura) e responde como se fosse o CLP real, via os mesmos objetos que o caminho
Modbus usa (controller para comandos/setpoints, reader para leitura contínua).

Ligado/desligado por ``simulator_enabled`` na config. Quando ligado, o ``main``
troca o controller/reader reais pelos simulados — nada mais muda no pipeline.
"""
from __future__ import annotations

import random
import time
from typing import Any


class _Sim:
    """Estado único do ensaio simulado (compartilhado entre requisições)."""

    def __init__(self) -> None:
        # Setpoints correntes (atualizados pela escrita antes do "iniciar").
        self.limite_forca = 5000.0
        self.velocidade = 50.0          # mm/min
        self.deslocamento_alvo = 50.0   # mm
        self.sentido = "cima"
        # Estado de execução.
        self.running = False
        self.t0: float | None = None
        self.ruptura = False
        self.fim = False
        self.residual_disp = 0.0        # deslocamento que "sobra" após o ensaio
        self._last_disp = 0.0
        self._last_forca = 0.0
        self._new_profile()

    # -- perfil aleatório (porém plausível) do corpo de prova -------------
    def _new_profile(self) -> None:
        self.rupture_force = random.uniform(2500.0, 6000.0)   # N
        self.stiffness = random.uniform(700.0, 1600.0)        # N/mm (região elástica)
        self.rupture_disp = random.uniform(6.0, 18.0)         # mm
        self.yield_frac = random.uniform(0.55, 0.78)          # fração de Fmax no escoamento
        self.noise = random.uniform(1.5, 6.0)                 # ruído de força (N)

    # -- comandos --------------------------------------------------------
    def start(self, setpoints: dict | None = None) -> None:
        sp = setpoints or {}
        if sp.get("limite_forca"):
            self.limite_forca = float(sp["limite_forca"])
        if sp.get("velocidade"):
            self.velocidade = float(sp["velocidade"])
        if sp.get("deslocamento"):
            self.deslocamento_alvo = float(sp["deslocamento"])
        if sp.get("sentido") in ("cima", "baixo"):
            self.sentido = sp["sentido"]
        self._new_profile()
        # A ruptura não passa muito do limite de força programado.
        if self.limite_forca > 0:
            self.rupture_force = min(self.rupture_force, self.limite_forca * random.uniform(0.85, 1.0))
        self.running = True
        self.ruptura = False
        self.fim = False
        self.t0 = time.time()

    def stop(self) -> None:
        self.running = False
        self.residual_disp = self._last_disp

    def zero_displacement(self) -> None:
        self.residual_disp = 0.0
        self._last_disp = 0.0

    def zero_cell(self) -> None:
        # Zerar a célula de carga também encerra o ensaio em curso.
        self.running = False
        self.ruptura = False
        self.fim = False
        self._last_forca = 0.0

    # -- física ----------------------------------------------------------
    def _force_for_disp(self, disp: float) -> float:
        fy = self.yield_frac * self.rupture_force
        dy = fy / self.stiffness if self.stiffness > 0 else 0.0
        if disp <= dy:
            return self.stiffness * disp                      # elástico
        if disp < self.rupture_disp:
            frac = (disp - dy) / max(1e-6, self.rupture_disp - dy)
            return fy + (self.rupture_force - fy) * frac       # encruamento
        return self.rupture_force

    def _advance(self) -> tuple[float, float]:
        """Atualiza e devolve (força, deslocamento) correntes."""
        if not self.running or self.t0 is None:
            forca = max(0.0, random.gauss(0.0, self.noise * 0.4))
            return round(forca, 2), round(self.residual_disp, 3)

        t = time.time() - self.t0
        rate = max(self.velocidade / 60.0, 0.5)  # mm/s (piso para o ensaio não demorar)
        disp = self.residual_disp + rate * t
        alvo = self.deslocamento_alvo if self.deslocamento_alvo and self.deslocamento_alvo > 0 else float("inf")
        end_disp = min(self.rupture_disp, alvo)

        if disp >= end_disp:
            # Fim do ensaio: ruptura (e fim de ensaio para a flexão).
            self.running = False
            self.ruptura = True
            self.fim = True
            self._last_disp = end_disp
            self.residual_disp = end_disp
            self._last_forca = 0.0
            return 0.0, round(end_disp, 3)

        forca = self._force_for_disp(disp) + random.gauss(0.0, self.noise)
        forca = max(0.0, forca)
        self._last_disp = disp
        self._last_forca = forca
        return round(forca, 2), round(disp, 3)

    # -- leitura por registrador ----------------------------------------
    def value_for_register(self, reg: dict) -> Any:
        forca, disp = self._advance()
        role = reg.get("role") or reg.get("name") or ""
        if role == "forca_atual":
            return forca
        if role == "deslocamento_atual":
            return disp
        if role == "material_integro_bit":
            return 0 if self.ruptura else 1
        if role == "ruptura_bit":
            return 1 if self.ruptura else 0
        if role == "fim_ensaio_bit":
            return 1 if self.fim else 0
        if role == "limite_forca":
            return round(self.limite_forca, 2)
        if role == "velocidade":
            return round(self.velocidade, 2)
        if role == "deslocamento_programado":
            return round(self.deslocamento_alvo, 2)
        if role in ("iniciar", "parar", "sentido_cima", "sentido_baixo",
                    "zerar_deslocamento", "zerar_celula"):
            return 1 if (role == "sentido_" + self.sentido and self.running) else 0
        # registrador desconhecido: valor plausível conforme o tipo
        dt = reg.get("data_type", "uint16")
        if dt == "coil":
            return 0
        if dt in ("float32",):
            return round(random.uniform(0.0, 10.0), 2)
        return int(random.uniform(0, 10))

    def read_registers(self, registers: list[dict]) -> dict[str, Any]:
        # Avança o tempo uma vez e usa o mesmo instante para todos os registradores.
        forca, disp = self._advance()
        out: dict[str, Any] = {}
        for reg in registers:
            role = reg.get("role") or reg.get("name") or ""
            if role == "forca_atual":
                out[reg["name"]] = forca
            elif role == "deslocamento_atual":
                out[reg["name"]] = disp
            else:
                out[reg["name"]] = self.value_for_register(reg)
        return out


# Instância única do processo.
SIM = _Sim()


class SimController:
    """Substitui ModbusController quando o simulador está ativo."""

    def __init__(self, registers: list[dict]) -> None:
        self.by_role = {r["role"]: r for r in registers if r.get("role")}
        self.by_name = {r["name"]: r for r in registers if r.get("name")}
        self._pending: dict = {}

    def connect(self) -> bool:
        return True

    def close(self) -> None:
        pass

    def resolve(self, role_or_name: str) -> dict | None:
        return self.by_role.get(role_or_name) or self.by_name.get(role_or_name)

    def _stash(self, role: str, value: float) -> None:
        if role == "limite_forca":
            self._pending["limite_forca"] = value
        elif role == "velocidade":
            self._pending["velocidade"] = value
        elif role == "deslocamento_programado":
            self._pending["deslocamento"] = value
        elif role == "sentido_cima" and value:
            self._pending["sentido"] = "cima"
        elif role == "sentido_baixo" and value:
            self._pending["sentido"] = "baixo"

    def write_register(self, reg: dict, value: float) -> bool:
        self._stash(reg.get("role") or reg.get("name") or "", value)
        return True

    def write_named(self, role_or_name: str, value: float) -> bool:
        self._stash(role_or_name, value)
        return True

    def pulse(self, role_or_name: str, ms: int = 300) -> bool:
        if role_or_name == "iniciar":
            SIM.start(self._pending)
        elif role_or_name == "parar":
            SIM.stop()
        elif role_or_name == "sentido_cima":
            self._pending["sentido"] = "cima"
        elif role_or_name == "sentido_baixo":
            self._pending["sentido"] = "baixo"
        elif role_or_name == "zerar_deslocamento":
            SIM.zero_displacement()
        elif role_or_name == "zerar_celula":
            SIM.zero_cell()
        return True


class SimReader:
    """Substitui RealtimeModbusReader quando o simulador está ativo."""

    def __init__(self, registers: list[dict]) -> None:
        self.registers = registers

    def connect(self) -> bool:
        return True

    def read(self) -> dict[str, Any]:
        return SIM.read_registers(self.registers)

    def close(self) -> None:
        pass


def sim_capture(registers: list[dict]) -> dict[str, Any]:
    """Equivalente simulado de capture_registers (status/leitura pontual)."""
    return SIM.read_registers(registers)
