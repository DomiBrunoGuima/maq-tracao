"""Relatório HTML: numeração, valores ausentes e comparativo."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.acquisition import build_ensaio_dataframe
from backend.calculator import calculate_kpis
from backend.models import ReportRequest
from backend.report import generate_html_report


def _df(area=50.0, l0=100.0, peak=3000.0):
    samples = [
        {"forca": peak * i / 60 if i < 60 else peak - 20 * (i - 60),
         "deslocamento": 0.1 * i, "elapsed_seconds": 0.1 * i}
        for i in range(100)
    ]
    return build_ensaio_dataframe(samples, area, l0)[1]


def _req(**kw):
    base = dict(ensaio_id=1, include_graficos_adicionais=True, include_comparativo=True,
                amostra={"id_interno": "A1", "imagem_data_url": "data:image/png;base64,AAA"})
    base.update(kw)
    return ReportRequest(**base)


def test_figuras_e_tabelas_numeradas_em_sequencia():
    df = _df()
    html = generate_html_report(SimpleNamespace(nome="CP1"), df, calculate_kpis(df), _req(),
                                comparacao_series=[("CP2", _df(peak=2500.0))])
    figs = [int(n) for n in re.findall(r"<p[^>]*>Figura (\d+) –", html)]
    tabs = [int(n) for n in re.findall(r"<p[^>]*>Tabela (\d+) –", html)]
    assert figs == list(range(1, len(figs) + 1)) and len(figs) == 5
    assert tabs == list(range(1, len(tabs) + 1))


def test_kpi_ausente_nao_quebra_relatorio():
    df = _df()
    kpis = calculate_kpis(df)
    kpis["tensao_escoamento_MPa"] = None
    kpis["energia_J"] = None
    kpis["modulo_elasticidade_GPa"] = float("nan")
    html = generate_html_report(SimpleNamespace(nome="CP1"), df, kpis, _req(include_comparativo=False))
    assert ">nan<" not in html.lower()
    assert "—" in html


def test_aviso_unidades_cruas_sem_area_l0():
    df = _df(area=0, l0=0)
    html = generate_html_report(SimpleNamespace(nome="CP1"), df, calculate_kpis(df), _req())
    assert "unidades cruas" in html


def test_energia_em_joules():
    df = _df()
    # triângulo até 3000 N em 6 mm + descida até 2220 N em 9.9 mm ≈ 9 J + 10 J
    assert 15 < calculate_kpis(df)["energia_J"] < 25
