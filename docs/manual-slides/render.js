const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + process.cwd() + '/novas.html'); await p.waitForTimeout(800);
  await p.pdf({ path: 'novas.pdf', printBackground: true, preferCSSPageSize: true });
  // overflow check
  const o = await p.$$eval('.page', ps => ps.map((pg,i)=>{const r=pg.getBoundingClientRect(); let maxb=0; pg.querySelectorAll('*').forEach(e=>{ if(e.closest('.foot')) return; const b=e.getBoundingClientRect().bottom-r.top; if(b>maxb) maxb=b;}); return [i, Math.round(maxb)];}));
  console.log(JSON.stringify(o));
  await b.close();
})();
