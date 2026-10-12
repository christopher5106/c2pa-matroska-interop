// usage: node run2.mjs <chromium|chrome|firefox|webkit> DIR [filter]
import { chromium, firefox, webkit } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
const W = path.dirname(new URL(import.meta.url).pathname);
const [which, dir, filter = ''] = process.argv.slice(2);
const BASE = 'http://127.0.0.1:8765';
const mimeFor = f => f.startsWith('mr_vp8') ? 'video/webm; codecs="vp8,opus"' : 'video/webm; codecs="vp9,opus"';
const seekFor = f => f.startsWith('long') ? 115 : 7.5;
const launchers = {
  chromium: () => chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] }),
  chrome: () => chromium.launch({ channel: 'chrome', args: ['--autoplay-policy=no-user-gesture-required'] }),
  firefox: () => firefox.launch({ firefoxUserPrefs: { 'media.autoplay.default': 0, 'media.autoplay.blocking_policy': 0 } }),
  webkit: () => webkit.launch(),
};
const browser = await launchers[which]();
const files = fs.readdirSync(path.join(W, dir)).filter(f => f.endsWith('.webm') && f.includes(filter)).sort();
const results = { browser: which, version: browser.version(), files: {} };
for (const f of files) {
  const page = await browser.newPage();
  const logs = [];
  if (which === 'chromium' || which === 'chrome') {
    const cdp = await page.context().newCDPSession(page);
    cdp.on('Media.playerMessagesLogged', e => e.messages.forEach(m => { if (m.level === 'error' || m.level === 'warning') logs.push(`${m.level}: ${m.message}`); }));
    await cdp.send('Media.enable');
  }
  await page.goto(BASE + '/www/index.html');
  const url = `${BASE}/${dir}/${f}`; const r = {};
  try { r.el = await page.evaluate(([u, m, s]) => window.testElement(u, m, false, false, s), [url, mimeFor(f), seekFor(f)]); } catch (e) { r.el = { exception: String(e).slice(0, 300) }; }
  try { r.mse = await page.evaluate(([u, m, s]) => window.testMSE(u, m, false, s), [url, mimeFor(f), seekFor(f)]); } catch (e) { r.mse = { exception: String(e).slice(0, 300) }; }
  r.medialog = [...new Set(logs)];
  results.files[f] = r;
  console.log(which, f, JSON.stringify(r).slice(0, 600));
  await page.close();
}
fs.writeFileSync(path.join(W, `r2_${which}${filter ? '_' + filter : ''}.json`), JSON.stringify(results, null, 1));
await browser.close();
