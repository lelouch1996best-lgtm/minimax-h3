# -*- coding: utf-8 -*-
"""
抖音真实浏览器抓取（playwright + 已登录 cookie）
真实浏览器里页面自己会带 a_bogus 签名，因此能绕过 verify_check 风控。

用法:
  python dy_browser.py search --kw-url "%E7%90%B5%E7%90%B6%E8%A1%8C%E8%88%9E%E8%B9%88" --out out.json
  python dy_browser.py grab --aweme-id 1234567890 --out video.mp4
"""
import argparse, json, os, re, sys, time

from playwright.sync_api import sync_playwright

COOKIE = r"D:\work\social-auto-upload\cookies\douyin_douyin_dance.json"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def state():
    with open(COOKIE, "r", encoding="utf-8") as f:
        d = json.load(f)
    return {"cookies": d.get("cookies", []), "origins": d.get("origins", [])}


def slim(aw):
    st = aw.get("statistics") or {}
    dur = aw.get("duration") or 0
    nu = ((aw.get("video") or {}).get("play_addr") or {}).get("url_list") or []
    return {
        "aweme_id": aw.get("aweme_id"),
        "desc": aw.get("desc"),
        "author": (aw.get("author") or {}).get("nickname"),
        "sec_uid": (aw.get("author") or {}).get("sec_uid"),
        "duration_s": round(dur / 1000.0, 1) if dur else None,
        "digg": st.get("digg_count"),
        "comment": st.get("comment_count"),
        "play_urls": nu[:2],
    }


CHANNEL = None


def run_search(kw_url, out, headed):
    found = {}
    dom_ids = set()
    with sync_playwright() as p:
        kw = {"headless": not headed, "args": ["--disable-blink-features=AutomationControlled"]}
        if CHANNEL:
            kw["channel"] = CHANNEL
        b = p.chromium.launch(**kw)
        ctx = b.new_context(storage_state=state(), user_agent=UA,
                            viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()

        def on_resp(r):
            if "general/search/single" in r.url or "/aweme/v1/web/search/" in r.url:
                try:
                    j = r.json()
                except Exception:
                    return
                for it in (j.get("data") or []):
                    aw = it.get("aweme_info") or {}
                    if aw.get("aweme_id"):
                        found[aw["aweme_id"]] = slim(aw)

        pg.on("response", on_resp)
        url = "https://www.douyin.com/search/" + kw_url
        pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        # 等结果渲染，滚动触发加载
        for _ in range(4):
            pg.wait_for_timeout(2500)
            html = pg.content()
            dom_ids |= set(re.findall(r"/video/(\d{6,})", html))
            pg.mouse.wheel(0, 2000)
        pg.wait_for_timeout(2000)
        html = pg.content()
        dom_ids |= set(re.findall(r"/video/(\d{6,})", html))
        title = pg.title()
        shot = os.path.splitext(out)[0] + "_page.png"
        try:
            pg.screenshot(path=shot, full_page=False)
        except Exception:
            pass
        ctx.close(); b.close()

    res = {"page_title": title, "api_items": list(found.values()),
           "dom_video_ids": sorted(dom_ids)[:60]}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print(json.dumps({"page_title": title, "api_count": len(found),
                      "dom_count": len(dom_ids), "out": out, "screenshot": shot},
                     ensure_ascii=False))


def run_grab(aweme_id, out, headed):
    with sync_playwright() as p:
        kw = {"headless": not headed, "args": ["--disable-blink-features=AutomationControlled"]}
        if CHANNEL:
            kw["channel"] = CHANNEL
        b = p.chromium.launch(**kw)
        ctx = b.new_context(storage_state=state(), user_agent=UA,
                            viewport={"width": 1440, "height": 900}, locale="zh-CN")
        pg = ctx.new_page()
        pg.goto("https://www.douyin.com/video/%s" % aweme_id,
                wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(6000)
        src = None
        try:
            src = pg.eval_on_selector("video", "el => el.src || (el.querySelector('source')||{}).src")
        except Exception:
            pass
        if not src:
            urls = re.findall(r'(https://[^"\']+\.mp4[^"\']*)', pg.content())
            src = urls[0] if urls else None
        info = {"aweme_id": aweme_id, "title": pg.title(), "video_src": src}
        if src:
            r = ctx.request.get(src, headers={"Referer": "https://www.douyin.com/"})
            with open(out, "wb") as f:
                f.write(r.body())
            info["saved"] = out
            info["bytes"] = os.path.getsize(out)
        with open(os.path.splitext(out)[0] + "_meta.json", "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)
        ctx.close(); b.close()
    print(json.dumps(info, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("search", "grab"):
        sp = sub.add_parser(name)
        sp.add_argument("--headed", action="store_true")
        sp.add_argument("--channel", default="chrome")
    s = sub.choices["search"]; s.add_argument("--kw-url", required=True); s.add_argument("--out", required=True)
    g = sub.choices["grab"]; g.add_argument("--aweme-id", required=True); g.add_argument("--out", required=True)
    args = ap.parse_args()
    global CHANNEL
    CHANNEL = args.channel or None
    if args.cmd == "search":
        run_search(args.kw_url, args.out, args.headed)
    else:
        run_grab(args.aweme_id, args.out, args.headed)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
