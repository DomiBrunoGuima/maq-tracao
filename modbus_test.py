"""
Teste interativo de registradores Modbus.

Uso:
  python modbus_test.py 5007                    # endereço único (16-bit)
  python modbus_test.py 5000 5099               # faixa (só não-zeros)
  python modbus_test.py 5007 5015 5021 5027     # lista de endereços
  python modbus_test.py 5000 5099 --all         # faixa mostrando zeros também
  python modbus_test.py 5000 5099 --32          # pares como uint32 (hi+lo e lo+hi)
  python modbus_test.py --float                 # decodifica pares configurados como IEEE 754

Variáveis de ambiente opcionais:
  MODBUS_IP    (padrão: 192.168.8.10)
  MODBUS_PORT  (padrão: 502)
"""

import sys
import os
import struct

IP   = os.getenv("MODBUS_IP",   "192.168.8.10")
PORT = int(os.getenv("MODBUS_PORT", "502"))

# Pares (hi_addr, lo_addr) a decodificar como float IEEE 754
FLOAT_PAIRS: list[tuple[int, int]] = [
    (40002, 40003),
    (40004, 40005),
    (40008, 40009),
    (40015, 40016),
]


def _decode_float(hi: int, lo: int) -> float:
    """Combina dois registradores 16-bit em float IEEE 754 big-endian."""
    try:
        from pymodbus.payload import BinaryPayloadDecoder
        from pymodbus.constants import Endian
        dec = BinaryPayloadDecoder.fromRegisters(
            [hi, lo], byteorder=Endian.BIG, wordorder=Endian.BIG
        )
        return dec.decode_32bit_float()
    except Exception:
        # fallback via struct se o decoder falhar
        raw = struct.pack(">HH", hi, lo)
        return struct.unpack(">f", raw)[0]


def _connect():
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        print("pymodbus não instalado. Execute: pip install pymodbus")
        sys.exit(1)
    client = ModbusTcpClient(IP, port=PORT, timeout=5)
    if not client.connect():
        print(f"Falha ao conectar em {IP}:{PORT}")
        sys.exit(1)
    print(f"Conectado em {IP}:{PORT}\n")
    return client


def read_floats(pairs: list[tuple[int, int]]) -> None:
    """Lê pares de registradores e decodifica como float IEEE 754."""
    client = _connect()

    hdr = f"  {'ADDR':>6}   {'RAW_HIGH':>8}   {'RAW_LOW':>8}   {'HEX_PAIR':>12}   {'FLOAT':>12}"
    print(hdr)
    print("  " + "-" * (len(hdr) - 2))

    for hi_addr, lo_addr in pairs:
        if not (0 <= hi_addr <= 65534 and 0 <= lo_addr <= 65535):
            print(f"  {hi_addr:>6}   FORA DO RANGE")
            continue

        r = client.read_holding_registers(address=hi_addr, count=2)
        if r.isError():
            print(f"  {hi_addr:>6}   ERRO ao ler {hi_addr}-{lo_addr}")
            continue

        hi, lo = r.registers[0], r.registers[1]
        hex_pair = f"0x{hi:04X}{lo:04X}"
        f_val = _decode_float(hi, lo)
        print(f"  {hi_addr:>6}   0x{hi:04X}       0x{lo:04X}    {hex_pair}   {f_val:>12.4f}")

    print()
    client.close()


def read_addrs(addrs: list[int], show_all: bool, mode32: bool) -> None:
    client = _connect()

    if mode32:
        print(f"  {'ADDR':>6}   {'HI (u16)':>10}   {'LO (u16)':>10}   {'HI<<16|LO':>12}   {'LO<<16|HI':>12}   {'int32':>10}   {'float(hi,lo)':>14}")
        print("  " + "-" * 88)
        found = 0
        for addr in addrs:
            if not (0 <= addr <= 65534):
                print(f"  {addr:>6}   FORA DO RANGE")
                continue
            r = client.read_holding_registers(address=addr, count=2)
            if r.isError():
                if show_all:
                    print(f"  {addr:>6}   ERRO")
                continue
            hi, lo = r.registers[0], r.registers[1]
            u32_hl = (hi << 16) | lo
            u32_lh = (lo << 16) | hi
            i32    = u32_hl if u32_hl < 2**31 else u32_hl - 2**32
            f_val  = _decode_float(hi, lo)
            if (hi != 0 or lo != 0) or show_all:
                marker = "  <--" if (hi != 0 or lo != 0) else ""
                print(f"  {addr:>6}   {hi:>10}   {lo:>10}   {u32_hl:>12}   {u32_lh:>12}   {i32:>10}   {f_val:>14.4f}{marker}")
                found += 1
        print(f"\n  {found} par(es) com valor != 0")
    else:
        print(f"  {'ADDR':>6}   {'uint16':>8}   {'int16':>8}   {'HEX':>6}")
        print("  " + "-" * 38)
        found = 0
        for addr in addrs:
            if not (0 <= addr <= 65535):
                print(f"  {addr:>6}   FORA DO RANGE (0-65535)")
                continue
            r = client.read_holding_registers(address=addr, count=1)
            if r.isError():
                if show_all:
                    print(f"  {addr:>6}   {'ERRO':>8}")
                continue
            u = r.registers[0]
            i = u if u < 32768 else u - 65536
            if u != 0 or show_all:
                marker = "  <--" if u != 0 else ""
                print(f"  {addr:>6}   {u:>8}   {i:>8}   0x{u:04X}{marker}")
                found += 1
        print()
        if not show_all:
            print(f"  {found} endereço(s) com valor != 0  (use --all para ver todos)")

    print()
    client.close()


def parse_args():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    if "--float" in args:
        # Pares extras passados após --float: --float 40002 40003 40010 40011 ...
        extra = [a for a in args if a != "--float"]
        pairs = list(FLOAT_PAIRS)
        if extra:
            if len(extra) % 2 != 0:
                print("Para pares customizados passe endereços em duplas: --float 40002 40003 40010 40011")
                sys.exit(1)
            pairs = [(int(extra[i]), int(extra[i+1])) for i in range(0, len(extra), 2)]
        return "float", pairs

    show_all = "--all" in args
    mode32   = "--32"  in args
    args = [a for a in args if a not in ("--all", "--32")]

    nums = []
    for a in args:
        try:
            nums.append(int(a))
        except ValueError:
            print(f"Argumento inválido: {a}")
            sys.exit(1)

    if len(nums) == 1:
        addrs = [nums[0]]
    elif len(nums) == 2 and nums[1] > nums[0] and (nums[1] - nums[0]) <= 2000:
        addrs = list(range(nums[0], nums[1] + 1))
    else:
        addrs = nums

    return "scan", (addrs, show_all, mode32)


if __name__ == "__main__":
    result = parse_args()
    if result[0] == "float":
        read_floats(result[1])
    else:
        addrs, show_all, mode32 = result[1]
        read_addrs(addrs, show_all, mode32)
