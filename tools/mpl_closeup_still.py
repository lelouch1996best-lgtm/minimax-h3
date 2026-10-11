# -*- coding: utf-8 -*-
"""幕沛灵（真人质感）· 古典美大电影滤镜 · 面部特写主视觉 · 65535 gpt-image-2.5-flare 图生图

与南宫婉版的差异（有意为之，两人气质完全不同，不能套同一套）：
  南宫婉 = 月白袍 · 清温柔婉 · 45号伦勃朗光（暖侧光）· 情绪内敛
  幕沛灵 = 红纱裙 · 高冷明艳 · 46号蝴蝶光（冷艳高调）· 情绪外放带攻击性

关键约束：她鼻梁与两颊有自然雀斑（65535 2026-10-07 生成时模型自行增加，原设定无）
→ **不能用暖侧光**（暖调会把雀斑糊成脏斑），改用正前方偏高柔光，让雀斑成为可辨识特征。
  特写是本版核心：额头顶到下颌的极近特写，蓝眸占视觉中心。

镜头= 46 号蝴蝶光人像镜（固定机位不加运镜）
胶片 = Kodak Portra 400（细腻奶油肤色，配冷调柔光更净）
画幅 = 9:16 竖屏 2k
红线 = 画面内无任何文字/字幕/水印/标注；单人；手部合理；首饰不穿模
"""
import base64
import json
import os
import sys
import time
import urllib.request

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

API = os.environ.get('S65535_API_KEY')
if not API:
    print('FATAL: S65535_API_KEY 未设置')
    sys.exit(1)

BASE = 'https://task-api-1-cn.65535.space'
REF = r'D:/work/minimax_h3/assets/凡人/character/幕沛灵/人物三视图（真人质感-基础）.png'
OUT_DIR = r'D:/work/minimax_h3/generated-images'
OUT = os.path.join(OUT_DIR, '幕沛灵_古典美_电影滤镜_面部特写.png')

PROMPT = """一位古典东方美人的电影级面部特写，竖幅 9:16 竖屏，单人，画面中不出现任何文字、字幕、水印、logo、字母、数字或标注。

【身份锁定 · 最高优先级，违反此条整图作废】
严格以参考图为唯一身份基准，保持同一位女性的面部五官、脸型、发型、发饰与服装形制完全一致：黑色长发盘成高髻、头顶缠系金色发饰带、两侧垂珍珠流苏长坠耳环、蓝色眼眸；红色 V 领纱质短裙配金腰带垂饰。不换人、不改发型、不改服装形制与配色、不增减任何饰件。**鼻梁与两颊的自然雀斑必须保留并清晰可辨**，这是她最重要的识别特征。

【景别 · 本图核心】
极近面部特写：取景从额头发际线到下颌底，画面里只有她的脸，蓝色眼眸占据视觉中心，颅顶与下巴都被画框切掉。肩部只在画面最下缘露出一线红纱。不出现全身，不出现半身。

【先画人物，再画场景，最后加质感】
她本人是画面唯一主体，正面朝向镜头，头微微抬起约五度使下颌线清晰，眼神直直看向镜头，眼睑半垂带着审视与倦意；双唇紧闭，唇线平直，唇角既不上扬也不下压，表情冷淡克制；一枚小小的金耳饰在画面左侧边缘轻微入画。
然后铺场景：背景是深色木格窗棂与幽暗殿内的立柱暗部轮廓，全部柔和虚化成低对比的色块，背景明度明显低于面部，不与面部争夺注意力。
最后加质感：整个画面呈现 Kodak Portra 400 胶片质感——细腻的奶油肤色、刻意压低的饱和度、明亮但柔缓的高光过渡、暗部偏暖的柔和过渡、极细的胶片颗粒在皮肤上均匀铺开。

【古典美的具体标准 · 五条】
一、气质：高冷明艳，古典仕女式的清贵，不甜不媚不撒娇，是一种「不必讨好任何人」的从容。
二、仪容：妆容极淡但眉眼锋利可见；皮肤质感真实——可见细小毛孔、面部绒毛、鼻梁与两颊散布的自然雀斑（大小深浅不均，靠近眼周更密）、自然泛红，保留眉眼脸颊嘴部的左右轻微不对称。
三、衣料：红色纱质短裙是真实薄纱，可见细密织纹与半透明的层次；金腰带垂饰有真实金属反光不是塑料高光。
四、发丝：盘发的黑发有飞散碎发、不均匀发束与轻微毛躁，几缕碎发被侧光勾出轮廓，不是根根分明的发丝。
五、配饰：金色发饰带与珍珠流苏耳环结构规整，珍珠有真实彩虹折射，不重复不悬空不穿模。

【布光 · 46 号蝴蝶光人像镜】
主光是一盏柔光灯，从正前方偏高的位置打下，在鼻梁正下方投出清晰的蝶状阴影，凸显颧骨的立体感与下颌的利落线条。镜头固定不动，机位与她的视线等高，不使用任何运镜。侧后有一道极弱的冷调轮廓光把耳饰与发丝的边缘从暗背景中勾出。整体对比度偏高但暗部保留细节不死黑。

【镜头与像质】
中长焦人像镜头观感（约 100mm 等效），大光圈但焦平面精准落在双眼上，虹膜纹理清晰可辨、瞳孔边缘锐利，睫毛根根分明并在虹膜上投下细影。背景完全柔化但木格窗棂的直线走向仍可辨。极轻微的高光溢出（halation）。画面无边框、无镜头畸变、无鱼眼。

【反向约束】
避免：CGI、3D 渲染、游戏建模感、娃娃皮肤、瓷肌、塑料感、过度磨皮、美颜 App 瘦脸大眼、眼睛过大、面部完全对称、睫毛过度锐化、油蜡感高光、影棚硬光、廉价滤镜感、浓妆、艳丽唇色、大面积正红唇、暴露服装、极端背景虚化糊成一片、过度 HDR、过曝死白、噪点过重、假锐度、明显的 AI 塑料感、雀斑被磨掉或糊成一片脏斑；画面无任何文字、字幕、水印、logo、标牌；无第二个人物、无背景人影、无第三只手；手与手指的数量、关节、长度合理（无多指、无粘连）；金发饰带、珍珠流苏耳环与金腰带垂饰不重复、不悬空、不穿模、不融化。"""


