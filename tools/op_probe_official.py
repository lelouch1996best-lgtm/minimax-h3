# -*- coding: utf-8 -*-
"""海贼王 · 探测 one-piece.com 官方角色页的立绘地址结构（只探测，不下载）。"""
import os
import re
import json
import urllib.request

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

SLUGS = ["luffy", "zoro", "nami", "usopp", "sanji",
         "chopper", "robin", "franky", "brook", "Jinbe"]

OUT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "海贼王", "_refs_raw")
os.makedirs(OUT, exist_ok=True)


def get(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def main():
    report = {}
    for slug in SLUGS:
        page = "https://one-piece.com/character/%s/index.html" % slug
        try:
            html = get(page).decode("utf-8", "ignore")
        except Exception as e:
            print("PAGE-ERR", slug, repr(e)[:80])
            report[slug] = {"error": repr(e)[:120]}
            continue
        # og:image
        og = re.findall(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)', html, re.I)
        og += re.findall(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']', html, re.I)
        # 所有图片
        imgs = set()
        for m in re.finditer(r'(?:src|data-src|href)\s*=\s*["\']([^"\']+\.(?:jpg|jpeg|png|webp))["\']', html, re.I):
            imgs.add(m.group(1))
        report[slug] = {"og": sorted(set(og)), "images": sorted(imgs)[:40], "html_len": len(html)}
        print("== %s html=%d og=%d imgs=%d" % (slug, len(html), len(set(og)), len(imgs)))
        for u in sorted(set(og)):
            print("   OG  ", u)
        for u in sorted(imgs)[:15]:
            print("   IMG ", u)
    with open(os.path.join(OUT, "_official_probe.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
