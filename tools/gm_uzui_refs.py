# -*- coding: utf-8 -*-
"""宇髄天元 多查询补搜。"""
import json
import os
import urllib.request

ROOT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "鬼灭之刃")
OUT = os.path.join(ROOT, "character", "宇髄天元", "官方参考")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

QUERIES = [
    "宇髄天元 立绘",
    "宇髄天元 鬼殺隊 制服 全身",
    "鬼滅の刃 宇髄天元 立ち絵",
    "Tengen Uzui official full body character design",
]

def key():
    k = os.environ.get("TAVILY_API_KEY", "").strip()
    if k:
        return k
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h:
        return winreg.QueryValueEx(h, "TAVILY_API_KEY")[0].strip()

def search(k, q):
    body = json.dumps({"query": q, "search_depth": "advanced", "max_results": 8,
                       "include_images": True, "include_image_descriptions": True}).encode()
    req = urllib.request.Request("https://api.tavily.com/search", data=body,
                                 headers={"Authorization": "Bearer " + k,
                                          "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))

def dl(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.headers.get("Content-Type", ""), r.read()

EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

def main():
    k = key()
    os.makedirs(OUT, exist_ok=True)
    seen, n = set(), 0
    for q in QUERIES:
        try:
            data = search(k, q)
        except Exception as e:
            print("SEARCH-ERR", q, repr(e)[:60])
            continue
        imgs = data.get("images") or []
        print("Q:", q, "imgs=", len(imgs))
        for it in imgs:
            url = it.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            try:
                ctype, blob = dl(url)
            except Exception as e:
                print("   XX", url[:75], repr(e)[:40])
                continue
            if len(blob) < 3000:
                continue
            n += 1
            ext = EXT.get(ctype.split(";")[0].strip().lower(), ".jpg")
            fn = "宇髄天元-补搜-%02d%s" % (n, ext)
            with open(os.path.join(OUT, fn), "wb") as g:
                g.write(blob)
            print("   OK", fn, len(blob), it.get("description", "")[:50] if it.get("description") else "")

if __name__ == "__main__":
    main()
