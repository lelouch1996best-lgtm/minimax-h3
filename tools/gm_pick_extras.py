# -*- coding: utf-8 -*-
"""核验补充候选底图：伊之助 / 蝴蝶忍 / 香奈乎 / 甘露寺 的全身或露脸素材"""
import os
import sys

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'D:/work/minimax_h3/assets/鬼灭之刃/character'
OUT = r'D:/work/minimax_h3/logs/_gm_check/bases_extra.jpg'

ITEMS = [
    ('伊之助-01', '嘴平伊之助/官方参考/嘴平伊之助-官方参考-01.webp'),
    ('伊之助-02', '嘴平伊之助/官方参考/嘴平伊之助-官方参考-02.png'),
    ('伊之助-03', '嘴平伊之助/官方参考/嘴平伊之助-官方参考-03.png'),
    ('蝴蝶忍-01', '蝴蝶忍/官方参考/蝴蝶忍-官方参考-01.jpg'),
    ('香奈乎-01', '栗花落香奈乎/官方参考/栗花落香奈乎-官方参考-01.png'),
    ('甘露寺-03', '甘露寺蜜璃/官方参考/甘露寺蜜璃-官方参考-03.png'),
]

TILE_H = 420
COLS = 3
PAD = 8
LABEL_H = 26

tiles = []
for name, rel in ITEMS:
    p = os.path.join(ROOT, rel)
    img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        print('FAIL decode', name)
        continue
    h, w = img.shape[:2]
    s = TILE_H / h
    img = cv2.resize(img, (int(w * s), TILE_H), interpolation=cv2.INTER_AREA)
    canvas = np.full((TILE_H + LABEL_H, img.shape[1], 3), 255, np.uint8)
    canvas[LABEL_H:, :] = img
    cv2.putText(canvas, str(len(tiles) + 1), (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    tiles.append(canvas)
    print('%-12s %dx%d' % (name, w, h))

rows = []
for i in range(0, len(tiles), COLS):
    chunk = tiles[i:i + COLS]
    rw = sum(t.shape[1] for t in chunk) + PAD * (len(chunk) + 1)
    rh = max(t.shape[0] for t in chunk) + PAD * 2
    row = np.full((rh, rw, 3), 255, np.uint8)
    x = PAD
    for t in chunk:
        row[PAD:PAD + t.shape[0], x:x + t.shape[1]] = t
        x += t.shape[1] + PAD
    rows.append(row)

W = max(r.shape[1] for r in rows)
H = sum(r.shape[0] for r in rows)
sheet = np.full((H, W, 3), 255, np.uint8)
y = 0
for r in rows:
    sheet[y:y + r.shape[0], 0:r.shape[1]] = r
    y += r.shape[0]

os.makedirs(os.path.dirname(OUT), exist_ok=True)
ok, buf = cv2.imencode('.jpg', sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
buf.tofile(OUT)
print('SHEET', OUT, sheet.shape[1], 'x', sheet.shape[0])
print('编号顺序:', ' | '.join('%d=%s' % (i + 1, n) for i, (n, _) in enumerate(ITEMS)))
