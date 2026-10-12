"""Minimal EBML/Matroska reader/writer (no deps)."""
import struct, zlib

def read_vint(b, o, is_id=False):
    first = b[o]
    if first == 0: raise ValueError('invalid vint at %d' % o)
    l = 1; m = 0x80
    while not (first & m): l += 1; m >>= 1
    if is_id:
        return int.from_bytes(b[o:o+l], 'big'), l
    v = first & (m - 1)
    for i in range(1, l): v = (v << 8) | b[o+i]
    unknown = (v == (1 << (7*l)) - 1)
    return (None if unknown else v), l

def enc_id(i):
    n = (i.bit_length() + 7) // 8
    return i.to_bytes(n, 'big')

def enc_size(v, length=None):
    if length is None:
        length = 1
        while v >= (1 << (7*length)) - 1: length += 1
    assert v < (1 << (7*length)) - 1
    return ((1 << (7*length)) | v).to_bytes(length, 'big') if length < 8 else (b'\x01' + v.to_bytes(7, 'big'))

def enc_uint(v):
    n = max(1, (v.bit_length() + 7) // 8)
    return v.to_bytes(n, 'big')

def el(i, payload):
    return enc_id(i) + enc_size(len(payload)) + payload

def void(total):
    """Void element of exactly `total` bytes."""
    if total < 2: raise ValueError('void too small')
    if total - 2 < 127: return b'\xEC' + enc_size(total - 2, 1) + b'\0'*(total-2)
    return b'\xEC' + enc_size(total - 9, 8) + b'\0'*(total-9)

class E:
    __slots__ = ('id','hlen','size','off','data_off','raw')
    def __init__(s, i, hlen, size, off): s.id, s.hlen, s.size, s.off = i, hlen, size, off; s.data_off = off+hlen
    @property
    def end(s): return s.data_off + s.size
    def __repr__(s): return 'E(%X @%d h%d s%s)' % (s.id, s.off, s.hlen, s.size)

def children(b, start, end):
    out = []; o = start
    while o < end:
        i, il = read_vint(b, o, True)
        sz, sl = read_vint(b, o+il)
        e = E(i, il+sl, sz, o)
        if sz is None: raise ValueError('unknown-size child at %d' % o)
        if e.end > end: raise ValueError('child %r overruns parent end %d' % (e, end))
        out.append(e); o = e.end
    if o != end: raise ValueError('children misaligned')
    return out

MASTERS = {0x1A45DFA3,0x18538067,0x114D9B74,0x4DBB,0x1549A966,0x1654AE6B,0xAE,0xE0,0xE1,0x6D80,0x6240,0x5034,0x5035,
           0x1F43B675,0xA0,0x75A1,0xA6,0x8E,0xE8,0x1C53BB6B,0xBB,0xB7,0xDB,0x1941A469,0x61A7,0x1043A770,0x45B9,0xB6,0x80,
           0x1254C367,0x7373,0x63C0,0x67C8,0x5854,0x7E5B,0x7E7B,0x6924,0x69BF,0x6944,0x7670,0x7671,0x55B0,0x55D0,0x5370,0x8F,0x41E4,0x41F0}

def parse_file(b):
    """Return (ebml_header E, segment E, [top-level children E]). Validates full tree."""
    top = []; o = 0
    while o < len(b):
        i, il = read_vint(b, o, True); sz, sl = read_vint(b, o+il)
        e = E(i, il+sl, sz if sz is not None else len(b)-(o+il+sl), o); top.append(e)
        o = e.end
    assert o == len(b), 'trailing garbage / size mismatch: parsed to %d of %d' % (o, len(b))
    hdr, seg = top[0], top[1]
    assert hdr.id == 0x1A45DFA3 and seg.id == 0x18538067, top
    assert len(top) == 2, 'extra top-level after segment: %r' % top[2:]
    kids = children(b, seg.data_off, seg.end)
    # recursive validation of known masters
    def rec(e, depth):
        if e.id in MASTERS and e.id not in (0x1F43B675,) or (e.id == 0x1F43B675):
            for c in children(b, e.data_off, e.end):
                if c.id in MASTERS: rec(c, depth+1)
    for k in kids: rec(k, 1)
    return hdr, seg, kids

def get_uint(b, e): return int.from_bytes(b[e.data_off:e.end], 'big')

NAMES = {0x114D9B74:'SeekHead',0x1549A966:'Info',0x1654AE6B:'Tracks',0x1F43B675:'Cluster',0x1C53BB6B:'Cues',0x1941A469:'Attachments',
         0x1043A770:'Chapters',0x1254C367:'Tags',0xEC:'Void',0xBF:'CRC-32'}
