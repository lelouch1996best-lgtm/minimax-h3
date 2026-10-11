# -*- coding: utf-8 -*-
"""仲神师「真人质感-基础」三视图（65535 gpt-image-2 图生图）

配方 = assets/真人质感美术基准.md §6 + logs/jobs-hanli-mupeiling.json（韩立/幕沛灵同批）：
  单参考图 = 仲神师「人物三视图（基础）.png」（2026-10-10 按参考图重制版）
  规格     = 16:9 / 2k / n=1
  提示词   = 两列版式 + 身份锁定 + 特征保护 + 真人实拍演绎 + 负面清单

与基准口径的说明：基准 §6 的 {composition}/{lock}/{realism}/{negative} 四段式在
"角色设定稿两列版式"用法下等价于韩立/幕沛灵那套（版式→身份锁定→真人质感→场景→负面），
这里沿用该已验证结构，并按仲神师特征补写"特征保护"段（男性单人，无 duo 槽）。
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
                 '（以参考图为唯一身份基准，不换人、不改发型、不改冠式、不改胡须、不改服装形制与配色）。')

FEATURES = ('特征保护：头冠为**黑色小布冠（软脚幞头式软冠）紧贴头顶**，仅一支短簪横向穿过冠体固定，'
            '不出现高冠、高耸发髻或向前后伸出的长簪；'
            '脸型**方阔厚重、下颌线条硬朗**，浓黑剑眉、深邃沉稳的眼睛、鼻梁挺直；'
            '**唇上八字短须 + 下巴一撮山羊尖须**（胡须清晰、修剪整齐）；'
            '鬓角垂下的黑色发带与耳侧菱形垂饰保留；'
            '服装为**炭灰色大袖交领外袍罩深蓝色交领内袍**，白中衣下摆微露，'
            '**红金腰带**系结、腰侧垂挂**金色流苏玉佩**；'
            '中年儒生修士，气质端肃沉稳。')

IDENTITY = '一位四十岁上下的成年男性，清癯端肃，元婴后期修士（慕兰四大神师之首）。'

REALISM = ('这不是 3D 渲染，而是一位真实的真人演员：真实亚洲男性皮肤质感，可见毛孔、细小绒毛、'
           '自然肤质与微小瑕疵，皮肤有真实的明暗过渡与柔和阴影；面部比例与骨相真实，不放大眼睛、'
           '不改脸型、不做磨皮美颜，保留眉/眼/脸颊/嘴部的左右轻微不对称；头发与胡须有真实的发束感、'
           '不均匀与轻微毛躁，不是根根分明的发丝；身材与身体比例真实、符合真人解剖。'
           '参考图中的一切须按真人实拍重新演绎——皮肤是真实皮肤，衣料是真实衣料'
           '（可见织物纹理、褶皱与垂坠感），金属饰件有真实反光而不是塑料高光。')

SCENE = ('场景：纯白色的摄影棚背景，柔和均匀的白光，无任何布景、道具与投影。\n'
         '人物全身直立自然站姿，正面、侧面、背面三个视角并排，另在左侧排一张面部特写；'
         '表情放松中性、沉稳，不做夸张表情与摆拍动作。')

NEGATIVE = ('避免：CGI、3D 渲染、游戏建模感、娃娃皮肤、瓷肌、塑料感、过度磨皮、美颜 App 瘦脸大眼、'
            '眼睛过大、面部完全对称、睫毛过度锐化、油蜡感高光、极端背景虚化、过度 HDR、'
            '不真实的解剖比例；'
            '头冠不得为高冠、不得出现高耸发髻或向前后伸出的长簪，不得添加参考图中没有的头饰或冠式；'
            '胡须不得缺失或改变形态，参考图中没有的面部标记不得添加；'
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
    name = '仲神师'
    ref_path = os.path.join(ROOT, name, '人物三视图（基础）.png')
    prompt = build()
    with open(r'D:/work/minimax_h3/logs/_zhongshen_real_prompt.txt', 'w', encoding='utf-8') as f:
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
            'ref': 'assets/凡人/character/仲神师/人物三视图（基础）.png'}
    with open(os.path.join(OUT, '仲神师_真人质感_三视图基础_task.json'), 'w', encoding='utf-8') as f:
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
    dst = os.path.join(OUT, '仲神师_真人质感_三视图基础.png')
    with urllib.request.urlopen(urls[0], timeout=240) as r:
        blob = r.read()
    with open(dst, 'wb') as f:
        f.write(blob)
    print('OK %.0fKB -> %s' % (len(blob) / 1024, dst))


if __name__ == '__main__':
    main()
