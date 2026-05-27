"""
Teste interativo de registradores Modbus.

Uso:
  python modbus_test.py 5007                    # endereço único (16-bit)
  python modbus_test.py 5000 5099               # faixa (16-bit, só não-zeros)
  python modbus_test.py 5007 5015 5021 5027     # lista de endereços
  python modbus_test.py 5000 5099 --all         # faixa mostrando zeros também
  python modbus_test.py 5000 5099 --32          # lê pares como 32-bit (hi+lo e lo+hi)

Variáveis de ambiente opcionais:
  MODBUS_IP    (padrão: 192.168.8.10)
  MODBUS_PORT  (padrão: 502)
"""

import sys
import os

IP   = os.getenv("MODBUS_IP",   "192.168.8.10")
PORT = int(os.getenv("MODBUS_PORT", "502"))


def read_addrs(addrs: list[int], show_all: bool, mode32: bool) -> None:
    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        print("pymodbus não instalado. Execute: pip install pymodbus")
        sys.exit(1)

    client = ModbusTcpClient(IP, port=PORT, timeout=5)
    if not client.connect():
        print(f"Falha ao conectar em {IP}:{PORT}")
        sys.exit(1)

    print(f"Conectado em {IP}:{PORT}  ({len(addrs)} endereços)\n")

    if mode32:
        # Lê 2 registradores por endereço e mostra interpretações 32-bit
        print(f"  {'ADDR':>6}   {'HI (16bit)':>10}   {'LO (16bit)':>10}   {'HI<<16|LO (uint32)':>20}   {'LO<<16|HI (uint32)':>20}   {'int32 (hi|lo)':>14}")
        print("  " + "-" * 90)
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
            u32_hl = (hi << 16) | lo      # big-endian word order
            u32_lh = (lo << 16) | hi      # little-endian word order
            i32_hl = u32_hl if u32_hl < 2**31 else u32_hl - 2**32
            if (hi != 0 or lo != 0) or show_all:
                marker = "  <--" if (hi != 0 or lo != 0) else ""
                print(f"  {addr:>6}   {hi:>10}   {lo:>10}   {u32_hl:>20}   {u32_lh:>20}   {i32_hl:>14}{marker}")
                found += 1
        print()
        print(f"  {found} par(es) com valor != 0")
    else:
        # Lê 1 registrador (16-bit)
        print(f"  {'ADDR':>6}   {'uint16':>8}   {'int16':>8}   {'HEX':>6}")
        print("  " + "-" * 40)
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


def parse_args() -> tuple[list[int], bool, bool]:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

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
        return [nums[0]], show_all, mode32
    if len(nums) == 2 and nums[1] > nums[0] and (nums[1] - nums[0]) <= 2000:
        return list(range(nums[0], nums[1] + 1)), show_all, mode32
    return nums, show_all, mode32


if __name__ == "__main__":
    addrs, show_all, mode32 = parse_args()
    read_addrs(addrs, show_all, mode32)
