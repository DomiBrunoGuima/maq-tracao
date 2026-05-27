from __future__ import annotations

import base64
import io
from datetime import datetime

import pandas as pd


# ──────────────────────────────────────────────
# Chart generation
# ──────────────────────────────────────────────

def _chart_stress_strain_b64(df: pd.DataFrame) -> str:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return ""

    fig, ax = plt.subplots(figsize=(8, 4.8))

    x = df["Deform_Along"].values * 100   # dimensionless → %
    y = df["Tensao_Pa"].values             # já em MPa

    ax.plot(x, y, color="#1e3a5f", linewidth=1.8, label="Tensão")

    rup_idx = int(df["Forca_N"].idxmax())
    ax.scatter([x[rup_idx]], [y[rup_idx]], color="#c0392b", s=60, zorder=5,
               label=f"Ruptura  {y[rup_idx]:.1f} MPa / {x[rup_idx]:.2f}%")

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
    return base64.b64encode(buf.read()).decode("utf-8")


def _chart_force_displacement_b64(df: pd.DataFrame) -> str:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return ""

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


# ──────────────────────────────────────────────
# HTML helpers
# ──────────────────────────────────────────────

def _esc(v) -> str:
    return str(v).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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
        f'<h2 style="font-size:12pt;font-weight:bold;margin:28px 0 10px;'
        f'text-transform:uppercase;letter-spacing:0.5px;'
        f'border-bottom:1px solid #ccc;padding-bottom:6px">'
        f'{num}&nbsp;&nbsp;{_esc(title)}</h2>'
    )


def _figure(img_src: str, caption: str) -> str:
    return (
        f'<div style="text-align:center;margin:14px 0 20px">'
        f'<img src="{img_src}" alt="{_esc(caption)}" '
        f'style="max-width:75%;border:1px solid #ddd;padding:2px"/>'
        f'<p style="font-style:italic;font-size:9pt;margin-top:6px">{_esc(caption)}</p>'
        f'</div>'
    )


_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: Arial, sans-serif; font-size: 10.5pt; color: #1a1a1a;
       line-height: 1.5; background: #fff; }
