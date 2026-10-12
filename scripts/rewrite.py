"""Produce C2PA embedding variants of a WebM/Matroska file.
usage: rewrite.py SRC PAYLOAD OUTDIR TAG   (TAG '-' for none)"""
import sys, os, zlib, hashlib
sys.path.insert(0, os.path.dirname(os.path.abspath(sys.argv[0])))
from ebml import *

SEEKHEAD, VOID, CLUSTER, CUES, TAGS, ATTACH, CRC = 0x114D9B74, 0xEC, 0x1F43B675, 0x1C53BB6B, 0x1254C367, 0x1941A469, 0xBF
UNKNOWN_ID = 0x1C2B5041   # 4-byte class-D ID, not in RFC 9559 / IANA Matroska element registry


def crc_le(payload):
    return (zlib.crc32(payload) & 0xffffffff).to_bytes(4, 'little')


def master(i, child_bytes, with_crc):
    if with_crc:
        child_bytes = b'\xBF\x84' + crc_le(child_bytes) + child_bytes
    return el(i, child_bytes)


def first_is_crc(b, e):
    k = children(b, e.data_off, e.end)
    return bool(k) and k[0].id == CRC


def rewrite_children(b, e, leaf_fn):
    """Re-encode master e; leaf_fn(id, raw_payload)->payload for leaves; recompute CRC-32 if present."""
    kids = children(b, e.data_off, e.end)
    had_crc = bool(kids) and kids[0].id == CRC
    out = b''
    for c in kids:
        if c.id == CRC:
            continue
        if c.id in MASTERS:
            out += rewrite_children(b, c, leaf_fn)
        else:
            out += el(c.id, leaf_fn(c.id, b[c.data_off:c.end]))
    return master(e.id, out, had_crc)


class Item:
    def __init__(s, kind, eid, old=None, data=None):
        s.kind, s.id, s.old, s.data, s.off = kind, eid, old, data, None


def build(b, seg, kids, inserts, seek_add, tag_merge=None):
    """inserts: list of (position, Item), position 'end' or 'before_cluster'.
    seek_add: Items to add SeekHead entries for. tag_merge: Tag element bytes appended into existing Tags."""
    rel0 = seg.data_off
    items = [Item('raw', k.id, k) for k in kids]
    sh = next(it for it in items if it.id == SEEKHEAD)
    has_crc = first_is_crc(b, sh.old)
    for pos, it in inserts:
        if pos == 'end':
            items.append(it)
        else:
            idx = next(i for i, x in enumerate(items) if x.id == CLUSTER)
            items.insert(idx, it)
    old2item = {it.old.off - rel0: it for it in items if it.old is not None}
    shi = items.index(sh)
    void_after = items[shi + 1] if shi + 1 < len(items) and items[shi + 1].id == VOID else None
    reserved = (sh.old.end - sh.old.off) + ((void_after.old.end - void_after.old.off) if void_after else 0)
    seeks = []
    for s in children(b, sh.old.data_off, sh.old.end):
        if s.id != 0x4DBB:
            continue
        cs = {c.id: c for c in children(b, s.data_off, s.end)}
        seeks.append((get_uint(b, cs[0x53AB]), old2item[get_uint(b, cs[0x53AC])]))
    for it in seek_add:
        seeks.append((it.id, it))
    if tag_merge is not None:
        t = next(it for it in items if it.id == TAGS)
        kk = children(b, t.old.data_off, t.old.end)
        body = b''.join(b[c.off:c.end] for c in kk if c.id != CRC) + tag_merge
        t.kind, t.data = 'bytes', master(TAGS, body, bool(kk) and kk[0].id == CRC)
    for it in items:
        if it.kind == 'raw':
            it.data = b[it.old.off:it.old.end]
    void_status = 'n/a'
    for _ in range(30):
        o = 0
        for it in items:
            it.off = o
            o += len(it.data)
        body = b''.join(el(0x4DBB, el(0x53AB, enc_id(tid)) + el(0x53AC, enc_uint(it.off))) for tid, it in seeks)
        newsh = master(SEEKHEAD, body, has_crc)
        newdata = {}
        for it in items:
            if it.id == CUES and it.old is not None:
                def fix(cid, pl):
                    if cid == 0xF1 or (cid == 0xEA and int.from_bytes(pl, 'big')):
                        return enc_uint(old2item[int.from_bytes(pl, 'big')].off)
                    return pl
                newdata[it] = rewrite_children(b, it.old, fix)
        changed = False
        if void_after is not None:
            rest = reserved - len(newsh)
            if rest == 0 or rest >= 2:
                ov = b[void_after.old.off:void_after.old.end]
                vd = ov if rest == len(ov) else (void(rest) if rest else b'')
                void_status = 'reserved Void %d->%d bytes' % (void_after.old.end - void_after.old.off, len(vd))
            else:
                vd = b''
                void_status = 'Void removed, SeekHead grew (shift)'
            if vd != void_after.data:
                void_after.data = vd
                changed = True
        if newsh != sh.data:
            sh.data = newsh
            changed = True
        for it, d in newdata.items():
            if d != it.data:
                it.data = d
                changed = True
        if not changed:
            break
    else:
        raise RuntimeError('layout did not converge')
    seg_payload = b''.join(it.data for it in items)
    seg_hdr = enc_id(0x18538067) + enc_size(len(seg_payload), seg.hlen - 4)
    return b[:seg.off] + seg_hdr + seg_payload, void_status


