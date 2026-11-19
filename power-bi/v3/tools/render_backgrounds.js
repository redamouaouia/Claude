// node render_backgrounds.js <in.html> <out.png> [<in.html> <out.png> ...]
// Renders 1280x720 HTML pages at 2x (2560x1440) for Power BI page backgrounds.
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 2 });
  const args = process.argv.slice(2);
  for (let i = 0; i < args.length; i += 2) {
    await page.setContent(fs.readFileSync(args[i], 'utf8'), { waitUntil: 'networkidle', timeout: 30000 }).catch(() => {});
    await page.evaluate(() => document.fonts.ready);
    const fonts = await page.evaluate(() => [...document.fonts].filter(f => f.status === 'loaded').map(f => f.family + ' ' + f.weight));
    await page.screenshot({ path: args[i + 1], clip: { x: 0, y: 0, width: 1280, height: 720 } });
    console.log(`rendered ${args[i + 1]}  fonts: ${[...new Set(fonts)].join(', ') || 'fallback only'}`);
  }
  await browser.close();
})();
