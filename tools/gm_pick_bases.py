# -*- coding: utf-8 -*-
"""核验 9 人的候选底图：拼成一张网格图，肉眼确认是否干净、无特效、无黑底"""
import os
import sys

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'D:/work/minimax_h3/assets/鬼灭之刃/character'
OUT = r'D:/work/minimax_h3/logs/_gm_check/bases_9.jpg'

ITEMS = [
    ('祢豆子', '灶门祢豆子/官方参考/灶门祢豆子-官网(hashirageikohen)-img_chara_nezuko.jpg'),
    ('善逸', '我妻善逸/官方参考/我妻善逸-官网(hashirageikohen)-img_chara_zennitsu.jpg'),
    ('伊之助', '嘴平伊之助/官方参考/嘴平伊之助-官网(hashirageikohen)-img_chara_inosuke.jpg'),
    ('义勇', '富冈义勇/官方参考/富冈义勇-官网(hashirageikohen)-img_chara_giyu.jpg'),
    ('蝴蝶忍', '蝴蝶忍/官方参考/蝴蝶忍-官网(hashirageikohen)-img_chara_shinobu.jpg'),
    ('炼狱(SEGA)', '炼狱杏寿郎/官方参考/炼狱杏寿郎-SEGA-chara10(基础).png'),
    ('炼狱(插画)', '炼狱杏寿郎/官方参考/炼狱杏寿郎-官方参考-01.webp'),
    ('香奈乎', '栗花落香奈乎/官方参考/栗花落香奈乎-官网(hashirageikohen)-img_chara_kanawo.jpg'),
    ('宇髄天元', '宇髄天元/官方参考/宇髄天元-官网(hashirageikohen)-img_chara_uzui.jpg'),
    ('甘露寺', '甘露寺蜜璃/官方参考/甘露寺蜜璃-官网(hashirageikohen)-img_chara_mitsuri.jpg'),
]

TILE_H = 300
COLS = 4
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
    # 纯 ASCII 标签避免字体乱码 -> 用序号，旁边按打印顺序对应
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