def attachments(payload, crc):
    uid = int.from_bytes(hashlib.sha256(payload).digest()[:8], 'big') | 1
    af = (el(0x466E, b'content_credential.c2pa') + el(0x4660, b'application/c2pa') +
          el(0x465C, payload) + el(0x46AE, enc_uint(uid)))
    return master(ATTACH, el(0x61A7, af), crc)


def tag_elem(payload):
    st = el(0x45A3, b'C2PA_MANIFEST') + el(0x4485, payload)
    return el(0x7373, el(0x63C0, b'') + el(0x67C8, st))


def validate(data, p):
    h2, s2, k2 = parse_file(data)  # full recursive well-formedness check
    assert data.count(p) >= 1, 'payload missing'
    starts = {k.off - s2.data_off: k.id for k in k2}
    shk = next(k for k in k2 if k.id == SEEKHEAD)
    for s in children(data, shk.data_off, shk.end):
        if s.id != 0x4DBB:
            continue
        cs = {c.id: c for c in children(data, s.data_off, s.end)}
        tid, pos = get_uint(data, cs[0x53AB]), get_uint(data, cs[0x53AC])
        assert starts.get(pos) == tid, ('bad seek', hex(tid), pos)
    cu = next((k for k in k2 if k.id == CUES), None)
    ncue = 0
    for cp in (children(data, cu.data_off, cu.end) if cu else []):
        if cp.id != 0xBB:
            continue
        for tp in children(data, cp.data_off, cp.end):
            if tp.id == 0xB7:
                for x in children(data, tp.data_off, tp.end):
                    if x.id == 0xF1:
                        assert starts.get(get_uint(data, x)) == CLUSTER, 'bad cue'
                        ncue += 1
    for k in k2:
        if k.id in MASTERS:
            cc = children(data, k.data_off, k.end)
            if cc and cc[0].id == CRC:
                assert data[cc[0].data_off:cc[0].end] == crc_le(data[cc[0].end:k.end]), 'crc mismatch %X' % k.id
    return ncue


def main():
    src, pfile, outdir, tag = sys.argv[1:5]
    b = open(src, 'rb').read()
    p = open(pfile, 'rb').read()
    hdr, seg, kids = parse_file(b)
    crc = first_is_crc(b, next(k for k in kids if k.id == SEEKHEAD))
    base, ext = os.path.splitext(os.path.basename(src))

    def A():
        return Item('bytes', ATTACH, data=attachments(p, crc))
    v = {}
    a = A(); v['A_end'] = build(b, seg, kids, [('end', a)], [a])
    a = A(); v['A_end_noseek'] = build(b, seg, kids, [('end', a)], [])
    a = A(); v['A_front'] = build(b, seg, kids, [('before_cluster', a)], [a])
    if any(k.id == TAGS for k in kids): v['B_tags'] = build(b, seg, kids, [], [], tag_merge=tag_elem(p))
    t = Item('bytes', TAGS, data=master(TAGS, tag_elem(p), crc)); v['B_tags_end'] = build(b, seg, kids, [('end', t)], [t])
    v['C_unknown'] = build(b, seg, kids, [('end', Item('bytes', UNKNOWN_ID, data=el(UNKNOWN_ID, p)))], [])
    v['D_void'] = build(b, seg, kids, [('end', Item('bytes', VOID, data=el(VOID, p)))], [])
    for name, (data, vs) in v.items():
        out = os.path.join(outdir, '%s__%s%s%s' % (base, name, '' if tag == '-' else '_' + tag, ext))
        ncue = validate(data, p)
        open(out, 'wb').write(data)
        print('%-44s %8d cues=%d  %s' % (os.path.basename(out), len(data), ncue, vs))


main()
