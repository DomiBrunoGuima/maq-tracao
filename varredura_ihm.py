"""Varredura (somente leitura) da memória Modbus da IHM.

Lê faixas de holding registers e coils e mostra o que tem valor, para comparar com
o que a tela da IHM está exibindo e descobrir em qual endereço está cada ponto.
Não escreve nada.

Uso (com o venv ativado, na pasta do projeto):
    python varredura_ihm.py                      # IP do config.json, faixas padrão
    python varredura_ihm.py --ip 192.168.11.10
    python varredura_ihm.py --hr 40000-40200 --coils 3900-4200
    python varredura_ihm.py --csv varredura.csv  # também salva em CSV

Dica: anote os valores da tela (ex.: deslocamento atual 12.34), rode a varredura,
mexa na máquina e rode de novo — o endereço cujo valor mudou junto é o certo.
"""
from __future__ import annotations

import argparse
import csv
import json
import struct
from pathlib import Path

from pymodbus.client import ModbusTcpClient

CONFIG = Path(__file__).resolve().parent / "backend" / "config.json"


def _faixa(txt: str) -> tuple[int, int]:
    a, _, b = txt.partition("-")
    return int(a), int(b or a)


def _ip_padrao() -> str:
    try:
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        return cfg.get("clp_ip") or cfg.get("ihm_ip") or ""
    except Exception:
        return ""


def _ler_blocos(fn, ini: int, fim: int, bloco: int):
    """Lê [ini, fim] em blocos; se um bloco for recusado, tenta endereço a endereço."""
    addr = ini
    while addr <= fim:
        n = min(bloco, fim - addr + 1)
        r = fn(address=addr, count=n)
        if not r.isError():
            vals = r.registers if hasattr(r, "registers") and r.registers else r.bits[:n]
            for i, v in enumerate(vals[:n]):
                yield addr + i, v
        else:
            for a in range(addr, addr + n):
                r1 = fn(address=a, count=1)
                if not r1.isError():
                    v = r1.registers[0] if getattr(r1, "registers", None) else r1.bits[0]
                    yield a, v
        addr += n


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ip", default=_ip_padrao())
    ap.add_argument("--port", type=int, default=502)
    ap.add_argument("--hr", default="40000-40200", help="faixa de holding registers (ex.: 40000-40200)")
    ap.add_argument("--coils", default="3900-4200", help="faixa de coils (ex.: 3900-4200)")
    ap.add_argument("--csv", help="salva o resultado neste arquivo CSV")
    ap.add_argument("--todos", action="store_true", help="mostra também os registradores zerados")
    args = ap.parse_args()

    if not args.ip:
        raise SystemExit("Informe o IP com --ip (ou preencha o IP no config.json).")

    cli = ModbusTcpClient(args.ip, port=args.port, timeout=3)
    if not cli.connect():
        raise SystemExit(f"Não conectou em {args.ip}:{args.port}")

    linhas: list[dict] = []
    try:
        h0, h1 = _faixa(args.hr)
        regs = dict(_ler_blocos(cli.read_holding_registers, h0, h1 + 1, 100))
        print(f"\n== Holding registers {h0}-{h1} em {args.ip} ==")
        print(f"{'end.':>7} {'word':>6} {'int16':>7}  {'float (este+próx., little)':>28}")
        for a in range(h0, h1 + 1):
            if a not in regs:
                continue
            w = regs[a]
            nxt = regs.get(a + 1)
            f = struct.unpack("<f", struct.pack("<HH", w, nxt))[0] if nxt is not None else None
            if not args.todos and w == 0 and (nxt in (0, None)):
                continue
            i16 = w - 0x10000 if w >= 0x8000 else w
            fs = f"{f:.4f}" if f is not None and abs(f) < 1e7 and (abs(f) > 1e-6 or f == 0) else "-"
            print(f"{a:>7} {w:>6} {i16:>7}  {fs:>28}")
            linhas.append({"tipo": "holding", "endereco": a, "word": w, "int16": i16, "float_little": fs})

        c0, c1 = _faixa(args.coils)
        bits = dict(_ler_blocos(cli.read_coils, c0, c1, 200))
        ligados = [a for a in range(c0, c1 + 1) if bits.get(a)]
        print(f"\n== Coils {c0}-{c1}: {len(bits)} lidos, ligados agora: {ligados or 'nenhum'}")
        for a in range(c0, c1 + 1):
            if a in bits and (args.todos or bits[a]):
                linhas.append({"tipo": "coil", "endereco": a, "word": int(bool(bits[a])), "int16": "", "float_little": ""})
    finally:
        cli.close()

    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=["tipo", "endereco", "word", "int16", "float_little"])
            w.writeheader()
            w.writerows(linhas)
        print(f"\nSalvo em {args.csv}")


if __name__ == "__main__":
    main()
