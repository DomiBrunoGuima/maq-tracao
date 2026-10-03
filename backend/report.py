from __future__ import annotations

import base64
import io
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import pandas as pd

from .calculator import calculate_kpis


# ──────────────────────────────────────────────
# Chart generation
# ──────────────────────────────────────────────

def _chart_stress_strain_b64(df: pd.DataFrame) -> str:
    try:
        fig, ax = plt.subplots(figsize=(8, 4.8))

        x = df["Deform_Along"].values * 100   # dimensionless → %
        y = df["Tensao_Pa"].values             # já em MPa

        ax.plot(x, y, color="#1e3a5f", linewidth=1.8, label="Tensão")

        fmax_pos = int(df["Forca_N"].fillna(float("-inf")).values.argmax())
        ax.scatter([x[fmax_pos]], [y[fmax_pos]], color="#c0392b", s=60, zorder=5,
                   label=f"Força máxima  {y[fmax_pos]:.1f} MPa / {x[fmax_pos]:.2f}%")

        ax.set_xlabel("Deformação (%)", fontsize=10)
        ax.set_ylabel("Tensão (MPa)", fontsize=10)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
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


def _chart_comparison_ss_b64(series: list[tuple[str, pd.DataFrame]]) -> str:
    """Gráfico σ×ε com múltiplas curvas sobrepostas."""
    try:
        palette = ["#1e3a5f", "#c0392b", "#27ae60", "#8e44ad", "#e67e22", "#2980b9"]
        fig, ax = plt.subplots(figsize=(8, 4.8))
        for idx, (label, df) in enumerate(series):
            color = palette[idx % len(palette)]
            x = df["Deform_Along"].values * 100
            y = df["Tensao_Pa"].values
            ax.plot(x, y, color=color, linewidth=1.8, label=label)
            fmax_pos = int(df["Forca_N"].fillna(float("-inf")).values.argmax())
            ax.scatter([x[fmax_pos]], [y[fmax_pos]], color=color, s=50, zorder=5)
        ax.set_xlabel("Deformação (%)", fontsize=10)
        ax.set_ylabel("Tensão (MPa)", fontsize=10)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
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


def _chart_comparison_fd_b64(series: list[tuple[str, pd.DataFrame]]) -> str:
    """Gráfico F×d com múltiplas curvas sobrepostas."""
    try:
        palette = ["#2e6da4", "#c0392b", "#27ae60", "#8e44ad", "#e67e22", "#1e3a5f"]
        fig, ax = plt.subplots(figsize=(8, 4))
        for idx, (label, df) in enumerate(series):
            color = palette[idx % len(palette)]
            ax.plot(df["Deslocamento"].values, df["Forca_N"].values,
                    color=color, linewidth=1.6, label=label)
        ax.set_xlabel("Deslocamento (mm)", fontsize=10)
        ax.set_ylabel("Força (N)", fontsize=10)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
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


def _chart_force_displacement_b64(df: pd.DataFrame) -> str:
    try:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(df["Deslocamento"].values, df["Forca_N"].values,
                color="#2e6da4", linewidth=1.6)
        ax.set_xlabel("Deslocamento (mm)", fontsize=10)
        ax.set_ylabel("Força (N)", fontsize=10)
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
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


# ──────────────────────────────────────────────
# Main function
# ──────────────────────────────────────────────

