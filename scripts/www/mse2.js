// Chunked MSE / ManagedMediaSource test. window.testMSE2(url, mime, isAudio, seekTo)
window.testMSE2 = async (url, mime, isAudio, seekTo = 7.5) => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const r = { api: null };
  const MS = window.MediaSource || window.ManagedMediaSource;
  r.api = window.MediaSource ? 'MediaSource' : (window.ManagedMediaSource ? 'ManagedMediaSource' : 'none');
  r.hasMMS = !!window.ManagedMediaSource;
  if (!MS) return r;
  r.isTypeSupported = MS.isTypeSupported(mime);
  if (!r.isTypeSupported) return r;
  const buf = new Uint8Array(await (await fetch(url)).arrayBuffer());
  const el = document.createElement(isAudio ? 'audio' : 'video'); el.muted = true; el.disableRemotePlayback = true; document.body.appendChild(el);
  const ms = new MS();
  const so = new Promise(res => ms.addEventListener('sourceopen', () => res('open'), { once: true }));
  el.src = URL.createObjectURL(ms);
  const s = await Promise.race([so, sleep(5000).then(() => 'timeout')]);
  if (s !== 'open') { r.error = 'sourceopen ' + s; return r; }
  let sb; try { sb = ms.addSourceBuffer(mime); } catch (e) { r.error = 'addSourceBuffer: ' + e.message; return r; }
  let sbErr = null; sb.addEventListener('error', () => { sbErr = 'SourceBuffer error event'; });
  const CH = 1 << 20; r.chunks = 0; r.quota = null;
  const upd = () => new Promise(res => { sb.addEventListener('updateend', () => res('updateend'), { once: true }); sb.addEventListener('error', () => res('error'), { once: true }); setTimeout(() => res('timeout'), 20000); });
  for (let o = 0; o < buf.length; o += CH) {
    let ok = false;
    for (let tries = 0; tries < 2 && !ok; tries++) {
      try { const p = upd(); sb.appendBuffer(buf.subarray(o, o + CH)); const x = await p; if (x !== 'updateend') { r.append = x + ' at chunk ' + r.chunks; break; } ok = true; }
      catch (e) { r.quota = e.name + ': ' + e.message + ' at byte ' + o; await sleep(200); }
    }
    if (!ok) break;
    r.chunks++;
  }
  if (!r.append) r.append = 'updateend';
  r.sbErr = sbErr;
  try { const b = sb.buffered; r.buffered = Array.from({ length: b.length }, (_, i) => [+b.start(i).toFixed(3), +b.end(i).toFixed(3)]); } catch (e) { r.buffered = 'threw ' + e.message; }
  r.readyState = ms.readyState;
  if (ms.readyState === 'open' && !sb.updating && r.append === 'updateend' && !r.quota) { try { ms.endOfStream(); } catch (e) { r.eos = e.message; } }
  try { await Promise.race([el.play(), sleep(3000).then(() => { throw new Error('play() timeout'); })]); r.play = 'ok'; } catch (e) { r.play = 'rejected: ' + e.message; }
  await sleep(1500); r.t_after_play = el.currentTime;
  el.currentTime = seekTo;
  r.seeked = await Promise.race([new Promise(res => el.addEventListener('seeked', () => res('seeked'), { once: true })), sleep(5000).then(() => 'timeout')]);
  r.t_after_seek = el.currentTime;
  r.elError = el.error ? `MediaError code=${el.error.code} msg=${JSON.stringify(el.error.message)}` : null;
  el.remove();
  return r;
};
