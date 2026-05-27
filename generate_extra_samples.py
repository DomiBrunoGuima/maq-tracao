"""Gera H0002.csv até H0005.csv com perfis de material distintos."""
from __future__ import annotations

import random
import string
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass


def _checksum(seed: int) -> str:
    random.seed(seed * 97 + 13)
    chars = string.ascii_letters + string.digits + "/+"
    return "".join(random.choices(chars, k=6))


@dataclass
class Perfil:
    nome: str
    equip_id: str
    n_amostras: int
    ruptura_i: int
    F_start: float
    F_max: float
    d_start: float
    d_max: float
    A: float          # área da seção mm²
    L0: float         # comprimento de referência mm
    ruido_F: float    # amplitude do ruído em N
    hora_inicio: str  # "HH:MM:SS"
    data: str         # "DD/MM/AAAA"
    curva: str        # "linear", "endurecimento", "fragil", "elastomero"


PERFIS = [
    Perfil(
        nome="H0002", equip_id="MAQ-TRACAO-001", n_amostras=55, ruptura_i=30,
        F_start=500.0, F_max=41200.0, d_start=0.5, d_max=22.5,
        A=350.0, L0=80.0, ruido_F=60.0,
        hora_inicio="09:15:00", data="03/03/2026",
        curva="endurecimento",
    ),
    Perfil(
        nome="H0003", equip_id="MAQ-TRACAO-001", n_amostras=28, ruptura_i=15,
        F_start=800.0, F_max=18500.0, d_start=1.0, d_max=9.8,
        A=600.0, L0=120.0, ruido_F=40.0,
        hora_inicio="14:02:30", data="03/03/2026",
        curva="fragil",
    ),
    Perfil(
        nome="H0004", equip_id="MAQ-TRACAO-002", n_amostras=70, ruptura_i=45,
        F_start=200.0, F_max=9800.0, d_start=8.0, d_max=38.0,
        A=200.0, L0=50.0, ruido_F=25.0,
        hora_inicio="16:45:10", data="04/03/2026",
        curva="elastomero",
    ),
    Perfil(
        nome="H0005", equip_id="MAQ-TRACAO-002", n_amostras=40, ruptura_i=22,
        F_start=1100.0, F_max=31000.0, d_start=2.0, d_max=14.5,
        A=450.0, L0=100.0, ruido_F=80.0,
        hora_inicio="08:30:00", data="05/03/2026",
        curva="linear",
    ),
]


def _forca_progress(progress: float, curva: str) -> float:
    """Converte progresso 0-1 em fração da força máxima segundo o perfil da curva."""
    if curva == "linear":
        return progress

    if curva == "endurecimento":
        # Elástico rápido, depois endurecimento strain-hardening
        if progress < 0.4:
            return progress * 0.45 / 0.4
        else:
            t = (progress - 0.4) / 0.6
            return 0.45 + 0.55 * (1 - (1 - t) ** 1.8)

    if curva == "fragil":
        # Sobe rápido e quebra abruptamente
        if progress < 0.7:
            return progress / 0.7 * 0.90
        else:
            return 0.90 + (progress - 0.7) / 0.3 * 0.10

    if curva == "elastomero":
        # Muito não-linear: mole no início, rigidifica no final
        return progress ** 0.5 * 0.6 + progress ** 2.5 * 0.4

    return progress


