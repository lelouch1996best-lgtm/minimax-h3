# -*- coding: utf-8 -*-
"""凡人修仙传 · 女性角色 16 人「真人质感-基础」三视图批量生成（65535 gpt-image-2 图生图）

配方 = 已验证的 韩立/幕沛灵 真人质感任务（logs/jobs-hanli-mupeiling.json）：
  单参考图 = 该角色「人物三视图（基础）.png」（跟班A/B 用校服版、元瑶用人视图错拼名）
  提示词   = 两列版式 + 身份锁定 + 特征保护点 + 真人实拍演绎 + 负面清单
  规格     = 16:9 / 2k / n=1

流程：压缩编码 -> 顺序提交 -> 统一轮询 -> 下载到 generated-images/<角色>_真人质感_三视图基础.png
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

# ref: 相对 ROOT 的路径；identity: 年龄气质行；features: 特征保护点（可空）；expr: 覆盖表情句（可空）
JOBS = [
    {
        'name': '南宫婉',
        'ref': '南宫婉/人物三视图（基础）.png',
        'identity': '一位二十多岁的成年女性，气质清温柔婉。',
        'features': '',
    },
    {
        'name': '紫灵',
        'ref': '紫灵/人物三视图（基础）.png',
        'identity': '一位二十多岁的成年女性，气质妖艳高冷。',
        'features': ('特征保护：鼻梁至下颌覆半透明紫色面纱，必须保留（面纱后唇形依稀可见）；'
                     '金色镂空发冠正中嵌紫宝石、紫罗兰色眼眸、紫色半透明纱质长裙均为核心辨识点，不得增删。'),
    },
    {
        'name': '跟班A',
        'ref': '跟班A/人物三视图（校服）.png',
        'identity': '一位十七岁的女学生，气质活泼搞怪。',
        'features': '特征保护：栗棕色高双马尾、暗红色发圈、发尾微卷、圆脸棕眼眼角上挑。',
        'expr': '表情保留标志性的得意坏笑，但姿态为标准自然站姿（不做叉腰指向动作）。',
    },
    {
        'name': '跟班B',
        'ref': '跟班B/人物三视图（校服）.png',
        'identity': '一位十七岁的女学生，气质淡漠安静。',
        'features': '特征保护：灰黑色波波头、银色细框圆眼镜（必须保留）、淡漠少表情。',
        'expr': '',
    },
    {
        'name': '宋玉',
        'ref': '宋玉/人物三视图（基础）.png',
        'identity': '一位二十岁上下的年轻女性，气质文雅温和。',
        'features': '',
    },
    {
        'name': '元瑶',
        'ref': '元瑶/人物人视图（基础）.png',
        'identity': '一位二十多岁的成年女性，气质温婉贤惠。',
        'features': '',
    },
    {
        'name': '凌玉灵',
        'ref': '凌玉灵/人物三视图（基础）.png',
        'identity': '一位二十岁上下的年轻女性，气质明媚活泼。',
        'features': '',
    },
    {
        'name': '墨彩环',
        'ref': '墨彩环/人物三视图（基础）.png',
        'identity': '一位二十岁上下的年轻女性，气质俏皮灵动。',
        'features': '',
    },
    {
        'name': '李缨宁',
        'ref': '李缨宁/人物三视图（基础）.png',
        'identity': '一位二十岁上下的年轻女性，气质甜美温婉。',
        'features': '',
    },
    {
        'name': '柳眉',
        'ref': '柳眉/人物三视图（基础）.png',
        'identity': '一位三十岁上下的成年女性，气质雍容华贵，有豪门主母的气场。',
        'features': '',
    },
    {
        'name': '梅凝',
        'ref': '梅凝/人物三视图（基础）.png',
        'identity': '一位二十岁上下的年轻女性，温婉清丽、眼角常含泪光。',
        'features': '特征保护：金色蝴蝶发饰、金色腰封、项链与耳坠必须保留。',
        'expr': '',
    },
    {
        'name': '燕如嫣',
        'ref': '燕如嫣/人物三视图（基础）.png',
        'identity': '一位二十岁上下的年轻女性，气质飒爽利落。',
        'features': '',
    },
    {
        'name': '穆兰圣女',
        'ref': '穆兰圣女/人物三视图（基础）.png',
        'identity': '一位三十出头、面容清丽的成年女性，气质神圣清冷。',
        'features': ('特征保护：眉间一点白痣（必须保留）；额前银色金属头冠正中镶翠绿宝石；'
                     '乌黑长发披散、绿衫女修装扮。'),
        'expr': '',
    },
    {
        'name': '文思月',
        'ref': '文思月/人物三视图（基础）.png',
        'identity': '一位二十多岁的成年女性，气质以参考图呈现的为准。',
        'features': '',
    },
    {
        'name': '辛如音',
        'ref': '辛如音/人物三视图（基础）.png',
        'identity': '一位二十多岁的成年女性，气质知性聪慧。',
        'features': '',
    },
    {
        'name': '银月',
        'ref': '银月/人物三视图（基础）.png',
        'identity': '一位十八九岁的狐妖少女，气质清冷温婉。',
        'features': ('特征保护：头顶两侧的大三角狐耳与身后的蓬松银白狐尾是该角色的核心人设特征，'
                     '必须保留，并按真实毛发质感写实化呈现——这两处非人类元素属于「正确的设定元素」，'
                     '不受「不真实解剖比例」这一负面词约束；'
                     '银白色及腰长发微卷、浅灰蓝色眼眸、淡橘粉唇、肤白如瓷。'),
        'expr': '',
    },
]


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


def build(job):
    lines = [LAYOUT, '', IDENTITY_LOCK]
    if job.get('features'):
        lines.append(job['features'])
    lines += [job['identity'], '', REALISM, '', SCENE]
    if job.get('expr'):
        lines.append(job['expr'])
    lines += ['', NEGATIVE]
    return '\n'.join(lines)


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
    tasks = []

    print('=== 阶段 1：提交 %d 个任务 ===' % len(JOBS))
    for job in JOBS:
        name = job['name']
        prompt = build(job)
        ref_path = os.path.join(ROOT, job['ref'])
        try:
            uri = load_b64(ref_path)
        except Exception as e:
            print('  [%s] 编码失败: %s' % (name, e))
            continue
        payload = {
            'kind': 'image', 'model': 'gpt-image-2',
            'input': {'prompt': prompt, 'size': '16:9', 'resolution': '2k', 'n': 1, 'image': [uri]},
        }
        try:
            resp = api('POST', '/v1/tasks', payload)
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', 'replace')[:400]
            print('  [%s] 提交失败 HTTP %s: %s' % (name, e.code, body))
            continue
        tid = resp.get('id') or resp.get('task_id')
        tasks.append({'name': name, 'id': tid})
        snap = {'task_id': tid, 'prompt': prompt,
                'ref': os.path.relpath(ref_path, 'D:/work/minimax_h3').replace('\\', '/')}
        with open(os.path.join(OUT, '%s_真人质感_task.json' % name), 'w', encoding='utf-8') as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
        print('  [%s] %s -> %s' % (name, job['ref'], tid))
        time.sleep(1)

    if not tasks:
        print('无任务提交成功')
        return

    print()
    print('=== 阶段 2：统一轮询（每 5s，最多 100 轮）===')
    pending = {t['id']: t for t in tasks}
    done = {}
    for rnd in range(100):
        time.sleep(5)
        for tid in list(pending.keys()):
            try:
                st = api('GET', '/v1/tasks/' + str(tid), timeout=60)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print('  poll 404 for', tid)
                continue
            s = st.get('status')
            if s in ('done', 'failed'):
                pending.pop(tid)
                done[tid] = st
                nm = [t['name'] for t in tasks if t['id'] == tid][0]
                print('  [%02d] %-8s %s' % (rnd, nm, s))
        if not pending:
            break
    for tid, t in pending.items():
        print('  超时未完成:', t['name'], tid)

    print()
    print('=== 阶段 3：下载 ===')
    for t in tasks:
        st = done.get(t['id'])
        if not st or st.get('status') != 'done':
            print('  [%s] 跳过（%s）' % (t['name'], (st or {}).get('status', 'no-result')))
            if st and st.get('status') == 'failed':
                print('      error:', json.dumps(st.get('error') or st, ensure_ascii=False)[:300])
            continue
        urls = st.get('result_urls') or []
        if not urls:
            print('  [%s] 无 result_urls' % t['name'])
            continue
        dst = os.path.join(OUT, '%s_真人质感_三视图基础.png' % t['name'])
        with urllib.request.urlopen(urls[0], timeout=180) as r:
            blob = r.read()
        with open(dst, 'wb') as f:
            f.write(blob)
        print('  [%s] %.0fKB  %s' % (t['name'], len(blob) / 1024, dst))

    print()
    print('SUMMARY ok=%d / total=%d' % (sum(1 for t in tasks if done.get(t['id'], {}).get('status') == 'done'), len(tasks)))


if __name__ == '__main__':
    main()
