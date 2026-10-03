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


def _is_little_word_order(word_order: Any) -> bool:
    """True quando a palavra baixa vai primeiro (CDAB) — comum em CLPs
    Mitsubishi e registradores D (doubleword: D_n = palavra baixa, D_n+1 = alta)."""
    return str(word_order).lower() in ("little", "lo", "low", "swap", "cdab", "lh")


def _order_words(hi: int, lo: int, word_order: Any) -> list[int]:
    """Ordena (HI, LO) conforme a convenção do CLP, para write_registers.
    'big' (padrão, ABCD) = palavra alta primeiro; 'little' (CDAB) = baixa primeiro."""
    return [lo, hi] if _is_little_word_order(word_order) else [hi, lo]


def _words_to_hilo(r0: int, r1: int, word_order: Any) -> tuple[int, int]:
    """Inverso de :func:`_order_words`: dado o par lido do CLP, devolve (HI, LO)."""
    return (r1, r0) if _is_little_word_order(word_order) else (r0, r1)


# ---------------------------------------------------------------------------
# Dispositivos Delta (D/M/X/Y) → endereço Modbus
# ---------------------------------------------------------------------------

PLC_FAMILIES = ("dvp", "direto", "as")


def _dvp_address(kind: str, n: int, raw: str) -> int:
    """Mapa Modbus dos CLPs Delta DVP (ES2/EX2/SS2/SA2/SX2/SE...).
    X e Y são numerados em octal (X0..X7, X10..), como no ISPSoft/DOPSoft."""
    if kind in ("X", "Y"):
        if any(c in "89" for c in raw):
            raise ValueError(f"{kind}{raw}: X/Y do DVP são octais (sem 8 e 9)")
        return (0x0400 if kind == "X" else 0x0500) + int(raw, 8)
    if kind == "M":
        return 0x0800 + n if n < 1536 else 0xB000 + (n - 1536)
    if kind == "D":
        return 0x1000 + n if n < 4096 else 0x9000 + (n - 4096)
    raise ValueError(f"dispositivo {kind} não suportado no DVP")


def _as_address(kind: str, raw: str) -> int:
    """Mapa Modbus dos CLPs Delta AS (AS200/AS300). X/Y usam a forma palavra.bit (X0.3)."""
    if kind in ("X", "Y"):
        word, _, bit = raw.partition(".")
        base = 0x6000 if kind == "X" else 0xA000
        return base + int(word) * 16 + int(bit or 0)
    if kind in ("M", "D"):
        return int(raw)
    raise ValueError(f"dispositivo {kind} não suportado no AS")


def device_to_modbus(device: str, family: str = "dvp") -> tuple[int, str]:
    """Converte um dispositivo Delta (``D412``, ``M101``, ``X0``) no endereço Modbus
    (0-based) e no tipo de acesso: ``"coil"`` (M/Y), ``"input"`` (X) ou ``"holding"`` (D)."""
    dev = device.strip().upper()
    if len(dev) < 2 or dev[0] not in "DMXY":
        raise ValueError(f"dispositivo inválido: {device!r} (use D, M, X ou Y — ex.: D412, M5, X0)")
    kind, raw = dev[0], dev[1:]
    if not raw.replace(".", "", 1).isdigit() or ("." in raw and kind not in "XY"):
        raise ValueError(f"dispositivo inválido: {device!r} (número esperado após {kind})")
    fam = (family or "dvp").lower()
    if fam == "as":
        address = _as_address(kind, raw)
    elif fam == "direto":
        # Sem offset: o número do dispositivo é o endereço (D600 → 600, M5 → 5;
        # X/Y continuam octais). Útil quando a IHM republica os registradores.
        if "." in raw:
            raise ValueError(f"{device!r}: use X/Y sem ponto (ex.: X0, X10)")
        address = int(raw, 8) if kind in "XY" else int(raw)
    elif fam == "dvp":
        if "." in raw:
            raise ValueError(f"{device!r}: no DVP use X/Y sem ponto (ex.: X0, X10)")
        address = _dvp_address(kind, int(raw), raw)
    else:
        raise ValueError(f"família de CLP desconhecida: {family!r} (use 'dvp', 'direto' ou 'as')")
    access = {"D": "holding", "M": "coil", "Y": "coil", "X": "input"}[kind]
    return address, access


