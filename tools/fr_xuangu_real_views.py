# -*- coding: utf-8 -*-
"""玄骨「真人质感-基础」三视图（65535 gpt-image-2 图生图）

配方 = assets/真人质感美术基准.md §6 + logs/jobs-hanli-mupeiling.json（韩立/幕沛灵同批骨架）：
  单参考图 = 玄骨「人物三视图（基础）.png」
  规格     = 16:9 / 2k / n=1
  提示词   = 两列版式 + 身份锁定 + 特征保护 + 真人实拍演绎 + 负面清单

注意：索引写「暗色长袍」，但「基础」三视图实际为**亮蓝色大袖长袍**（袖口衣摆深色几何菱纹、
金色腰封、内衬深色金纹、黑长靴、右耳蓝穗金质耳坠、暗红棕眼影、黑长发低马尾额前碎发）
→ 按「以参考图为准」写特征保护，纠正索引措辞。
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
MODEL = 'gpt-image-2'

LAYOUT = ('完整角色设定稿，白色背景，同画布分左右两列排版：第一列超精细面部特写（占30%宽度），'
          '第二列角色标准三视图（正面 / 侧面 / 背面）（占70%宽度）。'
          '画面中不出现任何文字、字母、数字、标注或水印（包括「正面 / 侧面 / 背面」等视角标签与角色名）。')

IDENTITY_LOCK = ('严格保持参考图中同一男性的面部五官、脸型、发型、发饰与服装形制完全不变'
                 '（以参考图为唯一身份基准，不换人、不改发型、不改发饰、不改服装形制与配色）。')

FEATURES = ('特征保护（务必与参考图一致）：'
            '黑长发**低马尾束于后颈**、**额前碎发参差**半遮前额；'
            '**右耳戴蓝穗金质长耳坠**（蓝色流苏明显垂落）；'
            '**眼周有暗红棕色眼影**（角色核心辨识点，不得去除）；'
            '面容清俊、眉形细长上挑、深色眼眸，气质锋利疏离；'
            '服装为**亮蓝色大袖交领长袍**（不是暗色袍），'
            '**袖口与衣摆有深色几何菱形纹样**，内衬为深色底配金线纹样，'
            '**金色腰封**系结并垂饰，黑色长裤外罩袍摆、**黑色长靴**。')

IDENTITY = '一位二十多岁的成年男性，面容清俊，气质锋利疏离。'

REALISM = ('这不是 3D 渲染，而是一位真实的真人演员：真实亚洲男性皮肤质感，可见毛孔、细小绒毛、'
           '自然肤质与微小瑕疵，皮肤有真实的明暗过渡与柔和阴影；面部比例与骨相真实，不放大眼睛、'
           '不改脸型、不做磨皮美颜，保留眉/眼/脸颊/嘴部的左右轻微不对称；头发有真实的发束感、'
           '不均匀与轻微毛躁，不是根根分明的发丝；身材与身体比例真实、符合真人解剖。'
           '参考图中的一切须按真人实拍重新演绎——皮肤是真实皮肤，衣料是真实衣料'
           '（可见织物纹理、褶皱与垂坠感），金属饰件有真实反光而不是塑料高光。')

SCENE = ('场景：纯白色的摄影棚背景，柔和均匀的白光，无任何布景、道具与投影。\n'
         '人物全身直立自然站姿，正面、侧面、背面三个视角并排，另在左侧排一张面部特写；'
         '表情放松中性、清冷，不做夸张表情与摆拍动作。')

NEGATIVE = ('避免：CGI、3D 渲染、游戏建模感、娃娃皮肤、瓷肌、塑料感、过度磨皮、美颜 App 瘦脸大眼、'
            '眼睛过大、面部完全对称、睫毛过度锐化、油蜡感高光、极端背景虚化、过度 HDR、'
            '不真实的解剖比例；'
            '服装不得改为暗色或深色系（须保持参考图的亮蓝色），不得删除袖口/衣摆的几何菱纹、'
            '金色腰封与右耳蓝穗金质耳坠，不得去除眼周暗红棕眼影；'
            '参考图中没有的配饰与面部标记不得添加；'
            '画面无任何文字、字母、字幕、水印、logo、视角标签；'
            '手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连）；'
            '发饰与腰饰不重复不悬空、不穿模。')


def build():
    return '\n'.join([LAYOUT, '', IDENTITY_LOCK, FEATURES, IDENTITY, '', REALISM, '', SCENE, '', NEGATIVE])


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
    os.makedirs(OUT, exist_ok=True)
    name = '玄骨'
    ref_path = os.path.join(ROOT, name, '人物三视图（基础）.png')
    prompt = build()
    with open(r'D:/work/minimax_h3/logs/_xuangu_real_prompt.txt', 'w', encoding='utf-8') as f:
        f.write(prompt)

    print('=== 提交任务（model=%s）===' % MODEL)
    uri = load_b64(ref_path)
    payload = {
        'kind': 'image', 'model': MODEL,
        'input': {'prompt': prompt, 'size': '16:9', 'resolution': '2k', 'n': 1, 'image': [uri]},
    }
    resp = api('POST', '/v1/tasks', payload)
    tid = resp.get('id') or resp.get('task_id')
    print('  task_id =', tid)
    snap = {'task_id': tid, 'model': MODEL, 'prompt': prompt,
            'ref': 'assets/凡人/character/玄骨/人物三视图（基础）.png'}
    with open(os.path.join(OUT, '玄骨_真人质感_三视图基础_task.json'), 'w', encoding='utf-8') as f:
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
    dst = os.path.join(OUT, '玄骨_真人质感_三视图基础.png')
    with urllib.request.urlopen(urls[0], timeout=240) as r:
        blob = r.read()
    with open(dst, 'wb') as f:
        f.write(blob)
    print('OK %.0fKB -> %s' % (len(blob) / 1024, dst))


if __name__ == '__main__':
    main()
