# -*- coding: utf-8 -*-
"""鬼灭之刃 · 火之神血风谭2 官网（kimetsu_hinokami2）原作立绘抓取。
该站角色表覆盖全柱，charaN.png 为透明底全身立绘，是 三视图 图生图的最佳底图。
排除「鬼灭学园」版本。
"""
import json
import os
import re
import urllib.request
import urllib.error
from urllib.parse import urljoin

ROOT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "鬼灭之刃")
CHDIR = os.path.join(ROOT, "character")
META = os.path.join(ROOT, "_refs_raw")

PAGES = [
    "https://asia.sega.com/kimetsu_hinokami2/cht/character",
    "https://asia.sega.com/kimetsu_hinokami2/character",
    "https://asia.sega.com/kimetsu_hinokami2/cht/",
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

MAP = [
    ("炭治郎", "灶门炭治郎"), ("禰豆子", "灶门祢豆子"), ("禰󠄀豆子", "灶门祢豆子"),
    ("善逸", "我妻善逸"), ("伊之助", "嘴平伊之助"), ("義勇", "富冈义勇"),
    ("胡蝶忍", "蝴蝶忍"), ("カナヲ", "栗花落香奈乎"), ("香奈乎", "栗花落香奈乎"),
    ("宇髄天元", "宇髄天元"), ("宇髓天元", "宇髄天元"), ("蜜璃", "甘露寺蜜璃"),
]
EXCLUDE = ["學園", "学园"]

def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def match_name(alt):
    if not alt or any(x in alt for x in EXCLUDE):
        return None
    for kw, name in MAP:
        if kw in alt:
            return name
    return None

def main():
    os.makedirs(META, exist_ok=True)
    uniq, seen = [], set()
    for page in PAGES:
        try:
            html = get(page).decode("utf-8", "ignore")
        except Exception as e:
            print("PAGE-ERR", page, repr(e))
            continue
        for m in re.finditer(r"<img\b[^>]*>", html, re.I):
            tag = m.group(0)
            src = re.search(r'src\s*=\s*["\']([^"\']+)["\']', tag, re.I)
            alt = re.search(r'alt\s*=\s*["\']([^"\']*)["\']', tag, re.I)
            if not src:
                continue
            s = urljoin(page, src.group(1))
            if "/character/" not in s or not s.lower().endswith(".png"):
                continue
            if "_thumb" in s or s in seen:
                continue
            seen.add(s)
            uniq.append({"page": page, "src": s, "alt": (alt.group(1) if alt else "")})
    with open(os.path.join(META, "_sega2_index.json"), "w", encoding="utf-8") as fh:
        json.dump(uniq, fh, ensure_ascii=False, indent=1)
    print("=== discovered %d ===" % len(uniq))
    for f in uniq:
        print("  %-14s | %s" % (f["src"].split("/")[-1], f["alt"] or "(no alt)"))
    print("--- download (原作造型) ---")
    for f in uniq:
        name = match_name(f["alt"])
        if not name:
            continue
        outdir = os.path.join(CHDIR, name, "官方参考")
        os.makedirs(outdir, exist_ok=True)
        base = f["src"].split("/")[-1]
        fn = "%s-SEGA2-%s" % (name, base)
        dst = os.path.join(outdir, fn)
        if os.path.exists(dst):
            continue
        try:
            blob = get(f["src"])
        except Exception as e:
            print("DL-ERR", fn, repr(e))
            continue
        with open(dst, "wb") as g:
            g.write(blob)
        print("DL", name, fn, len(blob))

if __name__ == "__main__":
    main()
