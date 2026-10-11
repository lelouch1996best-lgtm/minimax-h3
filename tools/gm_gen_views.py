# -*- coding: utf-8 -*-
"""鬼灭之刃 · 角色三视图生成（65535 gpt-image-2 图生图）

第 1 张试水：灶门炭治郎 · 真人质感 · 左列特写 + 右列三视图
- 参考图 1（画风基准）：凡人包 韩立 三视图（真人质感 3D 渲染 + 两列版式）
- 参考图 2（形象来源）：动画官网 柱稽古編 炭治郎立绘

流程：压缩编码 -> 提交 -> 轮询 -> 下载
输出：D:/work/minimax_h3/generated-images/
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
OUT = r'D:/work/minimax_h3/generated-images'

STYLE_REF = r'D:/work/minimax_h3/assets/凡人/character/韩立/人物三视图（基础）.png'
IDENTITY_REF = (r'D:/work/minimax_h3/assets/鬼灭之刃/character/灶门炭治郎/官方参考/'
                r'灶门炭治郎-官网(hashirageikohen)-img_chara_tanjiro.jpg')

OUT_NAME = '灶门炭治郎_真人质感_三视图基础.png'

PROMPT = """完整角色设定稿，白色背景，同画布分左右两列排版：第一列超精细面部特写（占30%宽度），第二列角色标准三视图（正面 / 侧面 / 背面）（占70%宽度）。画面中不出现任何文字、字母、数字、标注或水印（包括「正面 / 侧面 / 背面」等视角标签与角色名）。

第 1 张参考图仅用于确定渲染画风、材质、布光、纯白背景与两列版式：写实电影级 3D 渲染质感、真实皮肤材质与柔和布光；不要沿用该参考图中人物的长相、发型、服装与任何古装元素。
第 2 张参考图用于确定人物身份与造型：严格保持参考图中同一位年轻男性的面部五官、脸型、瞳色、发型与服装形制（以参考图为唯一身份基准，不换人、不改发型与服装形制）。

角色为一位写实化的少年剑士：深红色（赤褐）中分短发，发梢蓬松微翘，刘海半遮额；红色（栗红）瞳，浓眉，眼神温和而坚毅；左额有一大片深红烧伤疤痕（辨识度最高的锚点）；左耳佩戴「日轮花纸」耳饰——白色纸垂配红色太阳火纹；身穿黑色立领制服（配紫色圆形纽扣）与白色内衬，外披绿黑市松（棋盘格）纹羽织，黑色长裤、白色绑腿、白色腰带；腰间左侧佩一把日轮刀（黑色刀身、圆形刀镡）。

写实质感要求：这要像一位真实存在的年轻男性，而不是卡通、动漫或 CG 模型。真实亚洲人的皮肤质感，可见毛孔、细小绒毛、自然泛红与浅淡瑕疵，保留柔和的阴影过渡；面部比例与骨相符合真人，不放大眼睛、不改脸型、不做磨皮美颜；保留眉眼脸颊左右轻微不对称。布料要有真实的织物纹理与褶裥，羽织的绿黑格纹为印染质感而非纯色平涂。头发保留真实发束的体积感与飞散碎发，而非根根分明的发丝。全身三视图的三个视角必须是同一个人、同一套服装、同一发型。

避免：卡通、动漫、漫画、赛璐璐平涂、线稿描边、Q 版、夸张大眼、3D 游戏低模、塑料感皮肤、瓷肌、过度磨皮、美颜滤镜、影棚打光、商业时尚大片、油蜡感高光、过度 HDR、不真实的解剖比例；
画面中不出现任何文字、字幕、水印、logo、视角标签、人物姓名，不出现第二个人物，不出现背景场景与任何道具，背景为纯白；
手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连）；
三视图三个视角的服装细节（羽织格纹、纽扣、腰带、耳饰、佩刀）必须完全一致，不得增删配饰。"""


def load_b64(path, long_edge=1536, q=86):
    """读图 -> 长边缩到 long_edge -> JPEG q86 -> base64 data URI"""
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
    b = buf.tobytes()
    print('    %s  %dx%d  %.0fKB' % (os.path.basename(path), img.shape[1], img.shape[0], len(b) / 1024))
    return 'data:image/jpeg;base64,' + base64.b64encode(b).decode('ascii')


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

    print('[1/4] 压缩并编码两张参考图')
    uri_style = load_b64(STYLE_REF)
    uri_ident = load_b64(IDENTITY_REF)

    payload = {
        'kind': 'image',
        'model': 'gpt-image-2',
        'input': {
            'prompt': PROMPT,
            'size': '16:9',
            'resolution': '2k',
            'n': 1,
            'image': [uri_style, uri_ident],
        },
    }

    print('[2/4] 提交任务')
    try:
        resp = api('POST', '/v1/tasks', payload)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')[:800]
        print('    HTTP %s: %s' % (e.code, body))
        return
    tid = resp.get('id') or resp.get('task_id')
    print('    task id =', tid)
    if not tid:
        print('    响应:', json.dumps(resp, ensure_ascii=False)[:600])
        return

    # 存一份任务快照（不含 base64）
    snap = dict(payload)
    snap['input'] = dict(payload['input'])
    snap['input']['image'] = ['<data-uri #1 韩立三视图>', '<data-uri #2 炭治郎官网立绘>']
    with open(os.path.join(OUT, '灶门炭治郎_三视图_task.json'), 'w', encoding='utf-8') as f:
        json.dump({'task_id': tid, 'request': snap}, f, ensure_ascii=False, indent=2)

    print('[3/4] 轮询（每 3s，最多 100 次）')
    state = None
    for i in range(100):
        time.sleep(3)
        try:
            st = api('GET', '/v1/tasks/' + str(tid), timeout=60)
        except urllib.error.HTTPError as e:
            print('    poll HTTP %s' % e.code)
            continue
        state = st.get('status')
        if i % 5 == 0 or state in ('done', 'failed'):
            print('    [%02d] %s' % (i, state))
        if state in ('done', 'failed'):
            break

    if state != 'done':
        print('[4/4] 未成功，状态 =', state)
        print('    详情:', json.dumps(st, ensure_ascii=False)[:900])
        return

    urls = st.get('result_urls') or []
    if not urls:
        print('[4/4] 无 result_urls；响应:', json.dumps(st, ensure_ascii=False)[:900])
        return

    print('[4/4] 下载')
    saved = []
    for idx, u in enumerate(urls):
        name = OUT_NAME if idx == 0 else OUT_NAME.replace('.png', '_%d.png' % idx)
        dst = os.path.join(OUT, name)
        with urllib.request.urlopen(u, timeout=120) as r:
            blob = r.read()
        with open(dst, 'wb') as f:
            f.write(blob)
        saved.append(dst)
        print('    %s  %.0fKB' % (dst, len(blob) / 1024))

    print('DONE task_id=' + str(tid))
    for s in saved:
        print('FILE ' + s)


if __name__ == '__main__':
    main()
