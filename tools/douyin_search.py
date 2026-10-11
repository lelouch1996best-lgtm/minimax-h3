# -*- coding: utf-8 -*-
"""
抖音搜索 / 视频信息拉取（带本地 cookie）
用途：用 social-auto-upload 里已登录的抖音 cookie 调 Web 接口搜索视频，
      拿到 aweme_id / 文案 / 作者，供舞蹈复刻流水线当作「源舞」候选。

用法：
  python douyin_search.py --keyword "琵琶行舞蹈" --count 20
  python douyin_search.py --aweme-id 7430000000000000000     # 查单个视频详情
  python douyin_search.py --resolve "https://v.douyin.com/xxxx/"   # 解析短链

输出：JSON（stdout），字段见 print_result。
"""
import argparse
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import http.cookiejar

COOKIE_DIR = r"D:\work\social-auto-upload\cookies"
DEFAULT_COOKIE = os.path.join(COOKIE_DIR, "douyin_douyin_dance.json")

UA_PC = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
         "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def load_cookie_header(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    cookies = data.get("cookies", data if isinstance(data, list) else [])
    pairs = []
    seen = set()
    for c in cookies:
        dom = (c.get("domain") or "").lstrip(".")
        if "douyin.com" not in dom:
            continue
        name = c.get("name")
        if name in seen:
            continue
        seen.add(name)
        pairs.append("%s=%s" % (name, c.get("value", "")))
    return "; ".join(pairs)


def http_get(url, cookie_header, referer="https://www.douyin.com/", timeout=25):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA_PC,
        "Referer": referer,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9",
    })
    if cookie_header:
        req.add_header("Cookie", cookie_header)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {"_raw": raw[:2000].decode("utf-8", "replace")}


def search(keyword, cookie_header, count=20, offset=0):
    q = {
        "device_platform": "webapp",
        "aid": "6383",
        "channel": "channel_pc_web",
        "search_channel": "aweme_video_web",
        "keyword": keyword,
        "search_source": "normal_search",
        "query_correct_type": "1",
        "is_filter_search": "0",
        "offset": str(offset),
        "count": str(count),
        "pc_client_type": "1",
        "version_code": "170400",
        "version_name": "17.4.0",
        "cookie_enabled": "true",
        "platform": "PC",
        "browser_name": "Chrome",
        "browser_version": "120.0.0.0",
        "engine_name": "Blink",
        "os_name": "Windows",
        "os_version": "10",
    }
    url = "https://www.douyin.com/aweme/v1/web/general/search/single/?" + urllib.parse.urlencode(q)
    return http_get(url, cookie_header)


def aweme_detail(aweme_id, cookie_header):
    q = {
        "device_platform": "webapp",
        "aid": "6383",
        "aweme_id": str(aweme_id),
        "channel": "channel_pc_web",
        "pc_client_type": "1",
        "version_code": "170400",
        "version_name": "17.4.0",
        "cookie_enabled": "true",
        "platform": "PC",
        "browser_name": "Chrome",
        "browser_version": "120.0.0.0",
        "engine_name": "Blink",
        "os_name": "Windows",
        "os_version": "10",
    }
    url = "https://www.douyin.com/aweme/v1/web/aweme/detail/?" + urllib.parse.urlencode(q)
    return http_get(url, cookie_header)


def resolve_short(url, cookie_header):
    """短链 v.douyin.com/xxx -> 跟随跳转拿真实地址与 aweme_id"""
    req = urllib.request.Request(url, headers={"User-Agent": UA_PC, "Cookie": cookie_header or ""})
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    try:
        resp = opener.open(req, timeout=25)
        final = resp.geturl()
        html = resp.read(400000).decode("utf-8", "replace")
    except Exception as e:
        return {"_error": str(e)}
    ids = re.findall(r"/video/(\d{6,})", final + " " + html)
    return {"final_url": final, "aweme_ids": sorted(set(ids))}


def slim_items(resp):
    """从搜索结果里挑出有用的字段"""
    out = []
    for item in (resp.get("data") or []):
        aw = item.get("aweme_info") or {}
        if not aw:
            continue
        stats = aw.get("statistics") or {}
        dur = aw.get("duration") or 0
        out.append({
            "aweme_id": aw.get("aweme_id"),
            "desc": aw.get("desc"),
            "author": (aw.get("author") or {}).get("nickname"),
            "author_id": (aw.get("author") or {}).get("sec_uid"),
            "duration_s": round(dur / 1000.0, 1) if dur else None,
            "digg": stats.get("digg_count"),
            "comment": stats.get("comment_count"),
            "share": stats.get("share_count"),
            "create_time": aw.get("create_time"),
            "music": ((aw.get("music") or {}).get("title")),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword")
    ap.add_argument("--aweme-id")
    ap.add_argument("--resolve")
    ap.add_argument("--cookie", default=DEFAULT_COOKIE)
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--offset", type=int, default=0)
    ap.add_argument("--raw", action="store_true", help="输出原始 JSON（排障用）")
    args = ap.parse_args()

    ch = load_cookie_header(args.cookie)

    if args.resolve:
        print(json.dumps(resolve_short(args.resolve, ch), ensure_ascii=False, indent=2))
        return
    if args.aweme_id:
        resp = aweme_detail(args.aweme_id, ch)
        print(json.dumps(resp if args.raw else resp, ensure_ascii=False, indent=2)[:6000])
        return
    if args.keyword:
        resp = search(args.keyword, ch, args.count, args.offset)
        if args.raw:
            print(json.dumps(resp, ensure_ascii=False, indent=2)[:8000])
            return
        items = slim_items(resp)
        print(json.dumps({
            "status_code": resp.get("status_code"),
            "status_msg": resp.get("status_msg") or resp.get("status_msg"),
            "count": len(items),
            "items": items,
        }, ensure_ascii=False, indent=2))
        return
    ap.print_help()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
