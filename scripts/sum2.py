import json, os, sys, glob, collections
W = os.path.dirname(os.path.abspath(sys.argv[0]))
B = {json.load(open(f))['browser']: json.load(open(f)) for f in glob.glob(os.path.join(W, 'r2_*.json'))}
print({k: v['version'] for k, v in B.items()})
def st(f): return 115 if f.startswith('long') else 7.5
def chk(f, r, isbase):
    e, m = r.get('el', {}), r.get('mse', {})
    ei, mi = [], []
    if e.get('loadedmetadata') != 'loadedmetadata': ei.append('no metadata ' + str(e.get('error')))
    else:
        if (e.get('t_after_play') or 0) < 1: ei.append('no progress t=%s' % e.get('t_after_play'))
        if e.get('seeked') != 'seeked' or abs((e.get('t_after_seek') or 0) - st(f)) > 0.2: ei.append('seek %s t=%s' % (e.get('seeked'), e.get('t_after_seek')))
        if e.get('duration') == 0: ei.append('duration 0')
        if e.get('error'): ei.append(e['error'])
    if not m.get('isTypeSupported'): mi.append('n/a')
    else:
        if m.get('error'): mi.append(m['error'])
        if m.get('append') != 'updateend': mi.append('append=' + str(m.get('append')))
        if not m.get('buffered'): mi.append('buffered=[]')
        if (m.get('t_after_play') or 0) < 0.5: mi.append('no playback')
        if m.get('seeked') != 'seeked': mi.append('seek ' + str(m.get('seeked')))
        for x in (m.get('elError'), m.get('elError2')):
            if x and x not in mi: mi.append(x)
    return ('ok' if not ei else '; '.join(ei)), ('ok' if not mi else '; '.join(mi)), [l for l in r.get('medialog', []) if 'error' in l][:2]
for br in sorted(B):
    print('\n###', br)
    for f, r in sorted(B[br]['files'].items()):
        e, m, lg = chk(f, r, '__' not in f)
        print('  %-40s el=%s | mse=%s %s' % (f, e, m, ('| ' + ' / '.join(lg)) if lg and (e != 'ok' or m != 'ok') else ''))
