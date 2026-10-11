# -*- coding: utf-8 -*-
"""鬼灭之刃 · 定向补搜（Tavily include_images），补齐个别角色原作造型。"""
import json
import os
import urllib.error
import urllib.request

ROOT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "鬼灭之刃")
CHDIR = os.path.join(ROOT, "character")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

QUERIES = {
    "宇髄天元": "宇髄天元 鬼灭之刃 音柱 全身 立绘 官方设定 鬼杀队制服 日轮刀",
    "灶门祢豆子": "灶门祢豆子 鬼灭之刃 全身 立绘 官方 和服 竹筒",
}

def key():
    k = os.environ.get("TAVILY_API_KEY", "").strip()
    if k:
        return k
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h:
            return winreg.QueryValueEx(h, "TAVILY_API_KEY")[0].strip()
    except Exception:
        return ""

def search(k, query):
    body = json.dumps({"query": query, "search_depth": "basic", "max_results": 8,
                       "include_images": True, "include_image_descriptions": True}).encode("utf-8")
    req = urllib.request.Request("https://api.tavily.com/search", data=body,
                                 headers={"Authorization": "Bearer " + k,
                                          "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))

def dl(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": UA,
                                               "Accept": "image/avif,image/webp,image/png,image/jpeg,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.headers.get("Content-Type", ""), r.read()

EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

def main():
    k = key()
    if not k:
        print("NO_KEY")
        return
    for name, q in QUERIES.items():
        try:
            data = search(k, q)
        except Exception as e:
            print("SEARCH-ERR", name, repr(e))
            continue
        outdir = os.path.join(CHDIR, name, "官方参考")
        os.makedirs(outdir, exist_ok=True)
        n = 0
        for it in (data.get("images") or []):
            url = it.get("url")
            if not url:
                continue
            try:
                ctype, blob = dl(url)
            except Exception as e:
                print("  XX", name, url[:70], repr(e)[:50])
                continue
            if len(blob) < 3000:
                continue
            n += 1
            ext = EXT.get(ctype.split(";")[0].strip().lower(), ".jpg")
            fn = "%s-补搜-%02d%s" % (name, n, ext)
            with open(os.path.join(outdir, fn), "wb") as g:
                g.write(blob)
            print("  OK", name, fn, ctype.split(";")[0], len(blob), "|", url[:70])

if __name__ == "__main__":
    main()
