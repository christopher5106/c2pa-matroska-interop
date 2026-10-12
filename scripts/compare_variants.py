# For each check, count files where a variant is worse than its unsigned original.
import json, re, os, collections
VARS = ['A_end', 'A_end_noseek', 'A_front', 'B_tags', 'B_tags_end', 'C_unknown', 'D_void']
def split(name):
    n = os.path.basename(name)
    m = re.match(r'^(.*?)__([A-D]_[a-z_]+?)(_300k)?(\.webm|\.mkv)$', n)
    if not m or m.group(2) not in VARS: return None
    return m.group(1) + m.group(4), m.group(2)
def browser_ok(r):
    e, m = r.get('el', {}), r.get('mse', {})
    eo = e.get('loadedmetadata') == 'loadedmetadata' and (e.get('t_after_play') or 0) >= 1 and e.get('seeked') == 'seeked' and not e.get('error')
    mo = m.get('append') == 'updateend' and bool(m.get('buffered')) and (m.get('t_after_play') or 0) >= 1 and m.get('seeked') == 'seeked'
    return eo, mo
table = collections.OrderedDict()
def add(check, results, ok):
    base = {}
    for f, r in results.items():
        if split(f) is None: base[os.path.basename(f)] = ok(r)
    worse, total = collections.Counter(), collections.Counter()
    for f, r in results.items():
        s = split(f)
        if not s or s[0] not in base: continue
        b, v = base[s[0]], ok(r)
        total[s[1]] += 1
        if any(bb and not vv for bb, vv in zip(b, v)): worse[s[1]] += 1
    table[check] = (worse, total)
for br in ['chrome', 'chromium', 'firefox', 'webkit']:
    d = json.load(open(f'r2_{br}.json'))
    add(f"{br} {d['version']}", d['files'], browser_ok)
s = json.load(open('safari_safari.json'))
add(f"Safari {s['version']['browserVersion']}", s['files'], browser_ok)
v = json.load(open('vlccheck.json'))
add('VLC 3.0.24', v, lambda r: (r['play']['rc'] == 0 and not r['play']['err'], r['seek']['rc'] == 0))
f = json.load(open('ffcheck2.json'))
add('ffmpeg probe+decode', f, lambda r: (r['ffprobe_rc'] == 0, r['decode_rc'] == 0 and not r.get('decode_err')))
k = json.load(open('mkvcheck.json'))
add('mkvinfo / mkvmerge -J', k, lambda r: (r['mkvinfo_rc'] == 0 and not r['mkvinfo_msgs'], r['mkvmerge_J_rc'] == 0 and not r['J_errors']))
mv = json.load(open('mvcheck.json'))
basemsgs = {os.path.basename(f): set(r['std']['msgs']) for f, r in mv.items() if split(f) is None}
def mvok(f, r):
    s = split(f); b = basemsgs.get(s[0] if s else os.path.basename(f), set())
    return (not (set(r['std']['msgs']) - b),)
mvr = {f: dict(r, _f=f) for f, r in mv.items()}
add('mkvalidator (new messages)', mvr, lambda r: mvok(r['_f'], r))
show = ['A_end', 'A_end_noseek', 'A_front', 'B_tags', 'B_tags_end', 'C_unknown']
print(f"{'check':30}" + ''.join(f"{x:>14}" for x in show))
for c, (w, t) in table.items():
    print(f"{c:30}" + ''.join(f"{(str(w[x]) + '/' + str(t[x])) if t[x] else '-':>14}" for x in show))
