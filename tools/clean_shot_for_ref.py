# -*- coding: utf-8 -*-
"""把参考视频抽帧当作构图参考图前，先擦掉两类会被模型照抄的画面元素：

  ① bilibili 独播台标（右上角）
  ② 右侧竖排字幕（S08—S12）

做法：不是简单裁掉（会破坏构图比例），而是用**同帧邻域自贴回**——
从干净区域 crop 一块尺寸相近的图，按同帧光照/纹理 scale 后 overlay 回原位，
同帧自洽所以看不出修补痕迹（这与项目里「修画内文字」用的是同一套思路，
区别在于这里修的是噪声而不是内容）。

⚠️ 中文路径 cv2.imwrite 必失败，必须 imencode + tofile。

用法：python clean_shot_for_ref.py <in.png> <out.png> [mode]
      mode: full   擦台标 + 擦字幕带（默认）
            logo   只擦台标
            sub    只擦字幕带
"""
import os
import sys

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

# 台标区（右上角）：按 1920x1080 归一化。实测本片台标亮字范围
# x 0.876-0.960 / y 0.055-0.105（阈值 180 定位），留一圈余量。
LOGO_BOX = (0.865, 0.045, 0.972, 0.118)

# 竖排字幕带（右侧）：S08—S12 实测最下一字已到 y 0.97（"天旋"/"天坛"），
# 原设 0.87 会漏掉末字，实测补到 0.995 才干净。
SUB_BOX = (0.893, 0.105, 1.0, 0.995)


def patch(img, box, src_box=None, feather=14):
    """用邻域干净块同尺寸覆盖 box 区域，边缘做羽化融合。

    src_box 必须取**同帧同高度、平均亮度接近**的区域，否则天空等大面积平滑区域
    会出现明显色块（实测：拿左侧亮云补右侧亮天→亮度不匹配→黑块+硬边）。
    """
    h, w = img.shape[:2]
    x0, y0, x1, y1 = int(box[0] * w), int(box[1] * h), int(box[2] * w), int(box[3] * h)
    tw, th = x1 - x0, y1 - y0
    if tw <= 0 or th <= 0:
        return img

    roi = img[y0:y1, x0:x1]
    target_mean = float(roi.mean())

    # ⚠️ 候选坐标一律用**归一化**。踩过的坑：镜像候选曾写成 `1.0 - x1`，
    #    而 x1 已是像素值 → 负数 → 所有候选被判废 → best=None → 静默不改，
    #    擦除「成功」返回但图上一点没变。必须是 1.0 - (x1 / w)。
    cands = []
    if src_box:
        cands.append(src_box)
    cands += [
        (1.0 - x1 / w, y0 / h, 1.0 - x0 / w, y1 / h),        # 水平镜像对侧（归一化）
        ((x0 - tw) / w, y0 / h, (x0 - tw + tw) / w, y1 / h),  # 左侧同高
        (x0 / w, (y0 - th) / h, x1 / w, (y0 - th + th) / h),  # 正上方同宽
        ((x0 - tw) / w, (y0 - th) / h, (x0 - tw + tw) / w, (y0 - th + th) / h),
    ]

    best, best_diff = None, 1e9
    for cb in cands:
        sx0 = max(0, int(cb[0] * w))
        sy0 = max(0, int(cb[1] * h))
        sx1 = min(w, int(cb[2] * w))
        sy1 = min(h, int(cb[3] * h))
        if sx1 - sx0 < tw or sy1 - sy0 < th:
            continue
        src = img[sy0:sy0 + th, sx0:sx0 + tw]
        if src.shape[0] != th or src.shape[1] != tw:
            continue
        d = abs(float(src.mean()) - target_mean)
        if d < best_diff:
            best, best_diff = src, d

    if best is None:
        return img
    src = best

    mask = np.zeros((th, tw), np.uint8)
    cv2.rectangle(mask, (feather, feather), (tw - feather, th - feather), 255, -1)
    mask = cv2.GaussianBlur(mask, (feather * 2 + 1, feather * 2 + 1), 0)

    m3 = (mask.astype(np.float32) / 255.0)[:, :, None]
    roi[:] = (src.astype(np.float32) * m3 + roi.astype(np.float32) * (1.0 - m3)).astype(np.uint8)
    return img


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    src_path, dst_path = sys.argv[1], sys.argv[2]
    mode = sys.argv[3] if len(sys.argv) > 3 else 'full'

    raw = np.fromfile(src_path, dtype=np.uint8)
    img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit('decode failed: ' + src_path)
    h, w = img.shape[:2]

    if mode in ('full', 'logo'):
        img = patch(img, LOGO_BOX, src_box=None)
    if mode in ('full', 'sub'):
        img = patch(img, SUB_BOX, src_box=None)

    ok, buf = cv2.imencode('.png', img)
    if not ok:
        raise SystemExit('encode failed')
    buf.tofile(dst_path)
    print('CLEAN %dx%d -> %s  (%d bytes)  mode=%s' % (w, h, dst_path, os.path.getsize(dst_path), mode))


if __name__ == '__main__':
    main()