def generate_html_report(ensaio, df: pd.DataFrame, kpis: dict, req,
                         comparacao_series: list[tuple[str, pd.DataFrame]] | None = None) -> str:
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

    empresa_nome = req.empresa.nome if req.include_empresa and req.empresa.nome else "Relatório de Ensaio de Tração"
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
    emitido_html = f'<div style="font-size:7.5pt;color:#888;margin-top:6px">Emitido em {now}</div>'

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
          <div style="font-size:13pt;font-weight:bold;text-transform:uppercase;letter-spacing:0.5px;color:#1e3a5f">Relatório de Ensaio de Tração</div>
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
    if req.include_condicoes: toc_items.append("CONDIÇÕES DO ENSAIO DE TRAÇÃO")
    if req.include_resultados: toc_items.append("RESULTADOS")
    if req.include_conclusao: toc_items.append("CONCLUSÃO")
    if toc_items:
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
        body_parts.append(_section_header(sec_num, "Condições do Ensaio de Tração"))
        c = req.condicoes
        tab_num += 1
        body_parts.append(
            f'<p style="margin-bottom:8px">Na Tabela {tab_num} estão apresentadas as condições do ensaio.</p>'
            f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin-bottom:4px">'
            f'Tabela {tab_num} – Condições do ensaio de Tração.</p>'
        )
        rows = []
        if c.temp_laboratorio or c.umidade_laboratorio:
            rows.append(_td2("Temperatura do Laboratório:", f"{c.temp_laboratorio} °C" if c.temp_laboratorio else "—",
                             "Umidade do Laboratório:", f"{c.umidade_laboratorio} %" if c.umidade_laboratorio else "—"))
        if c.temp_ensaio or c.num_corpos_prova:
            te = c.temp_ensaio.strip() if c.temp_ensaio else "Tamb"
            # Append °C only when value is numeric (not "Tamb" or other text)
            te_display = te if not te.replace(",", ".").replace("-", "").strip().replace(".", "", 1).isdigit() else f"{te} °C"
            rows.append(_td2("Temperatura do Ensaio:", te_display,
                             "Número de Corpos de Prova:", c.num_corpos_prova or "—"))
        if c.celula_carga or c.comprimento_inicial_mm:
            carga_display = f"{c.celula_carga} {c.celula_carga_unidade}".strip() if c.celula_carga else "—"
            rows.append(_td2("Célula de Carga:", carga_display,
                             "Comprimento Inicial (L₀):", f"{c.comprimento_inicial_mm} mm" if c.comprimento_inicial_mm else "—"))
        if c.velocidade_ensaio or c.tipo_corpo_prova:
            vel_display = f"{c.velocidade_ensaio} {c.velocidade_ensaio_unidade}".strip() if c.velocidade_ensaio else "—"
            rows.append(_td2("Velocidade do Ensaio:", vel_display,
                             "Corpo de Prova:", c.tipo_corpo_prova or "—"))
        if c.distancia_garras_mm or c.extensometro:
            rows.append(_td2("Distância entre Garras:", f"{c.distancia_garras_mm} mm" if c.distancia_garras_mm else "—",
                             "Extensômetro:", c.extensometro or "—"))
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
        if c.norma_referencia:
            rows.append(f'<tr><td style="font-weight:bold;background:#f0f0f0;border:1px solid #bbb;padding:5px 9px">Norma de Referência:</td>'
                        f'<td colspan="3" style="border:1px solid #bbb;padding:5px 9px">{_esc(c.norma_referencia)}</td></tr>')
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

    # ── SEÇÃO 4: RESULTADOS ───────────────────
    if req.include_resultados:
        sec_num += 1
        body_parts.append(_section_header(sec_num, "Resultados"))

        if unidades_cruas:
            body_parts.append(
                '<p style="color:#b45309;background:#fff7ed;border:1px solid #fed7aa;'
                'padding:8px 12px;margin-bottom:12px">Atenção: este ensaio foi gravado sem '
                'área da seção e comprimento inicial (L₀). Tensão e deformação estão em '
                'unidades cruas (iguais à força em N e ao deslocamento em mm) e não devem '
                'ser usadas como resultado.</p>'
            )

        if req.include_stress_strain:
            chart_b64 = _chart_stress_strain_b64(df)
            if chart_b64:
                fig_num += 1
                body_parts.append(
                    f'<p style="margin-bottom:8px">Na Figura {fig_num} está apresentada a curva de tensão em função da deformação.</p>'
                )
                body_parts.append(_figure(
                    f"data:image/png;base64,{chart_b64}",
                    f"Figura {fig_num} – Curva Tensão × Deformação — {ensaio.nome}."
                ))
            else:
                body_parts.append('<p style="color:#c00;font-style:italic">[Gráfico σ×ε: falha na geração — ver terminal do backend]</p>')

        if req.include_graficos_adicionais:
            chart2 = _chart_force_displacement_b64(df)
            if chart2:
                fig_num += 1
                body_parts.append(_figure(
                    f"data:image/png;base64,{chart2}",
                    f"Figura {fig_num} – Curva Força × Deslocamento — {ensaio.nome}."
                ))
            else:
                body_parts.append('<p style="color:#c00;font-style:italic">[Gráfico F×d: falha na geração]</p>')

        if req.include_comparativo and comparacao_series:
            all_series = [(ensaio.nome, df)] + comparacao_series
            cmp_figs: list[tuple[str, str]] = []
            cmp_ss = _chart_comparison_ss_b64(all_series)
            if cmp_ss:
                cmp_figs.append((cmp_ss, f"Comparativo Tensão × Deformação ({len(all_series)} ensaios)."))
            cmp_fd = _chart_comparison_fd_b64(all_series)
            if cmp_fd:
                cmp_figs.append((cmp_fd, f"Comparativo Força × Deslocamento ({len(all_series)} ensaios)."))

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
            for nome, cdf in all_series:
                try:
                    ck = kpis if cdf is df else calculate_kpis(cdf)
                except Exception as exc:
                    print(f"[report] KPIs do comparativo falharam para {nome}: {exc}", flush=True)
                    continue
                ct = ck.get("tensao_max_calc_MPa")
                if ct is None:
                    ct = ck.get("tensao_max_MPa")
                ca = ck.get("alonga_calc_pct")
                if ca is None:
                    ca = ck.get("alonga_ruptura_pct")
                cmp_rows.append((nome, _num(ck.get("forca_max_N"), ".1f"), _num(ct), _num(ck.get("modulo_elasticidade_MPa"), ".1f"),
                                 _num(ca), _num(ck.get("energia_J"))))
            if cmp_rows:
                tab_num += 1
                th = 'style="background:#1e3a5f;color:#fff;padding:6px 9px;border:1px solid #999"'
                td = 'style="border:1px solid #bbb;padding:5px 9px;text-align:right;font-family:monospace"'
                body_parts.append(
                    f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin:8px 0 4px">'
                    f'Tabela {tab_num} – Comparativo dos resultados.</p>'
                    f'<table style="width:90%;margin:0 auto 20px"><thead><tr>'
                    f'<th {th}>Ensaio</th><th {th}>Fmax (N)</th><th {th}>σmax (MPa)</th>'
                    f'<th {th}>E (MPa)</th><th {th}>Alongamento (%)</th><th {th}>Energia (J)</th>'
                    f'</tr></thead><tbody>'
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
            f'Tabela {tab_num} – Resultados do ensaio de Tração.</p>'
        )
        kpi_rows = []
        if area:
            kpi_rows.append(("Área da Seção Transversal (A)", _num(area, ".4f"), "mm²"))
        if l0:
            kpi_rows.append(("Comprimento Inicial (L₀)", _num(l0, ".2f"), "mm"))
        kpi_rows += [
            ("Módulo de Elasticidade (E)", _num(kpis.get("modulo_elasticidade_GPa"), ".3f"), "GPa"),
            ("Módulo de Elasticidade (E)", _num(kpis.get("modulo_elasticidade_MPa"), ".1f"), "MPa"),
        ]
        if kpis.get("tensao_escoamento_MPa") is not None:
            kpi_rows.append(("Tensão de Escoamento (est.)", _num(kpis["tensao_escoamento_MPa"]), "MPa"))
        kpi_rows += [
            ("Tensão Máxima (σmax = Fmax/A)" if kpis.get("tensao_max_calc_MPa") is not None else "Tensão Máxima (σmax)",
             _num(tensao_max), "MPa"),
            ("Força Máxima (Fmax)", _num(kpis.get("forca_max_N"), ".1f"), "N"),
            ("Força Máxima (Fmax)", _num(kpis.get("forca_max_kN"), ".4f"), "kN"),
            ("Alongamento (A% = d/L₀×100)" if kpis.get("alonga_calc_pct") is not None else "Alongamento (δ)",
             _num(alongamento), "%"),
            ("Deslocamento Máximo", _num(kpis.get("deslocamento_max_mm")), "mm"),
            ("Tempo até a Força Máxima", _num(kpis.get("tempo_ruptura_s"), ".1f"), "s"),
            ("Rigidez (k)", _num(kpis.get("rigidez_N_mm")), "N/mm"),
            ("Energia Absorvida até a Ruptura", _num(kpis.get("energia_J")), "J"),
            ("Taxa de Carregamento Média", _num(kpis.get("taxa_carregamento_N_s")), "N/s"),
        ]
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
            rows_html = ""
            for _, row in df.iterrows():
                rows_html += (
                    f"<tr>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px'>{_esc(row.get('TIME',''))}</td>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px'>{_esc(row.get('DATA',''))}</td>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px;text-align:right'>{_num(row.get('Tensao_Pa'))}</td>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px;text-align:right'>{_num((row.get('Deform_Along') or 0) * 100, '.3f')}</td>"
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
                f'<th style="background:#1e3a5f;color:#fff;padding:4px 6px;border:1px solid #999">σ (MPa)</th>'
                f'<th style="background:#1e3a5f;color:#fff;padding:4px 6px;border:1px solid #999">ε (%)</th>'
                f'<th style="background:#1e3a5f;color:#fff;padding:4px 6px;border:1px solid #999">F (N)</th>'
                f'<th style="background:#1e3a5f;color:#fff;padding:4px 6px;border:1px solid #999">d (mm)</th>'
                f'</tr></thead>'
                f'<tbody>{rows_html}</tbody>'
                f'</table>'
            )

    # ── SEÇÃO 5: CONCLUSÃO ────────────────────
    if req.include_conclusao:
        sec_num += 1
        body_parts.append(_section_header(sec_num, "Conclusão"))
        tab_num += 1
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
            f'<tbody>'
            f'<tr><td style="border:1px solid #bbb;padding:5px 9px;font-weight:bold">Módulo de Elasticidade</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px;text-align:right;font-family:monospace">{_num(kpis.get("modulo_elasticidade_GPa"), ".3f")}</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px">GPa</td></tr>'
            f'<tr><td style="border:1px solid #bbb;padding:5px 9px;font-weight:bold">Tensão Máxima</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px;text-align:right;font-family:monospace">{_num(tensao_max)}</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px">MPa</td></tr>'
            f'<tr><td style="border:1px solid #bbb;padding:5px 9px;font-weight:bold">Alongamento</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px;text-align:right;font-family:monospace">{_num(alongamento)}</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px">%</td></tr>'
            f'<tr><td style="border:1px solid #bbb;padding:5px 9px;font-weight:bold">Energia Absorvida</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px;text-align:right;font-family:monospace">{_num(kpis.get("energia_J"))}</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px">J</td></tr>'
            f'</tbody></table>'
        )

        local_data = req.local_data or _data_extenso(datetime.now())
        body_parts.append(
            f'<p style="text-align:right;margin:20px 0">{_esc(local_data)}</p>'
        )

        if req.assinaturas:
            sigs_html = "".join(
                f'<div style="text-align:center">'
                f'<div style="border-top:1px solid #333;width:180px;margin:0 auto 6px"></div>'
                f'<div style="font-weight:bold">{_esc(s.nome)}</div>'
                f'<div style="font-size:9.5pt">{_esc(s.cargo)}</div>'
                f'</div>'
                for s in req.assinaturas if s.nome
            )
            if sigs_html:
                body_parts.append(
                    f'<div style="display:flex;gap:80px;justify-content:center;margin-top:40px">'
                    f'{sigs_html}</div>'
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
