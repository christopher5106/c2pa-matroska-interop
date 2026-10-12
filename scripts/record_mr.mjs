// Record ~10 s canvas+oscillator with Chromium MediaRecorder. usage: node record_mr.mjs OUTDIR
import { chromium } from 'playwright';
import fs from 'node:fs';
import path from 'node:path';
const out = process.argv[2];
const browser = await chromium.launch({ args: ['--autoplay-policy=no-user-gesture-required'] });
const page = await browser.newPage();
await page.goto('http://127.0.0.1:8765/www/index.html');
for (const [name, mime] of [['mr_vp8_opus', 'video/webm;codecs=vp8,opus'], ['mr_vp9_opus', 'video/webm;codecs=vp9,opus']]) {
  const b64 = await page.evaluate(async (mime) => {
    const c = document.createElement('canvas'); c.width = 320; c.height = 240; document.body.appendChild(c);
    const g = c.getContext('2d');
    let n = 0; const t0 = performance.now();
    const iv = setInterval(() => {
      const t = (performance.now() - t0) / 1000;
      g.fillStyle = `hsl(${(t * 36) % 360},70%,50%)`; g.fillRect(0, 0, 320, 240);
      g.fillStyle = '#fff'; g.font = '40px sans-serif'; g.fillText(t.toFixed(2), 80, 130);
      g.fillRect((t * 30) % 320, 200, 20, 20); n++;
    }, 33);
    const ac = new AudioContext(); const osc = ac.createOscillator(); osc.frequency.value = 440;
    const dst = ac.createMediaStreamDestination(); osc.connect(dst); osc.start();
    const stream = new MediaStream([...c.captureStream(30).getVideoTracks(), ...dst.stream.getAudioTracks()]);
    const rec = new MediaRecorder(stream, { mimeType: mime, videoBitsPerSecond: 500000 });
    const chunks = []; rec.ondataavailable = e => chunks.push(e.data);
    const done = new Promise(r => rec.onstop = r);
    rec.start(1000);
    await new Promise(r => setTimeout(r, 10000));
    rec.stop(); await done; clearInterval(iv); osc.stop(); await ac.close(); c.remove();
    const blob = new Blob(chunks, { type: mime });
    const buf = new Uint8Array(await blob.arrayBuffer());
    let s = ''; for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
    return btoa(s);
  }, mime);
  fs.writeFileSync(path.join(out, name + '.webm'), Buffer.from(b64, 'base64'));
  console.log(name, Buffer.from(b64, 'base64').length);
}
console.log('chromium', browser.version());
await browser.close();
