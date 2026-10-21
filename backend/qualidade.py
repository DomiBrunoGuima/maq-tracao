"""Status de qualidade dos dados de um ensaio de tração.

Cada verificação devolve {chave, titulo, status, detalhe}, com status:
  "ok"    — tudo certo
  "aviso" — o resultado pode ser usado, mas merece atenção
  "erro"  — o resultado não é confiável
  "info"  — informativo (ex.: como o alongamento foi obtido)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

MIN_AMOSTRAS = 50
R2_MIN = 0.98


def _f(v: float, d: int = 2) -> str:
    """Número no formato brasileiro (vírgula decimal)."""
    return f"{v:.{d}f}".replace(".", ",")


def _item(chave: str, titulo: str, status: str, detalhe: str) -> dict:
    return {"chave": chave, "titulo": titulo, "status": status, "detalhe": detalhe}


def _lacunas_tempo(t: np.ndarray) -> int:
    """Quantos intervalos entre amostras são > 5× o intervalo típico (perda de leitura)."""
    if len(t) < 3:
        return 0
    dt = np.diff(t)
    dt = dt[np.isfinite(dt)]
    if dt.size == 0:
        return 0
    tipico = float(np.median(dt[dt > 0])) if np.any(dt > 0) else 0.0
    if tipico <= 0:
        return 0
    return int(np.sum(dt > 5 * tipico))


def avaliar_qualidade(df: pd.DataFrame, kpis: dict, ihm_params: dict | None = None) -> list[dict]:
    n = len(df)
    itens: list[dict] = []

    # ── Dados faltantes ──────────────────────────────────────────────────────
    cols = [c for c in ("Forca_N", "Deslocamento", "Tensao_Pa", "Deform_Along") if c in df.columns]
    faltando = {c: int(df[c].isna().sum()) for c in cols}
    total_falt = sum(faltando.values())
    t = df["elapsed_seconds"].to_numpy(dtype=float) if "elapsed_seconds" in df.columns else np.array([])
    lacunas = _lacunas_tempo(t)
    if total_falt == 0 and lacunas == 0:
        itens.append(_item("dados_faltantes", "Dados faltantes", "ok", "Nenhum valor vazio nem lacuna de leitura."))
    else:
        partes = [f"{v} em {k}" for k, v in faltando.items() if v]
        if lacunas:
            partes.append(f"{lacunas} lacuna(s) de tempo entre leituras")
        pct = total_falt / max(1, n * max(1, len(cols))) * 100
        status = "erro" if pct > 10 else "aviso"
        itens.append(_item("dados_faltantes", "Dados faltantes", status, "; ".join(partes) + "."))

    # ── Dados completos ──────────────────────────────────────────────────────
    tem_carga = "fase" in df.columns and df["fase"].isin(["elastico_linear", "encruamento"]).any()
    if n >= MIN_AMOSTRAS and tem_carga and total_falt == 0:
        itens.append(_item("dados_completos", "Dados completos", "ok",
                           f"{n} amostras cobrindo o carregamento."))
    elif n < MIN_AMOSTRAS:
        itens.append(_item("dados_completos", "Dados completos", "aviso",
                           f"Só {n} amostras (mínimo recomendado: {MIN_AMOSTRAS})."))
    else:
        itens.append(_item("dados_completos", "Dados completos", "aviso",
                           "Há amostras com valores vazios ou o carregamento não foi identificado."))

    # ── Curva válida ─────────────────────────────────────────────────────────
    problemas: list[str] = []
    fmax = kpis.get("forca_max_N") or 0
    if fmax <= 0:
        problemas.append("força máxima nula")
    r2 = kpis.get("r2_elastico")
    if r2 is None:
        problemas.append("trecho elástico não identificado")
    elif r2 < R2_MIN:
        problemas.append(f"trecho elástico pouco linear (R² = {_f(r2, 3)})")
    if "Deslocamento" in df.columns and n > 2:
        d = df["Deslocamento"].to_numpy(dtype=float)
        dd = np.diff(d[np.isfinite(d)])
        if dd.size and np.mean(dd < -1e-6) > 0.05:
            problemas.append("deslocamento retrocede em mais de 5% das leituras")
    if not problemas:
        itens.append(_item("curva_valida", "Curva válida", "ok",
                           f"Trecho elástico linear com R² = {_f(r2, 4)}."))
    else:
        status = "erro" if fmax <= 0 or r2 is None else "aviso"
        itens.append(_item("curva_valida", "Curva válida", status, _maiuscula("; ".join(problemas)) + "."))

    # ── Ruptura detectada ────────────────────────────────────────────────────
    if kpis.get("ruptura_detectada"):
        fr = kpis.get("forca_ruptura_N")
        dr = kpis.get("deslocamento_ruptura_mm")
        det = "Queda brusca de força identificada"
        if fr is not None and dr is not None:
            det += f" em {_f(fr, 1)} N e {_f(dr)} mm"
        itens.append(_item("ruptura_detectada", "Ruptura detectada", "ok", det + "."))
    else:
        itens.append(_item("ruptura_detectada", "Ruptura detectada", "aviso",
                           "Sem queda brusca de força: o ensaio parece ter sido interrompido antes de romper."))

    # ── Alongamento estimado ─────────────────────────────────────────────────
    l0 = kpis.get("comprimento_inicial_mm")
    l0_informado = bool(ihm_params and ihm_params.get("comprimento_inicial"))
    if l0 and l0_informado:
        itens.append(_item("alongamento_estimado", "Alongamento estimado", "info",
                           f"Calculado pelo deslocamento do travessão com L₀ = {_f(l0)} mm informado (sem extensômetro)."))
    elif l0:
        itens.append(_item("alongamento_estimado", "Alongamento estimado", "aviso",
                           f"L₀ não informado; estimado em {_f(l0)} mm a partir dos dados da IHM."))
    else:
        itens.append(_item("alongamento_estimado", "Alongamento estimado", "erro",
                           "Sem L₀: não é possível calcular o alongamento."))

    return itens


def _maiuscula(t: str) -> str:
    return t[:1].upper() + t[1:]


def resumo_status(itens: list[dict]) -> str:
    st = {i["status"] for i in itens}
    return "erro" if "erro" in st else "aviso" if "aviso" in st else "ok"


def avaliar_qualidade_flexao(df: pd.DataFrame, kpis: dict) -> list[dict]:
    """Mesmos itens da tração, adaptados à flexão: em vez do alongamento, confere
    se a geometria do corpo de prova (b, h, L) foi informada."""
    n = len(df)
    itens: list[dict] = []

    cols = [c for c in ("Forca_N", "Deslocamento", "Tensao_Flexao", "Deform_Flexao") if c in df.columns]
    faltando = {c: int(df[c].isna().sum()) for c in cols}
    total_falt = sum(faltando.values())
    t = df["elapsed_seconds"].to_numpy(dtype=float) if "elapsed_seconds" in df.columns else np.array([])
    lacunas = _lacunas_tempo(t)
    if total_falt == 0 and lacunas == 0:
        itens.append(_item("dados_faltantes", "Dados faltantes", "ok", "Nenhum valor vazio nem lacuna de leitura."))
    else:
        partes = [f"{v} em {k}" for k, v in faltando.items() if v]
        if lacunas:
            partes.append(f"{lacunas} lacuna(s) de tempo entre leituras")
        pct = total_falt / max(1, n * max(1, len(cols))) * 100
        itens.append(_item("dados_faltantes", "Dados faltantes", "erro" if pct > 10 else "aviso",
                           "; ".join(partes) + "."))

    tem_carga = "fase" in df.columns and df["fase"].isin(["elastico_linear"]).any()
    if n >= MIN_AMOSTRAS and tem_carga and total_falt == 0:
        itens.append(_item("dados_completos", "Dados completos", "ok", f"{n} amostras cobrindo o carregamento."))
    elif n < MIN_AMOSTRAS:
        itens.append(_item("dados_completos", "Dados completos", "aviso",
                           f"Só {n} amostras (mínimo recomendado: {MIN_AMOSTRAS})."))
    else:
        itens.append(_item("dados_completos", "Dados completos", "aviso",
                           "Há amostras com valores vazios ou o carregamento não foi identificado."))

    problemas: list[str] = []
    fmax = kpis.get("forca_max_N") or 0
    if fmax <= 0:
        problemas.append("força máxima nula")
    r2 = kpis.get("r2_elastico")
    if r2 is None:
        problemas.append("trecho elástico não identificado")
    elif r2 < R2_MIN:
        problemas.append(f"trecho elástico pouco linear (R² = {_f(r2, 3)})")
    if not problemas:
        itens.append(_item("curva_valida", "Curva válida", "ok", f"Trecho elástico linear com R² = {_f(r2, 4)}."))
    else:
        itens.append(_item("curva_valida", "Curva válida", "erro" if fmax <= 0 or r2 is None else "aviso",
                           _maiuscula("; ".join(problemas)) + "."))

    if kpis.get("ruptura_detectada"):
        itens.append(_item("ruptura_detectada", "Ruptura detectada", "ok", "Queda brusca de força após o pico."))
    else:
        itens.append(_item("ruptura_detectada", "Ruptura", "info",
                           "Sem quebra: o ensaio terminou na deflexão-alvo ou foi parado (normal na flexão)."))

    faltam = [nome for chave, nome in (("largura_mm", "largura b"), ("espessura_mm", "espessura h"),
                                       ("span_mm", "distância entre apoios L")) if not kpis.get(chave)]
    if faltam:
        itens.append(_item("geometria", "Geometria do corpo de prova", "erro",
                           f"Sem {', '.join(faltam)}: σf e Ef não podem ser calculados."))
    else:
        itens.append(_item("geometria", "Geometria do corpo de prova", "ok",
                           f"b = {_f(kpis['largura_mm'], 1)} mm · h = {_f(kpis['espessura_mm'], 1)} mm · "
                           f"L = {_f(kpis['span_mm'], 1)} mm."))
    return itens
