# Render MCD sections the way the game lays them out (glyph advance + kerning) for visual checks.
import struct
import numpy as np
from PIL import Image
from mcd_tool import MCD, CTRL_SPACE


def render_sections(mcd_bytes, atlas, keys, scale=1.0, engine_spacing=True):
    """engine_spacing: 게임처럼 글자마다 글리프 메타[3](폰트 메트릭 b, 폰트 2는 -8px 등)만큼
    다음 글자를 당겨 찍는다. 이 값을 빼면 실제 화면보다 글자 사이가 넓게 보인다(2026-10-05 실기 확인)."""
    m = MCD(mcd_bytes)
    H, W = atlas.shape[:2]
    lines_img = []
    for i, j in keys:
        sec = m.messages[i]['sections'][j]
        font = sec['c'] >> 16
        fm = struct.unpack('>I4f', m.font_metrics(font))
        fh = int(round(fm[2]))
        for ln in sec['lines']:
            items, x = [], 0.0
            for v, q in ln['toks']:
                k = q - 0x10000 if q >= 0x8000 else q
                if v < 0x8000:
                    g = struct.unpack('>I9f', m.glyphs[m.symbols[v][2]])
                    x1, y1, x2, y2 = round(g[1] * W), round(g[2] * H), round(g[3] * W), round(g[4] * H)
                    if items:
                        x += k
                    items.append((x, atlas[y1:y2, x1:x2]))
                    x += g[5] + (g[8] if engine_spacing else 0)
                elif v == CTRL_SPACE:
                    x += fm[1]
                else:
                    items.append((x, np.full((fh, 8, 2), 90, np.uint8)))  # icon / tag marker
                    x += fh * 0.8
            if not items:
                continue
            x0 = min(0, int(np.floor(min(p for p, _ in items))))
            w = int(np.ceil(max(p + t.shape[1] for p, t in items))) - x0
            h = max(t.shape[0] for _, t in items)
            row = np.zeros((h, w, 2), np.uint8)
            for p, t in items:
                c = int(round(p)) - x0
                row[:t.shape[0], c:c + t.shape[1]] = np.maximum(row[:t.shape[0], c:c + t.shape[1]], t)
            lines_img.append(row)
    Wd = max(r.shape[1] for r in lines_img)
    sheet = np.concatenate([np.pad(r, ((0, 0), (0, Wd - r.shape[1]), (0, 0))) for r in lines_img], 0)
    rgb = np.zeros(sheet.shape[:2] + (3,), np.uint8)
    rgb[:, :, 0] = sheet[:, :, 0]
    rgb[:, :, 1] = sheet[:, :, 1]
    im = Image.fromarray(rgb)
    if scale != 1.0:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    return im
