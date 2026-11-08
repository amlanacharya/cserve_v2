const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
  const [src, out] = process.argv.slice(2);
  const browser = await puppeteer.launch({ headless: 'new', args: ['--no-sandbox'] });
  const page = await browser.newPage();
  await page.goto('file:///' + path.resolve(src).replace(/\\/g, '/'), { waitUntil: 'networkidle0', timeout: 60000 });
  await page.waitForFunction(() => document.body.dataset.ready === '1', { timeout: 30000 }).catch(() => {});
  await page.pdf({
    path: out, format: 'A4', printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate: '<div style="font-size:8px;width:100%;text-align:center;color:#64748b;font-family:Arial">Amlan Acharya - CloudServe Support Orchestrator Capstone Report - page <span class="pageNumber"></span> of <span class="totalPages"></span></div>',
    margin: { top: '24mm', bottom: '24mm', left: '22mm', right: '22mm' },
  });
  await browser.close();
})().catch((e) => { console.error(e); process.exit(1); });
