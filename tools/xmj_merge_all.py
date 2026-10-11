# -*- coding: utf-8 -*-
"""《心魔劫·慕沛灵》23 镜无损拼接（-c copy，同规格 960x1728/24fps）。

镜序按 v2 分镜（镜序表，无镜 22；12B 用 v2 定档、21 用 v2 定档）。
concat 列表必须写**绝对路径 + 正斜杠**（相对路径会报 Impossible to open）。
用法：venv python tools/xmj_merge_all.py
"""
import os
import subprocess
import sys

import cv2
import imageio_ffmpeg

sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VD = os.path.join(ROOT, '心魔劫_穆沛灵', 'video')
VER = os.path.join(VD, '验证片')
DST = os.path.join(VD, '心魔劫_慕沛灵_全片_无后期.mp4')
LST = os.path.join(ROOT, '心魔劫_穆沛灵', '_concat_list.txt')

# 定档成片（按镜序；镜号 -> 验证片目录文件名）
CLIPS = [
    ('01', '镜01_开篇空镜_v1_mp0.72_134币.mp4'),
    ('02', '镜02_缝衣中景_v1_mp0.72_118币.mp4'),
    ('03', '镜03_掀盖头_v1_mp0.72_146币.mp4'),
    ('04', '镜04_攥手指_v1_mp0.72_97币.mp4'),
    ('05', '镜05_雪夜并肩_v1_mp0.72_123币.mp4'),
    ('06', '镜06_理鬓相视_v1_mp0.72_150币.mp4'),
    ('07', '镜07_四季流转_v1_mp0.72_155币.mp4'),
    ('08', '镜08_临终揽抱_v1_mp0.72_130币.mp4'),
    ('09', '镜09_垂眸收紧_v1_mp0.72_132币.mp4'),
    ('10', '镜10_开口发问_v1_mp0.72_183币.mp4'),
    ('11', '镜11_悬停未落_v1_mp0.72_139币.mp4'),
    ('12A', '镜12A_验证片_v1_mp0.72_258币.mp4'),
    ('12B', '镜12B_记忆插入_v2_mp0.72_174币.mp4'),
    ('13', '镜13_手滑落_v1_mp0.72_146币.mp4'),
    ('14', '镜14_冷暖切换阀_v1_mp0.72_102币.mp4'),
    ('15', '镜15_石室盘坐_v1_mp0.72_147币.mp4'),
    ('16', '镜16_遗言近景_v1_mp0.72_165币.mp4'),
    ('17', '镜17_灵气气浪_v1_mp0.72_121币.mp4'),
    ('18', '镜18_验证片_v1_mp0.72_172币.mp4'),
    ('19', '镜19_飞灰散尽_v1_mp0.72_137币.mp4'),
    ('20', '镜20_泪悬未落_v1_mp0.72_116币.mp4'),
    ('21', '镜21_泪落无痕_v2_mp0.72_108币.mp4'),
    ('23', '镜23_空室收尾_v1_mp0.72_240币.mp4'),
]


def probe(p):
    c = cv2.VideoCapture(p)
    info = (int(c.get(cv2.CAP_PROP_FRAME_WIDTH)), int(c.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            c.get(cv2.CAP_PROP_FPS), int(c.get(cv2.CAP_PROP_FRAME_COUNT)))
    c.release()
    return info


def main():
    segs = []
    for sid, name in CLIPS:
        p = os.path.join(VER, name)
        if not os.path.exists(p):
            print('[缺失]', sid, name)
            return
        w, h, fps, fr = probe(p)
        ok = 'OK' if (w, h, round(fps)) == (960, 1728, 24) else '!!规格异常!!'
        print('%-4s %-42s %dx%d %.2ffps %4d帧 %5.2fs %s' % (sid, name, w, h, fps, fr, fr / fps, ok))
        segs.append(p.replace('\\', '/'))

    with open(LST, 'w', encoding='utf-8') as f:
        for s in segs:
            f.write("file '%s'\n" % s)

    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, '-y', '-f', 'concat', '-safe', '0', '-i', LST.replace('\\', '/'),
           '-c', 'copy', '-movflags', '+faststart', DST]
    r = subprocess.run(cmd, capture_output=True)
    print('ffmpeg rc', r.returncode)
    if r.returncode:
        print(r.stderr.decode('utf-8', 'replace')[-1500:])
        return

    print('成片 %.1f MB  %s' % (os.path.getsize(DST) / 1024 / 1024, DST))
    w, h, fps, fr = probe(DST)
    print('校验：%dx%d  %d 帧  %.2f fps  %.2f 秒' % (w, h, fr, fps, fr / fps))


if __name__ == '__main__':
    main()
