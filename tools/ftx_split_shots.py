# -*- coding: utf-8 -*-
"""参考视频镜头结构拆解（纯本地分析，不调 API）

用途：把 47.83s 的参考视频切成镜头段，统计每段时长与画面变化强度，
并抽取每段代表帧，供人工肉眼核验后作为 H3 分段生成的镜头依据。
"""
import os
import sys

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

VIDEO = r'D:\work\minimax_h3\法天象地\参考.mp4'
OUT = r'D:\work\minimax_h3\法天象地\shots'
THRESH = 22.0      # 帧间差均值阈值（0-255），高于判定为切镜
MIN_LEN = 0.45     # 最短镜头秒数


def main():
    os.makedirs(OUT, exist_ok=True)
    cap = cv2.VideoCapture(VIDEO)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    diffs = []
    prev = None
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        small = cv2.resize(frame, (320, 180))
        g = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if prev is not None:
            diffs.append((idx, float(np.abs(g - prev).mean())))
        prev = g
        idx += 1
    cap.release()

    cuts = [0]
    for i, (fno, d) in enumerate(diffs):
        if d > THRESH:
            # 抑制抖动：切镜后 12 帧内不再重复记
            if (i + 1) - cuts[-1] > 12:
                cuts.append(i + 1)
    cuts.append(total)

    segs = []
    for a, b in zip(cuts, cuts[1:]):
        if (b - a) / fps < MIN_LEN:
            if segs:
                segs[-1] = (segs[-1][0], b)
            continue
        segs.append((a, b))

    print('fps=%.3f total=%d dur=%.2fs  ->  %d shots' % (fps, total, total / fps, len(segs)))
    print('-' * 72)
    print('shot  start    end    dur   motion')
    for n, (a, b) in enumerate(segs, 1):
        seg_d = [d for fno, d in diffs if a <= fno < b]
        motion = sum(seg_d) / len(seg_d) if seg_d else 0.0
        peak = max(seg_d) if seg_d else 0.0
        print('S%02d  %6.2fs %6.2fs %5.2fs  avg=%5.1f peak=%5.1f'
              % (n, a / fps, b / fps, (b - a) / fps, motion, peak))
    print('-' * 72)
    print('sum dur = %.2fs' % (sum(b - a for a, b in segs) / fps))

    # 抽每段中点帧（信息量最大）
    # ⚠️ cv2.imwrite 写中文路径必失败（返回 False 静默），必须 imencode + tofile
    cap = cv2.VideoCapture(VIDEO)
    for n, (a, b) in enumerate(segs, 1):
        mid = a + (b - a) // 2
        cap.set(cv2.CAP_PROP_POS_FRAMES, mid)
        ok, frame = cap.read()
        if not ok:
            continue
        p = os.path.join(OUT, 'S%02d_%06.2fs.png' % (n, mid / fps))
        ok2, buf = cv2.imencode('.png', frame)
        if not ok2:
            print('encode fail', p)
            continue
        buf.tofile(p)
        print('SHOT %s  %d bytes' % (p, os.path.getsize(p)))
    cap.release()


if __name__ == '__main__':
    main()