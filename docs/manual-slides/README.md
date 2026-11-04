# Manual completo em slides

Gera `docs/Manual completo - Sistema de Ensaios.pdf` no mesmo formato da
apresentação (`docs/Apresentacao e Manual - Sistema de Ensaios.pdf`).

- Páginas 2, 3 e 6–18 e a última vêm direto da apresentação.
- A capa é a da apresentação com subtítulo e versão trocados.
- As páginas 4, 5 e 19–40 estão em `novas.html` (prints em `img/`, tirados com o simulador).

Para gerar de novo (precisa de Node com Playwright, PyMuPDF e a fonte Inter instalada):

```bash
cd docs/manual-slides
node render.js                     # novas.html -> novas.pdf
python montar.py "../Manual completo - Sistema de Ensaios.pdf"
```

Se mudar o número de páginas novas, ajuste a lista `nums` no fim de `novas.html` e as faixas em `montar.py`.
O texto completo também está em `docs/MANUAL.md`.
