# -*- coding: utf-8 -*-
"""文思月 · 真人质感三视图（宫装版为身份源）

背景：以「基础」为身份源两次被 OpenAI 安全审核误拒（深 V 纱裙触发），用户改用宫装版。
配方不变：单参考图 + LAYOUT/身份锁定/真人实拍演绎/NEGATIVE，gpt-image-2 / 16:9 / 2k。
产出归档名：人物三视图（真人质感-宫装）.png
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
ROOT = r'D:/work/minimax_h3/assets/凡人/character'
OUT = r'D:/work/minimax_h3/generated-images'
REF = os.path.join(ROOT, '文思月/人物三视图（宫装）.png')

LAYOUT = ('完整角色设定稿，白色背景，同画布分左右两列排版：第一列超精细面部特写（占30%宽度），'
          '第二列角色标准三视图（正面 / 侧面 / 背面）（占70%宽度）。'
          '画面中不出现任何文字、字母、数字、标注或水印（包括「正面 / 侧面 / 背面」等视角标签与角色名）。')

IDENTITY_LOCK = ('严格保持参考图中同一女性的面部五官、脸型、发型、发饰与服装形制完全不变'
                 '（以参考图为唯一身份基准，不换人、不改发型、不改服装形制与配色）。')

FEATURES = ('特征保护：棕色中长发半束、发间紫色花饰与珠串发簪组、额前金链坠紫宝石额饰、'
            '紫水晶坠耳环；服装为淡紫与米白层叠广袖宫装（内衬完整、剪裁端庄），'
            '腰间金色腰封垂金饰，裙面淡紫纱层与刺绣花纹按参考图原样呈现。')

IDENTITY = '一位二十多岁的成年女性，气质以参考图呈现的为准。'

REALISM = ('这不是 3D 渲染，而是一位真实的真人演员：真实亚洲女性皮肤质感，可见毛孔、细小绒毛、'
           '自然泛红与微小瑕疵，皮肤有真实的明暗过渡与柔和阴影；面部比例与骨相真实，不放大眼睛、'
           '不改脸型、不做磨皮美颜，保留眉/眼/脸颊/嘴部的左右轻微不对称；头发有飞散碎发、'
           '不均匀发束与轻微毛躁，不是根根分明的发丝；身材与身体比例真实、符合真人解剖。'
           '参考图中的一切须按真人实拍重新演绎——皮肤是真实皮肤，衣料是真实衣料'
           '（可见织物纹理、褶皱与垂坠感），金属饰件有真实反光而不是塑料高光。')

SCENE = ('场景：纯白色的摄影棚背景，柔和均匀的白光，无任何布景、道具与投影。\n'
         '人物全身直立自然站姿，正面、侧面、背面三个视角并排，另在左侧排一张面部特写；'
         '表情放松中性，不做夸张表情与摆拍动作。')

NEGATIVE = ('避免：CGI、3D 渲染、游戏建模感、娃娃皮肤、瓷肌、塑料感、过度磨皮、美颜 App 瘦脸大眼、'
            '眼睛过大、面部完全对称、睫毛过度锐化、油蜡感高光、极端背景虚化、过度 HDR、'
            '不真实的解剖比例；画面无任何文字、字母、字幕、水印、logo、视角标签；'
            '手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连）；'
            '发饰与腰饰不重复不悬空、不穿模。')


def load_b64(path, long_edge=1536, q=86):
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
    prompt = '\n'.join([LAYOUT, '', IDENTITY_LOCK, FEATURES, IDENTITY, '', REALISM, '', SCENE, '', NEGATIVE])
    uri = load_b64(REF)
    payload = {
        'kind': 'image', 'model': 'gpt-image-2',
        'input': {'prompt': prompt, 'size': '16:9', 'resolution': '2k', 'n': 1, 'image': [uri]},
    }
    resp = api('POST', '/v1/tasks', payload)
    tid = resp.get('id') or resp.get('task_id')
    print('submitted:', tid)
    with open(os.path.join(OUT, '文思月_真人质感宫装_task.json'), 'w', encoding='utf-8') as f:
        json.dump({'task_id': tid, 'prompt': prompt,
                   'ref': os.path.relpath(REF, 'D:/work/minimax_h3').replace('\\', '/')},
                  f, ensure_ascii=False, indent=2)

    for rnd in range(40):
        time.sleep(5)
        st = api('GET', '/v1/tasks/' + str(tid), timeout=60)
        s = st.get('status')
        print('[%02d] %s' % (rnd, s))
        if s in ('done', 'failed'):
            if s == 'failed':
                print('error:', json.dumps(st.get('error') or st, ensure_ascii=False)[:400])
                sys.exit(2)
            urls = st.get('result_urls') or []
            dst = os.path.join(OUT, '文思月_真人质感_三视图宫装.png')
            with urllib.request.urlopen(urls[0], timeout=180) as r:
                blob = r.read()
            with open(dst, 'wb') as f:
                f.write(blob)
            print('OK %.0fKB  %s' % (len(blob) / 1024, dst))
            return


if __name__ == '__main__':
    main()
