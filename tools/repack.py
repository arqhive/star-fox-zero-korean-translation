# DAT (PlatinumGames, big-endian) and CPK (CRI, uncompressed replacement) repackers.
import struct, hashlib, os
import cpk as cpklib


# ---------------- DAT ----------------
def _dat_align(name):
    return 0x2000 if name.endswith('.wtp') else 0x40


def _up(v, a):
    return (v + a - 1) // a * a


def repack_dat(orig, replace):
    """orig: original DAT bytes; replace: {name: bytes}. Keeps header/tables, relays file data."""
    magic, cnt, off_t, ext_t, name_t, size_t, hash_t, _ = struct.unpack('>8I', orig[:32])
    offs = struct.unpack('>%dI' % cnt, orig[off_t:off_t + 4 * cnt])
    sizes = struct.unpack('>%dI' % cnt, orig[size_t:size_t + 4 * cnt])
    nl = struct.unpack('>I', orig[name_t:name_t + 4])[0]
    names = [orig[name_t + 4 + i * nl:name_t + 4 + (i + 1) * nl].split(b'\0')[0].decode() for i in range(cnt)]
    unknown = set(replace) - set(names)
    assert not unknown, unknown
    head_end = min(offs)
    out = bytearray(orig[:head_end])
    new_offs, new_sizes = [], []
    for i, n in enumerate(names):
        data = replace.get(n, orig[offs[i]:offs[i] + sizes[i]])
        pos = _up(len(out), _dat_align(n))
        out += b'\0' * (pos - len(out))
        new_offs.append(pos)
        new_sizes.append(len(data))
        out += data
    out += b'\0' * (_up(len(out), 0x2000) - len(out))
    struct.pack_into('>%dI' % cnt, out, off_t, *new_offs)
    struct.pack_into('>%dI' % cnt, out, size_t, *new_sizes)
    return bytes(out)


# ---------------- CPK ----------------
def _utf_patch_rows(chunk_payload, updates):
    """In-place update of per-row (0x50) integer columns in an @UTF table.
    updates: {row_index: {column: value}}"""
    b = bytearray(chunk_payload)
    t0 = 8
    rows_off, = struct.unpack('>H', b[t0 + 2:t0 + 4])
    str_off, = struct.unpack('>I', b[t0 + 4:t0 + 8])
    ncol, roww, nrow = struct.unpack('>HHI', b[t0 + 16:t0 + 24])
    sizes = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 8, 7: 8, 8: 4, 9: 8, 10: 4, 11: 8}
    fmts = {0: '>B', 1: '>b', 2: '>H', 3: '>h', 4: '>I', 5: '>i', 6: '>Q', 7: '>q'}
    cols, p = [], t0 + 24
    for _ in range(ncol):
        fl = b[p]
        no, = struct.unpack('>I', b[p + 1:p + 5])
        e = b.index(0, t0 + str_off + no)
        name = b[t0 + str_off + no:e].decode()
        p += 5
        if fl & 0xF0 == 0x30:
            p += sizes[fl & 0xF]
        cols.append((name, fl & 0xF0, fl & 0xF))
    for r, vals in updates.items():
        q = t0 + rows_off + r * roww
        for name, st, typ in cols:
            if st != 0x50:
                continue
            if name in vals:
                struct.pack_into(fmts[typ], b, q, vals[name])
            q += sizes[typ]
    return bytes(b)


def _read_chunk(f, off):
    f.seek(off)
    hd = f.read(16)
    sz, = struct.unpack('<Q', hd[8:16])
    return hd, f.read(sz)


def repack_cpk(src_path, dst_path, replace, log=print):
    """replace: {'ui/ui_title.dat': bytes} stored uncompressed. Rewrites content in original order."""
    c = cpklib.CPK(src_path)
    hdr = c.hdr
    align = hdr['Align']
    toc_off, etoc_off = hdr['TocOffset'], hdr['EtocOffset']
    base = min(toc_off, hdr['ContentOffset'])
    f = open(src_path, 'rb')
    _, toc = _read_chunk(f, toc_off)
    _, rows = cpklib.read_utf(toc)
    names = [((r['DirName'] or '') + '/' + r['FileName']).lstrip('/') for r in rows]
    missing = set(replace) - set(names)
    assert not missing, missing
    order = sorted(range(len(rows)), key=lambda i: rows[i]['FileOffset'])

    f.seek(0)
    head = bytearray(f.read(hdr['ContentOffset']))  # header + TOC area (patched later)
    out = open(dst_path + '.tmp', 'wb')
    out.write(head)
    pos = hdr['ContentOffset']
    updates = {}
    for i in order:
        r = rows[i]
        if names[i] in replace:
            data = replace[names[i]]
            size = esize = len(data)
        else:
            f.seek(base + r['FileOffset'])
            data = f.read(r['FileSize'])
            size, esize = r['FileSize'], r['ExtractSize']
        new_off = pos
        out.write(data)
        pos += len(data)
        pad = _up(pos, align) - pos
        out.write(b'\0' * pad)
        pos += pad
        updates[i] = dict(FileOffset=new_off - base, FileSize=size, ExtractSize=esize)
    content_end = pos
    # ETOC (unchanged payload) at the new end
    f.seek(etoc_off)
    etoc = f.read(hdr['EtocSize'])
    out.write(etoc)
    out.close()

    # patch TOC rows and header
    hd_toc, toc_payload = _read_chunk(open(src_path, 'rb'), toc_off)
    new_toc = _utf_patch_rows(toc_payload, updates)
    hd_hdr, hdr_payload = _read_chunk(open(src_path, 'rb'), 0)
    new_hdr = _utf_patch_rows(hdr_payload, {0: dict(ContentSize=content_end - hdr['ContentOffset'],
                                                    EtocOffset=content_end)})
    with open(dst_path + '.tmp', 'r+b') as o:
        o.seek(16)
        o.write(new_hdr)
        o.seek(toc_off + 16)
        o.write(new_toc)
    if os.path.exists(dst_path):
        os.remove(dst_path)
    os.rename(dst_path + '.tmp', dst_path)
    log('CPK 작성: %s (%d bytes, 교체 %d개)' % (dst_path, content_end + len(etoc), len(replace)))
