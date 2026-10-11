# -*- coding: utf-8 -*-
"""鬼灭之刃 · 主角团官方参考图搜索（Tavily include_images）。
结果落盘 assets/鬼灭之刃/_refs_raw/{角色}.json，供人工/下一步筛选下载。
"""
import json
import os
import time
import urllib.request
import urllib.error

ROOT = os.path.join("D:", os.sep, "work", "minimax_h3", "assets", "鬼灭之刃")
RAW = os.path.join(ROOT, "_refs_raw")

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

QUERY_TPL = "鬼灭之刃 {name} 官方 全身立绘 设定图 角色"

def key():
    k = os.environ.get("TAVILY_API_KEY", "").strip()
    if k:
        return k
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h:
            v, _ = winreg.QueryValueEx(h, "TAVILY_API_KEY")
            return v.strip()
    except Exception:
        return ""

def search(k, query, max_results=6):
    body = json.dumps({
        "query": query,
        "search_depth": "basic",
        "max_results": max_results,
        "include_images": True,
        "include_image_descriptions": True,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=body,
        headers={
            "Authorization": "Bearer " + k,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    k = key()
    if not k:
        print("NO_KEY")
        return 1
    os.makedirs(RAW, exist_ok=True)
    summary = []
    for name in CHARACTERS:
        out = os.path.join(RAW, name + ".json")
        try:
            data = search(k, QUERY_TPL.format(name=name))
        except urllib.error.HTTPError as e:
            print("HTTPERR", name, e.code)
            summary.append((name, "HTTP %s" % e.code, 0))
            continue
        except Exception as e:
            print("ERR", name, repr(e))
            summary.append((name, "ERR", 0))
            continue
        imgs = data.get("images") or []
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        summary.append((name, "ok", len(imgs)))
        print("OK", name, "images=", len(imgs), "results=", len(data.get("results") or []))
        time.sleep(1.0)
    print("=== SUMMARY ===")
    for name, st, n in summary:
        print("  %-8s %-8s %d" % (name, st, n))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
