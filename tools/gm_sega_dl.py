# -*- coding: utf-8 -*-
"""鬼灭之刃 · SEGA 官方立绘下载（正确路径 /cht/assets/...）。"""
import os
import urllib.request
import urllib.error

ROOT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "鬼灭之刃")
CHDIR = os.path.join(ROOT, "character")
BASE = "https://asia.sega.com/kimetsu_hinokami/cht/assets/img/sub/character/chara%d.png"

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# charaN -> (角色目录, 造型后缀)
PICK = {
    1:  ("灶门炭治郎", "基础"),
    2:  ("灶门祢豆子", "基础"),
    3:  ("我妻善逸", "基础"),
    4:  ("嘴平伊之助", "基础"),
    5:  ("富冈义勇", "基础"),
    9:  ("蝴蝶忍", "基础"),
    10: ("炼狱杏寿郎", "基础"),
    11: ("灶门炭治郎", "火之神神乐"),
}

def get(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def main():
    for n, (name, tag) in PICK.items():
        url = BASE % n
        outdir = os.path.join(CHDIR, name, "官方参考")
        os.makedirs(outdir, exist_ok=True)
        fn = "%s-SEGA-chara%d(%s).png" % (name, n, tag)
        dst = os.path.join(outdir, fn)
        try:
            blob = get(url)
        except Exception as e:
            print("ERR", name, repr(e))
            continue
        with open(dst, "wb") as g:
            g.write(blob)
        print("OK", name, fn, len(blob))

if __name__ == "__main__":
    main()
