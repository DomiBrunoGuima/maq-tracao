"""
Teste interativo de registradores Modbus.

Uso:
  python modbus_test.py 5007                    # endereço único
  python modbus_test.py 5000 5099               # faixa
  python modbus_test.py 5007 5015 5021 5027     # lista de endereços
  python modbus_test.py 5000 5099 --all         # faixa mostrando zeros também

Variáveis de ambiente opcionais:
  MODBUS_IP    (padrão: 192.168.8.10)
  MODBUS_PORT  (padrão: 502)
"""

import sys
import os

IP   = os.getenv("MODBUS_IP",   "192.168.8.10")
PORT = int(os.getenv("MODBUS_PORT", "502"))

def read_addrs(addrs: list[int], show_all: bool) -> None:
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
    print(f"  {'ADDR':>6}   {'VALOR (uint)':>12}   {'VALOR (int16)':>13}   {'HEX':>6}")
    print("  " + "-" * 52)

    found = 0
    for addr in addrs:
        if not (0 <= addr <= 65535):
            print(f"  {addr:>6}   FORA DO RANGE (0-65535)")
            continue
        r = client.read_holding_registers(address=addr, count=1)
        if r.isError():
            if show_all:
                print(f"  {addr:>6}   {'ERRO':>12}")
            continue
        u = r.registers[0]
        i = u if u < 32768 else u - 65536
        if u != 0 or show_all:
            marker = "  <--" if u != 0 else ""
            print(f"  {addr:>6}   {u:>12}   {i:>13}   0x{u:04X}{marker}")
            found += 1

    client.close()
    print()
    if not show_all:
        print(f"  {found} endereço(s) com valor != 0  (use --all para ver todos)")
    print()


def parse_args() -> tuple[list[int], bool]:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    show_all = "--all" in args
    args = [a for a in args if a != "--all"]

    nums = []
    for a in args:
        try:
            nums.append(int(a))
        except ValueError:
            print(f"Argumento inválido: {a}")
            sys.exit(1)

    if len(nums) == 1:
        return [nums[0]], show_all
    if len(nums) == 2 and nums[1] > nums[0] and (nums[1] - nums[0]) <= 2000:
        return list(range(nums[0], nums[1] + 1)), show_all
    return nums, show_all


if __name__ == "__main__":
    addrs, show_all = parse_args()
    read_addrs(addrs, show_all)
