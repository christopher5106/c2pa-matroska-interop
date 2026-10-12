import subprocess, sys, os, json, glob
W = os.path.dirname(os.path.abspath(sys.argv[0]))
M = os.path.join(W, 'dl/MKVToolNix.app/Contents/MacOS')
OUT = os.path.join(W, 'out'); RMX = os.path.join(W, 'remux_mkvmerge'); os.makedirs(RMX, exist_ok=True)
P = {'': open(os.path.join(W, 'src/manifest.c2pa'), 'rb').read(), '300k': open(os.path.join(W, 'src/manifest_300k.c2pa'), 'rb').read()}

def run(a):
    r = subprocess.run(a, capture_output=True)
    return r.returncode, r.stdout.decode(errors='replace'), r.stderr.decode(errors='replace')

res = {}
for f in sorted(glob.glob(os.path.join(OUT, '*'))):
    n = os.path.basename(f); var = n.split('__')[1].rsplit('.', 1)[0] if '__' in n else 'baseline'
    pl = P['300k' if var.endswith('_300k') else '']
    r = {}
    rc, o, e = run([M + '/mkvinfo', '-v', f])
    r['mkvinfo_rc'] = rc
    r['mkvinfo_msgs'] = sorted({l.strip() for l in (o + e).splitlines() if 'rror' in l or 'arning' in l or 'nknown' in l or 'not' in l.lower() and 'note' not in l.lower()})[:6]
    rc, o, e = run([M + '/mkvmerge', '-J', f])
    j = json.loads(o)
    r['mkvmerge_J_rc'] = rc
    r['J_errors'] = j.get('errors', []) + j.get('warnings', [])
    r['J_attachments'] = [(a.get('file_name'), a.get('content_type'), a.get('size')) for a in j.get('attachments', [])]
    r['J_global_tags'] = j.get('global_tags')
    if var != 'baseline':
        r['remux'] = {}
        for mode, args, ext in (('mkv', [], 'mkv'), ('webm', ['--webm'], 'webm')):
            of = os.path.join(RMX, n.rsplit('.', 1)[0] + '.mkvmerge.' + ext)
            rc, o, e = run([M + '/mkvmerge'] + args + ['-o', of, f])
            msg = ' | '.join(l for l in o.splitlines() if l.startswith(('Warning', 'Error')))
            kept = os.path.exists(of) and pl in open(of, 'rb').read()
            r['remux'][mode] = ('KEPT' if kept else 'dropped') + (' rc=%d' % rc if rc else '') + ((' ' + msg) if msg else '')
    res[n] = r
json.dump(res, open(os.path.join(W, 'mkvcheck.json'), 'w'), indent=1)
for n, r in res.items():
    print(n, json.dumps(r)[:600])
