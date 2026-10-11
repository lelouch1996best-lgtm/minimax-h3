# -*- coding: utf-8 -*-
"""鬼灭之刃 · 萌娘百科 og:image 立绘抓取（补齐官方立绘缺口）。"""
import os
import re
import sys
import urllib.parse
import urllib.request

ROOT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "鬼灭之刃")
CHDIR = os.path.join(ROOT, "character")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

TARGETS = sys.argv[1:] or ["宇髄天元", "灶门祢豆子"]

PAGETPL = "https://zh.moegirl.org.cn/" + "%s"

def get(url, timeout=45, ref=None):
    h = {"User-Agent": UA}
    if ref:
        h["Referer"] = ref
    req = urllib.request.Request(url, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def main():
    for name in TARGETS:
        page = "https://zh.moegirl.org.cn/" + urllib.parse.quote(name)
        try:
            html = get(page).decode("utf-8", "ignore")
        except Exception as e:
            print("PAGE-ERR", name, repr(e))
            continue
        m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
        if not m:
            m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', html, re.I)
        if not m:
            print("NO-OG", name)
            continue
        img = m.group(1)
        if img.startswith("//"):
            img = "https:" + img
        try:
            blob = get(img, ref=page)
        except Exception as e:
            print("DL-ERR", name, img, repr(e))
            continue
        ext = ".png" if ".png" in img.lower() else ".jpg"
        outdir = os.path.join(CHDIR, name, "官方参考")
        os.makedirs(outdir, exist_ok=True)
        fn = "%s-萌娘百科-立绘%s" % (name, ext)
        with open(os.path.join(outdir, fn), "wb") as g:
            g.write(blob)
        print("OK", name, fn, len(blob), img[-60:])

if __name__ == "__main__":
    main()
