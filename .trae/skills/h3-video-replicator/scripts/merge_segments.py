# -*- coding: utf-8 -*-
"""Concatenate H3-generated segment videos into a single final video.

Priority: ffmpeg concat demuxer + -c copy (lossless, same-codec segments)
Fallback: OpenCV soft merge (re-encodes, only used when ffmpeg unavailable)
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import cv2

from extract_frames import find_working_ffmpeg


def parse_segment_list(path):
    """Parse ffmpeg concat list file lines like: file 'C:\\path\\to\\seg.mp4'"""
    segments = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            line = raw.strip().lstrip("\ufeff")  # strip BOM and whitespace
            if not line or line.startswith("#"):
                continue
            m = re.match(r"file\s+['\"](.+?)['\"]", line)
            if m:
                segments.append(m.group(1))
            else:
                # Allow plain paths too
                segments.append(line)
    if not segments:
        raise SystemExit(f"no segments found in {path}")
    for s in segments:
        if not os.path.isfile(s):
            raise SystemExit(f"segment not found: {s}")
    return segments


def ffprobe_stream_info(ffmpeg_root, video):
    """Return dict with width, height, fps, codec_name, pix_fmt."""
    ffprobe = os.path.join(os.path.dirname(ffmpeg_root), "ffprobe.exe")
    if not os.path.isfile(ffprobe):
        # Try PATH ffprobe
        ffprobe = shutil.which("ffprobe") or ffprobe
    cmd = [
        ffprobe, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,codec_name,pix_fmt",
        "-of", "json", video
    ]
    out = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    data = json.loads(out)
    stream = data["streams"][0]
    num, den = stream["r_frame_rate"].split("/")
    fps = float(num) / float(den) if int(den) else 0.0
    return {
        "width": stream.get("width"),
        "height": stream.get("height"),
        "fps": fps,
        "codec_name": stream.get("codec_name"),
        "pix_fmt": stream.get("pix_fmt"),
    }


def merge_with_ffmpeg(ffmpeg, segments, out_path):
    """Use ffmpeg concat demuxer with stream copy."""
    with tempfile.TemporaryDirectory() as tmp:
        list_file = os.path.join(tmp, "concat_list.txt")
        with open(list_file, "w", encoding="utf-8") as f:
            for s in segments:
                # ffmpeg concat demuxer requires escaping single quotes in path
                safe = s.replace("'", "'\\''")
                f.write(f"file '{safe}'\n")
        cmd = [ffmpeg, "-f", "concat", "-safe", "0", "-i", list_file,
               "-c", "copy", "-movflags", "+faststart", "-y", out_path]
        subprocess.run(cmd, check=True)
    print(f"merged (ffmpeg -c copy): {out_path}")


def merge_with_opencv(segments, out_path):
    """Fallback: read all segments and write a single mp4 with OpenCV."""
    print("ffmpeg unavailable; falling back to OpenCV soft merge (re-encodes).", file=sys.stderr)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = None
    for seg in segments:
        cap = cv2.VideoCapture(seg)
        if not cap.isOpened():
            raise SystemExit(f"cannot open segment: {seg}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if writer is None:
            writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))
            if not writer.isOpened():
                raise SystemExit(f"cannot open video writer: {out_path}")
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            writer.write(frame)
        cap.release()
    writer.release()
    print(f"merged (OpenCV fallback): {out_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Concatenate H3 segment videos into one final video. Uses ffmpeg -c copy if possible.")
    parser.add_argument("--list", required=True, help="ffmpeg concat list text file")
    parser.add_argument("--out", required=True, help="Output final video path")
    parser.add_argument("--skip-consistency-check", action="store_true",
                        help="Skip ffprobe consistency check (use only if you know segments match)")
    args = parser.parse_args()

    segments = parse_segment_list(args.list)
    print(f"segments to merge: {len(segments)}")

    ffmpeg = find_working_ffmpeg()

    if ffmpeg and not args.skip_consistency_check:
        infos = [ffprobe_stream_info(ffmpeg, s) for s in segments]
        base = infos[0]
        mismatches = []
        for i, info in enumerate(infos[1:], start=2):
            for key in ("width", "height", "fps", "codec_name", "pix_fmt"):
                if info[key] != base[key]:
                    mismatches.append(f"  segment {i} {key}={info[key]} vs segment 1 {key}={base[key]}")
        if mismatches:
            print("ERROR: segment parameters do not match; -c copy would fail.", file=sys.stderr)
            print("\n".join(mismatches), file=sys.stderr)
            print("\nTo re-encode instead, run:", file=sys.stderr)
            print(f"  ffmpeg -f concat -safe 0 -i {args.list} -c libx264 -pix_fmt yuv420p -y {args.out}", file=sys.stderr)
            raise SystemExit(1)

    if ffmpeg:
        merge_with_ffmpeg(ffmpeg, segments, args.out)
    else:
        merge_with_opencv(segments, args.out)


if __name__ == "__main__":
    main()
