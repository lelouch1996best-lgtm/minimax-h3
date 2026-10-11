# -*- coding: utf-8 -*-
"""把若干张代表帧拼成联系表，便于一次性肉眼核验。
用法：python make_sheet.py <out.jpg> <cols> <path1> <path2> ...
注意：每格下方用 ASCII 标注（cv2 无法渲染中文），文件名中的中文需另行说明。
"""
import os
import sys

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')


def main():
    out = sys.argv[1]
    cols = int(sys.argv[2])
    paths = sys.argv[3:]
    cell_w, cell_h = 480, 270
    label_h = 26
    rows = (len(paths) + cols - 1) // cols
    sheet = np.full((rows * (cell_h + label_h) + 4, cols * cell_w + 4, 3), 255, np.uint8)

    for i, p in enumerate(paths):
        img = cv2.imdecode(np.fromfile(p, dtype=np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            print('skip', p)
            continue
        h, w = img.shape[:2]
        s = min(cell_w / w, cell_h / h)
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
        r, c = divmod(i, cols)
        y0 = 2 + r * (cell_h + label_h)
        x0 = 2 + c * cell_w
        img = img[:cell_h, :cell_w]
        sheet[y0:y0 + img.shape[0], x0:x0 + img.shape[1]] = img
        # ASCII label: basename stem, non-ascii -> '?'
        stem = os.path.splitext(os.path.basename(p))[0]
        safe = ''.join(ch if 32 <= ord(ch) < 127 else '?' for ch in stem)
        cv2.putText(sheet, safe, (x0 + 6, y0 + img.shape[0] + 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 1, cv2.LINE_AA)

    cv2.imwrite(out, sheet)
    print('SHEET', out, sheet.shape)


if __name__ == '__main__':
    main()