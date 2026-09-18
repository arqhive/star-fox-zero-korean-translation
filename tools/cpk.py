import struct, sys, os

def read_utf(buf):
    assert buf[:4] == b'@UTF', buf[:4]
    size = struct.unpack('>I', buf[4:8])[0]
    t = buf[8:8+size]
    _, rows_off = struct.unpack('>HH', t[0:4])
    str_off, data_off, name_off = struct.unpack('>III', t[4:16])
    ncol, roww, nrow = struct.unpack('>HHI', t[16:24])
    def cstr(o):
        o += str_off
        e = t.index(b'\0', o)
        return t[o:e].decode('utf-8', 'replace')
    fmts = {0:'>B',1:'>b',2:'>H',3:'>h',4:'>I',5:'>i',6:'>Q',7:'>q',8:'>f',9:'>d'}
    def rd(typ, p):
        if typ in fmts:
            f = fmts[typ]; n = struct.calcsize(f)
            return struct.unpack(f, t[p:p+n])[0], n
        if typ == 0xA:
            return cstr(struct.unpack('>I', t[p:p+4])[0]), 4
        if typ == 0xB:
            o, l = struct.unpack('>II', t[p:p+8])
            return t[data_off+o:data_off+o+l], 8
        raise ValueError(typ)
    cols = []; p = 24
    for _ in range(ncol):
        flag = t[p]; nm = cstr(struct.unpack('>I', t[p+1:p+5])[0]); p += 5
        st, typ = flag & 0xF0, flag & 0x0F
        const = None
        if st == 0x30:
            const, n = rd(typ, p); p += n
        cols.append((nm, st, typ, const))
    rows = []; p = rows_off
    for _ in range(nrow):
        r = {}
        for nm, st, typ, const in cols:
            if st == 0x50:
                r[nm], n = rd(typ, p); p += n
            elif st == 0x30:
                r[nm] = const
            else:
                r[nm] = None
        rows.append(r)
    return cstr(name_off), rows

def decompress_layla(d):
    import numpy as np
    assert d[:8] == b'CRILAYLA'
    usize, hsize = struct.unpack('<II', d[8:16])
    out = bytearray(usize + 0x100)
    out[:0x100] = d[16+hsize:16+hsize+0x100]
    bits = np.unpackbits(np.frombuffer(d[16:16+hsize], np.uint8)[::-1]).tolist()
    p = 0
    w = usize - 1 + 0x100
    lvls = (2, 3, 5, 8)
    while w >= 0x100:
        if bits[p]:
            v = 0
            for b in bits[p+1:p+14]: v = (v << 1) | b
            p += 14
            off = v + 3; ln = 3; li = 0
            while True:
                L = lvls[li]; n = 0
                for b in bits[p:p+L]: n = (n << 1) | b
                p += L; ln += n
                if n != (1 << L) - 1: break
                if li < 3: li += 1
            for _ in range(ln):
                out[w] = out[w + off]; w -= 1
                if w < 0x100: break
        else:
            v = 0
            for b in bits[p+1:p+9]: v = (v << 1) | b
            p += 9
            out[w] = v; w -= 1
    return bytes(out)

class CPK:
    def __init__(self, path):
        self.path = path
        self.f = open(path, 'rb')
        h = self.f.read(0x800)
        _, self.hdr = read_utf(self._chunk(0))
        self.hdr = self.hdr[0]
        self.files = []
        toc = self.hdr.get('TocOffset')
        if toc:
            _, rows = read_utf(self._chunk(toc))
            base = self.hdr['ContentOffset'] if self.hdr['ContentOffset'] < toc else toc
            base = min(toc, self.hdr['ContentOffset'])
            for r in rows:
                name = (r.get('DirName') or '') + '/' + (r.get('FileName') or '')
                self.files.append(dict(name=name.lstrip('/'), off=r['FileOffset'] + base,
                                       size=r['FileSize'], esize=r['ExtractSize'], id=r.get('ID')))
        self.itoc = self.hdr.get('ItocOffset')
    def _chunk(self, off):
        self.f.seek(off)
        hd = self.f.read(16)
        sz = struct.unpack('<Q', hd[8:16])[0]
        return self.f.read(sz)
    def read(self, e):
        self.f.seek(e['off']); d = self.f.read(e['size'])
        if d[:8] == b'CRILAYLA':
            d = decompress_layla(d)
        return d

if __name__ == '__main__':
    c = CPK(sys.argv[1])
    for k, v in c.hdr.items():
        if not isinstance(v, bytes): print(' ', k, v)
    print(len(c.files), 'files')
    for e in c.files:
        print(e['size'], e['esize'], e['name'])
