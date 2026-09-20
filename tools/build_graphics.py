"""Upgrade only the two illustrated textures in an existing Korean CPK.

python tools/build_graphics.py --base out/data003.cpk --output out/graphics_v1.1
Original files and the v1.0 release are never overwritten.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

import numpy as np

import cpk
import datx
import invoice_patch
import logo_patch
import paths
import wtex


def digest(path):
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def verify_ranges(before, after, ranges):
    """Compare every byte outside the two replacement WTP ranges."""
    if before.stat().st_size != after.stat().st_size:
        raise ValueError('CPK size changed')
    pos = 0
    with before.open('rb') as a, after.open('rb') as b:
        for start, length in sorted(ranges) + [(before.stat().st_size, 0)]:
            while pos < start:
                n = min(8 << 20, start - pos)
                if a.read(n) != b.read(n):
                    raise ValueError(f'Unrelated CPK bytes changed at {pos}')
                pos += n
            pos = start + length
            a.seek(pos)
            b.seek(pos)


def build(base, original_dir, output, release_base, release_output):
    manifest = json.loads((release_base / 'patcher/payload/manifest.json').read_text(encoding='utf-8'))
    if base.stat().st_size != manifest['result']['size'] or digest(base) != manifest['result']['md5']:
        raise ValueError('Base CPK does not match the existing Korean release')
    if output.exists() or release_output.exists():
        raise FileExistsError('Choose new output directories; existing builds are preserved')
    output.mkdir(parents=True)
    replacements, writes = {}, []
    archive = cpk.CPK(str(base))
    try:
        for kind, index, builder in [('title', 0, logo_patch.build_title_wtp),
                                     ('ending', 1, invoice_patch.build_ending_wtp)]:
            key = f'ui/ui_{kind}.dat'
            original = original_dir / f'ui__ui_{kind}.dat'
            built = builder(str(original))
            new = built[0]
            entry = next(e for e in archive.files if e['name'] == key)
            if entry['size'] != entry['esize']:
                raise ValueError('Expected an uncompressed Korean DAT')
            dat = archive.read(entry)
            members, _ = datx.parse_dat(dat)
            member_map = {n: dat[o:o + s] for n, o, s in members}
            name = f'{kind}.wtp'
            _, offset, size = next(m for m in members if m[0] == name)
            if len(new) != size:
                raise ValueError('WTP size changed')
            wta = (original / f'{kind}.wta').read_bytes()
            if wta != member_map[f'{kind}.wta']:
                raise ValueError('Original texture header differs from base CPK')
            texture = wtex.wta_entries_any(wta)[index]
            lo, hi = texture['off'], texture['off'] + texture['isz']
            old = member_map[name]
            if old[:lo] != new[:lo] or old[hi:] != new[hi:]:
                raise ValueError('An unrelated texture changed')
            decoded = wtex.decode_surface(texture, new[lo:hi])
            expected = built[1] if kind == 'title' else built[3]
            if not np.array_equal(np.array(decoded.convert('RGBA' if kind == 'title' else 'RGB')), expected):
                raise ValueError('Texture encoding round trip differs')
            decoded.save(output / f'{kind}.png')
            replacements[key] = (name, new, (original / name).read_bytes())
            writes.append((entry['off'] + offset, new))
            print(f'{kind}: decoded and verified', flush=True)
    finally:
        archive.f.close()

    result = output / 'data003.cpk'
    shutil.copyfile(base, result)
    with result.open('r+b') as f:
        for offset, data in writes:
            f.seek(offset)
            f.write(data)
    verify_ranges(base, result, [(o, len(b)) for o, b in writes])
    # Re-read the delivered CPK, not just the images used to produce it.
    with result.open('rb') as f:
        for offset, data in writes:
            f.seek(offset)
            if f.read(len(data)) != data:
                raise ValueError('Written WTP differs')

    release_output.mkdir(parents=True)
    for folder in ('patcher', 'python'):
        shutil.copytree(release_base / folder, release_output / folder,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copyfile(release_base / '패치하기.bat', release_output / '패치하기.bat')
    version = 'v1.1'
    readme = (release_base / 'README_한국어.txt').read_text(encoding='utf-8')
    readme = readme.replace('v1.0', version, 1)
    readme += ('\n\n그래픽 개선판 변경 사항\n'
               '- 엔딩 청구서 손글씨의 영역 침범 수정\n'
               '- 청구서 제목의 원본 녹색 명암 복원\n'
               '- 타이틀 한글 로고 크기 및 중앙 정렬 조정\n'
               '- 대사, 번역, 메시지 폰트 데이터는 v1.0 그대로 유지\n'
               '파일 무결성 및 압축 후 이미지 검증 완료. 개선판의 게임 실행 검증은 별도입니다.\n')
    (release_output / 'README_한국어.txt').write_text(readme, encoding='utf-8')
    payload = release_output / 'patcher/payload'
    for key, (name, new, original) in replacements.items():
        item = next(e for e in manifest['dats'][key] if e['name'] == name)
        if len(new) != len(original):
            raise ValueError('Original WTP size differs')
        spans = []
        for offset in range(0, len(new), 4096):
            length = min(4096, len(new) - offset)
            if original[offset:offset + length] != new[offset:offset + length]:
                if spans and sum(spans[-1]) == offset:
                    spans[-1][1] += length
                else:
                    spans.append([offset, length])
        item['spans'] = spans
        blob = b''.join(new[o:o + n] for o, n in spans)
        (payload / item['file']).write_bytes(blob)
        reconstructed = bytearray(original)
        p = 0
        for o, n in spans:
            reconstructed[o:o + n] = blob[p:p + n]
            p += n
        if bytes(reconstructed) != new:
            raise ValueError('Release delta round trip differs')
    manifest['version'] = version
    manifest['result'] = {'size': result.stat().st_size, 'md5': digest(result)}
    (payload / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding='utf-8')
    zip_path = release_output.parent / f'StarFoxZero_KO_{version}.zip'
    if zip_path.exists():
        raise FileExistsError(zip_path)
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for path in sorted(release_output.rglob('*')):
            if path.is_file():
                z.write(path, Path(f'StarFoxZero_KO_{version}') / path.relative_to(release_output))
    print(json.dumps({'cpk': str(result), 'zip': str(zip_path), **manifest['result'],
                      'outside_graphics': 'byte-identical'}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, default=Path(paths.ROOT) / 'out/data003.cpk')
    parser.add_argument('--original-dir', type=Path, default=Path(paths.ORIG))
    parser.add_argument('--output', type=Path, default=Path(paths.ROOT) / 'out/graphics_v1.1')
    parser.add_argument('--release-base', type=Path, default=Path(paths.ROOT) / 'release')
    parser.add_argument('--release-output', type=Path, default=Path(paths.ROOT) / 'release/graphics_v1.1')
    args = parser.parse_args()
    build(args.base.resolve(), args.original_dir.resolve(), args.output.resolve(),
          args.release_base.resolve(), args.release_output.resolve())