.page { max-width: 21cm; margin: 0 auto; padding: 2cm 2.5cm 2.5cm; }
table { border-collapse: collapse; }
p { margin: 6px 0; }
@media print {
  .page { padding: 1.5cm 2cm; }
  .page-break { page-break-before: always; }
}
"""


# ──────────────────────────────────────────────
# Main function
# ──────────────────────────────────────────────

def generate_html_report(ensaio, df: pd.DataFrame, kpis: dict, req) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    body_parts: list[str] = []
    sec_num = 0

    # ── HEADER ────────────────────────────────
    logo_html = ""
    if req.include_empresa and req.empresa.logo_data_url:
        logo_html = (
            f'<img src="{req.empresa.logo_data_url}" alt="Logo" '
            f'style="max-height:55px;max-width:130px;object-fit:contain"/>'
        )

    empresa_nome = req.empresa.nome if req.include_empresa and req.empresa.nome else "Relatório de Ensaio de Tração"
    numero_rel = req.empresa.numero_relatorio if req.include_empresa else ""

    empresa_endereco = ""
    if req.include_empresa and req.empresa.endereco:
        parts = [req.empresa.endereco]
        if req.empresa.telefone: parts.append(f"Tel. {req.empresa.telefone}")
        if req.empresa.email:    parts.append(f"E-mail {req.empresa.email}")
        if req.empresa.site:     parts.append(req.empresa.site)
        empresa_endereco = " &nbsp;|&nbsp; ".join(parts)

    header_html = f"""
    <div style="display:flex;align-items:flex-start;justify-content:space-between;
                margin-bottom:16px;padding-bottom:12px;border-bottom:2px solid #1e3a5f">
      <div style="min-width:110px">{logo_html}</div>
      <div style="text-align:center;flex:1">
        <div style="font-size:13pt;font-weight:bold">Relatório de Ensaio</div>
        {"<div style='font-size:12pt;font-weight:bold'>" + _esc(numero_rel) + "</div>" if numero_rel else ""}
      </div>
      <div style="text-align:right;font-size:8pt;color:#444;min-width:200px;line-height:1.7">
        {_esc(empresa_nome)}<br/>
        {empresa_endereco}
      </div>
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
            f'<tr><td style="padding:3px 0">{i+1}&nbsp;&nbsp;{_esc(t)}</td></tr>'
            for i, t in enumerate(toc_items)
        )
        body_parts.append(
            f'<div style="margin:20px 0">'
            f'<div style="font-weight:bold;margin-bottom:8px">SUMÁRIO</div>'
            f'<table style="width:100%;font-size:10pt">{toc_rows}</table>'
            f'</div>'
        )

    # ── SEÇÃO 1: IDENTIFICAÇÃO DA AMOSTRA ─────
    if req.include_amostra:
        sec_num += 1
        body_parts.append(_section_header(sec_num, "Identificação da(s) Amostra(s)"))
        a = req.amostra
        if a.id_interno or a.id_cliente:
            body_parts.append(
                f'<p style="margin-bottom:8px">A amostra foi identificada conforme a Tabela {sec_num}.</p>'
                f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin-bottom:4px">'
                f'Tabela {sec_num} – Identificação da(s) Amostra(s).</p>'
                f'<table style="width:60%;margin:0 auto 16px">'
                f'<tr><th style="background:#1e3a5f;color:#fff;padding:6px 12px;border:1px solid #999">Identificação Interna</th>'
                f'<th style="background:#1e3a5f;color:#fff;padding:6px 12px;border:1px solid #999">Identificação do Cliente</th></tr>'
                f'<tr><td style="text-align:center;padding:6px 12px;border:1px solid #bbb">{_esc(a.id_interno)}</td>'
                f'<td style="text-align:center;padding:6px 12px;border:1px solid #bbb">{_esc(a.id_cliente)}</td></tr>'
                f'</table>'
            )
        if a.imagem_data_url:
            body_parts.append(_figure(a.imagem_data_url, f"Figura 1 – Imagem da Amostra{': ' + a.id_interno if a.id_interno else ''}."))

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
        body_parts.append(
            f'<p style="margin-bottom:8px">Na Tabela {sec_num} estão apresentadas as condições do ensaio.</p>'
            f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin-bottom:4px">'
            f'Tabela {sec_num} – Condições do ensaio de Tração.</p>'
        )
        rows = []
        if c.temp_laboratorio or c.umidade_laboratorio:
            rows.append(_td2("Temperatura do Laboratório:", f"{c.temp_laboratorio} °C" if c.temp_laboratorio else "—",
                             "Umidade do Laboratório:", f"{c.umidade_laboratorio} %" if c.umidade_laboratorio else "—"))
        if c.temp_ensaio or c.num_corpos_prova:
            rows.append(_td2("Temperatura do Ensaio:", c.temp_ensaio or "—",
                             "Número de Corpos de Prova:", c.num_corpos_prova or "—"))
        if c.celula_carga or c.comprimento_inicial_mm:
            rows.append(_td2("Célula de Carga:", c.celula_carga or "—",
                             "Comprimento Inicial (L₀):", f"{c.comprimento_inicial_mm} mm" if c.comprimento_inicial_mm else "—"))
        if c.velocidade_ensaio or c.tipo_corpo_prova:
            rows.append(_td2("Velocidade do Ensaio:", c.velocidade_ensaio or "—",
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

    # ── SEÇÃO 4: RESULTADOS ───────────────────
    if req.include_resultados:
        sec_num += 1
        body_parts.append(_section_header(sec_num, "Resultados"))
        fig_num = 1

        if req.include_stress_strain:
            chart_b64 = _chart_stress_strain_b64(df)
            if chart_b64:
                body_parts.append(
                    f'<p style="margin-bottom:8px">Na Figura {fig_num} estão apresentadas as curvas de tensão em função da deformação.</p>'
                )
                body_parts.append(_figure(
                    f"data:image/png;base64,{chart_b64}",
                    f"Figura {fig_num} – Curva Tensão × Deformação — {ensaio.nome}."
                ))
                fig_num += 1

        if req.include_graficos_adicionais:
            chart2 = _chart_force_displacement_b64(df)
            if chart2:
                body_parts.append(_figure(
                    f"data:image/png;base64,{chart2}",
                    f"Figura {fig_num} – Curva Força × Deslocamento — {ensaio.nome}."
                ))
                fig_num += 1

        if req.include_resultados:
            res_table_num = sec_num
            body_parts.append(
                f'<p style="margin-bottom:8px">Na Tabela {res_table_num} estão apresentados os resultados do ensaio.</p>'
                f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin-bottom:4px">'
                f'Tabela {res_table_num} – Resultados do ensaio de Tração.</p>'
            )
            kpi_rows = [
                ("Módulo de Elasticidade", f'{kpis["modulo_elasticidade_GPa"]:.3f}', "GPa"),
                ("Módulo de Elasticidade", f'{kpis["modulo_elasticidade_MPa"]:.1f}', "MPa"),
                ("Tensão Máxima (σmax)", f'{kpis["tensao_max_MPa"]:.2f}', "MPa"),
                ("Força Máxima (Fmax)", f'{kpis["forca_max_N"]:.1f}', "N"),
                ("Força Máxima (Fmax)", f'{kpis["forca_max_kN"]:.4f}', "kN"),
                ("Alongamento na Ruptura (δ)", f'{kpis["alonga_ruptura_pct"]:.2f}', "%"),
                ("Deslocamento Máximo", f'{kpis["deslocamento_max_mm"]:.2f}', "mm"),
                ("Tempo até a Ruptura", f'{kpis["tempo_ruptura_s"]:.1f}', "s"),
                ("Rigidez (k)", f'{kpis["rigidez_N_mm"]:.2f}', "N/mm"),
                ("Energia Absorvida até Ruptura", f'{kpis["energia_J"]:.2f}', "J"),
                ("Taxa de Carregamento Média", f'{kpis["taxa_carregamento_N_s"]:.2f}', "N/s"),
            ]
            if kpis.get("tensao_escoamento_MPa") is not None:
                kpi_rows.insert(2, ("Tensão de Escoamento (est.)", f'{kpis["tensao_escoamento_MPa"]:.2f}', "MPa"))
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
                    f"<td style='border:1px solid #ddd;padding:3px 6px'>{row.get('TIME','')}</td>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px'>{row.get('DATA','')}</td>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px;text-align:right'>{row.get('Tensao_Pa', 0):.2f}</td>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px;text-align:right'>{row.get('Deform_Along', 0)*100:.3f}</td>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px;text-align:right'>{row.get('Forca_N', 0):.2f}</td>"
                    f"<td style='border:1px solid #ddd;padding:3px 6px;text-align:right'>{row.get('Deslocamento', 0):.2f}</td>"
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
        body_parts.append(
            f'<p style="margin-bottom:8px">Na Tabela {sec_num} está apresentado um resumo dos resultados obtidos.</p>'
            f'<p style="text-align:center;font-style:italic;font-size:9.5pt;margin-bottom:4px">'
            f'Tabela {sec_num} – Resumo dos Resultados.</p>'
            f'<table style="width:65%;margin:0 auto 20px">'
            f'<thead><tr>'
            f'<th style="background:#1e3a5f;color:#fff;padding:6px 9px;border:1px solid #999">Propriedade</th>'
            f'<th style="background:#1e3a5f;color:#fff;padding:6px 9px;border:1px solid #999">Valor</th>'
            f'<th style="background:#1e3a5f;color:#fff;padding:6px 9px;border:1px solid #999">Unidade</th>'
            f'</tr></thead>'
            f'<tbody>'
            f'<tr><td style="border:1px solid #bbb;padding:5px 9px;font-weight:bold">Módulo de Elasticidade</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px;text-align:right;font-family:monospace">{kpis["modulo_elasticidade_GPa"]:.3f}</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px">GPa</td></tr>'
            f'<tr><td style="border:1px solid #bbb;padding:5px 9px;font-weight:bold">Tensão Máxima</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px;text-align:right;font-family:monospace">{kpis["tensao_max_MPa"]:.2f}</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px">MPa</td></tr>'
            f'<tr><td style="border:1px solid #bbb;padding:5px 9px;font-weight:bold">Alongamento na Ruptura</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px;text-align:right;font-family:monospace">{kpis["alonga_ruptura_pct"]:.2f}</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px">%</td></tr>'
            f'<tr><td style="border:1px solid #bbb;padding:5px 9px;font-weight:bold">Energia Absorvida</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px;text-align:right;font-family:monospace">{kpis["energia_J"]:.2f}</td>'
            f'<td style="border:1px solid #bbb;padding:5px 9px">J</td></tr>'
            f'</tbody></table>'
        )

        local_data = req.local_data or datetime.now().strftime(f"%d de %B de %Y").lower()
        local_data = local_data.replace("january","janeiro").replace("february","fevereiro") \
            .replace("march","março").replace("april","abril").replace("may","maio") \
            .replace("june","junho").replace("july","julho").replace("august","agosto") \
            .replace("september","setembro").replace("october","outubro") \
            .replace("november","novembro").replace("december","dezembro")
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
        body_parts.append(
            f'<div style="margin-top:30px;border-top:1px solid #ccc;padding-top:16px">'
            f'<div style="font-weight:bold;margin-bottom:8px">Observações Finais</div>'
        )
        for line in req.observacoes_finais.splitlines():
            if line.strip():
                body_parts.append(f'<p style="margin:4px 0">— {_esc(line.strip())}</p>')
        body_parts.append(
            f'<p style="text-align:center;margin-top:20px;font-weight:bold">— Fim do Relatório —</p>'
            f'</div>'
        )

    # ── FOOTER ────────────────────────────────
    footer_parts = [empresa_nome]
    if req.include_empresa:
        if req.empresa.endereco: footer_parts.append(req.empresa.endereco)
        if req.empresa.telefone: footer_parts.append(f"Tel. {req.empresa.telefone}")
        if req.empresa.email:    footer_parts.append(f"E-mail {req.empresa.email}")
    footer_line = " &nbsp;|&nbsp; ".join(footer_parts)
    body_parts.append(
        f'<div style="margin-top:40px;border-top:1px solid #ccc;padding-top:8px;'
        f'font-size:8pt;text-align:center;color:#666">'
        f'{footer_line}<br/>'
        f'<span style="font-size:7.5pt">Gerado em {now}</span>'
        f'</div>'
    )

    return f"""<!DOCTYPE html>
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