def resolve_register(reg: dict, family: str = "dvp") -> dict:
    """Devolve uma cópia do registrador com ``address`` calculado a partir de ``device``
    (quando preenchido). X vira ``data_type="input"`` (entrada digital, só leitura)."""
    device = str(reg.get("device") or "").strip()
    if not device:
        return reg
    address, access = device_to_modbus(device, family)
    out = {**reg, "address": address}
    if access == "input":
        out["data_type"] = "input"
        out["writable"] = False
    return out


def _read_register(client: Any, reg: dict) -> Any:
    """Lê um registrador (qualquer data_type suportado) e retorna o valor decodificado.

    Suporta: coil, input (entrada digital X), uint16, decimal (uint16×scale),
    int32/decimal32 (doubleword com sinal×scale) e float32 (IEEE 754 ×scale).
    Retorna None em erro de leitura."""
    address    = reg["address"]
    data_type  = reg.get("data_type", "uint16")
    scale      = float(reg.get("scale", 1.0))
    word_order = reg.get("word_order", "big")

    if data_type == "coil":
        resp = client.read_coils(address=address, count=1)
        return None if resp.isError() else (1 if resp.bits[0] else 0)

    if data_type == "input":
        resp = client.read_discrete_inputs(address=address, count=1)
        return None if resp.isError() else (1 if resp.bits[0] else 0)

    if data_type == "float32":
        resp = client.read_holding_registers(address=address, count=2)
        if resp.isError():
            return None
        hi, lo = _words_to_hilo(resp.registers[0], resp.registers[1], word_order)
        return round(_decode_float32(hi, lo) * scale, 4)

    if data_type in ("int32", "decimal32"):
        resp = client.read_holding_registers(address=address, count=2)
        if resp.isError():
            return None
        hi, lo = _words_to_hilo(resp.registers[0], resp.registers[1], word_order)
        raw = _decode_int32(hi, lo)
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
        """Escreve um valor respeitando o data_type e a ordem de palavra do registrador.

        Levanta RuntimeError se o CLP recusar a escrita (endereço/tipo inválido), em
        vez de falhar em silêncio — assim setpoints que não chegam à máquina aparecem
        como erro no endpoint, e não como sucesso fantasma."""
        if self._client is None:
            raise RuntimeError("Controlador Modbus não conectado")
        address    = reg["address"]
        data_type  = reg.get("data_type", "uint16")
        scale      = float(reg.get("scale", 1.0))
        word_order = reg.get("word_order", "big")

        sent: list[int]
        if data_type == "coil":
            sent = [1 if value else 0]
            ok = self._write_coil(address, bool(value))
        elif data_type == "input":
            raise RuntimeError(f"Entrada digital (input@{address}) é somente leitura")
        elif data_type == "float32":
            hi, lo = encode_float32(float(value) / scale)
            sent = _order_words(hi, lo, word_order)
            ok = self._write_words(address, sent)
        elif data_type in ("int32", "decimal32"):
            raw = int(round(float(value) / scale)) if scale != 1.0 else int(round(float(value)))
            hi, lo = encode_int32(raw)
            sent = _order_words(hi, lo, word_order)
            ok = self._write_words(address, sent)
        else:  # uint16 / decimal
            raw = int(round(float(value) / scale)) if scale != 1.0 else int(round(float(value)))
            sent = [raw & 0xFFFF]
            resp = self._client.write_register(address=address, value=raw & 0xFFFF)
            ok = not resp.isError()

        hexs = "[" + ", ".join(f"0x{w:04X}" for w in sent) + "]"
        print(f"[modbus-write] {data_type}@{address} wo={word_order} valor={value} "
              f"-> registers={sent} {hexs} ok={ok}", flush=True)

        if not ok:
            raise RuntimeError(
                f"CLP recusou a escrita em {data_type}@{address} (valor={value}). "
                "Verifique endereço, tipo e ordem de palavra do registrador em Controle (CLP)."
            )
        return True

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


