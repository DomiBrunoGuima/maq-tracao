from __future__ import annotations

import base64
import io
from datetime import datetime
from types import SimpleNamespace

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import pandas as pd

from .calculator import calculate_kpis


# ──────────────────────────────────────────────
# Chart generation
# ──────────────────────────────────────────────

# Colunas e rótulos dos gráficos por tipo de ensaio (deformação adimensional, tensão em MPa)
_EIXOS = {
    "tracao": {"x": "Deform_Along", "y": "Tensao_Pa", "x_label": "Deformação (%)",
               "y_label": "Tensão (MPa)", "d_label": "Deslocamento (mm)"},
    "flexao": {"x": "Deform_Flexao", "y": "Tensao_Flexao", "x_label": "Deformação de flexão εf (%)",
               "y_label": "Tensão de flexão σf (MPa)", "d_label": "Deflexão (mm)"},
}


def _eixos_a_partir_de_zero(ax) -> None:
    """Começa os eixos em 0 só quando os dados são positivos. Na flexão a travessa
    desce e a deflexão (e a força) podem vir negativas: cortar em 0 deixava o
    gráfico em branco."""
    xs, ys = [], []
    for line in ax.get_lines():
        xs.extend(v for v in line.get_xdata() if v == v)
        ys.extend(v for v in line.get_ydata() if v == v)
    if xs and min(xs) >= 0:
        ax.set_xlim(left=0)
    if ys and min(ys) >= 0:
        ax.set_ylim(bottom=0)


def _chart_stress_strain_b64(df: pd.DataFrame, modo: str = "tracao") -> str:
    try:
        eixos = _EIXOS[modo]
        fig, ax = plt.subplots(figsize=(8, 4.8))

        x = df[eixos["x"]].values * 100   # dimensionless → %
        y = df[eixos["y"]].values         # já em MPa

        ax.plot(x, y, color="#1e3a5f", linewidth=1.8, label="Tensão")

        fmax_pos = int(df["Forca_N"].fillna(float("-inf")).values.argmax())
        ax.scatter([x[fmax_pos]], [y[fmax_pos]], color="#c0392b", s=60, zorder=5,
                   label=f"Força máxima  {y[fmax_pos]:.1f} MPa / {x[fmax_pos]:.2f}%")

        ax.set_xlabel(eixos["x_label"], fontsize=10)
        ax.set_ylabel(eixos["y_label"], fontsize=10)
        _eixos_a_partir_de_zero(ax)
        ax.grid(True, alpha=0.25, linestyle="--", color="gray")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(fontsize=9)
        plt.tight_layout(pad=0.5)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        data = base64.b64encode(buf.read()).decode("utf-8")
        print(f"[report] stress_strain chart gerado: {len(data)} chars", flush=True)
        return data
    except Exception as exc:
        print(f"[report] _chart_stress_strain_b64 falhou: {exc}", flush=True)
        return ""


def _chart_comparison_ss_b64(series: list[tuple[str, pd.DataFrame]], modo: str = "tracao") -> str:
    """Gráfico σ×ε com múltiplas curvas sobrepostas."""
    try:
        eixos = _EIXOS[modo]
        palette = ["#1e3a5f", "#c0392b", "#27ae60", "#8e44ad", "#e67e22", "#2980b9"]
        fig, ax = plt.subplots(figsize=(8, 4.8))
        for idx, (label, df) in enumerate(series):
            color = palette[idx % len(palette)]
            x = df[eixos["x"]].values * 100
            y = df[eixos["y"]].values
            ax.plot(x, y, color=color, linewidth=1.8, label=label)
            fmax_pos = int(df["Forca_N"].fillna(float("-inf")).values.argmax())
            ax.scatter([x[fmax_pos]], [y[fmax_pos]], color=color, s=50, zorder=5)
        ax.set_xlabel(eixos["x_label"], fontsize=10)
        ax.set_ylabel(eixos["y_label"], fontsize=10)
        _eixos_a_partir_de_zero(ax)
        ax.grid(True, alpha=0.25, linestyle="--", color="gray")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(fontsize=8, loc="best")
        plt.tight_layout(pad=0.5)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")
    except Exception as exc:
        print(f"[report] _chart_comparison_ss_b64 falhou: {exc}", flush=True)
        return ""


