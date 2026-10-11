# -*- coding: utf-8 -*-
"""南宫婉（真人质感）· 古典美大电影滤镜人物展示 · 65535 gpt-image-2.5-flare 图生图

设计要点（对照项目基准的「电影感变体」）：
  身份源  = 人物三视图（真人质感-基础）.png（已读图确认：白外袍/深藏青内衬/银凤冠/金焰花钿/珍珠耳坠/褐绿眸）
  镜头    = 45 号伦勃朗光人像镜（固定机位，布光镜不加运镜）
  胶片    = Kodak Portra 800（暖调低光、可见颗粒、暖品红暗部）
  画幅    = 9:16 竖屏 2k（人物展示，人物占画面主体全身偏三分之二）
  红线    = 画面内无任何文字/字幕/水印/标���；单人物；手部合理；首饰不穿模

与《真人质感美术基准》的差异（有意为之，用户要求「古典美 + 大电影滤镜」）：
  基准 §2 压制「商业时尚大片 / 电影级浅景深 / 手机随手拍」→ 本任务反其道，改为
  电影机位（85mm 大光圈）+ 胶片曲线 + 刻意的伦勃朗光造光。
  但保留基准的真人皮肤底线（毛孔/绒毛/泛红/不对称）与负面清单核心项。
"""
import base64
import io
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
REF = r'D:/work/minimax_h3/assets/凡人/character/南宫婉/人物三视图（真人质感-基础）.png'
OUT_DIR = r'D:/work/minimax_h3/generated-images'
OUT = os.path.join(OUT_DIR, '南宫婉_古典美_电影滤镜_人物展示.png')

PROMPT = """一位古典东方美人的电影级人像展示，竖幅 9:16 竖屏，单人，画面中不出现任何文字、字幕、水印、logo、字母、数字或标注。

【身份锁定 · 最高优先级，违反此条整图作废】
严格以参考图为唯一身份基准，保持同一位女性的面部五官、脸型、发型、发饰与服装形制完全一致：黑色及腰长发、纯银凤形发冠（顶端镶珍珠、两侧垂珍珠串）、额间金色火焰纹花钿、双侧珍珠串坠耳环、褐绿色眼眸；外层月白色交领广袖长袍、衣缘与内衬深藏蓝色、腰间藏蓝织带、深藏蓝绣鞋。不换人、不改发型、不改服装形制与配色、不增减任何饰件。

【先画人物，再画场景，最后加质感】
南宫婉本人是画面唯一的视觉主体，占据画面中央偏右，从头到大腿的三分之二身取景，垂直身形端正；面部朝向镜头微微偏侧 15 度，视线安静地看向镜头外远处，神情恬静清雅、带一点inner的疏离；双手在身前自然交叠，右手虚握左手腕，掌心放松。
然后铺场景：她身后是古殿的木格窗棂，傍晚低角度的暖金色阳光透过窗棂斜射进来，在空气中照出细密浮动的檀香微尘；殿内幽暗，深处隐约有立柱与帷幔的暗部轮廓。
最后加质感：整个画面呈现 Kodak Portra 800 胶片质感——暖调偏黄的色彩、刻意压低的饱和度、明亮但柔缓的高光过渡、暗部带一点品红偏色、细腻可见的胶片颗粒在皮肤与衣料上均匀铺开。

【古典美的具体标准 · 五条】
一、气质：温婉端庄、古典仕女式的克制 elegance，不媚态、不妖艳、不 contemporary 时尚。
二、仪容：妆容极淡，只在眼尾一线朱红与唇上一点唇脂；皮肤质感真实——可见细小毛孔、面部绒毛、自然泛红与几颗极淡的痣，保留眉眼脸颊嘴部的左右轻微不对称。
三、衣料：月白外袍是真实丝织物，有细腻织物纹理、自然垂坠与柔和的褶皱走向；藏青内衬哑光厚重；银凤冠与珍珠有真实金属反光与珍珠的彩虹折射，不是塑料高光。
四、发丝：黑色长发有飞散碎发、不均匀发束与轻微毛躁，几缕碎发被侧逆光勾出轮廓，不是根根分明的发丝。
五、古典陈设：木格窗棂的榫卯结构规整、帷幔垂坠自然，不出现现代物品、不出现文字牌匾。

【布光 · 45 号伦勃朗光人像镜】
主光来自人物左侧上方约 45 度的窗棂光束，亮侧脸颊受光明亮通透，暗侧脸颊刚好被穿过鼻梁的光线照出一个倒三角形高光斑（伦勃朗三角光），额头上方有一小块柔和的过渡亮区。镜头固定不动，机位与人物视线等高略偏侧，不使用任何运镜。背景是幽暗殿内的柔和虚化，暖金窗光在她身后形成柔和的光晕轮廓，把人物从暗部中分离出来。整体曝光偏暗，暗部保留细节不死黑。

【镜头与像质】
中长焦人像镜头观感（约 85mm 等效），大光圈浅景深但保留可辨识的后景窗棂结构与浮尘，焦平面准确落在双眼上，背景呈柔和的散景光斑而不是糊成一片。轻微的镜头呼吸感与极低的高光溢出（halation），暖金高光边缘带一丝橙红光晕。画面无边框、无镜头畸变、无鱼眼。

【反向约束】
避免：CGI、3D 渲染、游戏建模感、娃娃皮肤、瓷肌、塑料感、过度磨皮、美颜 App 瘦脸大眼、眼睛过大、面部完全对称、睫毛过度锐化、油蜡感高光、影棚打光、硬光高对比、廉价滤镜感、浓妆、艳丽唇色、暴露服装、廉价影楼布景、极端背景虚化糊成一片、过度 HDR、过曝死白、噪点过重、画面的锐化假锐度、明显的 AI 塑料感；画面无任何文字、字幕、水印、logo、标牌、书法、书法条幅；无第二个人物、无背景人影、无第三只手；手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连、无六指）；银凤冠、珍珠串坠耳环与腰带扣饰不重复、不悬空、不穿模、不融化；衣料纹理不呈现为塑料光泽。"""

NEG_TAIL = '画面中不出现任何文字、字幕、水印、logo、字母、数字或标注。'


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
    print('submit resp=%s' % json.dumps(resp, ensure_ascii=False)[:400])
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
            print('final=%s' % json.dumps(st, ensure_ascii=False)[:1200])
            if status != 'done':
                return 2
            urls = st.get('result_urls') or []
            if not urls:
                rd = st.get('result') or {}
                arr = rd.get('data') or []
                for it in arr:
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
