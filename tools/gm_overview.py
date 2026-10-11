# -*- coding: utf-8 -*-
"""鬼灭之刃 · 主角团 10 人首选底图总览（5 列 × 2 行）。"""
import os

import cv2
import numpy as np

ROOT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "鬼灭之刃")
CH = os.path.join(ROOT, "character")
OUT = os.path.join(ROOT, "_preview", "00_总览_主角团首选底图.jpg")

PICKS = [
    ("灶门炭治郎", "灶门炭治郎-官网(hashirageikohen)-img_chara_tanjiro.jpg"),
    ("灶门祢豆子", "灶门祢豆子-官网(hashirageikohen)-img_chara_nezuko.jpg"),
    ("我妻善逸", "我妻善逸-官网(hashirageikohen)-img_chara_zennitsu.jpg"),
    ("嘴平伊之助", "嘴平伊之助-官网(hashirageikohen)-img_chara_inosuke.jpg"),
    ("富冈义勇", "富冈义勇-官网(hashirageikohen)-img_chara_giyu.jpg"),
    ("蝴蝶忍", "蝴蝶忍-官网(hashirageikohen)-img_chara_shinobu.jpg"),
    ("炼狱杏寿郎", "炼狱杏寿郎-SEGA-chara10(基础).png"),
    ("栗花落香奈乎", "栗花落香奈乎-官网(hashirageikohen)-img_chara_kanawo.jpg"),
    ("宇髄天元", "宇髄天元-官网(hashirageikohen)-img_chara_uzui.jpg"),
    ("甘露寺蜜璃", "甘露寺蜜璃-官网(hashirageikohen)-img_chara_mitsuri.jpg"),
]

H = 520
PAD = 14
COLS = 5

def imread_u(p):
    d = np.fromfile(p, dtype=np.uint8)
    return None if d.size == 0 else cv2.imdecode(d, cv2.IMREAD_COLOR)

def main():
    tiles = []
    for name, fn in PICKS:
        p = os.path.join(CH, name, "官方参考", fn)
        img = imread_u(p)
        if img is None:
            print("MISS", name, fn)
            continue
        h, w = img.shape[:2]
        nw = max(1, int(w * H / h))
        t = cv2.resize(img, (nw, H), interpolation=cv2.INTER_AREA)
        tiles.append(t)
    rows = [tiles[i:i + COLS] for i in range(0, len(tiles), COLS)]
    roww = [sum(t.shape[1] for t in r) + PAD * (len(r) + 1) for r in rows]
    W = max(roww)
    Ht = (H + PAD) * len(rows) + PAD
    canvas = np.full((Ht, W, 3), 250, np.uint8)
    y = PAD
    for r in rows:
        x = PAD
        for t in r:
            canvas[y:y + H, x:x + t.shape[1]] = t
            x += t.shape[1] + PAD
        y += H + PAD
    ok, buf = cv2.imencode(".jpg", canvas, [int(cv2.IMWRITE_JPEG_QUALITY), 86])
    if ok:
        buf.tofile(OUT)
        print("WROTE", OUT, canvas.shape)

if __name__ == "__main__":
    main()
