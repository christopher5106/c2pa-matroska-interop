"""Handle unknown-size Segment/Cluster WebM (MediaRecorder output).
usage: mr_tool.py SRC PAYLOAD OUTDIR  -> writes U_* (append to unknown-size Segment) and <name>F.webm (finalized baseline)"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
from ebml import *
LEVEL1 = {0x114D9B74, 0x1549A966, 0x1654AE6B, 0x1F43B675, 0x1C53BB6B, 0x1941A469, 0x1043A770, 0x1254C367}

def lenient(b):
    o = 0; i, il = read_vint(b, o, True); sz, sl = read_vint(b, o + il)
    hdr_end = o + il + sl + sz
    i, il = read_vint(b, hdr_end, True); assert i == 0x18538067
    ssz, sl = read_vint(b, hdr_end + il)
    seg_data = hdr_end + il + sl
    seg_end = len(b) if ssz is None else seg_data + ssz
    kids = []; o = seg_data
    while o < seg_end:
        i, il = read_vint(b, o, True); sz, sl = read_vint(b, o + il)
        d = o + il + sl
        if sz is None:
            c = d
            while c < seg_end:
                ci, cil = read_vint(b, c, True)
                if ci in LEVEL1: break
                csz, csl = read_vint(b, c + cil); c += cil + csl + csz
            end = c; unknown = True
        else:
            end = d + sz; unknown = False
        kids.append((i, o, d, end, unknown)); o = end
    assert o == seg_end, (o, seg_end)
    return hdr_end, ssz is None, kids

def main():
    src, pfile, outdir = sys.argv[1:4]
    b = open(src, 'rb').read(); p = open(pfile, 'rb').read()
    hdr_end, seg_unknown, kids = lenient(b)
    base = os.path.splitext(os.path.basename(src))[0]
    print(base, 'segment unknown size:', seg_unknown, 'top-level:', [('%X' % k[0], 'unk' if k[4] else 'known') for k in kids][:4], '... n=%d' % len(kids))
    att = el(0x1941A469, el(0x61A7, el(0x466E, b'content_credential.c2pa') + el(0x4660, b'application/c2pa') + el(0x465C, p) + el(0x46AE, b'\x01\x02\x03\x04\x05\x06\x07\x08')))
    tags = el(0x1254C367, el(0x7373, el(0x63C0, b'') + el(0x67C8, el(0x45A3, b'C2PA_MANIFEST') + el(0x4485, p))))
    unk = el(0x1C2B5041, p)
    for name, extra in (('U_A_append', att), ('U_B_append', tags), ('U_C_append', unk)):
        open(os.path.join(outdir, '%s__%s.webm' % (base, name)), 'wb').write(b + extra)
    # finalize: known sizes everywhere, SeekHead(Info,Tracks) + Void reserve in front
    body = []
    for i, o, d, end, unknown in kids:
        body.append((i, el(i, b[d:end]) if unknown else b[o:end]))
    RES = 128
    def layout():
        offs = {}; pos = RES
        for i, x in body:
            offs.setdefault(i, pos); pos += len(x)
        sh = el(0x114D9B74, b''.join(el(0x4DBB, el(0x53AB, enc_id(i)) + el(0x53AC, enc_uint(offs[i]))) for i in (0x1549A966, 0x1654AE6B)))
        return sh + void(RES - len(sh)) + b''.join(x for _, x in body)
    payload = layout()
    out = b[:hdr_end] + enc_id(0x18538067) + enc_size(len(payload), 8) + payload
    parse_file(out)
    fn = os.path.join(outdir, base + 'F.webm'); open(fn, 'wb').write(out); print('finalized ->', fn, len(out))
main()
