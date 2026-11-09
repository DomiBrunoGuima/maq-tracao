"""Gera o PDF do SDD com a identidade visual AUTOMATIC.

    python docs/sdd/gerar_pdf.py

Requer pandoc, Node com Playwright (Chromium), reportlab e pypdf.
Passos: SDD.md -> HTML (pandoc + estilo.css) -> PDF do corpo (Chromium) ->
fundo de cada página (moldura, logo, marca d'água, rodapé e paginação) com
reportlab, mesclado por baixo do corpo com pypdf.
"""
from __future__ import annotations

import io
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

AQUI = Path(__file__).resolve().parent
SAIDA = AQUI.parent / "SDD - Sistema de Ensaios.pdf"
DOC = "SDD nº 01/26 — Rev. 00"
W, H = 595.32, 841.92


def _fonte() -> str:
    for p in ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "C:/Windows/Fonts/arial.ttf"):
        if Path(p).exists():
            pdfmetrics.registerFont(TTFont("Corpo", p))
            return "Corpo"
    return "Helvetica"


def _fundo(n: int, total: int, fonte: str) -> PdfReader:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))
    # marca d'água
    c.drawImage(str(AQUI / "assets/marca-dagua.png"), (W - 370) / 2, H - 400 - 82, 370, 164, mask="auto")
    # moldura
    c.setLineWidth(0.6)
    c.rect(24, 24, W - 48, H - 48)
    # logo
    lw, lh = 34, 34 * 91 / 125
    c.drawImage(str(AQUI / "assets/logo.png"), (W - lw) / 2, H - 38 - lh, lw, lh, mask="auto")
    # rodapé
    c.setFillColor(HexColor("#a6a6a6"))
    c.setFont(fonte, 7.4)
    linhas = ["AUTOMATIC",
              "Rua Alto Paraguai, 236 CEP – 02238-240 Jardim Brasil (Zona Norte), São Paulo – SP- Brasil",
              "Telefone: (11) 2240-3099", "CNPJ – 47.503.132/0001-08"]
    for i, t in enumerate(linhas):
        c.drawString(85, H - 767 - i * 8.6, t)
    c.drawRightString(W - 85, H - 805, f"{DOC}   |   Página {n} de {total}")
    c.save()
    buf.seek(0)
    return PdfReader(buf)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        corpo = subprocess.run(["pandoc", "-f", "gfm", "-t", "html5", str(AQUI / "SDD.md")],
                               check=True, capture_output=True, text=True).stdout
        css = (AQUI / "estilo.css").read_text(encoding="utf-8")
        html = Path(tmp) / "sdd.html"
        html.write_text(f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
                        f'<title>SDD — Sistema de Ensaios</title><style>{css}</style></head>'
                        f'<body>{corpo}</body></html>', encoding="utf-8")
        pdf_corpo = Path(tmp) / "corpo.pdf"
        subprocess.run(["node", str(AQUI / "render.js"), str(html), str(pdf_corpo)], check=True)

        leitor = PdfReader(str(pdf_corpo))
        fonte = _fonte()
        total = len(leitor.pages)
        out = PdfWriter()
        for i, pag in enumerate(leitor.pages, 1):
            base = _fundo(i, total, fonte).pages[0]
            base.merge_page(pag)
            out.add_page(base)
        out.add_metadata({"/Title": "SDD - Sistema de Ensaios de Tração e Flexão", "/Author": "AUTOMATIC"})
        with open(SAIDA, "wb") as f:
            out.write(f)
    print(f"{SAIDA} ({total} páginas)")


if __name__ == "__main__":
    sys.exit(main())
