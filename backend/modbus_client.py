from __future__ import annotations

import logging
import struct
import time
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Codecs (big-endian, dois registradores HI+LO para tipos de 32 bits)
# ---------------------------------------------------------------------------

def _decode_float32(hi: int, lo: int) -> float:
    raw = struct.pack(">HH", hi, lo)
    return float(struct.unpack(">f", raw)[0])


def _decode_int32(hi: int, lo: int, signed: bool = True) -> int:
    raw = struct.pack(">HH", hi, lo)
    return int(struct.unpack(">i" if signed else ">I", raw)[0])


def encode_float32(value: float) -> tuple[int, int]:
    """IEEE 754 big-endian → (HI, LO) para write_registers."""
    raw = struct.pack(">f", float(value))
    hi, lo = struct.unpack(">HH", raw)
    return int(hi), int(lo)


def encode_int32(value: int, signed: bool = True) -> tuple[int, int]:
    """Inteiro de 32 bits big-endian → (HI, LO) para write_registers."""
    raw = struct.pack(">i" if signed else ">I", int(value))
    hi, lo = struct.unpack(">HH", raw)
    return int(hi), int(lo)


def _read_register(client: Any, reg: dict) -> Any:
    """Lê um registrador (qualquer data_type suportado) e retorna o valor decodificado.

    Suporta: coil, uint16, decimal (uint16×scale), int32/decimal32 (doubleword com
    sinal×scale) e float32 (IEEE 754). Retorna None em erro de leitura."""
    address   = reg["address"]
    data_type = reg.get("data_type", "uint16")
    scale     = float(reg.get("scale", 1.0))

    if data_type == "coil":
        resp = client.read_coils(address=address, count=1)
        return 0 if resp.isError() else (1 if resp.bits[0] else 0)

    if data_type == "float32":
        resp = client.read_holding_registers(address=address, count=2)
        if resp.isError():
            return None
        return round(_decode_float32(resp.registers[0], resp.registers[1]), 4)

    if data_type in ("int32", "decimal32"):
        resp = client.read_holding_registers(address=address, count=2)
        if resp.isError():
            return None
        raw = _decode_int32(resp.registers[0], resp.registers[1])
        return round(raw * scale, 6) if scale != 1.0 else raw

    # uint16 / decimal
    resp = client.read_holding_registers(address=address, count=1)
    if resp.isError():
        return None
    raw = resp.registers[0]
    return round(raw * scale, 6) if scale != 1.0 else raw


class RealtimeModbusReader:
    """Mantém uma conexão Modbus persistente para leituras em alta frequência."""

    def __init__(self, ip: str, port: int, timeout: int, registers: list[dict]) -> None:
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.registers = registers
        self._client: Any = None

    def connect(self) -> bool:
        try:
            from pymodbus.client import ModbusTcpClient
        except ImportError:
            logger.warning("[realtime] pymodbus não instalado.")
            return False
        try:
            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
            self._client = ModbusTcpClient(self.ip, port=self.port, timeout=self.timeout)
            ok = self._client.connect()
            if not ok:
                logger.warning(f"[realtime] Falha ao conectar em {self.ip}:{self.port}")
            return ok
        except Exception as e:
            logger.warning(f"[realtime] connect error: {e}")
            return False

    def read(self) -> dict[str, Any] | None:
        """Lê todos os registradores configurados. Retorna None se a conexão falhar."""
        if not self._client:
            return None
        result: dict[str, Any] = {}
        try:
            for reg in self.registers:
                result[reg["name"]] = _read_register(self._client, reg)
            return result
        except Exception as e:
            logger.warning(f"[realtime] read error: {e}")
            self._client = None
            return None

    def close(self) -> None:
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None


# ---------------------------------------------------------------------------
# Controlador Modbus — escrita de setpoints e comandos (iniciar/parar/sentido)
# ---------------------------------------------------------------------------

