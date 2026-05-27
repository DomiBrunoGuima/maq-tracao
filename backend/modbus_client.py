from __future__ import annotations

import logging
import struct
from typing import Any

logger = logging.getLogger(__name__)


def _decode_float32(hi: int, lo: int) -> float:
    raw = struct.pack(">HH", hi, lo)
    return float(struct.unpack(">f", raw)[0])


def capture_registers(
    ip: str,
    port: int,
    timeout: int,
    registers: list[dict],
) -> dict[str, Any] | None:
    """
    Conecta à IHM, lê os registradores configurados e retorna {name: valor}.
    Suporta data_type "uint16" (1 registrador) e "float32" (par hi+lo, big-endian).
    Retorna None se a IHM não estiver acessível ou não configurada.
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
            name      = reg["name"]
            address   = reg["address"]
            data_type = reg.get("data_type", "uint16")
            scale     = float(reg.get("scale", 1.0))
            try:
                if data_type == "float32":
                    resp = client.read_holding_registers(address=address, count=2)
                    if resp.isError():
                        result[name] = None
                    else:
                        hi, lo = resp.registers[0], resp.registers[1]
                        result[name] = round(_decode_float32(hi, lo), 4)
                else:  # uint16 ou decimal
                    resp = client.read_holding_registers(address=address, count=1)
                    if resp.isError():
                        result[name] = None
                    else:
                        raw = resp.registers[0]
                        result[name] = round(raw * scale, 6) if scale != 1.0 else raw
            except Exception as e:
                logger.warning(f"[modbus] Erro no registrador {address} ({name}): {e}")
                result[name] = None

        logger.info(f"[modbus] Captura concluída: {result}")
        return result

    except Exception as e:
        logger.warning(f"[modbus] Erro de conexão: {e}")
        return None
    finally:
        client.close()
