#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
new_music.py — APIMart 音乐生成固化脚本（Flow Music / Suno V6）

把「提交任务 -> 轮询状态 -> 下载音频 -> 可选剪辑」固化为一条命令，
仅依赖 Python 标准库；剪辑时优先使用 imageio_ffmpeg 自带的完整 ffmpeg。

典型用法：
  # 1) Flow Music 纯音乐（最常用）
  python new_music.py --title "E01 BGM" \
      --prompt "playful sweet acoustic guitar and ukulele, instrumental, no vocals" \
      --bpm 100 --length 30 --out "D:\\bgm" --trim 30.4

  # 2) Suno V6 纯音乐
  python new_music.py --model suno --version v6 --instrumental \
      --prompt "warm healing piano and strings, gentle, no vocals" --out "D:\\bgm"

  # 3) 只查询已有任务并下载（不扣费）
  python new_music.py --query task_01M2QY47C32MF0F1D05BY06W97 --out "D:\\bgm"

  # 4) 只看请求体，不真正提交
  python new_music.py --title test --prompt "piano, instrumental" --dry-run
"""

import argparse
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE_URL = "https://api.apimart.ai/v1"
TERMINAL_STATUSES = {"completed", "failed"}
# 提交后任务可能短暂查不到（实测现象），在此宽限期内 404 视为暂时现象
NOT_FOUND_GRACE_SECONDS = 60
# 本机常见代理端口（Clash 等），api.apimart.ai 在国内网络可能需要代理
LOCAL_PROXY_CANDIDATES = ["http://127.0.0.1:7890"]


class ApiError(Exception):
    def __init__(self, http_status, code, message):
        self.http_status = http_status
        self.code = code
        self.message = message
        super().__init__(f"[HTTP {http_status}] {code}: {message}")


def eprint(*args):
    print(*args, file=sys.stderr, flush=True)


def _proxy_alive(proxy_url):
    """快速探测本地代理端口是否在监听（超时 0.3s）。"""
    m = re.match(r"https?://([^:/]+):(\d+)", proxy_url)
    if not m:
        return False
    host, port = m.group(1), int(m.group(2))
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        try:
            s.connect((host, port))
            return True
        except OSError:
            return False


def _build_opener():
    """优先尊重标准代理环境变量；未设置时自动探测本地 Clash 端口；否则直连。"""
    if os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY"):
        return urllib.request.build_opener()  # urlopen 默认读取 *_PROXY
    for proxy in LOCAL_PROXY_CANDIDATES:
        if _proxy_alive(proxy):
            eprint(f"检测到本地代理 {proxy}，已启用。")
            handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
            return urllib.request.build_opener(handler)
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


OPENER = None


def opener():
    global OPENER
    if OPENER is None:
        OPENER = _build_opener()
    return OPENER


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
def api_request(method, path, api_key, body=None, timeout=60):
    url = BASE_URL + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    try:
        with opener().open(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        code, message = None, raw
        try:
            parsed = json.loads(raw)
            err = parsed.get("error") or parsed
            code = err.get("code")
            message = err.get("message", raw)
        except (ValueError, AttributeError):
            pass
        raise ApiError(e.code, code, message)
    except urllib.error.URLError as e:
        raise ConnectionError(f"网络错误：{e.reason}") from e


def submit_generation(payload, api_key):
    """提交收费请求。网络层失败时不自动重发，避免重复扣费。"""
    try:
        resp = api_request("POST", "/music/generations", api_key, body=payload)
    except ConnectionError:
        raise ConnectionError(
            "提交任务时网络中断，为避免重复扣费未自动重试；"
            "请稍后到 APIMart 后台确认是否已生成任务，再用 --query 查询。"
        )
    data = resp.get("data") or []
    if not data or not data[0].get("task_id"):
        raise RuntimeError(f"提交成功但未返回 task_id，响应：{resp}")
    return data[0]["task_id"]


def poll_task(task_id, api_key, interval, timeout):
    """轮询任务直到 completed/failed。GET 幂等，可安全重试。"""
    path = f"/music/tasks/{task_id}?language=zh"
    deadline = time.time() + timeout
    not_found_first_seen = None
    while True:
        try:
            resp = api_request("GET", path, api_key)
        except ApiError as e:
            if e.http_status == 404:
                now = time.time()
                not_found_grace = True
                if not_found_first_seen is None:
                    not_found_first_seen = now
                if now - not_found_first_seen < NOT_FOUND_GRACE_SECONDS:
                    eprint("任务刚提交、暂不可查，5 秒后重试…")
                    time.sleep(5)
                    continue
                raise ApiError(
                    404, e.code or "task_not_found",
                    f"任务持续不可查（超过 {NOT_FOUND_GRACE_SECONDS}s）：{e.message}",
                )
            if e.http_status in (429, 500, 502, 503, 504):
                eprint(f"服务暂时不可用（{e.code}），{interval}s 后重试…")
                _sleep_or_timeout(deadline, interval)
                continue
            raise
        data = resp.get("data", resp)
        status = (data.get("status") or "").lower()
        progress = data.get("progress")
        eprint(f"[{task_id}] status={status}" +
               (f" progress={progress}%" if progress is not None else ""))
        if status == "completed":
            return data
        if status == "failed":
            err = data.get("error") or {}
            raise RuntimeError(f"生成失败：{err.get('message', data)}")
        if status in ("pending", "processing", "unknown", "submitted", ""):
            _sleep_or_timeout(deadline, interval)
            continue
        # 未见过的状态也继续等，但用稍长间隔
        eprint(f"未知状态 {status!r}，继续等待…")
        _sleep_or_timeout(deadline, max(interval, 10))


def _sleep_or_timeout(deadline, seconds):
    if time.time() + seconds > deadline:
        raise TimeoutError("轮询超时，任务仍未完成；可稍后用 --query <task_id> 继续查询。")
    time.sleep(seconds)


# --------------------------------------------------------------------------- #
# 下载
# --------------------------------------------------------------------------- #
def download(url, dest):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with opener().open(url, timeout=300) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)
    return dest


def pick_ext(url, default):
    m = re.search(r"\.(m4a|mp3|wav|aac|flac)(?:\?|$)", url.lower())
    return "." + m.group(1) if m else default


def download_results(data, stem, out_dir):
    """从 result.music[] 下载全部音频/封面，返回 {种类: 路径}。"""
    music_list = ((data.get("result") or {}).get("music")) or []
    saved = {}
    for i, track in enumerate(music_list, start=1):
        suffix = "" if len(music_list) == 1 else f"_{i}"
        links = {
            "m4a": track.get("audio_url"),
            "wav": track.get("wav_url"),
            "cover": track.get("image_url") or track.get("image_large_url"),
        }
        for kind, url in links.items():
            if not url:
                continue
            if kind == "cover":
                ext = pick_ext(url, ".jpg")
                dest = out_dir / f"{stem}{suffix}_cover{ext}"
            elif kind == "m4a":
                dest = out_dir / f"{stem}{suffix}{pick_ext(url, '.m4a')}"
            else:
                dest = out_dir / f"{stem}{suffix}{pick_ext(url, '.wav')}"
            eprint(f"下载 {kind} -> {dest.name}")
            download(url, dest)
            saved.setdefault(kind, []).append(dest)
    return saved


# --------------------------------------------------------------------------- #
# ffmpeg 剪辑
# --------------------------------------------------------------------------- #
def find_ffmpeg():
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and Path(exe).exists():
            return exe
    except ImportError:
        pass
    exe = shutil.which("ffmpeg")
    if exe:
        # 校验是否具备 aac 编码器（TRAE 自带精简版没有）
        try:
            r = subprocess.run([exe, "-hide_banner", "-encoders"],
                               capture_output=True, text=True, timeout=20)
            if "aac" in r.stdout:
                return exe
        except (subprocess.SubprocessError, OSError):
            pass
    return None


def trim_audio(ffmpeg, src, seconds, fade_in, fade_out, make_wav=True):
    """截取前 seconds 秒并加淡入淡出，返回输出路径列表。"""
    if fade_in + fade_out > seconds:
        raise ValueError("淡入+淡出时长不能超过总时长")
    fade_out_start = round(seconds - fade_out, 3)
    af = f"afade=t=in:st=0:d={fade_in},afade=t=out:st={fade_out_start}:d={fade_out}"
    outputs = [src.with_name(f"{src.stem}-{seconds}s.m4a")]
    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
           "-i", str(src), "-t", str(seconds), "-af", af,
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
           str(outputs[0])]
    subprocess.run(cmd, check=True)
    if make_wav:
        wav_out = src.with_name(f"{src.stem}-{seconds}s.wav")
        subprocess.run([ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                        "-i", str(src), "-t", str(seconds), "-af", af,
                        "-ar", "48000", "-c:a", "pcm_s16le", str(wav_out)],
                       check=True)
        outputs.append(wav_out)
    return outputs


# --------------------------------------------------------------------------- #
# 请求体构造
# --------------------------------------------------------------------------- #
def read_text_file(path):
    return Path(path).read_text(encoding="utf-8").strip()


def build_flowmusic_payload(a):
    if not a.prompt and not a.lyrics and not a.lyrics_file:
        raise ValueError("Flow Music 要求 --prompt 与 --lyrics 至少提供一个")
    payload = {"model": "flowmusic"}
    if a.title:
        payload["title"] = a.title
    if a.prompt:
        payload["sound_prompt"] = a.prompt
    lyrics = a.lyrics or (read_text_file(a.lyrics_file) if a.lyrics_file else None)
    if lyrics:
        payload["lyrics"] = lyrics
    if a.bpm is not None:
        if a.bpm < 1:
            raise ValueError("--bpm 必须 >= 1")
        payload["bpm"] = str(a.bpm)
    if a.length is not None:
        if not 1 <= a.length <= 240:
            raise ValueError("Flow Music --length 范围 1~240 秒（参考值，实际可能更长）")
        payload["length"] = a.length
    if a.seed:
        payload["seed"] = str(a.seed)
    return payload


def build_suno_payload(a):
    if not a.custom_model_id and not a.version:
        raise ValueError("Suno 必须提供 --version（v6/v6-wild/v6-mini）或 --custom-model-id")
    if a.version and a.custom_model_id:
        raise ValueError("--version 与 --custom-model-id 互斥，只能给一个")
    if a.duration is not None and not a.custom:
        raise ValueError("--duration 仅在 --custom（自定义模式）下可用，范围 10~360")
    payload = {"model": "suno", "version": a.version or a.custom_model_id,
               "custom": a.custom, "instrumental": a.instrumental}
    if a.prompt:
        payload["prompt"] = a.prompt
    if a.custom:
        if a.title:
            payload["title"] = a.title[:80]
        if a.style:
            payload["style"] = a.style[:1000]
        if a.negative_tags:
            payload["negative_tags"] = a.negative_tags
        if a.duration is not None:
            if not 10 <= a.duration <= 360:
                raise ValueError("--duration 范围 10~360 秒")
            payload["duration"] = a.duration
        if a.max_mode:
            payload["max_mode"] = True
    if a.vocal_gender:
        payload["vocal_gender"] = a.vocal_gender
    for flag, key in ((a.style_weight, "style_weight"),
                      (a.weirdness, "weirdness_constraint"),
                      (a.audio_weight, "audio_weight")):
        if flag is not None:
            if not 0 <= flag <= 1:
                raise ValueError(f"{key} 范围 0~1")
            payload[key] = flag
    if a.variety:
        payload["variety"] = a.variety
    if a.audio_format:
        payload["audio_format"] = a.audio_format
    # 纯音乐/灵感模式下 prompt 的基本校验
    if not a.custom and not a.prompt and not a.instrumental:
        raise ValueError("Suno 灵感模式必须提供 --prompt（纯音乐可同时加 --instrumental）")
    return payload


def safe_stem(title, task_id):
    stem = re.sub(r'[\\/:*?"<>|\s]+', "_", (title or "").strip()).strip("_")
    return stem[:60] or task_id


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def main():
    p = argparse.ArgumentParser(
        description="APIMart 音乐生成（Flow Music / Suno V6），环境变量 APIMART_API_KEY 提供密钥")
    p.add_argument("--model", choices=["flowmusic", "suno"], default="flowmusic")
    p.add_argument("--query", metavar="TASK_ID", help="只查询并下载已有任务，不提交新任务")
    p.add_argument("--dry-run", action="store_true", help="打印请求体后退出，不提交")

    p.add_argument("--title", help="标题")
    p.add_argument("--prompt", help="风格/声音描述（Flow Music 的 sound_prompt；Suno 的 prompt）")
    p.add_argument("--lyrics", help="歌词文本（内联）")
    p.add_argument("--lyrics-file", help="歌词文件路径（UTF-8）")
    p.add_argument("--bpm", type=int, help="Flow Music BPM，>=1")
    p.add_argument("--length", type=int, help="Flow Music 目标时长（秒，1~240，参考值）")
    p.add_argument("--seed", help="Flow Music 随机种子")

    p.add_argument("--version", default="v6", help="Suno 版本 v6/v6-wild/v6-mini（默认 v6）")
    p.add_argument("--custom-model-id", help="Suno 自定义模型 UUID（与 --version 互斥）")
    p.add_argument("--custom", action="store_true", help="Suno 自定义模式（prompt 作歌词）")
    p.add_argument("--instrumental", action="store_true", help="Suno 纯音乐")
    p.add_argument("--style", help="Suno 自定义模式风格标签")
    p.add_argument("--negative-tags", help="Suno 负向风格标签")
    p.add_argument("--vocal-gender", choices=["Male", "Female", "male", "female", "m", "f"])
    p.add_argument("--style-weight", type=float)
    p.add_argument("--weirdness", type=float, help="Suno 创意度 0~1")
    p.add_argument("--audio-weight", type=float)
    p.add_argument("--variety", choices=["off", "normal", "high", "extra", "max"])
    p.add_argument("--max-mode", action="store_true", help="Suno Max 模式（2 倍计费）")
    p.add_argument("--audio-format", choices=["mp3", "m4a", "wav"])
    p.add_argument("--duration", type=int, help="Suno 自定义模式目标时长 10~360")

    p.add_argument("--out", default=".", help="输出目录（默认当前目录）")
    p.add_argument("--no-download", action="store_true", help="只轮询，不下载音频")
    p.add_argument("--trim", type=float, metavar="SECONDS", help="下载后截取前 N 秒并淡入淡出")
    p.add_argument("--fade-in", type=float, default=0.5)
    p.add_argument("--fade-out", type=float, default=1.4)
    p.add_argument("--no-wav", action="store_true", help="剪辑时不额外输出 wav")
    p.add_argument("--interval", type=float, default=10, help="轮询间隔秒（默认 10）")
    p.add_argument("--timeout", type=int, default=600, help="轮询超时秒（默认 600）")
    a = p.parse_args()
    out_dir = Path(a.out)

    # dry-run 不联网、不需要密钥，先构造请求体并退出
    if a.dry_run:
        payload = build_suno_payload(a) if a.model == "suno" else build_flowmusic_payload(a)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    api_key = os.environ.get("APIMART_API_KEY", "").strip()
    if not api_key:
        eprint("错误：未找到环境变量 APIMART_API_KEY。请先设置用户级环境变量后重试。")
        return 2

    # --- 只查询 ---
    if a.query:
        data = poll_task(a.query, api_key, a.interval, a.timeout)
        return after_poll(data, safe_stem(a.title, a.query), out_dir, a, task_id=a.query)
    if a.model == "flowmusic" and a.length:
        eprint("提示：length 为参考值，实际时长可能更长（实测 30 -> 58.8s），可用 --trim 精修。")

    # --- 提交并轮询（提交不做自动重试，避免重复扣费） ---
    payload = build_suno_payload(a) if a.model == "suno" else build_flowmusic_payload(a)
    task_id = submit_generation(payload, api_key)
    eprint(f"已提交任务：{task_id}")
    data = poll_task(task_id, api_key, a.interval, a.timeout)
    return after_poll(data, safe_stem(a.title, task_id), out_dir, a, task_id)


def after_poll(data, stem, out_dir, a, task_id):
    music = ((data.get("result") or {}).get("music")) or []
    duration = None
    if music:
        m0 = music[0]
        duration = m0.get("duration_seconds") or m0.get("duration")
    cost = data.get("cost")
    credits = data.get("credits_cost")
    eprint("生成完成" +
           (f"，时长 {duration}s" if duration else "") +
           (f"，费用 ${cost}（{credits} credits）" if cost is not None else ""))

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{stem}.result.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    if a.no_download:
        print(json.dumps({"task_id": data.get("id") or task_id, "duration": duration,
                          "cost": cost, "credits_cost": credits,
                          "music": music}, ensure_ascii=False, indent=2))
        return 0

    saved = download_results(data, stem, out_dir)

    trimmed = []
    if a.trim:
        ffmpeg = find_ffmpeg()
        if not ffmpeg:
            eprint("警告：未找到带 aac 编码器的 ffmpeg，跳过剪辑；音频已下载。")
        else:
            src = (saved.get("m4a") or [None])[0]
            if src:
                trimmed = trim_audio(ffmpeg, src, a.trim, a.fade_in, a.fade_out,
                                     make_wav=not a.no_wav)

    report = {
        "task_id": data.get("id") or task_id,
        "duration_seconds": duration,
        "cost": cost,
        "credits_cost": credits,
        "downloaded": [str(p) for files in saved.values() for p in files],
        "trimmed": [str(p) for p in trimmed],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ApiError, ConnectionError, TimeoutError, RuntimeError, ValueError,
            FileNotFoundError, subprocess.CalledProcessError) as e:
        eprint(f"错误：{e}")
        sys.exit(1)
