# -*- coding: utf-8 -*-
"""鬼灭之刃 · 官方参考图联系表（供人工/agent 肉眼核验）。
用 venv 的 OpenCV（支持 webp），中文路径走 imdecode/imencode 规避。
"""
import os
import sys

import cv2
import numpy as np

ROOT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "鬼灭之刃")
CHDIR = os.path.join(ROOT, "character")
OUT = os.path.join(ROOT, "_preview")

CHARACTERS = [
    "灶门炭治郎", "灶门祢豆子", "我妻善逸", "嘴平伊之助", "富冈义勇",
    "蝴蝶忍", "炼狱杏寿郎", "栗花落香奈乎", "宇髄天元", "甘露寺蜜璃",
]

H = 460
PAD = 12
PER_ROW = 5

def imread_u(path):
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)

def imwrite_u(path, img):
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    if ok:
        buf.tofile(path)

def main():
    os.makedirs(OUT, exist_ok=True)
    for name in CHARACTERS:
        d = os.path.join(CHDIR, name, "官方参考")
        if not os.path.isdir(d):
            print("SKIP", name)
            continue
        files = sorted(f for f in os.listdir(d)
                       if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")))
        tiles = []
        labels = []
        for f in files:
            img = imread_u(os.path.join(d, f))
            if img is None:
                print("  unreadable:", name, f)
                continue
            h, w = img.shape[:2]
            nw = max(1, int(w * H / h))
            tile = cv2.resize(img, (nw, H), interpolation=cv2.INTER_AREA)
            tiles.append(tile)
            labels.append(f)
        if not tiles:
            continue
        rows = [tiles[i:i + PER_ROW] for i in range(0, len(tiles), PER_ROW)]
        row_w = [sum(t.shape[1] for t in r) + PAD * (len(r) + 1) for r in rows]
        total_w = max(row_w)
        total_h = (H + PAD) * len(rows) + PAD
        canvas = np.full((total_h, total_w, 3), 245, np.uint8)
        y = PAD
        for r in rows:
            x = PAD
            for t in r:
                canvas[y:y + H, x:x + t.shape[1]] = t
                x += t.shape[1] + PAD
            y += H + PAD
        outp = os.path.join(OUT, name + "_preview.jpg")
        imwrite_u(outp, canvas)
        print("SHEET", name, "n=%d" % len(tiles), "->", outp)
        for i, l in enumerate(labels):
            print("     [%d] %s" % (i + 1, l))

if __name__ == "__main__":
    main()
