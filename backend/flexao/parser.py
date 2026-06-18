"""Detecção de fases do ensaio de flexão.

Mais simples que a tração: não há estricção nem alongamento de ruptura. O perfil
típico de flexão a 3 pontos é:

    acomodacao → elastico_linear → pos_escoamento → (ruptura | fim_ensaio)

Reaproveita ``_trim_precontact`` e ``_find_linear_region`` do parser de tração.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..parser import _find_linear_region, _trim_precontact  # noqa: F401  (reexport)

# Colunas que o pipeline de flexão espera no DataFrame.
COLUMN_NAMES = [
    "TIME", "DATA", "Tensao_Flexao", "Modulo_Flexao",
    "Deform_Flexao", "Deslocamento", "Forca_N",
]

FASES_FLEXAO = ["acomodacao", "elastico_linear", "pos_escoamento", "ruptura", "fim_ensaio"]


def detect_stages(df: pd.DataFrame) -> pd.Series:
    """Classifica cada ponto numa fase do ensaio de flexão.

    O ponto final recebe ``ruptura`` se houve queda abrupta de força após o pico
    (corpo de prova quebrou); caso contrário ``fim_ensaio`` (parou na deflexão-alvo).
    """
    n = len(df)
    stages = pd.Series("pos_escoamento", index=df.index)
    if n < 8:
        return stages

    forca = df["Forca_N"].values.astype(float)
    disp  = df["Deslocamento"].values.astype(float)

    peak_pos = int(np.argmax(forca))
    fmax = float(forca[peak_pos]) if n else 0.0

    # Houve quebra? Queda > 50% de Fmax num único passo depois do pico.
    rompeu = False
    if fmax > 0:
        for i in range(peak_pos + 1, n):
            if forca[i - 1] - forca[i] > fmax * 0.50:
                rompeu = True
                break

    n_load = peak_pos + 1
    if n_load >= 8:
        # Região elástica linear (mesmo detector da tração: estabilidade de rigidez).
        i_el_start, i_el_end = _find_linear_region(disp[:n_load], forca[:n_load])
        if i_el_start > 0:
            stages.iloc[:i_el_start] = "acomodacao"
        stages.iloc[i_el_start:i_el_end + 1] = "elastico_linear"
        # i_el_end+1 .. peak: pos_escoamento (default).
    else:
        i_el_start = i_el_end = 0

    # Label terminal por último, para sempre vencer sobre as fases anteriores.
    stages.iloc[-1] = "ruptura" if rompeu else "fim_ensaio"

    counts = {p: int((stages.values == p).sum()) for p in FASES_FLEXAO}
    print(
        f"[flexao.stages] n={n} pico={peak_pos} el=({i_el_start},{i_el_end}) "
        f"rompeu={rompeu} counts={counts}",
        flush=True,
    )
    return stages