def encode_ref(path):
    try:
        img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)
    except Exception:
        img = None
    if img is None:
        raise SystemExit('FATAL: 参考图读取失败 ' + path)
    h, w = img.shape[:2]
    scale = 1536 / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), 88])
    if not ok:
        raise SystemExit('FATAL: JPEG 编码失败')
    print('ref encoded bytes=%d' % len(buf))
    return 'data:image/jpeg;base64,' + base64.b64encode(buf).decode()


def post(payload):
    req = urllib.request.Request(
        BASE + '/v1/tasks',
        data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + API, 'Content-Type': 'application/json'},
        method='POST')
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode('utf-8'))


def get_task(tid):
    req = urllib.request.Request(
        BASE + '/v1/tasks/' + tid,
        headers={'Authorization': 'Bearer ' + API})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    print('prompt chars=%d' % len(PROMPT))

    payload = {
        'kind': 'image',
        'model': 'gpt-image-2.5-flare',
        'input': {
            'prompt': PROMPT,
            'image': encode_ref(REF),
            'size': '9:16',
            'resolution': '2k',
            'n': 1,
        },
    }
    resp = post(payload)
    print('submit resp=%s' % json.dumps(resp, ensure_ascii=False)[:300])
    tid = resp.get('id') or resp.get('task_id') or (resp.get('data') or {}).get('id')
    if not tid:
        print('FATAL: 未取到 task id')
        return 1
    print('TASK_ID=%s' % tid)

    for i in range(90):
        time.sleep(4)
        st = get_task(tid)
        status = st.get('status') or st.get('state')
        print('poll %02d status=%s' % (i + 1, status))
        if status in ('done', 'failed', 'error', 'cancelled'):
            print('final=%s' % json.dumps(st, ensure_ascii=False)[:800])
            if status != 'done':
                return 2
            urls = st.get('result_urls') or []
            if not urls:
                for it in ((st.get('result') or {}).get('data') or []):
                    if it.get('b64_json'):
                        with open(OUT, 'wb') as f:
                            f.write(base64.b64decode(it['b64_json']))
                        print('SAVED_B64 %s' % OUT)
                        return 0
                    if it.get('url'):
                        urls.append(it['url'])
            if urls:
                with urllib.request.urlopen(urls[0], timeout=120) as r:
                    data = r.read()
                with open(OUT, 'wb') as f:
                    f.write(data)
                print('SAVED %s bytes=%d' % (OUT, len(data)))
                return 0
            print('FATAL: done 但无图片地址')
            return 3
    print('FATAL: 轮询超时')
    return 4


if __name__ == '__main__':
    sys.exit(main())
