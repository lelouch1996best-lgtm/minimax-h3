#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extract frames from a video using OpenCV only.

Design rule (固化): on this machine the ffmpeg on PATH is a stripped build
without the image2 muxer and cannot write image frames. Probing ffmpeg first
wastes several failed attempts every time, so this script uses cv2 directly.
Do NOT add ffmpeg probing/extraction here.

Modes:
  --count N            N evenly spaced timestamps across the whole clip
  --interval S         one frame every S seconds
  --times a,b,c        explicit timestamps (seconds)
  --first / --last     only the first / last frame
  --sheet              build a contact sheet instead of individual files
"""
import argparse
import math
import os
import sys

import cv2


def open_video(path):
    if not os.path.isfile(path):
        sys.exit(f"video not found: {path}")
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        sys.exit(f"cannot open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total / fps if fps else 0.0
    print(f"fps={fps:g} frames={total} size={width}x{height} duration={duration:.2f}s")
    return cap, fps, total, width, height, duration


def read_at_index(cap, idx, total):
    """Seek to frame idx and read it; fall back near the real last frame."""
    idx = max(0, min(idx, total - 1))
    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
    ok, frame = cap.read()
    if ok:
        return frame, idx
    # Some containers report a frame count one or two frames too high.
    for back in range(idx, max(0, idx - 10), -1):
        cap.set(cv2.CAP_PROP_POS_FRAMES, back)
        ok, frame = cap.read()
        if ok:
            return frame, back
    return None, idx


def resize_to_height(frame, height):
    if height and height > 0:
        h, w = frame.shape[:2]
        if h != height:
            scale = height / h
            frame = cv2.resize(frame, (max(1, int(round(w * scale))), height))
    return frame


def timestamp_name(t):
    mm = int(t // 60)
    ss = t - mm * 60
    return f"t{mm:02d}m{ss:04.1f}s"


def resolve_timestamps(args, duration, fps, total):
    if args.times:
        return [float(x) for x in args.times.split(",") if x.strip() != ""]
    if args.first:
        return [0.0]
    if args.last:
        return [max(0.0, (total - 1) / fps)]
    if args.interval and args.interval > 0:
        ts = []
        t = 0.0
        while t < duration:
            ts.append(round(t, 3))
            t += args.interval
        if not ts or abs(ts[-1] - duration) > 1e-6:
            ts.append(round(max(0.0, duration - 1.0 / fps), 3))
        return ts
    # default: evenly spaced, include first and last frame
    n = max(1, args.count)
    if n == 1:
        return [0.0]
    return [round((total - 1) * i / (n - 1) / fps, 3) for i in range(n)]


def write_frame(frame, out_dir, name, png):
    ext = ".png" if png else ".jpg"
    path = os.path.join(out_dir, name + ext)
    if png:
        cv2.imwrite(path, frame)
    else:
        cv2.imwrite(path, frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return path


def annotate(frame, text, scale=0.8):
    annotated = frame.copy()
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, 2)
    cv2.rectangle(annotated, (0, 0), (tw + 16, th + 14), (0, 0, 0), -1)
    cv2.putText(annotated, text, (8, th + 6), cv2.FONT_HERSHEY_SIMPLEX,
                scale, (255, 255, 255), 2, cv2.LINE_AA)
    return annotated


def build_sheet(frames, cols, sheet_width, out_dir):
    if not frames:
        sys.exit("no frames for contact sheet")
    thumbs = []
    ph = 0
    for frame, label in frames:
        h, w = frame.shape[:2]
        th_height = max(1, int(round(h * sheet_width / w)))
        thumb = cv2.resize(frame, (sheet_width, th_height))
        thumb = annotate(thumb, label)
        thumbs.append(thumb)
        ph = max(ph, thumb.shape[0])
    rows = math.ceil(len(thumbs) / cols)
    pad = 8
    sheet = [0, 0, 0]
    canvas_h = rows * ph + (rows + 1) * pad
    canvas_w = cols * sheet_width + (cols + 1) * pad
    canvas = None
    import numpy as np
    canvas = np.full((canvas_h, canvas_w, 3), 30, dtype=np.uint8)
    for i, thumb in enumerate(thumbs):
        r, c = divmod(i, cols)
        y = pad + r * (ph + pad)
        x = pad + c * (sheet_width + pad)
        canvas[y:y + thumb.shape[0], x:x + sheet_width] = thumb
    path = os.path.join(out_dir, "contact_sheet.jpg")
    cv2.imwrite(path, canvas, [cv2.IMWRITE_JPEG_QUALITY, 88])
    return path


def main():
    parser = argparse.ArgumentParser(
        description="Extract frames from a video with OpenCV (no ffmpeg).")
    parser.add_argument("--video", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--count", type=int, default=5,
                        help="evenly spaced frame count (default 5)")
    parser.add_argument("--interval", type=float, default=0.0,
                        help="fixed seconds between frames")
    parser.add_argument("--times", default="", help="comma-separated seconds")
    parser.add_argument("--first", action="store_true")
    parser.add_argument("--last", action="store_true")
    parser.add_argument("--sheet", action="store_true",
                        help="write one contact sheet")
    parser.add_argument("--cols", type=int, default=3)
    parser.add_argument("--sheet-width", type=int, default=360)
    parser.add_argument("--height", type=int, default=0,
                        help="resize frames to this height (0 = original)")
    parser.add_argument("--png", action="store_true")
    parser.add_argument("--name", default="",
                        help="filename prefix for --first/--last")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    cap, fps, total, width, height, duration = open_video(args.video)

    timestamps = resolve_timestamps(args, duration, fps, total)
    single = args.first or args.last

    sheet_items = []
    written = []
    for t in timestamps:
        idx = int(round(t * fps))
        frame, real_idx = read_at_index(cap, idx, total)
        if frame is None:
            print(f"SKIP t={t:g}s (read failed)")
            continue
        frame = resize_to_height(frame, args.height)
        real_t = real_idx / fps if fps else t
        if single and args.name:
            name = args.name
        else:
            name = timestamp_name(real_t)
        if args.sheet:
            sheet_items.append((frame, f"{real_t:g}s"))
        else:
            path = write_frame(frame, args.out, name, args.png)
            written.append(path)
            print("OK", path)
    cap.release()

    if args.sheet:
        path = build_sheet(sheet_items, max(1, args.cols),
                           max(64, args.sheet_width), args.out)
        print(f"SHEET {path} ({len(sheet_items)} frames)")
    print(f"done: {len(written) if not args.sheet else len(sheet_items)} frame(s)")


if __name__ == "__main__":
    main()
