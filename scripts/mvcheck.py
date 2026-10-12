import subprocess, sys, os, glob, re, json
W = os.path.dirname(os.path.abspath(sys.argv[0]))
MV = os.path.join(W, 'build/fs-build/mkvalidator/pkg_bin/mkvalidator')
res = {}
for d in ('out', 'out2'):
    for f in sorted(glob.glob(os.path.join(W, d, '*'))):
        n = os.path.basename(f); r = {}
        for mode, args in (('std', ['--quiet']), ('live', ['--quiet', '--live'])):
            p = subprocess.run([MV] + args + [f], capture_output=True, timeout=300)
            txt = (p.stdout + p.stderr).decode(errors='replace')
            msgs = sorted({re.sub(r' at \d+', '', m).strip() for m in re.findall(r'((?:ERR|WRN)[0-9A-F]+:[^\n]*)', txt)})
            r[mode] = {'rc': p.returncode, 'msgs': msgs}
        res[d + '/' + n] = r
json.dump(res, open(os.path.join(W, 'mvcheck.json'), 'w'), indent=1)
# diff vs baseline
for k, r in res.items():
    d, n = k.split('/')
    base = n.split('__')[0]
    bk = next((x for x in res if x.split('/')[1].startswith(base + '.') and x.split('/')[0] == d), None)
    if bk is None: continue
    extra = {m: sorted(set(r[m]['msgs']) - set(res[bk][m]['msgs'])) for m in ('std', 'live')}
    if k == bk: print('BASE', k, r['std']['rc'], r['std']['msgs'], '| live', r['live']['msgs'])
    elif extra['std'] or extra['live']: print('  ', k, 'extra std:', extra['std'], '| extra live:', extra['live'])
    else: print('  ', k, 'same as baseline')
