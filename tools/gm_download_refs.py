# -*- coding: utf-8 -*-
"""鬼灭之刃 · 官方参考图下载 + 存活校验。
只取 Tavily 返回的顶层 images[]（result 内嵌图噪声高，丢弃）。
下载到 character/{角色}/官方参考/，并写 _refs_raw/_download_manifest.json 记录映射。
"""
import json
import os
import urllib.request
import urllib.error

ROOT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "鬼灭之刃")
RAW = os.path.join(ROOT, "_refs_raw")
CHDIR = os.path.join(ROOT, "character")

CHARACTERS = [
    "灶门炭治郎", "灶门祢豆子", "我妻善逸", "嘴平伊之助", "富冈义勇",
    "蝴蝶忍", "炼狱杏寿郎", "栗花落香奈乎", "宇髄天元", "甘露寺蜜璃",
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

EXTMAP = {"image/jpeg": ".jpg", "image/jpg": ".jpg", "image/png": ".png",
          "image/webp": ".webp", "image/gif": ".gif"}

def host_of(url):
    try:
        return url.split("//", 1)[1].split("/", 1)[0]
    except Exception:
        return "unknown"

def get(url, timeout=45):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read()

def main():
    manifest = {}
    tot_ok = 0
    tot_try = 0
    for name in CHARACTERS:
        src = os.path.join(RAW, name + ".json")
        if not os.path.exists(src):
            print("MISSING-RAW", name)
            continue
        with open(src, encoding="utf-8") as f:
            data = json.load(f)
        imgs = data.get("images") or []
        outdir = os.path.join(CHDIR, name, "官方参考")
        os.makedirs(outdir, exist_ok=True)
        entries = []
        idx = 0
        seen = set()
        for it in imgs:
            url = (it or {}).get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            tot_try += 1
            try:
                status, ctype, blob = get(url)
            except urllib.error.HTTPError as e:
                entries.append({"url": url, "title": it.get("title"),
                                "desc": it.get("description"),
                                "status": "HTTP %s" % e.code, "file": None})
                continue
            except Exception as e:
                entries.append({"url": url, "title": it.get("title"),
                                "desc": it.get("description"),
                                "status": "ERR", "file": None})
                continue
            if status != 200 or len(blob) < 3000:
                entries.append({"url": url, "title": it.get("title"),
                                "desc": it.get("description"),
                                "status": "bad(%s,%dB)" % (status, len(blob)),
                                "file": None})
                continue
            idx += 1
            ext = EXTMAP.get(ctype.split(";")[0].strip().lower(), ".jpg")
            fn = "%s-官方参考-%02d%s" % (name, idx, ext)
            with open(os.path.join(outdir, fn), "wb") as g:
                g.write(blob)
            tot_ok += 1
            entries.append({"url": url, "title": it.get("title"),
                            "desc": it.get("description"),
                            "status": "ok %s %dB" % (ctype.split(";")[0], len(blob)),
                            "host": host_of(url), "file": fn})
            print("OK", name, fn, ctype.split(";")[0], len(blob))
        manifest[name] = entries
    with open(os.path.join(RAW, "_download_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print("=== DONE ok=%d / try=%d ===" % (tot_ok, tot_try))

if __name__ == "__main__":
    main()
