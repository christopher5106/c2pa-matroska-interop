import struct,sys
d=open(sys.argv[2],'rb').read()
assert d[:4]==b'glTF'
off=12
while off<len(d):
    ln,ty=struct.unpack('<II',d[off:off+8])
    if ty==0x41503243:
        c=d[off+8:off+8+ln]
        sb=struct.unpack('>I',c[:4])[0]
        print('chunk len',ln,'superbox len',sb,'type',c[4:8], c[8:30])
        j=c[:sb]
        assert not any(c[sb:]), 'nonzero trailing'
        open(sys.argv[1]+'/manifest.c2pa','wb').write(j)
        # large: append padding box ('free' box) after? Keep superbox valid: we append a JUMBF-style 'free' box? simpler: raw append zeros is invalid. Append a 'free' ISO box.
        pad=300*1024-len(j)
        big=j+struct.pack('>I',pad)+b'free'+b'\x00'*(pad-8)
        open(sys.argv[1]+'/manifest_300k.c2pa','wb').write(big)
        print(len(j),len(big))
    off+=8+ln
