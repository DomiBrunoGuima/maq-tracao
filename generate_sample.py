"""Generates data/H0001.csv — a realistic traction test with 43 samples."""
from __future__ import annotations

import math
import os
import random
import string
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)


def _checksum(i: int) -> str:
    chars = string.ascii_letters + string.digits + "/+"
    random.seed(i * 31 + 7)
    return "".join(random.choices(chars, k=6))


def generate() -> None:
    start = datetime(2026, 2, 2, 18, 31, 47)
    n = 43
    rupture_i = 22

    # Anchor points matching the prompt example
    F_start, F_max = 1250.35, 23580.09
    d_start, d_max = 13.48, 19.41
    A = 500.0  # cross-section mm²
    L0 = 100.0  # gauge length mm

    rows: list[dict] = []
    rng = random.Random(0)

    for i in range(n):
        t = start + timedelta(seconds=i)

        if i <= rupture_i:
            progress = i / rupture_i
            # Slightly nonlinear loading (elastic then plastic region)
            if progress < 0.55:
                fp = progress / 0.55 * 0.50
            else:
                fp = 0.50 + (progress - 0.55) / 0.45 * 0.50
            forca = F_start + (F_max - F_start) * fp
            if i == rupture_i:
                forca = F_max
            else:
                forca += rng.uniform(-25, 25)

            deslocamento = d_start + (d_max - d_start) * progress
            if i < rupture_i:
                deslocamento += rng.uniform(-0.04, 0.04)
            else:
                deslocamento = d_max

            deform_along = round(deslocamento / L0, 3)
            alonga_ruptura = round(deform_along * 100, 2)
            tensao_pa = forca / A
            tensao_max = tensao_pa

            if i == 0:
                modulo = 18.55
            else:
                prev = rows[-1]
                ds = tensao_pa - prev["Tensao_Pa"]
                de = deform_along - prev["Deform_Along"]
                modulo = (ds / de) if abs(de) > 0.001 else prev["Modulo_Elast"]
                modulo = max(5.0, min(600.0, modulo))
        else:
            prev = rows[-1]
            forca = prev["Forca_N"] - rng.uniform(15, 50)
            forca = max(F_max * 0.96, forca)
            deslocamento = d_max + rng.uniform(-0.01, 0.01)
            deform_along = round(d_max / L0, 3)
            tensao_pa = forca / A
            tensao_max = 47.34          # frozen at peak
            alonga_ruptura = 19.42     # frozen at rupture

            ds = tensao_pa - prev["Tensao_Pa"]
            de = deform_along - prev["Deform_Along"]
            if abs(de) > 0.001:
                modulo = max(5.0, abs(ds / de))
            else:
                modulo = max(5.0, prev["Modulo_Elast"] * (1 - rng.uniform(0, 0.015)))

        rows.append({
            "TIME": t.strftime("%H:%M:%S"),
            "DATA": t.strftime("%d/%m/%Y"),
            "Tensao_Pa": round(tensao_pa, 2),
            "Modulo_Elast": round(modulo, 2),
            "Tensao_Max": round(tensao_max, 2),
            "Deform_Along": deform_along,
            "Alonga_Ruptura": alonga_ruptura,
            "Deslocamento": round(deslocamento, 2),
            "Forca_N": round(forca, 2),
            "Checksum": _checksum(i),
        })

    out = Path("data") / "H0001.csv"
    out.parent.mkdir(parents=True, exist_ok=True)

    with open(out, "w", encoding="utf-16", newline="") as f:
        f.write("HISTORY V1.0\tMAQ-TRACAO-001\tH0001\n")
        f.write("\n")
        f.write(
            "TIME\tDATA\tTensao_Pa\tModulo_Elast\tTensao_Max\t"
            "Deform_Along\tAlonga_Ruptura\tDeslocamento\tForca_N\tChecksum\n"
        )
        f.write("TIME\tDATA\t1\t1\t1\t1\t1\t1\t1\tChecksum\n")
        for r in rows:
            line = "\t".join(
                [
                    r["TIME"], r["DATA"],
                    str(r["Tensao_Pa"]), str(r["Modulo_Elast"]),
                    str(r["Tensao_Max"]), str(r["Deform_Along"]),
                    str(r["Alonga_Ruptura"]), str(r["Deslocamento"]),
                    str(r["Forca_N"]), r["Checksum"],
                ]
            )
            f.write(line + "\n")

    rup = rows[rupture_i]
    print(f"Generated {out}  ({n} samples)")
    print(f"  Rupture at t={rupture_i}s  F={rup['Forca_N']} N  sigma={rup['Tensao_Pa']} MPa")


if __name__ == "__main__":
    generate()
