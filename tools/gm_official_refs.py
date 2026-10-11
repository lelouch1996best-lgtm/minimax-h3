# -*- coding: utf-8 -*-
"""鬼灭之刃 · 动画官网全篇章角色立绘抓取（通用版）。
覆盖 /character/ 与 /chara/ 两种路径，按文件名 key 映射到本地角色目录。
"""
import json
import os
import re
import urllib.request
from urllib.parse import urljoin

ROOT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "鬼灭之刃")
CHDIR = os.path.join(ROOT, "character")
META = os.path.join(ROOT, "_refs_raw")

ARCS = ["risshihen", "yukakuhen", "mugenresshahen_tv", "mugenresshahen_movie",
        "katanakajinosatohen", "hashirageikohen", "mugenjyohen_movie"]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

KEYMAP = [
    ("tanjiro", "灶门炭治郎"), ("tanjirou", "灶门炭治郎"),
    ("nezuko", "灶门祢豆子"),
    ("zenitsu", "我妻善逸"), ("zennitsu", "我妻善逸"),
    ("inosuke", "嘴平伊之助"),
    ("giyu", "富冈义勇"), ("giyuu", "富冈义勇"),
    ("shinobu", "蝴蝶忍"),
    ("kyoujurou", "炼狱杏寿郎"), ("kyojurou", "炼狱杏寿郎"), ("kyoujuro", "炼狱杏寿郎"),
    ("mitsuri", "甘露寺蜜璃"), ("kanroji", "甘露寺蜜璃"),
    ("kanao", "栗花落香奈乎"), ("kanawo", "栗花落香奈乎"),
    ("uzui", "宇髄天元"), ("tengen", "宇髄天元"),
]

def get(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def key_of(base):
    b = base.rsplit(".", 1)[0]
    for pre in ("img_chara_", "img_", "thumb_", "chara_"):
        if b.startswith(pre):
            b = b[len(pre):]
    return b.lower()

def match(base):
    k = key_of(base)
    for kw, name in KEYMAP:
        if k == kw:
            return name
    return None

def main():
    os.makedirs(META, exist_ok=True)
    log = []
    for arc in ARCS:
        page = "https://kimetsu.com/anime/%s/character/" % arc
        try:
            html = get(page).decode("utf-8", "ignore")
        except Exception as e:
            print("PAGE-ERR", arc, repr(e)[:60])
            continue
        srcs = set()
        for m in re.finditer(r'src\s*=\s*["\']([^"\']+)["\']', html, re.I):
            s = m.group(1)
            if "/chara/" in s or "/character/" in s:
                srcs.add(urljoin(page, s))
        got = 0
        for s in sorted(srcs):
            base = s.split("/")[-1]
            if not base.lower().endswith((".jpg", ".jpeg", ".png")):
                continue
            name = match(base)
            if not name:
                continue
            outdir = os.path.join(CHDIR, name, "官方参考")
            os.makedirs(outdir, exist_ok=True)
            fn = "%s-官网(%s)-%s" % (name, arc, base)
            dst = os.path.join(outdir, fn)
            if os.path.exists(dst):
                continue
            try:
                blob = get(s)
            except Exception as e:
                print("   DL-ERR", fn, repr(e)[:50])
                continue
            with open(dst, "wb") as g:
                g.write(blob)
            log.append({"arc": arc, "file": fn, "url": s, "bytes": len(blob)})
            got += 1
            print("   OK", fn, len(blob))
        print("== %s : srcs=%d matched=%d" % (arc, len(srcs), got))
    with open(os.path.join(META, "_official_index.json"), "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=1)

if __name__ == "__main__":
    main()