def _chart_comparison_fd_b64(series: list[tuple[str, pd.DataFrame]], modo: str = "tracao") -> str:
    """Gráfico F×d com múltiplas curvas sobrepostas."""
    try:
        palette = ["#2e6da4", "#c0392b", "#27ae60", "#8e44ad", "#e67e22", "#1e3a5f"]
        fig, ax = plt.subplots(figsize=(8, 4))
        for idx, (label, df) in enumerate(series):
            color = palette[idx % len(palette)]
            ax.plot(df["Deslocamento"].values, df["Forca_N"].values,
                    color=color, linewidth=1.6, label=label)
        ax.set_xlabel(_EIXOS[modo]["d_label"], fontsize=10)
        ax.set_ylabel("Força (N)", fontsize=10)
        _eixos_a_partir_de_zero(ax)
        ax.grid(True, alpha=0.25, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.legend(fontsize=8, loc="best")
        plt.tight_layout(pad=0.5)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")
    except Exception as exc:
        print(f"[report] _chart_comparison_fd_b64 falhou: {exc}", flush=True)
        return ""


def _chart_force_displacement_b64(df: pd.DataFrame, modo: str = "tracao") -> str:
    try:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(df["Deslocamento"].values, df["Forca_N"].values,
                color="#2e6da4", linewidth=1.6)
        ax.set_xlabel(_EIXOS[modo]["d_label"], fontsize=10)
        ax.set_ylabel("Força (N)", fontsize=10)
        _eixos_a_partir_de_zero(ax)
        ax.grid(True, alpha=0.25, linestyle="--")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        plt.tight_layout(pad=0.5)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")
    except Exception as exc:
        print(f"[report] _chart_force_displacement_b64 falhou: {exc}", flush=True)
        return ""


# ──────────────────────────────────────────────
# HTML helpers
# ──────────────────────────────────────────────

def _esc(v) -> str:
    return (str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def _src(url: str) -> str:
    """Escapa uma data URL/URL para uso dentro de src="..."."""
    return str(url or "").replace('"', "%22").replace("<", "%3C").replace(">", "%3E")


def _num(v, fmt: str = ".2f") -> str:
    """Formata número; None/NaN/inf viram '—' em vez de quebrar o relatório."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if f != f or f in (float("inf"), float("-inf")):
        return "—"
    return format(f, fmt)


_MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
          "agosto", "setembro", "outubro", "novembro", "dezembro"]


def _data_extenso(d: datetime) -> str:
    return f"{d.day:02d} de {_MESES[d.month - 1]} de {d.year}"


def _td(label: str, value: str, label_width: str = "38%") -> str:
    return (
        f'<tr>'
        f'<td style="font-weight:bold;width:{label_width};background:#f0f0f0;'
        f'border:1px solid #bbb;padding:5px 9px">{_esc(label)}</td>'
        f'<td style="border:1px solid #bbb;padding:5px 9px">{_esc(value)}</td>'
        f'</tr>'
    )


def _td2(label1: str, val1: str, label2: str, val2: str) -> str:
    return (
        f'<tr>'
        f'<td style="font-weight:bold;width:22%;background:#f0f0f0;border:1px solid #bbb;padding:5px 9px">{_esc(label1)}</td>'
        f'<td style="width:28%;border:1px solid #bbb;padding:5px 9px">{_esc(val1)}</td>'
        f'<td style="font-weight:bold;width:22%;background:#f0f0f0;border:1px solid #bbb;padding:5px 9px">{_esc(label2)}</td>'
        f'<td style="width:28%;border:1px solid #bbb;padding:5px 9px">{_esc(val2)}</td>'
        f'</tr>'
    )


def _section_header(num: int, title: str) -> str:
    return (
        f'<h2 style="font-size:10.5pt;font-weight:bold;margin:28px 0 12px;'
        f'text-transform:uppercase;letter-spacing:0.6px;color:#1e3a5f;'
        f'background:#f4f6f9;border-left:4px solid #1e3a5f;'
        f'padding:8px 12px">'
        f'{num}&nbsp;&nbsp;{_esc(title)}</h2>'
    )


def _figure(img_src: str, caption: str) -> str:
    return (
        f'<div style="text-align:center;margin:14px 0 20px">'
        f'<img src="{_src(img_src)}" alt="{_esc(caption)}" '
        f'style="max-width:75%;border:1px solid #ddd;padding:2px"/>'
        f'<p style="font-style:italic;font-size:9pt;margin-top:6px">{_esc(caption)}</p>'
        f'</div>'
    )


_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Arial, sans-serif; font-size: 10.5pt; color: #1a1a1a;
       line-height: 1.6; background: #edf0f4; }
.page { max-width: 1040px; margin: 28px auto; padding: 52px 72px 72px;
        background: #fff; box-shadow: 0 2px 16px rgba(0,0,0,0.10); border-radius: 2px; }
table { border-collapse: collapse; }
p { margin: 6px 0; }
@media print {
  body { background: #fff; }
  .page { max-width: 21cm; margin: 0; padding: 1.5cm 2cm;
          box-shadow: none; border-radius: 0; }
  .page-break { page-break-before: always; }
}
"""


def _linhas_resultado_tracao(kpis: dict, tensao_max, alongamento, area, l0) -> list[tuple[str, str, str]]:
    rows = []
    if area:
        rows.append(("Área da Seção Transversal (A)", _num(area, ".4f"), "mm²"))
    if l0:
        rows.append(("Comprimento Inicial (L₀)", _num(l0, ".2f"), "mm"))
    rows += [
        ("Módulo de Elasticidade (E)", _num(kpis.get("modulo_elasticidade_GPa"), ".3f"), "GPa"),
        ("Módulo de Elasticidade (E)", _num(kpis.get("modulo_elasticidade_MPa"), ".1f"), "MPa"),
    ]
    if kpis.get("tensao_escoamento_MPa") is not None:
        rows.append(("Tensão de Escoamento (est.)", _num(kpis["tensao_escoamento_MPa"]), "MPa"))
    rows += [
        ("Tensão Máxima (σmax = Fmax/A)" if kpis.get("tensao_max_calc_MPa") is not None else "Tensão Máxima (σmax)",
         _num(tensao_max), "MPa"),
        ("Força Máxima (Fmax)", _num(kpis.get("forca_max_N"), ".1f"), "N"),
        ("Força Máxima (Fmax)", _num(kpis.get("forca_max_kN"), ".4f"), "kN"),
        ("Alongamento na Força Máxima (d/L₀×100)", _num(alongamento), "%"),
    ]
    if kpis.get("alonga_fmax_menos_l0_pct") is not None:
        rows.append(("Alongamento na Força Máxima ((d−L₀)/L₀×100)", _num(kpis["alonga_fmax_menos_l0_pct"]), "%"))
    rows.append(("Alongamento Final (d/L₀×100)", _num(kpis.get("alonga_final_pct")), "%"))
    if kpis.get("alonga_final_menos_l0_pct") is not None:
        rows.append(("Alongamento Final ((d−L₀)/L₀×100)", _num(kpis["alonga_final_menos_l0_pct"]), "%"))
    rows += [
        ("Deslocamento Final", _num(kpis.get("deslocamento_final_mm")), "mm"),
        ("Deslocamento Máximo", _num(kpis.get("deslocamento_max_mm")), "mm"),
        ("Tempo até a Força Máxima", _num(kpis.get("tempo_ruptura_s"), ".1f"), "s"),
        ("Rigidez (k)", _num(kpis.get("rigidez_N_mm")), "N/mm"),
        ("Energia Absorvida até a Ruptura", _num(kpis.get("energia_J")), "J"),
        ("Taxa de Carregamento Média", _num(kpis.get("taxa_carregamento_N_s")), "N/s"),
    ]
    return rows


def _linhas_resultado_flexao(kpis: dict) -> list[tuple[str, str, str]]:
    rows = []
    for chave, rotulo in (("largura_mm", "Largura do Corpo de Prova (b)"),
                          ("espessura_mm", "Espessura do Corpo de Prova (h)"),
                          ("span_mm", "Distância entre Apoios (L)")):
        if kpis.get(chave):
            rows.append((rotulo, _num(kpis[chave]), "mm"))
    rows += [
        ("Módulo de Flexão (Ef)", _num(kpis.get("modulo_flexao_GPa"), ".3f"), "GPa"),
        ("Módulo de Flexão (Ef)", _num(kpis.get("modulo_flexao_MPa"), ".1f"), "MPa"),
    ]
    if kpis.get("modulo_cordal_MPa") is not None:
        rows.append(("Módulo de Flexão Cordal", _num(kpis["modulo_cordal_MPa"], ".1f"), "MPa"))
    if kpis.get("r2_elastico") is not None:
        rows.append(("R² do Trecho Elástico", _num(kpis["r2_elastico"], ".4f"), "—"))
    rows += [
        ("Resistência à Flexão (σfM)", _num(kpis.get("tensao_flexao_max_MPa")), "MPa"),
        ("Força Máxima (Fmax)", _num(kpis.get("forca_max_N"), ".1f"), "N"),
        ("Força Máxima (Fmax)", _num(kpis.get("forca_max_kN"), ".4f"), "kN"),
        ("Deflexão na Força Máxima", _num(kpis.get("deflexao_pico_mm")), "mm"),
        ("Deflexão Máxima", _num(kpis.get("deflexao_max_mm")), "mm"),
        ("Deformação de Flexão Máxima (εf)", _num(kpis.get("deform_flexao_max_pct")), "%"),
        ("Tempo até a Força Máxima", _num(kpis.get("tempo_pico_s"), ".1f"), "s"),
        ("Tempo de Ensaio", _num(kpis.get("tempo_ensaio_s"), ".1f"), "s"),
        ("Rigidez (k)", _num(kpis.get("rigidez_N_mm")), "N/mm"),
        ("Energia Absorvida", _num(kpis.get("energia_J")), "J"),
        ("Taxa de Carregamento Média", _num(kpis.get("taxa_carregamento_N_s")), "N/s"),
        ("Ruptura", "detectada" if kpis.get("ruptura_detectada") else "não detectada", "—"),
    ]
    return rows


# ──────────────────────────────────────────────
# Modelo resumido (tração): relatório por teste ou por lote de CPs
# ──────────────────────────────────────────────

# Gráficos que o laboratório pode escolher. Deformação usa o comprimento inicial
# (L₀, base de medida); alongamento usa a distância entre garras. São curvas
# diferentes porque as duas distâncias são diferentes.
GRAFICOS_TRACAO = {
    "tensao_alongamento": ("Tensão × Alongamento", "Alongamento (%)", "Tensão (MPa)"),
    "tensao_deformacao": ("Tensão × Deformação", "Deformação (%)", "Tensão (MPa)"),
    "tensao_deslocamento": ("Tensão × Deslocamento", "Deslocamento (mm)", "Tensão (MPa)"),
    "forca_deslocamento": ("Força × Deslocamento", "Deslocamento (mm)", "Força (N)"),
}

_PALETA = ["#1e3a5f", "#c0392b", "#27ae60", "#8e44ad", "#e67e22", "#2980b9",
           "#7f8c8d", "#d35400", "#16a085", "#2c3e50"]

# Fora disso o valor quase sempre é área digitada errada (ex.: "1.127" em vez de 1127 mm²)
_AREA_MIN_MM2 = 5.0
_TENSAO_MAX_PLAUSIVEL_MPA = 100.0


def _float_br(v) -> float | None:
    """Converte texto digitado no formulário ("115", "115,0") em número."""
    if v is None:
        return None
    try:
        f = float(str(v).strip().replace(" ", "").replace(",", "."))
    except ValueError:
        return None
    return f if f > 0 else None


def _kpis_do_cp(cp: tuple) -> dict:
    if len(cp) > 2 and cp[2] is not None:
        return cp[2]
    return calculate_kpis(cp[1])


def _linhas_por_cp(cps: list[tuple], condicoes) -> list[dict]:
    """Fmax, σmax e alongamento final de cada CP. O alongamento usa a distância entre
    garras quando ela foi informada; senão usa L₀."""
    garras = _float_br(getattr(condicoes, "distancia_garras_mm", ""))
    linhas = []
    for cp in cps:
        nome, cdf = cp[0], cp[1]
        try:
            k = _kpis_do_cp(cp)
        except Exception as exc:
            print(f"[report] KPIs do CP {nome} falharam: {exc}", flush=True)
            continue
        area = k.get("area_secao_mm2")
        l0 = k.get("comprimento_inicial_mm")
        fmax = k.get("forca_max_N")
        tensao = k.get("tensao_max_calc_MPa")
        if tensao is None:
            tensao = k.get("tensao_max_MPa")
        base = garras or l0
        desl = k.get("deslocamento_final_mm")
        along = (desl / base * 100) if (desl is not None and base) else k.get("alonga_final_pct")
        linhas.append({"nome": nome, "df": cdf, "kpis": k, "area": area, "l0": l0,
                       "base": base, "base_garras": bool(garras),
                       "forca_max": fmax, "tensao_max": tensao, "alongamento": along})
    return linhas


def _curva_xy(linha: dict, grafico: str):
    cdf = linha["df"]
    d = cdf["Deslocamento"].to_numpy(dtype=float)
    f = cdf["Forca_N"].to_numpy(dtype=float)
    area = linha["area"]
    if area and area > 0:
        sigma = f / area
    else:
        sigma = cdf["Tensao_Pa"].to_numpy(dtype=float)
    if grafico == "forca_deslocamento":
        return d, f
    if grafico == "tensao_deslocamento":
        return d, sigma
    if grafico == "tensao_deformacao":
        if linha["l0"]:
            return d / linha["l0"] * 100, sigma
        return cdf["Deform_Along"].to_numpy(dtype=float) * 100, sigma
    base = linha["base"]   # tensao_alongamento
    if base:
        return d / base * 100, sigma
    return cdf["Deform_Along"].to_numpy(dtype=float) * 100, sigma


def _chart_curvas_b64(linhas: list[dict], grafico: str) -> str:
    """Uma curva por CP no mesmo gráfico, com o ponto de força máxima marcado."""
    try:
        _, x_label, y_label = GRAFICOS_TRACAO[grafico]
        fig, ax = plt.subplots(figsize=(8, 4.8))
        for idx, ln in enumerate(linhas):
            cor = _PALETA[idx % len(_PALETA)]
            x, y = _curva_xy(ln, grafico)
            ax.plot(x, y, color=cor, linewidth=1.6, label=ln["nome"] if len(linhas) > 1 else None)
            pos = int(ln["df"]["Forca_N"].fillna(float("-inf")).values.argmax())
            ax.scatter([x[pos]], [y[pos]], color=cor, s=40, zorder=5)
        ax.set_xlabel(x_label, fontsize=10)
        ax.set_ylabel(y_label, fontsize=10)
        _eixos_a_partir_de_zero(ax)
        ax.grid(True, alpha=0.25, linestyle="--", color="gray")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        if len(linhas) > 1:
            ax.legend(fontsize=8, loc="best")
        plt.tight_layout(pad=0.5)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buf.seek(0)
        return base64.b64encode(buf.read()).decode("utf-8")
    except Exception as exc:
        print(f"[report] _chart_curvas_b64({grafico}) falhou: {exc}", flush=True)
        return ""


def _estatisticas(valores: list) -> tuple | None:
    v = [float(x) for x in valores if x is not None and x == x]
    if not v:
        return None
    return min(v), max(v), sum(v) / len(v)


_TH = 'style="background:#1e3a5f;color:#fff;padding:6px 9px;border:1px solid #999"'
_TD_NUM = 'style="border:1px solid #bbb;padding:5px 9px;text-align:right;font-family:monospace"'
_TD_TXT = 'style="border:1px solid #bbb;padding:5px 9px"'


def _resultados_resumido(cps, linhas, req, fig_num, tab_num, kpis, tensao_max, alongamento, area, l0):
    partes: list[str] = []

    # Aviso de área/tensão fora do esperado (quase sempre área digitada errada na IHM)
    suspeitos = [ln for ln in linhas
                 if (ln["area"] is not None and 0 < ln["area"] < _AREA_MIN_MM2)
                 or (ln["tensao_max"] is not None and ln["tensao_max"] > _TENSAO_MAX_PLAUSIVEL_MPA)]
    if suspeitos:
        itens = "; ".join(f'{_esc(ln["nome"])}: área {_num(ln["area"], ".3f")} mm², σmax {_num(ln["tensao_max"])} MPa'
                          for ln in suspeitos)
        partes.append(
            '<p class="aviso-area" style="color:#b45309;background:#fff7ed;border:1px solid #fed7aa;'
            f'padding:8px 12px;margin-bottom:12px">Atenção: a tensão calculada está fora do esperado '
            f'({itens}). Confira a área da seção digitada na IHM antes de emitir o relatório.</p>'
        )

    n = len(linhas)
    graficos = [g for g in (getattr(req, "graficos", None) or []) if g in GRAFICOS_TRACAO]
    for g in graficos:
        b64 = _chart_curvas_b64(linhas, g)
        titulo = GRAFICOS_TRACAO[g][0]
        if not b64:
            partes.append(f'<p style="color:#c00;font-style:italic">[Gráfico {titulo}: falha na geração]</p>')
            continue
        fig_num += 1
        detalhe = ""
        if g == "tensao_alongamento" and linhas:
            ln0 = linhas[0]
            if ln0["base"]:
                detalhe = (f" (base: distância entre garras de {_num(ln0['base'], '.0f')} mm)" if ln0["base_garras"]
                           else f" (base: L₀ de {_num(ln0['base'], '.0f')} mm)")
        alvo = f"dos {n} corpos de prova" if n > 1 else f"do ensaio {linhas[0]['nome']}" if linhas else ""
        partes.append(f'<p style="margin-bottom:8px">Na Figura {fig_num} está apresentada a curva '
                      f'{_esc(titulo)} {_esc(alvo)}.</p>')
        partes.append(_figure(f"data:image/png;base64,{b64}",
                              f"Figura {fig_num} – Curva {titulo}{detalhe}" + (f" — {n} CPs." if n > 1 else ".")))

    if linhas:
        tab_num += 1
        base_txt = ""
        if linhas[0]["base"]:
            base_txt = ("distância entre garras" if linhas[0]["base_garras"] else "comprimento inicial L₀")
        corpo = "".join(
            f'<tr><td {_TD_TXT}>{_esc(ln["nome"])}</td><td {_TD_NUM}>{_num(ln["forca_max"], ".1f")}</td>'
            f'<td {_TD_NUM}>{_num(ln["tensao_max"])}</td><td {_TD_NUM}>{_num(ln["alongamento"])}</td></tr>'
            for ln in linhas
        )
        if n > 1:
            est = [_estatisticas([ln[k] for ln in linhas]) for k in ("forca_max", "tensao_max", "alongamento")]
            for i, rotulo in enumerate(("Mínimo", "Máximo", "Média")):
                fmts = (".1f", ".2f", ".2f")
                corpo += (f'<tr style="background:#f4f6f9;font-weight:bold"><td {_TD_TXT}>{rotulo}</td>'
                          + "".join(f'<td {_TD_NUM}>{_num(e[i], fmts[j]) if e else "—"}</td>' for j, e in enumerate(est))
                          + '</tr>')
        partes.append(
            f'<p style="margin-bottom:8px">Na Tabela {tab_num} estão apresentados os resultados '
            f'{"de cada corpo de prova" if n > 1 else "do ensaio"}.</p>'
            f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin-bottom:4px">'
            f'Tabela {tab_num} – Resultados do ensaio de tração.</p>'
            f'<table style="width:85%;margin:0 auto 6px"><thead><tr>'
            f'<th {_TH}>Corpo de prova</th><th {_TH}>Fmax (N)</th><th {_TH}>σmax (MPa)</th>'
            f'<th {_TH}>Alongamento final (%)</th></tr></thead><tbody>{corpo}</tbody></table>'
            + (f'<p style="text-align:center;font-size:8.5pt;color:#555;margin-bottom:18px">'
               f'Alongamento final calculado sobre a {base_txt}.</p>' if base_txt else
               '<div style="margin-bottom:18px"></div>')
        )

    if getattr(req, "include_tabela_detalhada", False):
        tab_num += 1
        rows = _linhas_resultado_tracao(kpis, tensao_max, alongamento, area, l0)
        partes.append(
            f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin-bottom:4px">'
            f'Tabela {tab_num} – Resultados detalhados — {_esc(linhas[0]["nome"] if linhas else "")}.</p>'
            f'<table style="width:70%;margin:0 auto 20px"><thead><tr><th {_TH}>Propriedade</th>'
            f'<th {_TH}>Valor</th><th {_TH}>Unidade</th></tr></thead><tbody>'
            + "".join(f'<tr><td {_TD_TXT}>{_esc(r[0])}</td><td {_TD_NUM}>{r[1]}</td><td {_TD_TXT}>{r[2]}</td></tr>'
                      for r in rows)
            + '</tbody></table>'
        )
    return partes, fig_num, tab_num


_PROPRIEDADES = {
    "tensao_max": ("Tensão Máxima", "MPa", ".2f"),
    "alongamento": ("Alongamento Final", "%", ".2f"),
    "forca_max": ("Força Máxima", "N", ".1f"),
}


def _conclusao_resumida(linhas: list[dict], req, tab_num: int) -> str:
    """Tensão máxima e alongamento final (menor valor entre os CPs), com os requisitos
    definidos pelo laboratório e a conclusão APROVADO/REPROVADO."""
    n = len(linhas)
    requisitos = [r for r in (getattr(req, "requisitos", None) or [])
                  if r.propriedade in _PROPRIEDADES and _float_br(r.valor) is not None]
    props = ["tensao_max", "alongamento"] + [r.propriedade for r in requisitos
                                              if r.propriedade not in ("tensao_max", "alongamento")]
    props = list(dict.fromkeys(props))
    linhas_html = ""
    resultados: list[bool] = []
    for p in props:
        rotulo, unidade, fmt = _PROPRIEDADES[p]
        est = _estatisticas([ln[p] for ln in linhas])
        reqs = [r for r in requisitos if r.propriedade == p]
        # Para requisito de mínimo vale o menor valor; para máximo, o maior.
        usa_maior = bool(reqs) and all(r.criterio == "<=" for r in reqs)
        valor = (est[1] if usa_maior else est[0]) if est else None
        if n > 1:
            rotulo += " (maior valor encontrado)" if usa_maior else " (menor valor encontrado)"
        req_txt, res_txt = "—", "—"
        if reqs:
            partes_req, oks = [], []
            for r in reqs:
                lim = _float_br(r.valor)
                sinal = "≤" if r.criterio == "<=" else "≥"
                partes_req.append(f"{sinal} {r.valor.strip()} {unidade}" + (f" ({r.referencia.strip()})" if r.referencia.strip() else ""))
                if est:
                    v = est[1] if r.criterio == "<=" else est[0]
                    oks.append(v <= lim if r.criterio == "<=" else v >= lim)
            req_txt = "; ".join(partes_req)
            if oks:
                ok = all(oks)
                resultados.append(ok)
                res_txt = "Conforme" if ok else "Não conforme"
        cor = "" if res_txt == "—" else (";color:#15803d" if res_txt == "Conforme" else ";color:#b91c1c")
        linhas_html += (
            f'<tr><td style="border:1px solid #bbb;padding:5px 9px;font-weight:bold">{_esc(rotulo)}</td>'
            f'<td {_TD_NUM}>{_num(valor, fmt)}</td><td {_TD_TXT}>{unidade}</td>'
            f'<td {_TD_TXT}>{_esc(req_txt)}</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px;font-weight:bold{cor}">{res_txt}</td></tr>'
        )

    if resultados:
        conclusao = "APROVADO" if all(resultados) else "REPROVADO"
    else:
        conclusao = (getattr(req, "conclusao_manual", "") or "").strip().upper()
    if conclusao:
        cor = "#15803d" if conclusao == "APROVADO" else "#b91c1c" if conclusao == "REPROVADO" else "#1a1a1a"
        linhas_html += (
            f'<tr><td style="border:1px solid #bbb;padding:7px 9px;font-weight:bold;background:#f4f6f9">Conclusão</td>'
            f'<td colspan="4" class="conclusao" style="border:1px solid #bbb;padding:7px 9px;font-weight:bold;'
            f'font-size:12pt;letter-spacing:1px;color:{cor}">{_esc(conclusao)}</td></tr>'
        )
    return (
        f'<p style="margin-bottom:8px">Na Tabela {tab_num} está apresentado um resumo dos resultados obtidos.</p>'
        f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin-bottom:4px">'
        f'Tabela {tab_num} – Resumo dos Resultados.</p>'
        f'<table style="width:90%;margin:0 auto 20px"><thead><tr>'
        f'<th {_TH}>Propriedade</th><th {_TH}>Valor</th><th {_TH}>Unidade</th>'
        f'<th {_TH}>Requisito normativo</th><th {_TH}>Resultado</th></tr></thead>'
        f'<tbody>{linhas_html}</tbody></table>'
    )


# ──────────────────────────────────────────────
# Main function
# ──────────────────────────────────────────────

def generate_html_report(ensaio, df: pd.DataFrame, kpis: dict, req,
                         comparacao_series: list[tuple] | None = None,
                         modo: str = "tracao", responsavel: dict | None = None) -> str:
    """Relatório HTML de um ensaio. ``modo`` é "tracao" ou "flexao". Cada item de
    ``comparacao_series`` é (nome, df) ou (nome, df, kpis) com os KPIs já calculados.
    ``responsavel`` traz o usuário logado que emite o relatório (``emissor``: nome,
    cargo, registro, login, mestre) e quem executou o ensaio (``executor``)."""
    responsavel = responsavel or {}
    emissor = responsavel.get("emissor") or {}
    executor = (responsavel.get("executor") or "").strip()
    flexao = modo == "flexao"
    tipo_ensaio = "Flexão" if flexao else "Tração"
    titulo_rel = (getattr(req, "titulo", "") or "").strip() or f"Relatório de Ensaio de {tipo_ensaio}"
    resumido = (not flexao) and getattr(req, "modelo", "completo") == "resumido"
    # Série de CPs: o ensaio principal + os outros CPs do lote (cada item é
    # (nome, df) ou (nome, df, kpis)). No modelo resumido os CPs do lote chegam
    # por ``comparacao_series``.
    cps: list[tuple] = [(ensaio.nome, df, kpis)]
    if resumido and comparacao_series:
        cps += list(comparacao_series)
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    body_parts: list[str] = []
    sec_num = 0
    tab_num = 0   # numeração própria de tabelas
    fig_num = 0   # numeração própria de figuras (contínua no documento)

    # ── HEADER ────────────────────────────────
    logo_html = ""
    if req.include_empresa and req.empresa.logo_data_url:
        logo_html = (
            f'<img src="{_src(req.empresa.logo_data_url)}" alt="Logo" '
            f'style="max-height:55px;max-width:130px;object-fit:contain"/>'
        )

    empresa_nome = req.empresa.nome if req.include_empresa and req.empresa.nome else titulo_rel
    numero_rel = req.empresa.numero_relatorio if req.include_empresa else ""

    empresa_endereco = ""
    if req.include_empresa and req.empresa.endereco:
        parts = [_esc(req.empresa.endereco)]
        if req.empresa.telefone: parts.append(f"Tel. {_esc(req.empresa.telefone)}")
        if req.empresa.email:    parts.append(f"E-mail {_esc(req.empresa.email)}")
        if req.empresa.site:     parts.append(_esc(req.empresa.site))
        empresa_endereco = " &nbsp;|&nbsp; ".join(parts)

    numero_html = (
        f'<div style="font-size:9pt;color:#444;margin-top:3px">N°&nbsp;{_esc(numero_rel)}</div>'
        if numero_rel else ""
    )
    # Quem emitiu é controle interno: só aparece com o quadro de responsabilidade
    emitido_por = (f" por {_esc(emissor['nome'])}"
                   if emissor.get("nome") and getattr(req, "include_responsabilidade", True) else "")
    emitido_html = f'<div style="font-size:7.5pt;color:#888;margin-top:6px">Emitido em {now}{emitido_por}</div>'

    header_html = f"""
    <div style="border-top:5px solid #1e3a5f;padding-top:16px;margin-bottom:0">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:14px">
        <div style="display:flex;align-items:center;gap:14px">
          {logo_html}
          <div>
            <div style="font-size:11pt;font-weight:bold;color:#1e3a5f">{_esc(empresa_nome)}</div>
            {"<div style='font-size:8pt;color:#555;margin-top:3px'>" + empresa_endereco + "</div>" if empresa_endereco else ""}
          </div>
        </div>
        <div style="text-align:right">
          <div style="font-size:13pt;font-weight:bold;text-transform:uppercase;letter-spacing:0.5px;color:#1e3a5f">{_esc(titulo_rel)}</div>
          {numero_html}
          {emitido_html}
        </div>
      </div>
      <div style="border-top:1px solid #c8d0dc;margin-bottom:20px"></div>
    </div>
    """
    body_parts.append(header_html)

    # ── DADOS DO CLIENTE ──────────────────────
    if req.include_cliente:
        c = req.cliente
        rows = []
        if c.nome or c.os:
            rows.append(_td2("Cliente:", c.nome, "OS:", c.os))
        if c.contato:
            rows.append(_td("Contato:", c.contato))
        if c.email_cliente or c.telefone_cliente:
            rows.append(_td2("E-mail:", c.email_cliente, "Telefone:", c.telefone_cliente))
        if c.endereco or c.bairro:
            rows.append(_td2("Endereço:", c.endereco, "Bairro:", c.bairro))
        if c.cidade_uf or c.cep:
            rows.append(_td2("Cidade/UF:", c.cidade_uf, "CEP:", c.cep))
        if c.data_recebimento:
            rows.append(_td("Data de Recebimento da(s) Amostra(s):", c.data_recebimento))
        if c.periodo_realizacao:
            rows.append(_td("Período de Realização do Trabalho:", c.periodo_realizacao))
        if rows:
            body_parts.append(
                f'<table style="width:100%;margin:16px 0">{"".join(rows)}</table>'
            )

    # ── SUMÁRIO ───────────────────────────────
    toc_items = []
    if req.include_amostra:  toc_items.append("IDENTIFICAÇÃO DA(S) AMOSTRA(S)")
    if req.include_objetivos: toc_items.append("OBJETIVOS")
    if req.include_condicoes: toc_items.append(f"CONDIÇÕES DO ENSAIO DE {tipo_ensaio.upper()}")
    if req.include_resultados: toc_items.append("RESULTADOS")
    if req.include_conclusao: toc_items.append("CONCLUSÃO")
    if toc_items and getattr(req, "include_sumario", True):
        toc_rows = "".join(
            f'<tr>'
            f'<td style="padding:7px 14px;width:30px;font-weight:bold;color:#1e3a5f;'
            f'vertical-align:top;{"border-bottom:1px solid #eee;" if i < len(toc_items)-1 else ""}">'
            f'{i+1}</td>'
            f'<td style="padding:7px 0 7px 4px;font-size:10pt;'
            f'{"border-bottom:1px solid #eee;" if i < len(toc_items)-1 else ""}">'
            f'{_esc(t.title())}</td>'
            f'</tr>'
            for i, t in enumerate(toc_items)
        )
        body_parts.append(
            f'<div style="margin:24px 0;border:1px solid #d0d7e3;border-radius:2px;overflow:hidden">'
            f'<div style="background:#1e3a5f;color:#fff;padding:7px 14px;'
            f'font-size:8.5pt;font-weight:bold;letter-spacing:1px;text-transform:uppercase">'
            f'Sumário</div>'
            f'<table style="width:100%;border-collapse:collapse">{toc_rows}</table>'
            f'</div>'
        )

    # ── SEÇÃO 1: IDENTIFICAÇÃO DA AMOSTRA ─────
    if req.include_amostra:
        sec_num += 1
        body_parts.append(_section_header(sec_num, "Identificação da(s) Amostra(s)"))
        a = req.amostra
        if a.id_interno or a.id_cliente:
            tab_num += 1
            body_parts.append(
                f'<p style="margin-bottom:8px">A amostra foi identificada conforme a Tabela {tab_num}.</p>'
                f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin-bottom:4px">'
                f'Tabela {tab_num} – Identificação da(s) Amostra(s).</p>'
                f'<table style="width:60%;margin:0 auto 16px">'
                f'<tr><th style="background:#1e3a5f;color:#fff;padding:6px 12px;border:1px solid #999">Identificação Interna</th>'
                f'<th style="background:#1e3a5f;color:#fff;padding:6px 12px;border:1px solid #999">Identificação do Cliente</th></tr>'
                f'<tr><td style="text-align:center;padding:6px 12px;border:1px solid #bbb">{_esc(a.id_interno)}</td>'
                f'<td style="text-align:center;padding:6px 12px;border:1px solid #bbb">{_esc(a.id_cliente)}</td></tr>'
                f'</table>'
            )
        if a.imagem_data_url:
            fig_num += 1
            body_parts.append(_figure(a.imagem_data_url, f"Figura {fig_num} – Imagem da Amostra{': ' + a.id_interno if a.id_interno else ''}."))

    # ── SEÇÃO 2: OBJETIVOS ────────────────────
    if req.include_objetivos and req.objetivos:
        sec_num += 1
        body_parts.append(_section_header(sec_num, "Objetivos"))
        body_parts.append(f'<p style="margin-left:20px">{_esc(req.objetivos)}</p>')

    # ── SEÇÃO 3: CONDIÇÕES DO ENSAIO ──────────
    if req.include_condicoes:
        sec_num += 1
        body_parts.append(_section_header(sec_num, f"Condições do Ensaio de {tipo_ensaio}"))
        c = req.condicoes
        tab_num += 1
        body_parts.append(
            f'<p style="margin-bottom:8px">Na Tabela {tab_num} estão apresentadas as condições do ensaio.</p>'
            f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin-bottom:4px">'
            f'Tabela {tab_num} – Condições do ensaio de {tipo_ensaio}.</p>'
        )
        rows = []
        # Só entram os campos preenchidos, dois por linha (a qualidade pediu para
        # tirar "Temperatura do ensaio" e "Célula de carga": basta deixá-los vazios).
        pares: list[tuple[str, str]] = []

        def _par(rotulo: str, valor: str, sufixo: str = "") -> None:
            v = (valor or "").strip()
            if v:
                pares.append((rotulo, f"{v} {sufixo}".strip() if sufixo else v))

        _par("Temperatura do Laboratório:", c.temp_laboratorio, "°C")
        _par("Umidade do Laboratório:", c.umidade_laboratorio, "%")
        te = (c.temp_ensaio or "").strip()
        if te:
            numerico = te.replace(",", ".").replace("-", "").strip().replace(".", "", 1).isdigit()
            _par("Temperatura do Ensaio:", te, "°C" if numerico else "")
        n_cps = (c.num_corpos_prova or "").strip()
        if resumido and len(cps) > 1 and n_cps in ("", "1"):
            n_cps = str(len(cps))
        _par("Número de Corpos de Prova:", n_cps)
        if c.celula_carga:
            _par("Célula de Carga:", c.celula_carga, c.celula_carga_unidade)
        if flexao:
            _par("Distância entre Apoios (L):", c.distancia_garras_mm, "mm")
        else:
            _par("Comprimento Inicial (L₀):", c.comprimento_inicial_mm, "mm")
            _par("Distância entre Garras:", c.distancia_garras_mm, "mm")
        if c.velocidade_ensaio:
            _par("Velocidade do Ensaio:", c.velocidade_ensaio, c.velocidade_ensaio_unidade)
        _par("Tipo de Corpo de Prova:" if resumido else "Corpo de Prova:", c.tipo_corpo_prova)
        _par("Extensômetro:", c.extensometro)
        for i in range(0, len(pares), 2):
            if i + 1 < len(pares):
                rows.append(_td2(pares[i][0], pares[i][1], pares[i + 1][0], pares[i + 1][1]))
            else:
                rows.append(f'<tr><td style="font-weight:bold;width:22%;background:#f0f0f0;border:1px solid #bbb;padding:5px 9px">{_esc(pares[i][0])}</td>'
                            f'<td colspan="3" style="border:1px solid #bbb;padding:5px 9px">{_esc(pares[i][1])}</td></tr>')
        if c.largura_cp_mm or c.espessura_cp_mm:
            rows.append(f'<tr>'
                        f'<td style="font-weight:bold;background:#f0f0f0;border:1px solid #bbb;padding:5px 9px" rowspan="2">Dimensões dos Corpos de Prova:</td>'
                        f'<td colspan="3" style="border:1px solid #bbb;padding:5px 9px"><b>Largura:</b> {_esc(c.largura_cp_mm + " mm" if c.largura_cp_mm else "—")}</td>'
                        f'</tr>'
                        f'<tr><td colspan="3" style="border:1px solid #bbb;padding:5px 9px"><b>Espessura:</b> {_esc(c.espessura_cp_mm + " mm" if c.espessura_cp_mm else "—")}</td></tr>')
        if c.preparacao_cp:
            opcoes = ["Injeção", "Usinagem", "Prensagem", "Estampagem", "Recorte", "Enviados pelo Cliente"]
            prep_html = " &nbsp; ".join(
                f'<b>( {"X" if op in c.preparacao_cp else "&nbsp;"} )</b>&nbsp;{_esc(op)}'
                for op in opcoes
            )
            rows.append(f'<tr><td style="font-weight:bold;background:#f0f0f0;border:1px solid #bbb;padding:5px 9px">Preparação dos Corpos de Prova:</td>'
                        f'<td colspan="3" style="border:1px solid #bbb;padding:5px 9px">{prep_html}</td></tr>')
        if c.data_realizacao:
            rows.append(f'<tr><td colspan="4" style="font-weight:bold;border:1px solid #bbb;padding:5px 9px">Data de Realização: {_esc(c.data_realizacao)}</td></tr>')
        if c.equipamentos:
            rows.append(f'<tr><td style="font-weight:bold;background:#f0f0f0;border:1px solid #bbb;padding:5px 9px">Equipamento(s):</td>'
                        f'<td colspan="3" style="border:1px solid #bbb;padding:5px 9px">{_esc(c.equipamentos)}</td></tr>')
        metodo = (getattr(c, "metodo_ensaio", "") or "").strip()
        if metodo:
            rows.append(f'<tr><td style="font-weight:bold;background:#f0f0f0;border:1px solid #bbb;padding:5px 9px">Método de Ensaio:</td>'
                        f'<td colspan="3" style="border:1px solid #bbb;padding:5px 9px">{_esc(metodo)}</td></tr>')
        norma_ref = c.norma_referencia
        if flexao and norma_ref == "ISO 527-1:2019":   # padrão do pedido é o da tração
            norma_ref = kpis.get("norma") or norma_ref
        if norma_ref:
            rows.append(f'<tr><td style="font-weight:bold;background:#f0f0f0;border:1px solid #bbb;padding:5px 9px">Norma de Referência:</td>'
                        f'<td colspan="3" style="border:1px solid #bbb;padding:5px 9px">{_esc(norma_ref)}</td></tr>')
        body_parts.append(f'<table style="width:100%;margin-bottom:16px">{"".join(rows)}</table>')

    # Valores "oficiais" usados tanto em Resultados quanto na Conclusão:
    # preferem o cálculo por A e L₀ (Fmax/A, d/L₀) quando disponível.
    tensao_max = kpis.get("tensao_max_calc_MPa")
    if tensao_max is None:
        tensao_max = kpis.get("tensao_max_MPa")
    alongamento = kpis.get("alonga_calc_pct")
    if alongamento is None:
        alongamento = kpis.get("alonga_ruptura_pct")
    area = kpis.get("area_secao_mm2")
    l0 = kpis.get("comprimento_inicial_mm")
    unidades_cruas = (area is not None and abs(float(area) - 1.0) < 1e-9
                      and l0 is not None and abs(float(l0) - 1.0) < 1e-9)
    if flexao:
        # σf/εf só existem com largura, espessura e vão gravados no ensaio
        unidades_cruas = not all(kpis.get(k) for k in ("largura_mm", "espessura_mm", "span_mm"))

    # ── SEÇÃO 4: RESULTADOS ───────────────────
    linhas_cp: list[dict] = []
    if resumido:
        linhas_cp = _linhas_por_cp(cps, req.condicoes)
    if resumido and req.include_resultados:
        sec_num += 1
        body_parts.append(_section_header(sec_num, "Resultados"))
        partes, fig_num, tab_num = _resultados_resumido(cps, linhas_cp, req, fig_num, tab_num,
                                                       kpis, tensao_max, alongamento, area, l0)
        body_parts += partes
    elif req.include_resultados:
        sec_num += 1
        body_parts.append(_section_header(sec_num, "Resultados"))

        if unidades_cruas and flexao:
            body_parts.append(
                '<p style="color:#b45309;background:#fff7ed;border:1px solid #fed7aa;'
                'padding:8px 12px;margin-bottom:12px">Atenção: este ensaio foi gravado sem '
                'largura, espessura ou distância entre apoios. Tensão e deformação de flexão '
                'não puderam ser calculadas e não devem ser usadas como resultado.</p>'
            )
        elif unidades_cruas:
            body_parts.append(
                '<p style="color:#b45309;background:#fff7ed;border:1px solid #fed7aa;'
                'padding:8px 12px;margin-bottom:12px">Atenção: este ensaio foi gravado sem '
                'área da seção e comprimento inicial (L₀). Tensão e deformação estão em '
                'unidades cruas (iguais à força em N e ao deslocamento em mm) e não devem '
                'ser usadas como resultado.</p>'
            )

        if req.include_stress_strain:
            chart_b64 = _chart_stress_strain_b64(df, modo)
            if chart_b64:
                fig_num += 1
                body_parts.append(
                    f'<p style="margin-bottom:8px">Na Figura {fig_num} está apresentada a curva de tensão em função da deformação.</p>'
                )
                body_parts.append(_figure(
                    f"data:image/png;base64,{chart_b64}",
                    f"Figura {fig_num} – Curva Tensão × Deformação{' de Flexão' if flexao else ''} — {ensaio.nome}."
                ))
            else:
                body_parts.append('<p style="color:#c00;font-style:italic">[Gráfico σ×ε: falha na geração — ver terminal do backend]</p>')

        if req.include_graficos_adicionais:
            chart2 = _chart_force_displacement_b64(df, modo)
            if chart2:
                fig_num += 1
                body_parts.append(_figure(
                    f"data:image/png;base64,{chart2}",
                    f"Figura {fig_num} – Curva Força × {'Deflexão' if flexao else 'Deslocamento'} — {ensaio.nome}."
                ))
            else:
                body_parts.append('<p style="color:#c00;font-style:italic">[Gráfico F×d: falha na geração]</p>')

        if req.include_comparativo and comparacao_series:
            all_series = [(ensaio.nome, df, kpis)] + list(comparacao_series)
            curvas = [(s[0], s[1]) for s in all_series]
            cmp_figs: list[tuple[str, str]] = []
            cmp_ss = _chart_comparison_ss_b64(curvas, modo)
            if cmp_ss:
                cmp_figs.append((cmp_ss, f"Comparativo Tensão × Deformação ({len(all_series)} ensaios)."))
            cmp_fd = _chart_comparison_fd_b64(curvas, modo)
            if cmp_fd:
                cmp_figs.append((cmp_fd, f"Comparativo Força × {'Deflexão' if flexao else 'Deslocamento'} ({len(all_series)} ensaios)."))

            if cmp_figs:
                first = fig_num + 1
                refs = f"Figura {first}" if len(cmp_figs) == 1 else f"Figuras {first} e {first + 1}"
                verbo = "é apresentada a curva comparativa" if len(cmp_figs) == 1 else "são apresentadas as curvas comparativas"
                body_parts.append(
                    f'<p style="margin-bottom:8px">{"Na" if len(cmp_figs) == 1 else "Nas"} {refs} {verbo} '
                    f'entre os {len(all_series)} ensaios selecionados.</p>'
                )
                for b64, cap in cmp_figs:
                    fig_num += 1
                    body_parts.append(_figure(f"data:image/png;base64,{b64}", f"Figura {fig_num} – {cap}"))
            else:
                body_parts.append('<p style="color:#c00;font-style:italic">[Gráficos comparativos: falha na geração]</p>')

            # Tabela comparativa com os principais resultados de cada ensaio
            cmp_rows = []
            for serie in all_series:
                nome, cdf = serie[0], serie[1]
                try:
                    ck = serie[2] if len(serie) > 2 else calculate_kpis(cdf)
                except Exception as exc:
                    print(f"[report] KPIs do comparativo falharam para {nome}: {exc}", flush=True)
                    continue
                if flexao:
                    cmp_rows.append((nome, _num(ck.get("forca_max_N"), ".1f"), _num(ck.get("tensao_flexao_max_MPa")),
                                     _num(ck.get("modulo_flexao_MPa"), ".1f"), _num(ck.get("deflexao_max_mm")),
                                     _num(ck.get("energia_J"))))
                    continue
                ct = ck.get("tensao_max_calc_MPa")
                if ct is None:
                    ct = ck.get("tensao_max_MPa")
                ca = ck.get("alonga_calc_pct")
                if ca is None:
                    ca = ck.get("alonga_ruptura_pct")
                cmp_rows.append((nome, _num(ck.get("forca_max_N"), ".1f"), _num(ct), _num(ck.get("modulo_elasticidade_MPa"), ".1f"),
                                 _num(ca), _num(ck.get("alonga_final_pct")), _num(ck.get("energia_J"))))
            if cmp_rows:
                tab_num += 1
                th = 'style="background:#1e3a5f;color:#fff;padding:6px 9px;border:1px solid #999"'
                td = 'style="border:1px solid #bbb;padding:5px 9px;text-align:right;font-family:monospace"'
                body_parts.append(
                    f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin:8px 0 4px">'
                    f'Tabela {tab_num} – Comparativo dos resultados.</p>'
                    f'<table style="width:90%;margin:0 auto 20px"><thead><tr>'
                    + (f'<th {th}>Ensaio</th><th {th}>Fmax (N)</th><th {th}>σfM (MPa)</th>'
                       f'<th {th}>Ef (MPa)</th><th {th}>Deflexão máx. (mm)</th><th {th}>Energia (J)</th>'
                       if flexao else
                       f'<th {th}>Ensaio</th><th {th}>Fmax (N)</th><th {th}>σmax (MPa)</th>'
                       f'<th {th}>E (MPa)</th><th {th}>Along. Fmáx (%)</th><th {th}>Along. final (%)</th><th {th}>Energia (J)</th>')
                    + '</tr></thead><tbody>'
                    + "".join(
                        f'<tr><td style="border:1px solid #bbb;padding:5px 9px">{_esc(r[0])}</td>'
                        + "".join(f'<td {td}>{v}</td>' for v in r[1:]) + '</tr>'
                        for r in cmp_rows
                    )
                    + '</tbody></table>'
                )

        tab_num += 1
        body_parts.append(
            f'<p style="margin-bottom:8px">Na Tabela {tab_num} estão apresentados os resultados do ensaio.</p>'
            f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin-bottom:4px">'
            f'Tabela {tab_num} – Resultados do ensaio de {tipo_ensaio}.</p>'
        )
        if flexao:
            kpi_rows = _linhas_resultado_flexao(kpis)
        else:
            kpi_rows = _linhas_resultado_tracao(kpis, tensao_max, alongamento, area, l0)
        kpi_html = "".join(
            f'<tr>'
            f'<td style="border:1px solid #bbb;padding:5px 9px">{_esc(r[0])}</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px;text-align:right;font-family:monospace">{r[1]}</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px;width:60px">{r[2]}</td>'
            f'</tr>'
            for r in kpi_rows
        )
        body_parts.append(
            f'<table style="width:70%;margin:0 auto 20px">'
            f'<thead><tr>'
            f'<th style="background:#1e3a5f;color:#fff;padding:6px 9px;border:1px solid #999;text-align:left">Propriedade</th>'
            f'<th style="background:#1e3a5f;color:#fff;padding:6px 9px;border:1px solid #999;text-align:right">Valor</th>'
            f'<th style="background:#1e3a5f;color:#fff;padding:6px 9px;border:1px solid #999">Unidade</th>'
            f'</tr></thead>'
            f'<tbody>{kpi_html}</tbody>'
            f'</table>'
        )

        if req.include_raw_data:
            col_tensao = _EIXOS[modo]["y"]
            col_deform = _EIXOS[modo]["x"]
            sub = "f" if flexao else ""
            rows_html = ""
            for _, row in df.iterrows():
                rows_html += (
                    f"<tr>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px'>{_esc(row.get('TIME',''))}</td>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px'>{_esc(row.get('DATA',''))}</td>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px;text-align:right'>{_num(row.get(col_tensao))}</td>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px;text-align:right'>{_num((row.get(col_deform) or 0) * 100, '.3f')}</td>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px;text-align:right'>{_num(row.get('Forca_N'))}</td>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px;text-align:right'>{_num(row.get('Deslocamento'))}</td>"
                    f"</tr>\n"
                )
            body_parts.append(
                f'<h3 style="font-size:10.5pt;margin:20px 0 8px">Dados Brutos</h3>'
                f'<table style="width:100%;font-size:8.5pt">'
                f'<thead><tr>'
                f'<th style="background:#1e3a5f;color:#fff;padding:4px 6px;border:1px solid #999">Hora</th>'
                f'<th style="background:#1e3a5f;color:#fff;padding:4px 6px;border:1px solid #999">Data</th>'
                f'<th style="background:#1e3a5f;color:#fff;padding:4px 6px;border:1px solid #999">σ{sub} (MPa)</th>'
                f'<th style="background:#1e3a5f;color:#fff;padding:4px 6px;border:1px solid #999">ε{sub} (%)</th>'
                f'<th style="background:#1e3a5f;color:#fff;padding:4px 6px;border:1px solid #999">F (N)</th>'
                f'<th style="background:#1e3a5f;color:#fff;padding:4px 6px;border:1px solid #999">{"δ" if flexao else "d"} (mm)</th>'
                f'</tr></thead>'
                f'<tbody>{rows_html}</tbody>'
                f'</table>'
            )

    # ── SEÇÃO 5: CONCLUSÃO ────────────────────
    if req.include_conclusao:
        sec_num += 1
        body_parts.append(_section_header(sec_num, "Conclusão"))
        tab_num += 1
        if resumido:
            body_parts.append(_conclusao_resumida(linhas_cp, req, tab_num))
            resumo = []
        elif flexao:
            resumo = [
                ("Módulo de Flexão", _num(kpis.get("modulo_flexao_GPa"), ".3f"), "GPa"),
                ("Resistência à Flexão", _num(kpis.get("tensao_flexao_max_MPa")), "MPa"),
                ("Deflexão na Força Máxima", _num(kpis.get("deflexao_pico_mm")), "mm"),
                ("Energia Absorvida", _num(kpis.get("energia_J")), "J"),
            ]
        else:
            resumo = [
                ("Módulo de Elasticidade", _num(kpis.get("modulo_elasticidade_GPa"), ".3f"), "GPa"),
                ("Tensão Máxima", _num(tensao_max), "MPa"),
                ("Alongamento na Força Máxima", _num(alongamento), "%"),
                ("Alongamento Final", _num(kpis.get("alonga_final_pct")), "%"),
                ("Energia Absorvida", _num(kpis.get("energia_J")), "J"),
            ]
        if not resumido:
            resumo_html = "".join(
                f'<tr><td style="border:1px solid #bbb;padding:5px 9px;font-weight:bold">{_esc(r[0])}</td>'
                f'<td style="border:1px solid #bbb;padding:5px 9px;text-align:right;font-family:monospace">{r[1]}</td>'
                f'<td style="border:1px solid #bbb;padding:5px 9px">{r[2]}</td></tr>'
                for r in resumo
            )
            body_parts.append(
                f'<p style="margin-bottom:8px">Na Tabela {tab_num} está apresentado um resumo dos resultados obtidos.</p>'
                f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin-bottom:4px">'
                f'Tabela {tab_num} – Resumo dos Resultados.</p>'
                f'<table style="width:65%;margin:0 auto 20px">'
                f'<thead><tr>'
                f'<th style="background:#1e3a5f;color:#fff;padding:6px 9px;border:1px solid #999">Propriedade</th>'
                f'<th style="background:#1e3a5f;color:#fff;padding:6px 9px;border:1px solid #999">Valor</th>'
                f'<th style="background:#1e3a5f;color:#fff;padding:6px 9px;border:1px solid #999">Unidade</th>'
                f'</tr></thead>'
                f'<tbody>{resumo_html}'
                f'</tbody></table>'
            )

        local_data = req.local_data or _data_extenso(datetime.now())
        body_parts.append(
            f'<p style="text-align:right;margin:20px 0">{_esc(local_data)}</p>'
        )

        # O usuário logado que emite o relatório assina automaticamente (se ainda
        # não estiver na lista). O acesso mestre não assina por ninguém.
        assinaturas = [s for s in req.assinaturas if s.nome]
        if emissor.get("nome") and not emissor.get("mestre") and getattr(req, "assinar_emissor", True):
            nomes = {s.nome.strip().lower() for s in assinaturas}
            if emissor["nome"].strip().lower() not in nomes:
                cargo = " · ".join(x for x in (emissor.get("cargo"), emissor.get("registro")) if x)
                assinaturas.insert(0, SimpleNamespace(nome=emissor["nome"], cargo=cargo, funcao=""))
        if assinaturas:
            sigs_html = "".join(
                f'<div style="text-align:center">'
                + (f'<div style="font-size:8.5pt;font-weight:bold;text-transform:uppercase;letter-spacing:0.5px;'
                   f'color:#555;text-align:left;margin-bottom:34px">{_esc(s.funcao)}:</div>'
                   if (getattr(s, "funcao", "") or "").strip() else "")
                + f'<div style="border-top:1px solid #333;width:180px;margin:0 auto 6px"></div>'
                f'<div style="font-weight:bold">{_esc(s.nome)}</div>'
                f'<div style="font-size:9.5pt">{_esc(s.cargo)}</div>'
                f'</div>'
                for s in assinaturas
            )
            if sigs_html:
                body_parts.append(
                    f'<div style="display:flex;gap:80px;justify-content:center;margin-top:40px">'
                    f'{sigs_html}</div>'
                )

    # ── RESPONSABILIDADE (usuário logado) ─────
    if (emissor.get("nome") or executor) and getattr(req, "include_responsabilidade", True):
        linhas = []
        if executor:
            linhas.append(("Ensaio executado por", executor))
        if emissor.get("nome"):
            emi = emissor["nome"]
            extra = " · ".join(x for x in (emissor.get("cargo"), emissor.get("registro")) if x)
            if extra:
                emi += f" — {extra}"
            linhas.append(("Relatório emitido por", emi))
            if emissor.get("login"):
                linhas.append(("Usuário do sistema", emissor["login"]))
            if emissor.get("email"):
                linhas.append(("E-mail", emissor["email"]))
        linhas.append(("Data de emissão", now))
        rows_html = "".join(
            f'<tr><td style="padding:3px 10px 3px 0;color:#555;white-space:nowrap;width:1%">{_esc(k)}:</td>'
            f'<td style="padding:3px 0;font-weight:bold">{_esc(v)}</td></tr>'
            for k, v in linhas
        )
        body_parts.append(
            f'<div class="responsavel" style="margin-top:28px;border:1px solid #c8d0dc;border-radius:4px;'
            f'padding:10px 14px;font-size:9pt;page-break-inside:avoid">'
            f'<div style="font-size:8.5pt;font-weight:bold;letter-spacing:0.8px;text-transform:uppercase;'
            f'color:#1e3a5f;margin-bottom:6px">Responsabilidade</div>'
            f'<table style="border-collapse:collapse">{rows_html}</table></div>'
        )

    # ── OBSERVAÇÕES FINAIS ────────────────────
    if req.include_observacoes_finais and req.observacoes_finais:
        lines_html = "".join(
            f'<p style="margin:5px 0;font-size:9pt;color:#444;padding-left:12px;'
            f'border-left:2px solid #ddd">{_esc(line.strip())}</p>'
            for line in req.observacoes_finais.splitlines() if line.strip()
        )
        body_parts.append(
            f'<div style="margin-top:32px;border-top:1px solid #ddd;padding-top:14px">'
            f'<div style="font-size:8.5pt;font-weight:bold;letter-spacing:0.8px;'
            f'text-transform:uppercase;color:#666;margin-bottom:10px">Observações</div>'
            f'{lines_html}'
            f'</div>'
        )

    # ── FOOTER ────────────────────────────────
    footer_parts = []
    if req.include_empresa:
        if req.empresa.nome:     footer_parts.append(_esc(req.empresa.nome))
        if req.empresa.endereco: footer_parts.append(_esc(req.empresa.endereco))
        if req.empresa.telefone: footer_parts.append(f"Tel.&nbsp;{_esc(req.empresa.telefone)}")
        if req.empresa.email:    footer_parts.append(_esc(req.empresa.email))
    footer_company = " &nbsp;&nbsp;·&nbsp;&nbsp; ".join(footer_parts) if footer_parts else ""
    body_parts.append(
        f'<div style="margin-top:40px;border-top:2px solid #1e3a5f;padding-top:10px;'
        f'font-size:8pt;color:#666;display:flex;justify-content:space-between;align-items:center">'
        f'<span>{footer_company}</span>'
        f'<span style="color:#999;font-size:7.5pt">Gerado em {now}</span>'
        f'</div>'
    )

    return f"""<!DOCTYPE html>
<!-- REPORT-ENGINE-V2 -->
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório — {_esc(ensaio.nome)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">
{"".join(body_parts)}
</div>
</body>
</html>"""
