"""Gera o PDF do Manual de Cálculos com a identidade visual AUTOMATIC.

    python docs/calculos/gerar_pdf.py

Mesmo processo do SDD (docs/sdd/gerar_pdf.py): CALCULOS.md -> HTML (pandoc +
docs/sdd/estilo.css) -> PDF do corpo (Chromium) -> fundo de cada página
(moldura, logo, marca d'água, rodapé e paginação) com reportlab, mesclado por
baixo do corpo com pypdf.

O logo e a marca d'água ficam em docs/calculos/assets/ (PNGs não vão para o
git). Se não existirem, são extraídos do PDF do SDD que está em docs/.

Requer pandoc, Node com Playwright (Chromium), reportlab e pypdf.
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
DOCS = AQUI.parent
SDD = DOCS / "sdd"
ASSETS = AQUI / "assets"
SAIDA = DOCS / "Manual de Cálculos - Sistema de Ensaios.pdf"
DOC = "MC nº 01/26 — Rev. 00"
W, H = 595.32, 841.92

CSS_EXTRA = """
h2 { color: #1d2021; border-left: 3pt solid #f9bd00; padding-left: 6pt; }
li, p { text-align: left; }
"""


def _assets() -> None:
    """Garante logo.png e marca-dagua.png, tirando-os do PDF do SDD se faltarem."""
    if (ASSETS / "logo.png").exists() and (ASSETS / "marca-dagua.png").exists():
        return
    ASSETS.mkdir(exist_ok=True)
    for img in PdfReader(str(DOCS / "SDD - Sistema de Ensaios.pdf")).pages[0].images:
        nome = "logo.png" if img.image.size[0] < 200 else "marca-dagua.png"
        img.image.save(ASSETS / nome)


def _fonte() -> str:
    for p in ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "C:/Windows/Fonts/arial.ttf"):
        if Path(p).exists():
            pdfmetrics.registerFont(TTFont("Corpo", p))
            return "Corpo"
    return "Helvetica"


def _fundo(n: int, total: int, fonte: str) -> PdfReader:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(W, H))
    c.drawImage(str(ASSETS / "marca-dagua.png"), (W - 370) / 2, H - 400 - 82, 370, 164, mask="auto")
    c.setLineWidth(0.6)
    c.rect(24, 24, W - 48, H - 48)
    lw, lh = 34, 34 * 91 / 125
    c.drawImage(str(ASSETS / "logo.png"), (W - lw) / 2, H - 38 - lh, lw, lh, mask="auto")
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
    _assets()
    with tempfile.TemporaryDirectory() as tmp:
        corpo = subprocess.run(["pandoc", "-f", "gfm", "-t", "html5", str(AQUI / "CALCULOS.md")],
                               check=True, capture_output=True, text=True, encoding="utf-8").stdout
        css = (SDD / "estilo.css").read_text(encoding="utf-8") + CSS_EXTRA
        html = Path(tmp) / "calculos.html"
        html.write_text(f'<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
                        f'<title>Manual de Cálculos — Sistema de Ensaios</title><style>{css}</style></head>'
                        f'<body>{corpo}</body></html>', encoding="utf-8")
        pdf_corpo = Path(tmp) / "corpo.pdf"
        subprocess.run(["node", str(SDD / "render.js"), str(html), str(pdf_corpo)], check=True)

        leitor = PdfReader(str(pdf_corpo))
        fonte = _fonte()
        total = len(leitor.pages)
        out = PdfWriter()
        for i, pag in enumerate(leitor.pages, 1):
            base = _fundo(i, total, fonte).pages[0]
            base.merge_page(pag)
            out.add_page(base)
        out.add_metadata({"/Title": "Manual de Cálculos - Sistema de Ensaios de Tração e Flexão",
                          "/Author": "AUTOMATIC"})
        with open(SAIDA, "wb") as f:
            out.write(f)
    print(f"{SAIDA} ({total} páginas)")


if __name__ == "__main__":
    sys.exit(main())