def gerar(p: Perfil, rng: random.Random) -> None:
    hora = datetime.strptime(f"{p.data} {p.hora_inicio}", "%d/%m/%Y %H:%M:%S")
    rows: list[dict] = []

    for i in range(p.n_amostras):
        t = hora + timedelta(seconds=i)

        if i <= p.ruptura_i:
            progress = i / p.ruptura_i if p.ruptura_i > 0 else 1.0
            fp = _forca_progress(progress, p.curva)

            forca = p.F_start + (p.F_max - p.F_start) * fp
            if i == p.ruptura_i:
                forca = p.F_max
            else:
                forca += rng.uniform(-p.ruido_F, p.ruido_F)

            deslocamento = p.d_start + (p.d_max - p.d_start) * progress
            if i < p.ruptura_i:
                deslocamento += rng.uniform(-0.05, 0.05)
            else:
                deslocamento = p.d_max

            deform = round(deslocamento / p.L0, 3)
            alonga = round(deform * 100, 2)
            tensao = forca / p.A
            tensao_max = tensao

            if i == 0:
                modulo = (tensao / deform) if deform > 0 else 50.0
                modulo = min(modulo, 600.0)
            else:
                prev = rows[-1]
                ds = tensao - prev["Tensao_Pa"]
                de = deform - prev["Deform_Along"]
                modulo = (ds / de) if abs(de) > 0.0005 else prev["Modulo_Elast"]
                modulo = max(5.0, min(800.0, modulo))

        else:
            prev = rows[-1]
            forca = prev["Forca_N"] - rng.uniform(20, 80)
            forca = max(p.F_max * 0.94, forca)
            deslocamento = p.d_max + rng.uniform(-0.02, 0.02)
            deform = round(p.d_max / p.L0, 3)
            tensao = forca / p.A
            tensao_max = round(p.F_max / p.A, 2)
            alonga = round(deform * 100, 2)

            ds = tensao - prev["Tensao_Pa"]
            de = deform - prev["Deform_Along"]
            if abs(de) > 0.0005:
                modulo = max(5.0, abs(ds / de))
            else:
                modulo = max(5.0, prev["Modulo_Elast"] * (1 - rng.uniform(0, 0.02)))

        rows.append({
            "TIME": t.strftime("%H:%M:%S"),
            "DATA": t.strftime("%d/%m/%Y"),
            "Tensao_Pa": round(float(tensao), 2),
            "Modulo_Elast": round(float(modulo), 2),
            "Tensao_Max": round(float(tensao_max), 2),
            "Deform_Along": deform,
            "Alonga_Ruptura": alonga,
            "Deslocamento": round(float(deslocamento), 2),
            "Forca_N": round(float(forca), 2),
            "Checksum": _checksum(i * 100 + hash(p.nome) % 1000),
        })

    out = Path("data") / f"{p.nome}.csv"
    with open(out, "w", encoding="utf-16", newline="") as f:
        f.write(f"HISTORY V1.0\t{p.equip_id}\t{p.nome}\n")
        f.write("\n")
        f.write(
            "TIME\tDATA\tTensao_Pa\tModulo_Elast\tTensao_Max\t"
            "Deform_Along\tAlonga_Ruptura\tDeslocamento\tForca_N\tChecksum\n"
        )
        f.write("TIME\tDATA\t1\t1\t1\t1\t1\t1\t1\tChecksum\n")
        for r in rows:
            f.write(
                "\t".join([
                    r["TIME"], r["DATA"],
                    str(r["Tensao_Pa"]), str(r["Modulo_Elast"]),
                    str(r["Tensao_Max"]), str(r["Deform_Along"]),
                    str(r["Alonga_Ruptura"]), str(r["Deslocamento"]),
                    str(r["Forca_N"]), r["Checksum"],
                ]) + "\n"
            )

    rup = rows[p.ruptura_i]
    print(
        f"[{p.nome}] {p.curva:12s} | {p.n_amostras} amostras | "
        f"Fmax={rup['Forca_N']:.0f} N  sigma_max={rup['Tensao_Pa']:.1f} MPa  "
        f"d_max={rup['Deslocamento']:.1f} mm"
    )


if __name__ == "__main__":
    Path("data").mkdir(exist_ok=True)
    rng = random.Random(2026)
    for perfil in PERFIS:
        gerar(perfil, rng)
    print("\nArquivos gerados em data/. Use 'Escanear' no software para carrega-los.")
