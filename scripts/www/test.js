// In-page test functions. window.testElement(url, mime, isAudio, alpha) / window.testMSE(url, mime, isAudio)
const sleep = ms => new Promise(r => setTimeout(r, ms));
function waitEv(el, ok, ms) {
  return new Promise(res => {
    let done = false;
    const fin = v => { if (!done) { done = true; res(v); } };
    el.addEventListener(ok, () => fin(ok), { once: true });
    el.addEventListener('error', () => fin('error'), { once: true });
    setTimeout(() => fin('timeout'), ms);
  });
}
function mediaErr(el) { return el.error ? `MediaError code=${el.error.code} msg=${JSON.stringify(el.error.message)}` : null; }
function alphaAt(el) {
  const c = document.createElement('canvas'); c.width = el.videoWidth; c.height = el.videoHeight;
  const g = c.getContext('2d'); g.drawImage(el, 0, 0);
  const a = (x, y) => Array.from(g.getImageData(x, y, 1, 1).data);
  return { left_mid: a(40, 120), right_bottom: a(280, 230) };
}
window.testElement = async (url, mime, isAudio, alpha, seekTo = 7.5) => {
  const r = { canPlayType: null, events: [] };
  const el = document.createElement(isAudio ? 'audio' : 'video');
  r.canPlayType = el.canPlayType(mime);
  el.muted = true; el.preload = 'auto'; el.playsInline = true;
  document.body.appendChild(el);
  el.src = url;
  const lm = await waitEv(el, 'loadedmetadata', 10000);
  r.loadedmetadata = lm;
  if (lm !== 'loadedmetadata') { r.error = mediaErr(el) || lm; el.remove(); return r; }
  r.duration = el.duration; r.w = el.videoWidth; r.h = el.videoHeight;
  try { await Promise.race([el.play(), sleep(3000).then(() => { throw new Error('play() timeout'); })]); r.play = 'ok'; }
  catch (e) { r.play = 'rejected: ' + e.message; }
  await sleep(2000);
  r.t_after_play = el.currentTime;
  el.pause();
  el.currentTime = seekTo;
  const sk = await waitEv(el, 'seeked', 6000);
  r.seeked = sk; r.t_after_seek = el.currentTime;
  if (alpha && !isAudio) {
    await sleep(300);
    try { r.alpha = alphaAt(el); } catch (e) { r.alpha = 'canvas error: ' + e.message; }
  }
  r.error = mediaErr(el);
  el.remove();
  return r;
};
window.testMSE = async (url, mime, isAudio, seekTo = 7.5) => {
  const r = {};
  if (!window.MediaSource) { r.supported = 'no MediaSource'; return r; }
  r.isTypeSupported = MediaSource.isTypeSupported(mime);
  if (!r.isTypeSupported) return r;
  const buf = await (await fetch(url)).arrayBuffer();
  const el = document.createElement(isAudio ? 'audio' : 'video'); el.muted = true; document.body.appendChild(el);
  const ms = new MediaSource();
  el.src = URL.createObjectURL(ms);
  const so = await waitEv(ms, 'sourceopen', 5000);
  if (so !== 'sourceopen') { r.error = 'sourceopen ' + so; return r; }
  let sb;
  try { sb = ms.addSourceBuffer(mime); } catch (e) { r.error = 'addSourceBuffer: ' + e.message; return r; }
  let sbErr = null;
  sb.addEventListener('error', () => { sbErr = 'SourceBuffer error event'; });
  try { sb.appendBuffer(buf); } catch (e) { r.error = 'appendBuffer threw: ' + e.message; return r; }
  r.append = await waitEv(sb, "updateend", 60000);
  r.sbErr = sbErr;
  r.elError = mediaErr(el);
  try { const b = sb.buffered; r.buffered = Array.from({ length: b.length }, (_, i) => [+b.start(i).toFixed(3), +b.end(i).toFixed(3)]); }
  catch (e) { r.buffered = 'threw: ' + e.message; }
  r.readyState = ms.readyState;
  if (ms.readyState === 'open' && !sb.updating) { try { ms.endOfStream(); } catch (e) { r.eos = e.message; } }
  try { await Promise.race([el.play(), sleep(3000).then(() => { throw new Error('play() timeout'); })]); r.play = 'ok'; }
  catch (e) { r.play = 'rejected: ' + e.message; }
  await sleep(1500);
  r.t_after_play = el.currentTime;
  el.currentTime = seekTo;
  r.seeked = await waitEv(el, 'seeked', 5000); r.t_after_seek = el.currentTime;
  r.elError2 = mediaErr(el);
  el.remove();
  return r;
};
