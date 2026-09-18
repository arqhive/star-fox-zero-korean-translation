import struct, sys
def parse_dat(d):
    assert d[:4] in (b'DAT\0', b'DAT\x00'), d[:4]
    E = '<'
    n, off_off, ext_off, name_off, size_off = struct.unpack(E+'IIIII', d[4:24])
    if n > 100000:
        E = '>'; n, off_off, ext_off, name_off, size_off = struct.unpack(E+'IIIII', d[4:24])
    offs = struct.unpack(E+'%dI'%n, d[off_off:off_off+4*n])
    sizes = struct.unpack(E+'%dI'%n, d[size_off:size_off+4*n])
    nl = struct.unpack(E+'I', d[name_off:name_off+4])[0]
    names = [d[name_off+4+i*nl:name_off+4+(i+1)*nl].split(b'\0')[0].decode() for i in range(n)]
    return [(names[i], offs[i], sizes[i]) for i in range(n)], E
