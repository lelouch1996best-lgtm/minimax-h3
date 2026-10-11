# -*- coding: utf-8 -*-
"""两图两裁：把「1 横 + 1 竖」两张母图裁成四平台封面（8 位 RGB JPEG）。

背景（2026-10-11 用户指定）：
    不再为每个平台各生成一张封面。只生成 2 张母图——
      横屏母图 size="16:10"  → B站
      竖屏母图 size="2:3"    → 9:16（抖音/快手，居中裁两侧）＋ 3:4（小红书，居中裁上下）
    竖母图取 2:3 = 9:16(0.5625) 与 3:4(0.75) 的几何中值，两侧损失最小且均衡
    （裁 9:16 丢 7.8% 宽、裁 3:4 丢 5.6% 高），一张图裁两次都不伤主体。

平台规格（2026-10-11 联网核实）：
    B站     1146x717  官方推荐 16:10（与视频的 16:9 不同，须单独出）≤2MB
    抖音    1080x1920 9:16
    快手    1080x1920 9:16
    小红书  1080x1440 3:4（信息流占屏最大，优先）

用法：
    python tools/crop_covers.py --horiz <横母图> --vert <竖母图> --out-dir <目录>
    # 只给一个也能跑：缺 horiz 就只出竖屏三张，缺 vert 就只出 B站
    # 可选 --platforms 封面_B站,封面_抖音
    # 可选 --quality 92

注意：输出统一 8 位 RGB。B站 -111 教训：48 位 rgb48be 会让建稿前直接中止。
"""
import argparse
import os
import sys

from PIL import Image

sys.stdout.reconfigure(encoding='utf-8')

# (输出文件名, 源, 目标宽高, 目标比例)
TARGETS = [
    ('封面_B站.jpg', 'horiz', (1920, 1200), 16 / 10),
    ('封面_抖音.jpg', 'vert', (1080, 1920), 9 / 16),
    ('封面_快手.jpg', 'vert', (1080, 1920), 9 / 16),
    ('封面_小红书.jpg', 'vert', (1080, 1440), 3 / 4),
]


def center_crop(im, ratio):
    """居中裁到目标宽高比（不改比例方向，只切多余边）。"""
    w, h = im.size
    if abs(w / h - ratio) < 1e-4:
        return im
    if w / h > ratio:                      # 太宽 → 裁两侧
        nw = int(round(h * ratio))
        x = (w - nw) // 2
        return im.crop((x, 0, x + nw, h))
    nh = int(round(w / ratio))             # 太高 → 裁上下
    y = (h - nh) // 2
    return im.crop((0, y, w, y + nh))


def run(src, dst, size, ratio, quality):
    im = Image.open(src)
    if im.mode != 'RGB':
        im = im.convert('RGB')             # 强制 8 位 RGB（丢 48 位/alpha）
    before = im.size
    im = center_crop(im, ratio)
    if im.size != size:
        im = im.resize(size, Image.LANCZOS)
    im.save(dst, 'JPEG', quality=quality, optimize=True)

    chk = Image.open(dst)
    kb = os.path.getsize(dst) / 1024
    flag = 'OK' if (chk.size == size and chk.mode == 'RGB') else '!! 校验失败'
    print('  %-18s %sx%s r=%.4f  ->  %sx%s %s  %.0fKB  %s'
          % (os.path.basename(src), before[0], before[1], before[0] / before[1],
             chk.size[0], chk.size[1], chk.mode, kb, flag))
    return chk.size == size and chk.mode == 'RGB'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--horiz', help='横屏母图（16:10 生成）→ B站')
    ap.add_argument('--vert', help='竖屏母图（2:3 生成）→ 抖音/快手(9:16) + 小红书(3:4)')
    ap.add_argument('--out-dir', required=True, help='输出目录（如 <项目>/发布）')
    ap.add_argument('--platforms', default='', help='只出指定文件（逗号分隔，如 封面_B站,封面_小红书）')
    ap.add_argument('--quality', type=int, default=92)
    args = ap.parse_args()

    srcs = {'horiz': args.horiz, 'vert': args.vert}
    for k, v in srcs.items():
        if v and not os.path.exists(v):
            print('FATAL: %s 母图不存在: %s' % (k, v))
            return 1
    if not args.horiz and not args.vert:
        print('FATAL: --horiz / --vert 至少给一个')
        return 1

    only = {x.strip() for x in args.platforms.split(',') if x.strip()}
    os.makedirs(args.out_dir, exist_ok=True)

    ok = True
    for name, kind, size, ratio in TARGETS:
        if only and name not in only:
            continue
        src = srcs.get(kind)
        if not src:
            print('  %-18s 跳过（未提供 %s 母图）' % (name, kind))
            continue
        ok &= run(src, os.path.join(args.out_dir, name), size, ratio, args.quality)

    print('完成 -> ' + os.path.abspath(args.out_dir))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
