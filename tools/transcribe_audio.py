#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""transcribe_audio.py — 用 APIMart whisper-1 转写本地音频（OpenAI 兼容 /audio/transcriptions）。

multipart/form-data 手工拼装（标准库）。
"""

import argparse
import json
import mimetypes
import os
import ssl
import sys
import time
import urllib.request
import uuid
from pathlib import Path

BASE = os.environ.get("APIMART_BASE_URL", "https://api.apib.ai/v1").rstrip("/")


def build_multipart(fields, file_field, file_path):
    boundary = "----wb" + uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f"--{boundary}\r\n".encode()
        out += f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode()
        out += f"{v}\r\n".encode()
    fname = Path(file_path).name
    ctype = mimetypes.guess_type(fname)[0] or "application/octet-stream"
    out += f"--{boundary}\r\n".encode()
    out += (f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{fname}"\r\n').encode("utf-8")
    out += f"Content-Type: {ctype}\r\n\r\n".encode()
    out += Path(file_path).read_bytes()
    out += f"\r\n--{boundary}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={boundary}"


def transcribe(audio, model="whisper-1", language="zh", prompt=None, timeout=900,
               granularity=None):
    """调用 whisper-1 转写单个音频文件，返回 verbose_json 字典。

    granularity: None（默认，用 segments）/ "word"（词级，返回 words，精度高得多，无 segments）
                 / "segment"（段级，实测被 5s 网格吸附，精度差）
    失败抛 RuntimeError。可供其他脚本 import 复用（av_align.py 即如此）。
    """
    key = os.environ.get("APIMART_API_KEY", "").strip()
    if not key:
        raise RuntimeError("未设置 APIMART_API_KEY")

    fields = {"model": model, "language": language,
              "response_format": "verbose_json"}
    if granularity:
        fields["timestamp_granularities[]"] = granularity
    if prompt:
        fields["prompt"] = prompt
    body, ctype = build_multipart(fields, "file", audio)

    req = urllib.request.Request(BASE + "/audio/transcriptions", data=body, method="POST")
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("Content-Type", ctype)

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            raw = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8','replace')[:500]}")
    except Exception as e:
        raise RuntimeError(f"{type(e).__name__}: {e}")

    try:
        return json.loads(raw)
    except ValueError:
        raise RuntimeError("非 JSON 响应: " + raw[:500])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio")
    ap.add_argument("--model", default="whisper-1")
    ap.add_argument("--language", default="zh")
    ap.add_argument("--prompt", help="提示词，可引导歌词/专有名词写法；"
                                     "传简体提示词可把输出从繁体拉到简体")
    ap.add_argument("--granularity", choices=["word", "segment"],
                    help="word = 词级时间戳（精度高，无 segments）；segment = 段级（会被 5s 吸附）")
    ap.add_argument("--words", action="store_true", help="同 --granularity word")
    ap.add_argument("--show-words", action="store_true", help="打印词级时间戳明细")
    ap.add_argument("--out", help="把结果写到这个文件")
    a = ap.parse_args()

    gran = a.granularity or ("word" if a.words else None)
    print(f"上传 {a.audio} ({Path(a.audio).stat().st_size/1e6:.1f} MB) ...", flush=True)
    t0 = time.time()
    try:
        d = transcribe(a.audio, model=a.model, language=a.language,
                       prompt=a.prompt, granularity=gran)
    except RuntimeError as e:
        print(f"ERR {e}", file=sys.stderr)
        return 1

    text = d.get("text") or ""
    segs = d.get("segments") or []
    words = d.get("words") or []
    print(f"耗时 {time.time()-t0:.1f}s，segments={len(segs)}，words={len(words)}，chars={len(text)}")
    if segs:
        for s in segs:
            t0s, t1s = s.get("start", 0), s.get("end", 0)
            print(f"  [{t0s:6.2f}-{t1s:6.2f}] {s.get('text','').strip()}")
    elif words:
        print("  (词级模式，无 segments；下面按 0.35s 静音间隔切句)")
        cur, out_lines = [], []
        for w in words:
            if cur and (w.get("start", 0) - cur[-1].get("end", 0)) > 0.35:
                out_lines.append(cur)
                cur = []
            cur.append(w)
        if cur:
            out_lines.append(cur)
        for ln in out_lines:
            print(f"  [{ln[0].get('start',0):6.2f}-{ln[-1].get('end',0):6.2f}] "
                  + "".join(w.get("word", "") for w in ln).strip())
        if a.show_words:
            for w in words:
                print(f"    {w.get('start',0):6.2f}-{w.get('end',0):6.2f} {w.get('word','')}")
    else:
        print(text)
    if a.out:
        Path(a.out).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"-> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
