"""
Teste isolado do registrador de bit (inicio do ensaio).

Uso:
  python test_bit.py                        # usa config.json do backend
  python test_bit.py --ip 192.168.8.10 --addr 100 --type coil
  python test_bit.py --ip 192.168.8.10 --addr 100 --type uint16

O script fica em loop lendo o registrador a cada 200 ms e mostra
o valor bruto + interpretacao booleana. Ctrl+C para parar.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def load_config() -> dict:
    cfg_path = Path(__file__).parent / "backend" / "config.json"
    if cfg_path.exists():
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    return {}


def find_bit_register(cfg: dict, bit_name: str) -> dict | None:
    for r in cfg.get("ihm_registers", []):
        if r["name"] == bit_name:
            return r
    return None


def read_bit(client, address: int, data_type: str) -> tuple[int | None, str]:
    """Retorna (valor_bruto, descricao_tipo)."""
    try:
        if data_type == "coil":
            resp = client.read_coils(address=address, count=1)
            if resp.isError():
                return None, "coil ERROR"
            return int(resp.bits[0]), "coil"
        else:
            resp = client.read_holding_registers(address=address, count=1)
            if resp.isError():
                return None, "holding ERROR"
            return resp.registers[0], "holding register"
    except Exception as e:
        return None, f"excecao: {e}"


def main():
    parser = argparse.ArgumentParser(description="Teste do bit de inicio do ensaio")
    parser.add_argument("--ip",    default=None, help="IP da IHM")
    parser.add_argument("--port",  type=int, default=None, help="Porta Modbus (padrao 502)")
    parser.add_argument("--addr",  type=int, default=None, help="Endereco do registrador")
    parser.add_argument("--type",  default=None, choices=["coil", "uint16"], help="Tipo do registrador")
    parser.add_argument("--name",  default=None, help="Nome do registrador (busca no config.json)")
    parser.add_argument("--interval", type=float, default=0.2, help="Intervalo de leitura em segundos (padrao 0.2)")
    args = parser.parse_args()

    cfg = load_config()

    # Resolve parametros: argumento > config.json
    ip      = args.ip   or cfg.get("ihm_ip", "")
    port    = args.port or int(cfg.get("ihm_port", 502))
    timeout = int(cfg.get("ihm_timeout", 3))

    bit_name    = args.name or cfg.get("realtime_bit_name", "teste_ativo_bit")
    reg_from_cfg = find_bit_register(cfg, bit_name)

    address   = args.addr if args.addr is not None else (reg_from_cfg["address"]   if reg_from_cfg else None)
    data_type = args.type or (reg_from_cfg.get("data_type", "uint16") if reg_from_cfg else "uint16")

    # Validacoes
    if not ip:
        print("ERRO: IP da IHM nao encontrado. Passe --ip ou configure no backend/config.json")
        sys.exit(1)
    if address is None:
        print(f"ERRO: Endereco nao encontrado para o registrador '{bit_name}'.")
        print("      Passe --addr ou cadastre o registrador no sistema.")
        sys.exit(1)

    print("=" * 56)
    print("  TESTE DO BIT DE INICIO DO ENSAIO")
    print("=" * 56)
    print(f"  IP      : {ip}:{port}")
    print(f"  Registro: '{bit_name}' — endereco {address} ({data_type})")
    print(f"  Intervalo: {args.interval * 1000:.0f} ms")
    print("=" * 56)
    print("Pressione Ctrl+C para parar.\n")

    try:
        from pymodbus.client import ModbusTcpClient
    except ImportError:
        print("ERRO: pymodbus nao instalado. Execute: pip install pymodbus")
        sys.exit(1)

    client = ModbusTcpClient(ip, port=port, timeout=timeout)

    print(f"Conectando em {ip}:{port}...", end=" ", flush=True)
    if not client.connect():
        print("FALHOU")
        print("Verifique o IP, porta e se a IHM esta acessivel na rede.")
        sys.exit(1)
    print("OK\n")

    last_val = None
    try:
        while True:
            raw, tipo = read_bit(client, address, data_type)

            ativo = raw is not None and raw > 0
            estado = "[ ATIVO  ]" if ativo else "[ parado ]"
            cor = "\033[92m" if ativo else "\033[90m"
            reset = "\033[0m"

            if raw is None:
                linha = f"\r  {cor}ERRO de leitura ({tipo}){reset}    "
            else:
                mudou = " <<< MUDOU" if (last_val is not None and raw != last_val) else ""
                linha = f"\r  {cor}{estado}{reset}  raw={raw:<6}  tipo={tipo}{mudou}     "

            print(linha, end="", flush=True)
            last_val = raw

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\nParado pelo usuario.")
    finally:
        client.close()


if __name__ == "__main__":
    main()
