"""ffprobe / full decode / framemd5 / remux checks for every file in out/."""
import subprocess, sys, os, json, glob, re, hashlib
W = os.path.dirname(os.path.abspath(sys.argv[0]))
OUT = os.path.join(W, 'out2'); RMX = os.path.join(W, 'remux2'); os.makedirs(RMX, exist_ok=True)
FF, FP = '/opt/homebrew/bin/ffmpeg', '/opt/homebrew/bin/ffprobe'
P = {'': open(os.path.join(W, 'src/manifest.c2pa'), 'rb').read(), '300k': open(os.path.join(W, 'src/manifest_300k.c2pa'), 'rb').read()}

def run(a):
    r = subprocess.run(a, capture_output=True)
    return r.returncode, r.stdout.decode(errors='replace'), r.stderr.decode(errors='replace').strip()

def framemd5(f):
    rc, o, e = run([FF, '-v', 'error', '-i', f, '-map', '0:v?', '-map', '0:a?', '-f', 'framemd5', '-'])
    lines = [l for l in o.splitlines() if not l.startswith('#')]
    return hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:16], len(lines), e

res = {}
files = [f for f in sorted(glob.glob(os.path.join(OUT, '*'))) if not ('long1080' in f and '__' in f and not any(x in f for x in ('__A_end.', '__B_tags_end.', '__A_end_300k.')))]
bases = {}
for f in files:
    n = os.path.basename(f)
    base = n.split('__')[0].split('.')[0]
    var = n.split('__')[1].rsplit('.', 1)[0] if '__' in n else 'baseline'
    tag = '300k' if var.endswith('_300k') else ''
    pl = P[tag]
    r = {'file': n}
    rc, o, e = run([FP, '-v', 'error', '-show_streams', '-show_format', '-of', 'json', f])
    r['ffprobe_rc'], r['ffprobe_err'] = rc, e
    j = json.loads(o) if o else {}
    r['streams'] = [(s.get('codec_type'), s.get('codec_name'), s.get('tags', {}).get('mimetype'), s.get('tags', {}).get('filename')) for s in j.get('streams', [])]
    r['format_tags'] = sorted(j.get('format', {}).get('tags', {}).keys())
    r['duration'] = j.get('format', {}).get('duration')
    rc, o, e = run([FF, '-v', 'error', '-i', f, '-f', 'null', '-'])
    r['decode_rc'], r['decode_err'] = rc, e
    rc, o, e = run([FF, '-v', 'warning', '-i', f, '-f', 'null', '-'])
    r['decode_warn'] = e
    h, nfr, e = framemd5(f)
    r['framemd5'], r['frames'] = h, nfr
    if var == 'baseline':
        bases[base] = h
    # seek decode test: decode from 7.5 s
    rc, o, e = run([FF, '-v', 'error', '-ss', '7.5', '-i', f, '-f', 'null', '-'])
    r['seek_decode_rc'], r['seek_err'] = rc, e
    if var != 'baseline':
        r['remux'] = {}
        for ext in ('webm', 'mkv'):
            for mapping in (['-map', '0'], []):
                key = ext + ('_map0' if mapping else '_default')
                of = os.path.join(RMX, n.rsplit('.', 1)[0] + '.' + key + '.' + ext)
                rc, o, e = run([FF, '-v', 'error', '-y', '-i', f] + mapping + ['-c', 'copy', of])
                kept = os.path.exists(of) and rc == 0 and pl in open(of, 'rb').read()
                r['remux'][key] = ('KEPT' if kept else ('FAIL rc=%d %s' % (rc, e.splitlines()[-1] if e else '') if rc else 'dropped'))
    res[n] = r
for n, r in res.items():
    b = n.split('__')[0].split('.')[0]
    r['frames_identical'] = (r['framemd5'] == bases.get(b))
json.dump(res, open(os.path.join(W, 'ffcheck2.json'), 'w'), indent=1)
for n, r in res.items():
    print(n, '| probe_rc', r['ffprobe_rc'], repr(r['ffprobe_err'][:120]), '| dec', r['decode_rc'], repr(r['decode_warn'][:160]),
          '| seek', r['seek_decode_rc'], '| md5==base', r['frames_identical'], r['frames'], '| streams', [s for s in r['streams'] if s[0] not in ('video', 'audio')],
          '| remux', r.get('remux'))
