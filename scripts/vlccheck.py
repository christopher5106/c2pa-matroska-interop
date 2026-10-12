import subprocess, sys, os, glob, re, json
from concurrent.futures import ThreadPoolExecutor
W = os.path.dirname(os.path.abspath(sys.argv[0]))
VLC = os.path.join(W, 'dl/vlc/VLC.app/Contents/MacOS/VLC')
KEEP = ('', 'A_end', 'A_end_noseek', 'A_front', 'B_tags_end', 'C_unknown', 'U_A_append', 'U_B_append', 'U_C_append')
files = []
for d in ('out', 'out2'):
    for f in sorted(glob.glob(os.path.join(W, d, '*'))):
        n = os.path.basename(f); v = n.split('__')[1].rsplit('.', 1)[0] if '__' in n else ''
        if v in KEEP: files.append(f)
def run(f, start):
    a = [VLC, '-I', 'dummy', '--vout', 'dummy', '--aout', 'dummy', '--no-video-title-show', '--play-and-exit', '-vv']
    a += ['--start-time', str(start), '--run-time', '1.5'] if start else ['--run-time', '2']
    p = subprocess.run(a + [f], capture_output=True, timeout=60)
    t = (p.stdout + p.stderr).decode(errors='replace')
    lines = t.splitlines()
    err = sorted({re.sub(r'0x[0-9a-f]+', '', l)[:200] for l in lines if (' error:' in l or (' warning:' in l and 'libvlc' not in l)) and 'auhal' not in l and 'macosx' not in l.lower()})
    mkv = sorted({re.sub(r'0x[0-9a-f]+', '', l)[:200] for l in lines if 'mkv' in l and ('ttach' in l or 'c2pa' in l.lower() or 'Dummy' in l or 'm_el' in l)})
    dec = [l for l in lines if 'using decoder module' in l or 'using packetizer' in l]
    return {'rc': p.returncode, 'err': err, 'mkv': mkv, 'decoders': sorted({re.sub(r'.*using ', '', l) for l in dec})}
def job(f):
    n = os.path.relpath(f, W); start = 115 if 'long1080' in n else 7.5
    return n, {'play': run(f, 0), 'seek': run(f, start)}
with ThreadPoolExecutor(6) as ex: res = dict(ex.map(job, files))
json.dump(res, open(os.path.join(W, 'vlccheck.json'), 'w'), indent=1)
print(len(res))
