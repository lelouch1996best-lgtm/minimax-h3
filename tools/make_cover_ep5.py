# -*- coding: utf-8 -*-
"""第五集《一脚踹碎》三平台封面生成。

主体图= 用户指定的 `法天象地/第五集/第五集_备选_B.png`（鞋底压满画面、黄色标识居中，
喜剧感最强的那张）。
输出三规格：B站 16:9（1920×1080）／抖音 3:4／快手 3:4。

⚠️ B站 -111 教训：封面必须 8 位RGB PNG/JPG。源自 10-bit HEVC 的 48 位 rgb48be PNG
会让 `--cover` 在建稿前直接中止 —— 所以本脚本统一用 `-pix_fmt rgb24` 落盘。
"""
import os
import subprocess
import sys

FFMPEG = subprocess.run(
    [sys.executable, "-c", "import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())"],
    capture_output=True, text=True).stdout.strip()
FONT = "C\\:/Windows/Fonts/msyhbd.ttc"

SRC = r"D:/work/minimax_h3/法天象地/第五集/第五集_备选_B.png"
OUT = r"D:/work/minimax_h3/法天象地/发布"
TITLE = "一脚踹碎法天象地"
SUB = "西装大嘴鱼被打脸"


def run(dst, vf):
    cmd = [FFMPEG, "-y", "-hide_banner", "-i", SRC, "-vf", vf,
           "-frames:v", "1", "-update", "1", "-pix_fmt", "rgb24", dst]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("[X]", os.path.basename(dst), r.stderr[-1200:])
        return False
    print("[OK]", os.path.basename(dst), "%.0f KB" % (os.path.getsize(dst) / 1024))
    return True


def text_block(y_frac, fs_frac, fs2_frac):
    """标题+副标题居中，y_frac 为第一行y 位置（h 的比例），字号同样用 h 的比例表达式。"""
    return (
        f"drawtext=fontfile='{FONT}':text='{TITLE}':fontsize={fs_frac}:"
        f"fontcolor=0xFFFFFF:borderw=10:bordercolor=0x101010:"
        f"x=(w-text_w)/2:y={y_frac},"
        f"drawtext=fontfile='{FONT}':text='{SUB}':fontsize={fs2_frac}:"
        f"fontcolor=0xFFE500:borderw=10:bordercolor=0x101010:"
        f"x=(w-text_w)/2:y={y_frac}+h*0.085+22"
    )


def main():
    os.makedirs(OUT, exist_ok=True)
    src_w, src_h = 1152, 2048  # 2048×1152 竖图

    # ---- 抖音/快手 3:4：竖图居中，上下用模糊底填充
    #原图 1152×2048（≈9:16），目标 3:4（≈0.75）→ 竖图需按高度铺满、左右补模糊底
    port_vf = (
        "split=2[a][b];"
        "[a]scale=1200:1600,setsar=1,boxblur=24:12[bg];"
        f"[b]scale=-1:1600[fg];"
        "[bg][fg]overlay=(W-w)/2:0,"
        + text_block("h*0.10", "h/12", "h/15")
    )
    print("--- 抖音封面 3:4 ---")
    run(os.path.join(OUT, "封面_抖音.jpg"), port_vf)
    print("--- 快手封面 3:4 ---")
    run(os.path.join(OUT, "封面_快手.jpg"), port_vf)

    # ---- B站 16:9：竖图缩到高 1080 居中，两侧模糊底
    bili_vf = (
        "split=2[a][b];"
        "[a]scale=1920:1080,setsar=1,boxblur=28:14[bg];"
        "[b]scale=-1:1080[fg];"
        "[bg][fg]overlay=(W-w)/2:0,"
        "drawtext=fontfile='%s':text='%s':fontsize=86:"
        "fontcolor=0xFFFFFF:borderw=9:bordercolor=0x101010:"
        "x=(w-text_w)/2:y=h-290,"
        "drawtext=fontfile='%s':text='%s':fontsize=68:"
        "fontcolor=0xFFE500:borderw=9:bordercolor=0x101010:"
        "x=(w-text_w)/2:y=h-180" % (FONT, TITLE, FONT, SUB)
    )
    print("--- B站封面 16:9 ---")
    run(os.path.join(OUT, "封面_B站.jpg"), bili_vf)


if __name__ == "__main__":
    main()