# -*- coding: utf-8 -*-
"""Extract representative frames from a reference video.

Priority: ffmpeg (fast native decode)
Fallback: OpenCV (works out-of-the-box when ffmpeg is unavailable)

On this machine there are multiple ffmpeg executables:
  - TRAE's bundled ffmpeg on PATH: cannot write image sequences (no image2 muxer)
  - C:\Program Files (x86)\M_IMG2SCREEN_LY360\ffmpeg.exe: CAN write png/jpg frames
The script auto-discovers and tests candidates, then falls back to OpenCV.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

import cv2


def _can_extract_image(ffmpeg):
    """Probe whether this ffmpeg build can write a single PNG frame."""
    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "probe.png")
        try:
            subprocess.run(
                [ffmpeg, "-f", "lavfi", "-i", "color=c=black:s=32x32:d=0.1",
                 "-frames:v", "1", out],
                check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10
            )
            return os.path.isfile(out) and os.path.getsize(out) > 0
        except Exception:
            return False


def find_working_ffmpeg():
    """Return the full path to a usable ffmpeg that can output image frames."""
    candidates = []

    # PATH first
    path_exe = shutil.which("ffmpeg")
    if path_exe:
        candidates.append(path_exe)

    # Common absolute locations
    candidates += [
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\M_IMG2SCREEN_LY360\ffmpeg.exe",
        os.path.expanduser(r"~\.trae-cn\ffmpeg\ffmpeg.exe"),
    ]

    seen = set()
    for c in candidates:
        if not c or not os.path.isfile(c):
            continue
        c = os.path.abspath(c)
        if c in seen:
            continue
        seen.add(c)
        if _can_extract_image(c):
            return c
    return None


def extract_with_ffmpeg(ffmpeg, video, out_dir, interval, start, height):
    """Use ffmpeg to dump one frame every `interval` seconds.

    Uses -f image2 to force the image2 muxer, which works even when
    TRAE's bundled ffmpeg would otherwise refuse to infer the format.
    """
    os.makedirs(out_dir, exist_ok=True)

    # scale filter: keep aspect ratio, target height = requested (even number)
    step = int(round(interval * 24))
    if height > 0:
        vf = f"select='not(mod(n\\,{step}))',scale=-2:{height}"
    else:
        vf = f"select='not(mod(n\\,{step}))'"

    # If start > 0, skip the beginning
    input_args = ["-ss", str(start)] if start > 0 else []

    tmp_pattern = os.path.join(out_dir, "tmp_frame_%04d.jpg")
    cmd = [ffmpeg, *input_args, "-i", video, "-vf", vf, "-vsync", "vfr",
           "-f", "image2", "-q:v", "2", tmp_pattern]
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    # ffmpeg outputs generic sequential names; rename to timestamp-based names
    files = sorted(f for f in os.listdir(out_dir) if f.startswith("tmp_frame_") and f.endswith(".jpg"))
    count = 0
    t = start
    for old in files:
        new_name = f"f_{int(t // 60):02d}_{int(t % 60):02d}s.jpg"
        os.rename(os.path.join(out_dir, old), os.path.join(out_dir, new_name))
        count += 1
        t += interval
    return count


def extract_with_opencv(video, out_dir, interval, start, height):
    """Pure OpenCV fallback. Always works as long as cv2 can open the video."""
    os.makedirs(out_dir, exist_ok=True)

    cap = cv2.VideoCapture(video)
    if not cap.isOpened():
        raise SystemExit(f"cannot open video: {video}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total / fps if fps else 0.0
    print(f"fps={fps}, frames={total}, duration={duration:.2f}s")

    count = 0
    t = start
    while t < duration:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ret, frame = cap.read()
        if not ret:
            break
        h, w = frame.shape[:2]
        if height and h != height:
            scale = height / h
            frame = cv2.resize(frame, (int(w * scale), height))
        name = f"f_{int(t // 60):02d}_{int(t % 60):02d}s.jpg"
        cv2.imwrite(os.path.join(out_dir, name), frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        count += 1
        t += interval

    cap.release()
    return count


def main():
    parser = argparse.ArgumentParser(
        description="Extract frames from a video at a fixed interval. Prefers a working ffmpeg, falls back to OpenCV.")
    parser.add_argument("--video", required=True, help="Path to the source video")
    parser.add_argument("--out", required=True, help="Output directory for JPEG frames")
    parser.add_argument("--interval", type=float, default=4.0, help="Seconds between frames")
    parser.add_argument("--start", type=float, default=0.0, help="First timestamp to grab (seconds)")
    parser.add_argument("--height", type=int, default=480, help="Resize frames to this height (0 = keep original)")
    parser.add_argument("--backend", choices=["auto", "ffmpeg", "opencv"], default="auto",
                        help="Frame extraction backend")
    args = parser.parse_args()

    if args.backend == "opencv":
        count = extract_with_opencv(args.video, args.out, args.interval, args.start, args.height)
        print(f"extracted {count} frames (OpenCV) to {args.out}")
        return

    if args.backend in ("auto", "ffmpeg"):
        ffmpeg = find_working_ffmpeg()
        if ffmpeg:
            print(f"using ffmpeg: {ffmpeg}")
            try:
                count = extract_with_ffmpeg(ffmpeg, args.video, args.out, args.interval, args.start, args.height)
                print(f"extracted {count} frames (ffmpeg) to {args.out}")
                return
            except subprocess.CalledProcessError as e:
                print(f"ffmpeg failed ({e.returncode}), falling back to OpenCV", file=sys.stderr)
                if e.stderr:
                    print(e.stderr.decode("utf-8", errors="ignore")[-500:], file=sys.stderr)
        elif args.backend == "ffmpeg":
            raise SystemExit("no working ffmpeg found; use --backend opencv or install ffmpeg")

    print("using OpenCV fallback")
    count = extract_with_opencv(args.video, args.out, args.interval, args.start, args.height)
    print(f"extracted {count} frames (OpenCV) to {args.out}")


if __name__ == "__main__":
    main()
