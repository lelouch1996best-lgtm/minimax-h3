# -*- coding: utf-8 -*-
"""通用核验联系表生成器（中文路径安全）。

用法：
    python tools/xmj_sheet.py <视频路径> <输出目录> [标签前缀] [裁切上比例] [裁切下比例]
"""
import cv2, os, sys, numpy as np

VID = sys.argv[1]
OUT = sys.argv[2]
TAG = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(os.path.basename(VID))[0]
TOP = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
BOT = float(sys.argv[5]) if len(sys.argv) > 5 else 1.0

os.makedirs(OUT, exist_ok=True)
cap = cv2.VideoCapture(VID)
n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
fps = cap.get(cv2.CAP_PROP_FPS)
W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
print(f'[{TAG}] frames={n} fps={fps} dur={n/fps:.2f}s {W}x{H}')

idx = [int(round(i * (n - 1) / 11)) for i in range(12)]
thumbs = []
for i in idx:
    cap.set(cv2.CAP_PROP_POS_FRAMES, i)
    ok, fr = cap.read()
    if not ok:
        continue
    cv2.putText(fr, str(i), (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.8, (0, 255, 255), 4)
    crop = fr[int(fr.shape[0]*TOP):int(fr.shape[0]*BOT), :]
    thumbs.append(cv2.resize(crop, (320, int(320*crop.shape[0]/crop.shape[1]))))
cap.release()

h = max(t.shape[0] for t in thumbs); w = max(t.shape[1] for t in thumbs)
canvas = np.zeros((h*3, w*4, 3), np.uint8)
for k, t in enumerate(thumbs[:12]):
    r, c = divmod(k, 4)
    canvas[r*h:r*h+t.shape[0], c*w:c*w+t.shape[1]] = t

sp = os.path.join(OUT, f'{TAG}_联系表.jpg')
cv2.imencode('.jpg', canvas)[1].tofile(sp)
print('sheet:', sp, 'exists=', os.path.exists(sp), 'size=', os.path.getsize(sp) if os.path.exists(sp) else 0)

cap = cv2.VideoCapture(VID)
for label, fi in [('起', idx[0]), ('中', idx[5]), ('尾', idx[-1])]:
    cap.set(cv2.CAP_PROP_POS_FRAMES, fi)
    ok, f2 = cap.read()
    if ok:
        p = os.path.join(OUT, f'{TAG}_帧{label}_f{fi}.png')
        cv2.imencode('.png', f2)[1].tofile(p)
        print('frame:', p, 'exists=', os.path.exists(p))
cap.release()
