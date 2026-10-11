# -*- coding: utf-8 -*-
"""幕沛灵「看够了吗」三平台封面：B站 16:9 / 抖音 3:4 / 快手 3:4。

沿用 旅游段子复刻/make_cover.py 配方：boxblur 底 + 居中主体 + drawtext borderw 描边。
注意坑（来自 make_cover_ep5.py）：
  - fontsize 比例必须全程用字符串表达式（fs*0.78 会报 can't multiply sequence by non-int）
  - 副标题另给一个比例参数
  - ffmpeg drawtext 的 fontfile 里Windows 盘符冒号必须转义：'C\\:/Windows/Fonts/msyhbd.ttc'
  - ffmpeg 不在 PATH，走 imageio_ffmpeg.get_ffmpeg_exe()
  - cv2 写不出中文路径 -> 抽帧交给 ffmpeg，成品核验另存 ASCII 名
"""
import os
import subprocess
import sys

FFMPEG = subprocess.run(
    [sys.executable, "-c", "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"],
    capture_output=True, text=True).stdout.strip()
FONT = "C\\:/Windows/Fonts/msyhbd.ttc"

VIDEO = r"D:/work/minimax_h3/南宫婉灵动表情/成片/1.mp4"
OUT = r"D:/work/minimax_h3/南宫婉灵动表情/发布"
SRC = os.path.join(OUT, "_src_cover.jpg")
T = 3.0   # Shot1 面部特写，眼神最足的一帧

TITLE = "看够了吗"
SUB = "南宫婉 · 幕沛灵"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print(r.stderr[-1500:])
        raise SystemExit("[X] ffmpeg 失败: %s" % " ".join(cmd[:6]))
    return r


def pick_frame():
    os.makedirs(OUT, exist_ok=True)
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-ss", str(T), "-i", VIDEO,
         "-frames:v", "1", "-q:v", "2", SRC])
    print("frame ->", SRC)


def texts(vf, y_title, y_sub, fs_t, fs_s):
    return (
        vf + ","
        "drawtext=fontfile='%s':text='%s':fontsize=%s:"
        "fontcolor=0xFFFFFF:borderw=10:bordercolor=0x101010:"
        "x=(w-text_w)/2:y=%s,"
        "drawtext=fontfile='%s':text='%s':fontsize=%s:"
        "fontcolor=0xFFE9A8:borderw=10:bordercolor=0x101010:"
        "x=(w-text_w)/2:y=%s" % (FONT, TITLE, fs_t, y_title, FONT, SUB, fs_s, y_sub)
    )


def cover_bili():
    """B站 16:9 —— 1920x1080，主体居中，boxblur 铺底。"""
    dst = os.path.join(OUT, "封面_B站.jpg")
    # 竖屏原片 1056x1920 -> 16:9 先裁上下再缩放，居中保留人物
    vf = ("split[bg][fg];"
          "[bg]scale=1920:1080:force_original_aspect_ratio=increase,"
          "crop=1920:1080,boxblur=28:2[bgb];"
          "[fg]scale=1920:-2[fgs];"
          "[bgb][fgs]overlay=(W-w)/2:(H-h)/2")
    vf = texts(vf, "h/2-h/13", "h/2-h/13+h/12", "h/11", "h/24")
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", SRC,
         "-vf", vf, "-frames:v", "1", "-q:v", "2", "-pix_fmt", "yuvj420p", dst])
    print("B站 ->", dst)


def cover_vertical(platform):
    """抖音/快手 3:4 —— 1200x1600。"""
    dst = os.path.join(OUT, "封面_%s.jpg" % platform)
    vf = ("scale=1200:1600:force_original_aspect_ratio=increase,"
          "crop=1200:1600")
    vf = texts(vf, "h/2-h/11", "h/2-h/11+h/12", "h/11", "h/26")
    run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", SRC,
         "-vf", vf, "-frames:v", "1", "-q:v", "2", "-pix_fmt", "yuvj420p", dst])
    print("%s ->" % platform, dst)


if __name__ == "__main__":
    pick_frame()
    cover_bili()
    cover_vertical("抖音")
    cover_vertical("快手")
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        print("  %-22s %8.1f KB" % (f, os.path.getsize(p) / 1024))
