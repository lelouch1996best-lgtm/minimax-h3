# -*- coding: utf-8 -*-
"""穆兰圣女「真人质感-基础」三视图 · 重生 v2（去掉额头白点）

问题：v1 依据索引「眉间一点白痣」描述，在提示词里写死「眉间一点白痣（必须保留）」，
      导致成图额头多出一个白点；但其实「基础」三视图里额头是干净的，白点属模型加戏。
v2 修法：
  1) 删除「眉间一点白痣（必须保留）」，改为「额头与眉心光洁，无任何痣、斑点、印记、饰点」；
  2) 负面清单新增：额头与眉心无任何白点/痣/斑点/印记/饰点、无额饰贴片。
配方其余部分与 tools/fr_real_views_batch.py 保持一致（65535 gpt-image-2 / 16:9 / 2k / n=1）。
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

LAYOUT = ('完整角色设定稿，白色背景，同画布分左右两列排版：第一列超精细面部特写（占30%宽度），'
          '第二列角色标准三视图（正面 / 侧面 / 背面）（占70%宽度）。'
          '画面中不出现任何文字、字母、数字、标注或水印（包括「正面 / 侧面 / 背面」等视角标签与角色名）。')

IDENTITY_LOCK = ('严格保持参考图中同一女性的面部五官、脸型、发型、发饰与服装形制完全不变'
                 '（以参考图为唯一身份基准，不换人、不改发型、不改服装形制与配色）。')

FEATURES = ('特征保护：额头与眉心区域光洁干净，不出现任何痣、白点、斑点、印记或装饰点；'
            '额前银色金属头冠正中镶翠绿宝石；乌黑长发披散、绿衫女修装扮。')

IDENTITY = '一位三十出头、面容清丽的成年女性，气质神圣清冷。'

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
            '不真实的解剖比例；'
            '额头与眉心必须光洁：不出现任何白点、白痣、斑点、印记、饰点、贴片、额饰点缀（尤其是眉心与额心的孤立白色圆点），'
            '参考图中不存在的面部标记一律不得添加；'
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
    name = '穆兰圣女'
    ref_path = os.path.join(ROOT, name, '人物三视图（基础）.png')
    prompt = build()

    with open(r'D:/work/minimax_h3/logs/_mulan_v2_prompt.txt', 'w', encoding='utf-8') as f:
        f.write(prompt)

    print('=== 提交任务 ===')
    uri = load_b64(ref_path)
    payload = {
        'kind': 'image', 'model': 'gpt-image-2',
        'input': {'prompt': prompt, 'size': '16:9', 'resolution': '2k', 'n': 1, 'image': [uri]},
    }
    resp = api('POST', '/v1/tasks', payload)
    tid = resp.get('id') or resp.get('task_id')
    print('  task_id =', tid)
    snap = {'task_id': tid, 'prompt': prompt, 'ref': 'assets/凡人/character/穆兰圣女/人物三视图（基础）.png'}
    with open(os.path.join(OUT, '穆兰圣女_真人质感_三视图基础_v2_task.json'), 'w', encoding='utf-8') as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)

    print('=== 轮询 ===')
    st = None
    for rnd in range(120):
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
        print('未完成/失败:', json.dumps(st, ensure_ascii=False)[:500])
        return

    urls = st.get('result_urls') or []
    dst = os.path.join(OUT, '穆兰圣女_真人质感_三视图基础_v2.png')
    with urllib.request.urlopen(urls[0], timeout=180) as r:
        blob = r.read()
    with open(dst, 'wb') as f:
        f.write(blob)
    print('OK %.0fKB -> %s' % (len(blob) / 1024, dst))


if __name__ == '__main__':
    main()
