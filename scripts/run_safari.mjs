// Real Safari via safaridriver (W3C WebDriver over plain HTTP, no extra deps). Also runnable against Playwright WebKit with arg 'pwwebkit'.
import fs from 'node:fs';
import path from 'node:path';
const W = path.dirname(new URL(import.meta.url).pathname);
const mode = process.argv[2] || 'safari';
const BASE = 'http://127.0.0.1:8765';
const VARS = ['', '__A_end', '__A_end_noseek', '__B_tags_end', '__A_front'];
const SRC = [
  ['out2', 'ffx_vp9_opus', '.webm', 'video/webm; codecs="vp9,opus"'], ['out2', 'ffx_vp9_opus_cf', '.webm', 'video/webm; codecs="vp9,opus"'],
  ['out2', 'ffx_2audio', '.webm', 'video/webm; codecs="vp9,opus"'], ['out', 'vp9_alpha', '.webm', 'video/webm; codecs="vp9"'],
  ['out', 'av1_only', '.webm', 'video/webm; codecs="av01.0.00M.08"'], ['out', 'opus_only', '.webm', 'audio/webm; codecs="opus"'],
  ['out2', 'long1080_vp9_opus', '.webm', 'video/webm; codecs="vp9,opus"'], ['out2', 'mr_vp8_opusF', '.webm', 'video/webm; codecs="vp8,opus"'],
  ['out2', 'mr_vp9_opusF', '.webm', 'video/webm; codecs="vp9,opus"'], ['out', 'h264_aac', '.mkv', 'video/x-matroska; codecs="avc1.64000d,mp4a.40.2"'],
];
const jobs = [];
for (const [d, s, ext, mime] of SRC) for (const v of VARS) { const f = `${s}${v}${ext}`; if (fs.existsSync(path.join(W, d, f))) jobs.push({ d, f, mime, s }); }
let call, close, version;
if (mode === 'safari') {
  const D = 'http://127.0.0.1:4444';
  const req = async (method, p, body) => { const r = await fetch(D + p, { method, headers: { 'Content-Type': 'application/json' }, body: body ? JSON.stringify(body) : undefined }); return (await r.json()).value; };
  const sess = await req('POST', '/session', { capabilities: { alwaysMatch: { browserName: 'safari' } } });
  const sid = sess.sessionId; version = { browserVersion: sess.capabilities.browserVersion, platformVersion: sess.capabilities['safari:platformVersion'], build: sess.capabilities['safari:platformBuildVersion'] };
  await req('POST', `/session/${sid}/timeouts`, { script: 180000 });
  call = async (fn, args) => {
    await req('POST', `/session/${sid}/url`, { url: BASE + '/www/index.html' });
    const v = await req('POST', `/session/${sid}/execute/async`, { script: `const cb = arguments[arguments.length-1]; (${fn})(...arguments[0]).then(x => cb(JSON.stringify(x)), e => cb(JSON.stringify({exception: String(e)})));`, args: [args] });
    try { return JSON.parse(v); } catch { return { webdriver: v }; }
  };
  version.ua = await call('async () => navigator.userAgent', []);
  close = () => req('DELETE', `/session/${sid}`);
} else {
  const { webkit } = await import('playwright');
  const b = await webkit.launch(); const page = await b.newPage(); version = { browserVersion: b.version() };
  call = async (fn, args) => { await page.goto(BASE + '/www/index.html'); return JSON.parse(await page.evaluate(([f, a]) => eval(`(${f})`)(...a).then(x => JSON.stringify(x)), [fn, args])); };
  close = () => b.close();
}
const res = { mode, version, files: {} };
for (const j of jobs) {
  const url = `${BASE}/${j.d}/${j.f}`; const seek = j.s.startsWith('long') ? 115 : 7.5; const isAudio = j.s === 'opus_only'; const alpha = j.s === 'vp9_alpha';
  const el = await call('(u,m,a,al,s) => window.testElement(u,m,a,al,s)', [url, j.mime, isAudio, alpha, seek]);
  const mse = await call('(u,m,a,s) => window.testMSE2(u,m,a,s)', [url, j.mime, isAudio, seek]);
  res.files[j.f] = { el, mse };
  console.log(mode, j.f, JSON.stringify({ el, mse }).slice(0, 500));
}
fs.writeFileSync(path.join(W, `safari_${mode}.json`), JSON.stringify(res, null, 1));
await close();
