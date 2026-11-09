// Imprime o HTML do SDD em PDF A4 (Chromium do Playwright). Uso: node render.js entrada.html saida.pdf
const { chromium } = require('playwright');
(async () => {
  const [inp, out] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + require('path').resolve(inp), { waitUntil: 'networkidle' });
  await page.pdf({ path: out, format: 'A4', printBackground: true,
    margin: { top: '27mm', bottom: '35mm', left: '30mm', right: '30mm' } });
  await browser.close();
})();
