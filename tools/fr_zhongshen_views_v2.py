# -*- coding: utf-8 -*-
"""仲神师「基础」三视图 · 按参考图重制（写实游戏 CG 质感）

背景：现有「人物三视图（基础）.png」与参考图不符 —— 头部错为「发髻 + 长簪高冠」，
      参考图实为「黑色小布冠（软脚幞头式）+ 短簪横插」，且脸型更方阔厚重、浓眉、
      唇上八字短须 + 下巴山羊尖须。
用户裁定（2026-10-10）：
  · 参考源 = 参考图/全身.png（服装/站姿）+ 参考图/面部特写.png（五官/冠式/胡须），两张都用；
  · 画风   = 写实游戏 CG（同参考图），凡人 IP 统一写实 3D 国漫质感。

配方：65535 gpt-image-2.5-flare 图生图（多参考图），16:9 / 2k / n=1。
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request

import cv2
import numpy as np

sys.stdout.reconfigure(encoding='utf-8')

API = os.environ.get('S65535_API_KEY')
if not API:
    print('FATAL: S65535_API_KEY 未设置')
    sys.exit(1)

BASE = 'https://task-api-1-cn.65535.space'
CHAR_DIR = r'D:/work/minimax_h3/assets/凡人/character/仲神师'
OUT = r'D:/work/minimax_h3/generated-images'
MODEL = 'gpt-image-2.5-flare'

LAYOUT = ('完整角色设定稿，纯白色背景，同画布分左右两列排版：第一列超精细面部特写（占30%宽度），'
          '第二列角色标准三视图（正面 / 侧面 / 背面 三个视角并排）（占70%宽度）。'
          '人物全身从头到脚完整入画、脚部不裁切；画面中不出现任何文字、字母、数字、标注或水印'
          '（包括「正面 / 侧面 / 背面」等视角标签与角色名）。')

# 身份锁定：以两张参考图为唯一基准
IDENTITY_LOCK = ('严格以参考图为唯一身份基准，保持同一位中年男性修士的面部骨相、五官比例、'
                 '胡须形态、头冠形制、发型与服装形制、配色完全不变（不换人、不改脸型、'
                 '不改冠式、不改胡须、不改服装形制与配色）。')

# 特征保护：把「参考图身上有、且容易画错」的点逐条写死
FEATURES = ('特征保护（务必与参考图一致）：'
            '头冠为**黑色小布冠（软脚幞头式软冠）紧贴头顶**，不用高冠、不出现高耸发髻或向前后伸出的长簪，'
            '仅一支短簪横向穿过冠体固定；'
            '脸型**方阔厚重、下颌线条硬朗**，浓黑剑眉、深邃沉稳的眼睛、鼻梁挺直；'
            '**唇上八字短须 + 下巴一撮山羊尖须**（胡须清晰、修剪整齐）；'
            '鬓角垂下的黑色发带/耳侧垂饰保留；'
            '服装为**炭灰色大袖交领外袍罩深蓝色交领内袍**，白中衣下摆微露，'
            '**红金腰带**系结、腰侧垂挂**金色流苏玉佩**；'
            '气质端肃沉稳，中年儒生修士。')

IDENTITY = '一位四十岁上下的成年男性，清癯端肃，元婴后期修士（慕兰四大神师之首）。'

# 写实游戏 CG 质感（对齐参考图，非真人实拍、非日式2D）
QUALITY = ('这是一张写实风格的 3D 游戏角色设定图：写实亚洲男性皮肤质感，可见毛孔、细小绒毛、'
           '自然肤质与微小瑕疵，面部有真实的明暗过渡与柔和阴影；骨相与解剖真实，不夸张、不美颜磨皮；'
           '头发有真实发束感与少量飞散碎发；衣料有真实的织物纹理、褶皱与垂坠感，'
           '金属饰件有真实反光而不是塑料高光；整体灯光为摄影棚级的柔和均匀白光。')

SCENE = ('场景：纯白色摄影棚背景，无任何布景、道具与投影。\n'
         '人物全身直立自然站姿，正面、侧面、背面三个视角并排，另在左侧排一张面部特写；'
         '表情自然中性、沉稳，不做夸张表情与摆拍动作。')

NEGATIVE = ('避免：日式动漫脸、2D 插画、卡通渲染、游戏低模、面部过度光滑磨皮、瓷肌、'
            '娃娃脸、眼睛过大、面部完全对称、睫毛过度锐化、油蜡感高光、极端背景虚化、过度 HDR、'
            '不真实的解剖比例；'
            '头冠不得为高冠、不得出现高耸发髻或向前后伸出的长簪，不得添加参考图中没有的头饰或冠式；'
            '胡须不得缺失或改变形态，参考图中没有的面部标记不得添加；'
            '画面无任何文字、字母、字幕、水印、logo、视角标签；'
            '手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连）；'
            '发饰与腰饰不重复不悬空、不穿模，背景陈设不变形不重复。')


def build():
    return '\n'.join([LAYOUT, '', IDENTITY_LOCK, FEATURES, IDENTITY, '', QUALITY, '', SCENE, '', NEGATIVE])


def load_b64(path, long_edge=1536, q=88):
    raw = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(raw, cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError('图片解码失败: ' + path)
    h, w = img.shape[:2]
    scale = long_edge / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode('.jpg', img, [int(cv2.IMWRITE_JPEG_QUALITY), q])
    if not ok:
        raise RuntimeError('JPEG 编码失败: ' + path)
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.tobytes()).decode('ascii')


def api(method, path, payload=None, timeout=180):
    url = BASE + path
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + API)
    if data:
        req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def main():
    os.makedirs(OUT, exist_ok=True)
    name = '仲神师'
    refs = [
        os.path.join(CHAR_DIR, '参考图', '面部特写.png'),   # 五官/冠式/胡须
        os.path.join(CHAR_DIR, '参考图', '全身.png'),       # 服装形制/站姿
    ]
    prompt = build()
    with open(r'D:/work/minimax_h3/logs/_zhongshen_v2_prompt.txt', 'w', encoding='utf-8') as f:
        f.write(prompt)

    print('=== 提交任务（model=%s, refs=%d）===' % (MODEL, len(refs)))
    uris = [load_b64(p) for p in refs]
    payload = {
        'kind': 'image', 'model': MODEL,
        'input': {'prompt': prompt, 'size': '16:9', 'resolution': '2k', 'n': 1, 'image': uris},
    }
    resp = api('POST', '/v1/tasks', payload)
    tid = resp.get('id') or resp.get('task_id')
    print('  task_id =', tid)
    snap = {'task_id': tid, 'model': MODEL, 'prompt': prompt,
            'refs': [os.path.relpath(p, 'D:/work/minimax_h3').replace('\\', '/') for p in refs]}
    with open(os.path.join(OUT, '仲神师_三视图基础_v2_task.json'), 'w', encoding='utf-8') as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)

    print('=== 轮询 ===')
    st = None
    for rnd in range(160):
        time.sleep(5)
        try:
            st = api('GET', '/v1/tasks/' + str(tid), timeout=60)
        except urllib.error.HTTPError as e:
            print('  poll HTTP %s' % e.code)
            continue
        s = st.get('status')
        if s in ('done', 'failed'):
            print('  [%02d] %s' % (rnd, s))
            break
        if rnd % 6 == 0:
            print('  [%02d] %s' % (rnd, s))

    if not st or st.get('status') != 'done':
        print('未完成/失败:', json.dumps(st, ensure_ascii=False)[:600])
        return

    urls = st.get('result_urls') or []
    if not urls:
        print('无 result_urls:', json.dumps(st, ensure_ascii=False)[:400])
        return
    dst = os.path.join(OUT, '仲神师_三视图基础_v2.png')
    with urllib.request.urlopen(urls[0], timeout=240) as r:
        blob = r.read()
    with open(dst, 'wb') as f:
        f.write(blob)
    print('OK %.0fKB -> %s' % (len(blob) / 1024, dst))


if __name__ == '__main__':
    main()
