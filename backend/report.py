from __future__ import annotations

from datetime import datetime

import pandas as pd


def generate_html_report(ensaio, df: pd.DataFrame, kpis: dict, req) -> str:
    now = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    sections: list[str] = []

    if req.include_metadata:
        sections.append(f"""
        <section>
            <h2>Identificação do Ensaio</h2>
            <table class="meta">
                <tr><td>Arquivo</td><td>{ensaio.filename}</td></tr>
                <tr><td>Data do Ensaio</td><td>{ensaio.data_ensaio}</td></tr>
                <tr><td>Equipamento</td><td>{ensaio.metadata_equipment_id}</td></tr>
                <tr><td>Código Interno</td><td>{ensaio.metadata_code}</td></tr>
                <tr><td>Versão Protocolo</td><td>{ensaio.metadata_version}</td></tr>
                <tr><td>Total de Amostras</td><td>{ensaio.num_amostras}</td></tr>
                <tr><td>Operador</td><td>{req.operator_name or "—"}</td></tr>
                <tr><td>Corpo de Prova / Material</td><td>{req.specimen_id or "—"}</td></tr>
                <tr><td>Norma Aplicada</td><td>{req.standard or "—"}</td></tr>
            </table>
        </section>""")

    if req.include_kpis:
        yield_row = (
            f'<tr><td>Tensão de Escoamento (est.)</td>'
            f'<td>{kpis["tensao_escoamento_MPa"]:.2f}</td><td>MPa</td></tr>'
            if kpis.get("tensao_escoamento_MPa") is not None
            else ""
        )
        sections.append(f"""
        <section>
            <h2>Resultados — KPIs</h2>
            <table class="kpi">
                <thead><tr><th>Parâmetro</th><th>Valor</th><th>Unidade</th></tr></thead>
                <tbody>
                <tr><td>Força Máxima (Fmax)</td><td>{kpis["forca_max_N"]:.2f}</td><td>N</td></tr>
                <tr><td>Força Máxima (Fmax)</td><td>{kpis["forca_max_kN"]:.4f}</td><td>kN</td></tr>
                <tr><td>Tensão Máxima (σmax)</td><td>{kpis["tensao_max_MPa"]:.2f}</td><td>MPa</td></tr>
                <tr><td>Módulo de Elasticidade (E)</td><td>{kpis["modulo_elasticidade_MPa"]:.2f}</td><td>MPa</td></tr>
                <tr><td>Módulo de Elasticidade (E)</td><td>{kpis["modulo_elasticidade_GPa"]:.5f}</td><td>GPa</td></tr>
                <tr><td>Alongamento na Ruptura (δ)</td><td>{kpis["alonga_ruptura_pct"]:.2f}</td><td>%</td></tr>
                <tr><td>Deslocamento Máximo</td><td>{kpis["deslocamento_max_mm"]:.2f}</td><td>mm</td></tr>
                <tr><td>Tempo até a Ruptura</td><td>{kpis["tempo_ruptura_s"]:.1f}</td><td>s</td></tr>
                <tr><td>Taxa de Carregamento Média</td><td>{kpis["taxa_carregamento_N_s"]:.2f}</td><td>N/s</td></tr>
                <tr><td>Rigidez (k)</td><td>{kpis["rigidez_N_mm"]:.2f}</td><td>N/mm</td></tr>
                <tr><td>Energia Absorvida até Ruptura</td><td>{kpis["energia_J"]:.2f}</td><td>J</td></tr>
                {yield_row}
                <tr><td>CV do Módulo (fase elástica)</td><td>{kpis["cv_modulo"]:.4f}</td><td>—</td></tr>
                </tbody>
            </table>
        </section>""")

    if req.include_raw_data:
        rows_html = ""
        for _, row in df.iterrows():
            fase_label = {"carregamento": "C", "ruptura": "R", "pos_ruptura": "P"}.get(
                row.get("fase", ""), ""
            )
            rows_html += (
                f"<tr>"
                f"<td>{row.get('TIME','')}</td>"
                f"<td>{row.get('DATA','')}</td>"
                f"<td>{row.get('Tensao_Pa', 0):.2f}</td>"
                f"<td>{row.get('Modulo_Elast', 0):.2f}</td>"
                f"<td>{row.get('Tensao_Max', 0):.2f}</td>"
                f"<td>{row.get('Deform_Along', 0):.3f}</td>"
                f"<td>{row.get('Alonga_Ruptura', 0):.2f}</td>"
                f"<td>{row.get('Deslocamento', 0):.2f}</td>"
                f"<td>{row.get('Forca_N', 0):.2f}</td>"
                f"<td>{fase_label}</td>"
                f"</tr>\n"
            )
        sections.append(f"""
        <section>
            <h2>Dados Brutos</h2>
            <table class="data">
                <thead>
                    <tr>
                        <th>Hora</th><th>Data</th><th>σ (MPa)</th><th>E (MPa)</th>
                        <th>σmax (MPa)</th><th>ε</th><th>δ (%)</th>
                        <th>d (mm)</th><th>F (N)</th><th>Fase</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </section>""")

    if req.observations:
        sections.append(f"""
        <section>
            <h2>Observações</h2>
            <p class="obs">{req.observations}</p>
        </section>""")

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<title>Relatório — {ensaio.nome}</title>
<style>
  *{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:Arial,sans-serif;font-size:11pt;line-height:1.5;
        color:#1a1a1a;padding:2cm}}
  h1{{color:#003366;font-size:18pt;border-bottom:2px solid #003366;
      padding-bottom:8px;margin-bottom:16px}}
  h2{{color:#003366;font-size:13pt;margin:24px 0 10px;
      border-left:4px solid #003366;padding-left:8px}}
  table{{width:100%;border-collapse:collapse;margin:8px 0;font-size:10pt}}
  th{{background:#003366;color:#fff;padding:6px 10px;text-align:left}}
  td{{border:1px solid #ccc;padding:5px 10px}}
  tr:nth-child(even){{background:#f5f7fa}}
  table.meta td:first-child{{font-weight:bold;width:220px;background:#eef2ff}}
  table.kpi td:nth-child(2){{text-align:right;font-family:monospace}}
  table.data{{font-size:8.5pt}}
  .obs{{background:#fffbe6;border-left:4px solid #f59e0b;
        padding:10px 14px;margin-top:6px;border-radius:2px}}
  .footer{{margin-top:30px;border-top:1px solid #ccc;padding-top:10px;
           font-size:9pt;color:#666;text-align:center}}
  @media print{{body{{padding:1cm}}}}
</style>
</head>
<body>
<h1>Relatório de Ensaio de Tração</h1>
<p style="margin-bottom:6px">
  <strong>Ensaio:</strong> {ensaio.nome} &nbsp;|&nbsp;
  <strong>Gerado em:</strong> {now}
</p>
{"".join(sections)}
<div class="footer">
  Relatório gerado pelo Sistema de Análise de Ensaios de Tração
</div>
</body>
</html>"""
