"""
Teste isolado do registrador de bit (inicio do ensaio).

Modos de uso:
  python test_bit.py                          # monitora o bit configurado
  python test_bit.py --addr 4000 --type coil  # monitora endereco especifico
  python test_bit.py --scan                   # varre coils e holding registers e mostra o que muda
  python test_bit.py --scan --start 0 --end 50  # varre faixa personalizada

Ctrl+C para parar.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def load_config() -> dict:
    for candidate in [
        Path(__file__).parent / "backend" / "config.json",
        Path(__file__).parent / "config.json",
    ]:
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    return {}


def find_bit_register(cfg: dict, bit_name: str) -> dict | None:
    for r in cfg.get("ihm_registers", []):
        if r["name"] == bit_name:
            return r
    return None


def read_one(client, address: int, data_type: str):
    try:
        if data_type == "coil":
            resp = client.read_coils(address=address, count=1)
            return None if resp.isError() else int(resp.bits[0])
        else:
            resp = client.read_holding_registers(address=address, count=1)
            return None if resp.isError() else resp.registers[0]
    except Exception:
        return None


def connect(ip: str, port: int, timeout: int):
    from pymodbus.client import ModbusTcpClient
    client = ModbusTcpClient(ip, port=port, timeout=timeout)
    print(f"Conectando em {ip}:{port}...", end=" ", flush=True)
    if not client.connect():
        print("FALHOU\nVerifique IP e se a IHM esta na rede.")
        sys.exit(1)
    print("OK\n")
    return client


# ── modo scan ────────────────────────────────────────────────────────────────

def mode_scan(client, start: int, end: int):
    print(f"Varrendo coils {start}–{end} e holding registers {start}–{end}")
    print("Pressione o botão na IHM para ver quais endereços mudam.\n")
    print(f"{'Tipo':<10} {'Addr':>6}  {'Valor atual':>12}  {'Mudancas':>8}  {'Ultima mudanca'}")
    print("-" * 70)

    # Leitura inicial
    snapshot: dict[tuple[str, int], int | None] = {}
    changes:  dict[tuple[str, int], int]         = {}

    for dtype in ("coil", "holding"):
        for addr in range(start, end + 1):
            v = read_one(client, addr, dtype)
            snapshot[(dtype, addr)] = v
            changes[(dtype, addr)]  = 0

    print(f"Snapshot inicial capturado ({(end - start + 1) * 2} enderecos). Aguardando mudancas...\n")

    changed_ever: dict[tuple[str, int], tuple[int | None, int | None, int]] = {}  # key: (prev, curr, count)

    try:
        while True:
            time.sleep(0.1)
            for dtype in ("coil", "holding"):
                for addr in range(start, end + 1):
                    v = read_one(client, addr, dtype)
                    prev = snapshot[(dtype, addr)]
                    if v != prev and v is not None:
                        changes[(dtype, addr)] += 1
                        changed_ever[(dtype, addr)] = (prev, v, changes[(dtype, addr)])
                        snapshot[(dtype, addr)] = v

            # Redesenha apenas os que ja mudaram
            if changed_ever:
                # Clear e reimprime
                lines = []
                for (dtype, addr), (p, c, n) in sorted(changed_ever.items()):
                    cur = snapshot[(dtype, addr)]
                    ativo = cur is not None and cur > 0
                    estado = "\033[92mATIVO\033[0m  " if ativo else "\033[90mparado\033[0m"
                    lines.append(
                        f"  {dtype:<10} {addr:>6}  {estado}  raw={str(cur):<6}  "
                        f"{n:>4}x  {str(p)} -> {str(c)}"
                    )
                # Move cursor para cima e reimprime
                sys.stdout.write(f"\033[{len(lines)}A")
                for l in lines:
                    print(l + " " * 10)

    except KeyboardInterrupt:
        print("\n\nResultado final:")
        if not changed_ever:
            print("  Nenhum endereco mudou. Verifique se o botao esta na faixa varrida.")
        else:
            for (dtype, addr), (p, c, n) in sorted(changed_ever.items()):
                print(f"  {dtype:<10}  addr={addr}  mudou {n}x  ({p} -> {c})")
            print("\nUse o endereco e tipo indicados acima na configuracao do bit.")


# ── modo monitor ─────────────────────────────────────────────────────────────

def mode_monitor(client, address: int, data_type: str, bit_name: str, interval: float):
    print(f"Monitorando '{bit_name}' — endereco {address} ({data_type})")
    print("Pressione Ctrl+C para parar.\n")

    last_val = None
    try:
        while True:
            raw = read_one(client, address, data_type)
            ativo = raw is not None and raw > 0
            estado = "[ ATIVO  ]" if ativo else "[ parado ]"
            cor   = "\033[92m" if ativo else "\033[90m"
            reset = "\033[0m"

            if raw is None:
                linha = f"\r  {cor}ERRO de leitura{reset}                          "
            else:
                mudou = "  <<< MUDOU" if (last_val is not None and raw != last_val) else ""
                linha = f"\r  {cor}{estado}{reset}  raw={raw:<6}  tipo={data_type}{mudou}     "

            print(linha, end="", flush=True)
            last_val = raw
            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n\nParado.")


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Teste do bit de inicio do ensaio")
    parser.add_argument("--ip",       default=None)
    parser.add_argument("--port",     type=int,   default=None)
    parser.add_argument("--addr",     type=int,   default=None,  help="Endereco do registrador")
    parser.add_argument("--type",     default=None, choices=["coil", "uint16", "holding"])
    parser.add_argument("--name",     default=None, help="Nome do registrador no config")
    parser.add_argument("--interval", type=float, default=0.2)
    parser.add_argument("--scan",     action="store_true", help="Varre faixa de enderecos procurando mudancas")
    parser.add_argument("--start",    type=int,   default=0,     help="Inicio da faixa de scan (padrao 0)")
    parser.add_argument("--end",      type=int,   default=40,    help="Fim da faixa de scan (padrao 40)")
    args = parser.parse_args()

    try:
        from pymodbus.client import ModbusTcpClient  # noqa: F401
    except ImportError:
        print("ERRO: pymodbus nao instalado. Execute: pip install pymodbus")
        sys.exit(1)

    cfg     = load_config()
    ip      = args.ip   or cfg.get("ihm_ip", "")
    port    = args.port or int(cfg.get("ihm_port", 502))
    timeout = int(cfg.get("ihm_timeout", 3))

    if not ip:
        print("ERRO: IP nao encontrado. Passe --ip ou configure no sistema.")
        sys.exit(1)

    print("=" * 56)
    print("  TESTE DO BIT DE INICIO DO ENSAIO")
    print("=" * 56)
    print(f"  IP: {ip}:{port}")
    if args.scan:
        print(f"  Modo: SCAN  coils+holding  [{args.start}..{args.end}]")
    print("=" * 56 + "\n")

    client = connect(ip, port, timeout)

    if args.scan:
        mode_scan(client, args.start, args.end)
    else:
        bit_name     = args.name or cfg.get("realtime_bit_name", "teste_ativo_bit")
        reg_from_cfg = find_bit_register(cfg, bit_name)
        address      = args.addr if args.addr is not None else (reg_from_cfg["address"]   if reg_from_cfg else None)
        data_type    = args.type or (reg_from_cfg.get("data_type", "uint16") if reg_from_cfg else "uint16")

        if address is None:
            print(f"ERRO: Endereco nao encontrado para '{bit_name}'. Passe --addr.")
            sys.exit(1)

        mode_monitor(client, address, data_type, bit_name, args.interval)

    client.close()


if __name__ == "__main__":
    main()