class ModbusController:
    """Conexão Modbus persistente para escrita de comandos e setpoints no CLP."""

    def __init__(self, ip: str, port: int, timeout: int, registers: list[dict]) -> None:
        self.ip = ip
        self.port = port
        self.timeout = timeout
        # Mapa por nome e por role para resolução de comandos
        self.by_name: dict[str, dict] = {r["name"]: r for r in registers if r.get("name")}
        self.by_role: dict[str, dict] = {r["role"]: r for r in registers if r.get("role")}
        self._client: Any = None

    def connect(self) -> bool:
        try:
            from pymodbus.client import ModbusTcpClient
        except ImportError:
            logger.warning("[control] pymodbus não instalado.")
            return False
        try:
            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
            self._client = ModbusTcpClient(self.ip, port=self.port, timeout=self.timeout)
            ok = self._client.connect()
            if not ok:
                logger.warning(f"[control] Falha ao conectar em {self.ip}:{self.port}")
            return ok
        except Exception as e:
            logger.warning(f"[control] connect error: {e}")
            return False

    def close(self) -> None:
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None

    # -- resolução ---------------------------------------------------------

    def resolve(self, role_or_name: str) -> dict | None:
        return self.by_role.get(role_or_name) or self.by_name.get(role_or_name)

    # -- escrita primitiva -------------------------------------------------

    def _write_coil(self, address: int, value: bool) -> bool:
        resp = self._client.write_coil(address=address, value=bool(value))
        return not resp.isError()

    def _write_words(self, address: int, words: list[int]) -> bool:
        resp = self._client.write_registers(address=address, values=words)
        return not resp.isError()

    def write_register(self, reg: dict, value: float) -> bool:
        """Escreve um valor respeitando o data_type do registrador."""
        if self._client is None:
            raise RuntimeError("Controlador Modbus não conectado")
        address   = reg["address"]
        data_type = reg.get("data_type", "uint16")
        scale     = float(reg.get("scale", 1.0))

        if data_type == "coil":
            return self._write_coil(address, bool(value))
        if data_type == "float32":
            hi, lo = encode_float32(float(value))
            return self._write_words(address, [hi, lo])
        if data_type in ("int32", "decimal32"):
            raw = int(round(float(value) / scale)) if scale != 1.0 else int(round(float(value)))
            hi, lo = encode_int32(raw)
            return self._write_words(address, [hi, lo])
        # uint16 / decimal
        raw = int(round(float(value) / scale)) if scale != 1.0 else int(round(float(value)))
        resp = self._client.write_register(address=address, value=raw & 0xFFFF)
        return not resp.isError()

    def write_named(self, role_or_name: str, value: float) -> bool:
        reg = self.resolve(role_or_name)
        if reg is None:
            raise KeyError(f"Registrador de controle '{role_or_name}' não configurado")
        return self.write_register(reg, value)

    def pulse(self, role_or_name: str, ms: int = 300) -> bool:
        """Pulso momentâneo num coil: escreve 1, aguarda ms, escreve 0."""
        reg = self.resolve(role_or_name)
        if reg is None:
            raise KeyError(f"Registrador de controle '{role_or_name}' não configurado")
        if self._client is None:
            raise RuntimeError("Controlador Modbus não conectado")
        address = reg["address"]
        ok = self._write_coil(address, True)
        time.sleep(max(0, ms) / 1000)
        ok = self._write_coil(address, False) and ok
        return ok


def capture_registers(
    ip: str,
    port: int,
    timeout: int,
    registers: list[dict],
) -> dict[str, Any] | None:
    """
    Conecta ao CLP/IHM, lê os registradores configurados e retorna {name: valor}.
    Suporta data_type "coil", "uint16"/"decimal" (1 registrador ×escala),
    "int32"/"decimal32" (doubleword com sinal ×escala) e "float32" (par hi+lo, big-endian).
    Retorna None se o dispositivo não estiver acessível ou não configurado.
    """
    if not ip or not registers:
        return None

    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        logger.warning("[modbus] pymodbus não instalado.")
        return None

    client = ModbusTcpClient(ip, port=port, timeout=timeout)
    try:
        if not client.connect():
            logger.warning(f"[modbus] Falha ao conectar em {ip}:{port}")
            return None

        result: dict[str, Any] = {}
        for reg in registers:
            name = reg["name"]
            try:
                result[name] = _read_register(client, reg)
            except Exception as e:
                logger.warning(f"[modbus] Erro no registrador {reg.get('address')} ({name}): {e}")
                result[name] = None

        logger.info(f"[modbus] Captura concluída: {result}")
        return result

    except Exception as e:
        logger.warning(f"[modbus] Erro de conexão: {e}")
        return None
    finally:
        client.close()
