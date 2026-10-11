# -*- coding: utf-8 -*-
"""把 shots 目录下的代表帧拼成联系表。
中文路径不通过 argv 传递（Windows 编码会坏），改为脚本内 glob。
用法：python make_sheet_shots.py <shots_dir> <out.jpg> [cols]
"""
import glob
import os
import sys

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

SHOTS_DIR = r'D:\work\minimax_h3\法天象地\shots'
OUT = r'D:\work\minimax_h3\法天象地\shots_sheet.jpg'
COLS = 3


def main():
    shots_dir = sys.argv[1] if len(sys.argv) > 1 else SHOTS_DIR
    out = sys.argv[2] if len(sys.argv) > 2 else OUT
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else COLS

    paths = sorted(glob.glob(os.path.join(shots_dir, 'S*.png')))
    if not paths:
        print('no frames in', shots_dir)
        return
    cell_w, cell_h, label_h = 480, 270, 26
    rows = (len(paths) + cols - 1) // cols
    sheet = np.full((rows * (cell_h + label_h) + 4, cols * cell_w + 4, 3), 255, np.uint8)

    for i, p in enumerate(paths):
        img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print('skip', p)
            continue
        h, w = img.shape[:2]
        s = min(cell_w / w, cell_h / h)
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)[:cell_h, :cell_w]
        r, c = divmod(i, cols)
        y0, x0 = 2 + r * (cell_h + label_h), 2 + c * cell_w
        sheet[y0:y0 + img.shape[0], x0:x0 + img.shape[1]] = img
        stem = os.path.splitext(os.path.basename(p))[0]
        safe = ''.join(ch if 32 <= ord(ch) < 127 else '?' for ch in stem)
        cv2.putText(sheet, safe, (x0 + 6, y0 + img.shape[0] + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)

    ok, buf = cv2.imencode('.jpg', sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    if not ok:
        print('encode fail')
        return
    buf.tofile(out)
    print('SHEET %s  %dx%d  frames=%d' % (out, sheet.shape[1], sheet.shape[0], len(paths)))


if __name__ == '__main__':
    main()