def probe_register(
    ip: str,
    port: int,
    timeout: int,
    reg: dict,
    *,
    direction: str = "read",
    value: float | None = None,
) -> dict[str, Any]:
    """Testa UM registrador isoladamente e devolve o que foi/voltou no fio.

    direction="write" escreve ``value`` e relê para confirmar; direction="read"
    apenas lê. Para tipos de 32 bits, devolve a leitura interpretada como float E
    como int (sob a ordem de palavra escolhida), para você comparar com a IHM e
    descobrir tipo/ordem corretos. Não levanta exceção — devolve ``error``."""
    out: dict[str, Any] = {
        "ok": False,
        "direction": direction,
        "address": reg.get("address"),
        "name": reg.get("name", ""),
        "data_type": reg.get("data_type", "uint16"),
        "word_order": reg.get("word_order", "big"),
        "scale": float(reg.get("scale", 1.0)),
        "ip": ip, "port": port,
        "sent_words": None,
        "read_words": None,
        "decoded": None,
        "as_float": None,
        "as_int": None,
        "error": None,
    }
    address    = reg["address"]
    data_type  = out["data_type"]
    scale      = out["scale"]
    word_order = out["word_order"]

    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        out["error"] = "pymodbus não instalado"
        return out

    client = ModbusTcpClient(ip, port=port, timeout=timeout)
    try:
        if not client.connect():
            out["error"] = f"IHM/CLP inacessível em {ip}:{port}"
            return out

        # -- escrita (opcional) --------------------------------------------
        if direction == "write":
            if data_type == "input":
                out["error"] = "entrada digital (X) é somente leitura"
                return out
            if value is None:
                out["error"] = "valor obrigatório para escrita"
                return out
            if data_type == "coil":
                out["sent_words"] = [1 if value else 0]
                r = client.write_coil(address=address, value=bool(value))
            elif data_type == "float32":
                hi, lo = encode_float32(float(value) / scale)
                out["sent_words"] = _order_words(hi, lo, word_order)
                r = client.write_registers(address=address, values=out["sent_words"])
            elif data_type in ("int32", "decimal32"):
                raw = int(round(float(value) / scale)) if scale != 1.0 else int(round(float(value)))
                hi, lo = encode_int32(raw)
                out["sent_words"] = _order_words(hi, lo, word_order)
                r = client.write_registers(address=address, values=out["sent_words"])
            else:
                raw = int(round(float(value) / scale)) if scale != 1.0 else int(round(float(value)))
                out["sent_words"] = [raw & 0xFFFF]
                r = client.write_register(address=address, value=raw & 0xFFFF)
            if r.isError():
                out["error"] = f"escrita recusada pela IHM em {data_type}@{address}"
                print(f"[probe] WRITE FALHOU {data_type}@{address} valor={value} sent={out['sent_words']}", flush=True)
                return out

        # -- leitura (sempre, para confirmar) ------------------------------
        if data_type in ("coil", "input"):
            rr = (client.read_coils if data_type == "coil" else client.read_discrete_inputs)(address=address, count=1)
            if rr.isError():
                out["error"] = f"leitura recusada ({data_type}@{address})"
                return out
            out["read_words"] = [1 if rr.bits[0] else 0]
            out["decoded"] = out["read_words"][0]
        elif data_type in ("float32", "int32", "decimal32"):
            rr = client.read_holding_registers(address=address, count=2)
            if rr.isError():
                out["error"] = f"leitura recusada (holding@{address}, count=2)"
                return out
            w0, w1 = rr.registers[0], rr.registers[1]
            out["read_words"] = [w0, w1]
            hi, lo = _words_to_hilo(w0, w1, word_order)
            out["as_float"] = round(_decode_float32(hi, lo), 6)
            int_raw = _decode_int32(hi, lo)
            out["as_int"] = int_raw
            if data_type == "float32":
                out["decoded"] = round(out["as_float"] * scale, 6) if scale != 1.0 else out["as_float"]
            else:
                out["decoded"] = round(int_raw * scale, 6) if scale != 1.0 else int_raw
        else:
            rr = client.read_holding_registers(address=address, count=1)
            if rr.isError():
                out["error"] = f"leitura recusada (holding@{address})"
                return out
            raw = rr.registers[0]
            out["read_words"] = [raw]
            out["decoded"] = round(raw * scale, 6) if scale != 1.0 else raw

        out["ok"] = True
        print(f"[probe] {direction} {data_type}@{address} wo={word_order} "
              f"sent={out['sent_words']} read={out['read_words']} decoded={out['decoded']} "
              f"as_float={out['as_float']} as_int={out['as_int']}", flush=True)
        return out

    except Exception as e:
        out["error"] = str(e)
        print(f"[probe] ERRO {data_type}@{address}: {e}", flush=True)
        return out
    finally:
        client.close()
