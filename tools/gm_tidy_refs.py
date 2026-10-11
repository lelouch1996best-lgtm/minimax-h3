# -*- coding: utf-8 -*-
"""鬼灭之刃 · 官方参考图整理归档（不删除，移入 _废弃_/_备选_ 子目录）。"""
import os
import shutil
import sys

ROOT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "鬼灭之刃")
CHDIR = os.path.join(ROOT, "character")

MOVES = [
    ("宇髄天元", "宇髄天元-SEGA2-chara43.png", "_废弃_非原作造型"),
    ("宇髄天元", "宇髄天元-官方参考-01.png", "_废弃_非原作造型"),
    ("宇髄天元", "宇髄天元-官方参考-02.png", "_废弃_非原作造型"),
    ("宇髄天元", "宇髄天元-补搜-01.jpg", "_废弃_非原作造型"),
    ("宇髄天元", "宇髄天元-补搜-02.png", "_废弃_重复"),
    ("宇髄天元", "宇髄天元-补搜-04.jpg", "_废弃_损坏"),
    ("宇髄天元", "宇髄天元-补搜-05.jpg", "_备选_服装实拍"),
    ("宇髄天元", "宇髄天元-补搜-06.jpg", "_备选_服装实拍"),
    ("宇髄天元", "宇髄天元-补搜-07.jpg", "_备选_服装实拍"),
    ("炼狱杏寿郎", "炼狱杏寿郎-官方参考-02.png", "_废弃_非原作造型"),
    ("炼狱杏寿郎", "炼狱杏寿郎-官网(无限列车)-img_cha_01.jpg", "_废弃_错配(实为炭治郎)"),
    ("炼狱杏寿郎", "炼狱杏寿郎-官网(无限列车电影)-thumb_02.png", "_废弃_错配(实为祢豆子)"),
    ("富冈义勇", "富冈义勇-官方参考-03.webp", "_废弃_周边实拍"),
    ("甘露寺蜜璃", "甘露寺蜜璃-官方参考-02.png", "_废弃_重复"),
    ("灶门祢豆子", "灶门祢豆子-补搜-02.jpg", "_废弃_重复"),
    ("灶门祢豆子", "灶门祢豆子-官方参考-02.jpg", "_备选_带文字海报"),
]

def main():
    dry = "--write" not in sys.argv
    n_ok = n_miss = 0
    for name, fn, sub in MOVES:
        src = os.path.join(CHDIR, name, "官方参考", fn)
        dst_dir = os.path.join(CHDIR, name, "官方参考", sub)
        dst = os.path.join(dst_dir, fn)
        if not os.path.exists(src):
            print("MISS", name, fn)
            n_miss += 1
            continue
        if dry:
            print("PLAN", name, "|", fn, "->", sub)
            n_ok += 1
            continue
        os.makedirs(dst_dir, exist_ok=True)
        shutil.move(src, dst)
        print("MOVED", name, "|", fn, "->", sub)
        n_ok += 1
    print("=== %s ok=%d miss=%d ===" % ("DRY" if dry else "WRITE", n_ok, n_miss))

if __name__ == "__main__":
    main()
