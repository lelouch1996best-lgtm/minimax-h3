# -*- coding: utf-8 -*-
"""建立 鬼灭之刃 素材包目录骨架（对齐 assets/凡人 结构）。
纯 ASCII 之外的中文都在本文件内，避免经过 bash 传参。
"""
import os
import sys

ROOT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "鬼灭之刃")

CHARACTERS = [
    "灶门炭治郎",
    "灶门祢豆子",
    "我妻善逸",
    "嘴平伊之助",
    "富冈义勇",
    "蝴蝶忍",
    "炼狱杏寿郎",
    "栗花落香奈乎",
    "宇髄天元",
    "甘露寺蜜璃",
]

# 顶层：character / scene / props / voice（scene、props、voice 本轮留说明位）
DIRS = ["character", "scene", "props", os.path.join("props", "服装"), "voice",
        "_refs_raw"]

def main():
    made = []
    for d in DIRS:
        p = os.path.join(ROOT, d)
        os.makedirs(p, exist_ok=True)
        made.append(p)
    for c in CHARACTERS:
        p = os.path.join(ROOT, "character", c, "官方参考")
        os.makedirs(p, exist_ok=True)
        made.append(p)
    print("ROOT:", ROOT)
    print("created/ensured:", len(made))
    for p in made:
        print("  ", p)

if __name__ == "__main__":
    main()
