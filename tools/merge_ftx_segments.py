# -*- coding: utf-8 -*-
"""法天象地四段（FTX01—FTX04）流拷贝合并。

四段规格已实测一致（1056x1920 / 24fps / 294 帧），故可用 -c copy 无损拼接。
concat 列表必须写**绝对路径 + 正斜杠**：相对路径会因 concat 的相对基准与
列表文件所在目录叠加而报 "Impossible to open"。
"""
import glob
import os
import subprocess
import sys

import cv2
import imageio_ffmpeg

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATTERN = os.path.join(ROOT, '法天象地', 'video', '宫装女友FTX0*.mp4')
DST = os.path.join(ROOT, '法天象地', 'video', '恶搞第五集前置_法天象地四段合并.mp4')
LST = os.path.join(ROOT, '法天象地', '_concat_list.txt')


def main():
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    segs = sorted(glob.glob(PATTERN))
    segs = [s.replace('\\', '/') for s in segs]
    if not segs:
        print('未找到分段视频')
        return
    print('分段（%d 段）：' % len(segs))
    for s in segs:
        print('  ', os.path.basename(s))

    with open(LST, 'w', encoding='utf-8') as f:
        for s in segs:
            f.write("file '%s'\n" % s)

    cmd = [ff, '-y', '-f', 'concat', '-safe', '0', '-i', LST.replace('\\', '/'),
           '-c', 'copy', '-movflags', '+faststart', DST]
    r = subprocess.run(cmd, capture_output=True)
    print('ffmpeg rc', r.returncode)
    if r.returncode:
        print(r.stderr.decode('utf-8', 'replace')[-1500:])
        return

    print('成片 %.1f MB  %s' % (os.path.getsize(DST) / 1024 / 1024, DST))
    c = cv2.VideoCapture(DST)
    fps, fr = c.get(cv2.CAP_PROP_FPS), int(c.get(cv2.CAP_PROP_FRAME_COUNT))
    print('校验：%dx%d  %d 帧  %.1f fps  %.2f 秒' % (
        int(c.get(cv2.CAP_PROP_FRAME_WIDTH)), int(c.get(cv2.CAP_PROP_FRAME_HEIGHT)),
        fr, fps, fr / fps))
    c.release()


if __name__ == '__main__':
    main()