# -*- coding: utf-8 -*-
"""嘴平伊之助 · 双形态拆分三视图（65535 gpt-image-2 图生图）

把原先「左列露脸 + 右列戴猪头套」的合一版拆成两张独立标准三视图：
  ① 人物三视图（基础）    —— 左列人脸特写 + 右列三视图，全程露脸
  ② 人物三视图（猪头套）  —— 左列野猪头套精细特写 + 右列三视图，全程戴头套

两版服装完全一致：赤膊 + 灰褐兽皮腰卷 + 深蓝黑长裤(裤脚兽毛) + 白绑腿草鞋 + 双手锯齿双刀。

流程：归档旧合一版 -> 压缩编码 -> 提交 -> 轮询 -> 下载到 generated-images/
"""
import base64
import json
import os
import shutil
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
CHAR = r'D:/work/minimax_h3/assets/鬼灭之刃/character/嘴平伊之助'
OUT = r'D:/work/minimax_h3/generated-images'
STYLE_REF = r'D:/work/minimax_h3/assets/凡人/character/韩立/人物三视图（基础）.png'

# 标准两列版式（左列面部特写）
LAYOUT_STD = ('完整角色设定稿，白色背景，同画布分左右两列排版：第一列超精细面部特写（占30%宽度），'
              '第二列角色标准三视图（正面 / 侧面 / 背面）（占70%宽度）。'
              '画面中不出现任何文字、字母、数字、标注或水印（包括「正面 / 侧面 / 背面」等视角标签与角色名）。')

# 头套版版式（左列改为野猪头套特写）
LAYOUT_MASK = ('完整角色设定稿，白色背景，同画布分左右两列排版：第一列野猪头套的超精细特写（占30%宽度，'
               '需清晰呈现灰褐色粗糙兽毛质感、粉红色猪鼻、一对蓝色圆形眼孔、獠牙与立起的双耳），'
               '第二列角色标准三视图（正面 / 侧面 / 背面，角色全程佩戴该野猪头套）（占70%宽度）。'
               '画面中不出现任何文字、字母、数字、标注或水印（包括「正面 / 侧面 / 背面」等视角标签与角色名）。')

STYLE_NOTE = ('第 1 张参考图仅用于确定渲染画风、材质、布光、纯白背景与两列版式：写实电影级 3D 渲染质感、'
              '真实皮肤材质与柔和布光；不要沿用该参考图中人物的长相、发型、服装与任何古装元素。')

REALISM = ('写实质感要求：这要像一位真实存在的人，而不是卡通、动漫或 CG 模型。真实亚洲人的皮肤质感，'
           '可见毛孔、细小绒毛、自然泛红与浅淡瑕疵，保留柔和的阴影过渡；面部比例与骨相符合真人，'
           '不放大眼睛、不改脸型、不做磨皮美颜；保留眉眼脸颊左右轻微不对称。'
           '布料要有真实的织物纹理与褶裥，兽皮要有蓬松的毛发质感而非色块平涂。'
           '头发保留真实发束的体积感与飞散碎发，而非根根分明的发丝。'
           '全身三视图的三个视角必须是同一个人、同一套服装、同一发型。')

NEGATIVE = ('避免：卡通、动漫、漫画、赛璐璐平涂、线稿描边、Q 版、夸张大眼、3D 游戏低模、塑料感皮肤、瓷肌、'
            '过度磨皮、美颜滤镜、影棚打光、商业时尚大片、油蜡感高光、过度 HDR、不真实的解剖比例；'
            '画面中不出现任何文字、字幕、水印、logo、视角标签、人物姓名，不出现第二个人物，'
            '不出现背景场景与任何特效（不出现火焰、水流、闪电、蝴蝶等呼吸特效），背景为纯白；'
            '手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连）；'
            '三视图三个视角的服装细节（兽皮腰卷、裤脚兽毛、绑腿、草鞋、双刀）必须完全一致，不得增删配饰。')

BODY = ('赤裸上身、胸腹肌肉线条清晰，腰际缠裹灰褐色粗糙兽皮（兽毛蓬松、自然垂坠呈短裙状），'
        '下身穿深蓝黑色宽松长裤（裤脚边缘带一圈蓬松兽毛）、小腿缠白色绑腿、足踏草鞋，'
        '双手各持一把日轮刀（刀身灰白色、刀刃带明显锯齿缺口，刀柄缠浅色布）。')

JOBS = [
    {
        'key': '基础',
        'out': '嘴平伊之助_真人质感_三视图基础.png',
        'ref': '官方参考/嘴平伊之助-官方参考-03.png',
        'ref_note': ('该图为该角色的露脸全身立绘（纯白背景）：只取面部五官、发型、瞳色与整体服装形制；'
                     '不要沿用其战斗动作、握刀姿势与张开的双腿站姿。'),
        'layout': LAYOUT_STD,
        'desc': ('角色为一位写实化的年轻男性剑士：深蓝黑色中长发，发丝略带凌乱、发梢垂至下颌一线；'
                 '灰绿色瞳，眉形锐利，神情张扬带笑；' + BODY +
                 '本图中角色全程不佩戴任何面具或头套，面部自始至终完整可见、不得遮挡。'),
        'neg_extra': '本图不得出现野猪头套、面具或任何覆盖头部的物件。',
    },
    {
        'key': '猪头套',
        'out': '嘴平伊之助_真人质感_三视图猪头套.png',
        'ref': '官方参考/嘴平伊之助-官方参考-02.png',
        'ref_note': ('该图为该角色佩戴野猪头套的战斗造型立绘（纯白背景）：只取野猪头套的形制与配色'
                     '（灰褐兽毛、粉色猪鼻、蓝色圆眼孔、獠牙、立耳）以及整体服装形制；'
                     '不要沿用其战斗动作、握刀姿势与张开的双腿站姿。'),
        'layout': LAYOUT_MASK,
        'desc': ('角色为一位写实化的年轻男性剑士，本图中全程佩戴野猪头套：头套由灰褐色粗糙兽毛构成，'
                 '毛发蓬松竖起、有立起的双耳与獠牙，面部为粉红色猪鼻与一对蓝色圆形眼孔'
                 '（眼孔内可见眼睛反光）；头套完整包裹整个头部，不露出人的头发与面部皮肤；'
                 '身形健硕；' + BODY +
                 '三视图的正面、侧面、背面三个视角必须全程佩戴同一顶野猪头套。'),
        'neg_extra': '本图不得露出人物的真实面部与头发，头部必须被野猪头套完整覆盖。',
    },
]


def archive_old():
    """把原「双形态合一」版归档（不删除）"""
    old = os.path.join(CHAR, '人物三视图（基础）.png')
    dst_dir = os.path.join(CHAR, '_废弃_双形态合一版')
    dst = os.path.join(dst_dir, '人物三视图（基础·双形态合一）.png')
    if os.path.exists(old):
        os.makedirs(dst_dir, exist_ok=True)
        if os.path.exists(dst):
            print('旧合一版已归档过，跳过')
        else:
            shutil.move(old, dst)
            print('归档旧合一版 -> %s (%.0fKB)' % (dst, os.path.getsize(dst) / 1024))
    else:
        print('未发现旧合一版（可能已归档）')


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
    refs = [STYLE_REF, os.path.join(CHAR, job['ref'])]
    lines = [job['layout'], '', STYLE_NOTE,
             '第 2 张参考图：' + job['ref_note'], '',
             job['desc'], '', REALISM, '', NEGATIVE + ' ' + job['neg_extra']]
    return '\n'.join(lines), refs


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
    print('=== 阶段 0：归档旧合一版 ===')
    archive_old()

    print()
    print('=== 阶段 1：提交 %d 个任务 ===' % len(JOBS))
    tasks = []
    for job in JOBS:
        prompt, refs = build(job)
        try:
            uris = [load_b64(p) for p in refs]
        except Exception as e:
            print('  [%s] 编码失败: %s' % (job['key'], e))
            continue
        payload = {
            'kind': 'image', 'model': 'gpt-image-2',
            'input': {'prompt': prompt, 'size': '16:9', 'resolution': '2k', 'n': 1, 'image': uris},
        }
        try:
            resp = api('POST', '/v1/tasks', payload)
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', 'replace')[:400]
            print('  [%s] 提交失败 HTTP %s: %s' % (job['key'], e.code, body))
            continue
        tid = resp.get('id') or resp.get('task_id')
        tasks.append({'key': job['key'], 'out': job['out'], 'id': tid, 'refs': len(refs)})
        snap = {'task_id': tid, 'prompt': prompt,
                'refs': [os.path.relpath(p, 'D:/work/minimax_h3').replace('\\', '/') for p in refs]}
        with open(os.path.join(OUT, '嘴平伊之助_三视图(%s)_task.json' % job['key']), 'w', encoding='utf-8') as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
        print('  [%s] %d 张参考图 -> %s' % (job['key'], len(refs), tid))
        time.sleep(1)

    if not tasks:
        print('无任务提交成功')
        return

    print()
    print('=== 阶段 2：轮询（每 5s，最多 90 轮）===')
    pending = {t['id']: t for t in tasks}
    done = {}
    for rnd in range(90):
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
                nm = [t['key'] for t in tasks if t['id'] == tid][0]
                print('  [%02d] %-8s %s' % (rnd, nm, s))
        if not pending:
            break
    for tid, t in pending.items():
        print('  超时未完成:', t['key'], tid)

    print()
    print('=== 阶段 3：下载 ===')
    for t in tasks:
        st = done.get(t['id'])
        if not st or st.get('status') != 'done':
            print('  [%s] 跳过（%s）' % (t['key'], (st or {}).get('status', 'no-result')))
            if st and st.get('status') == 'failed':
                print('      error:', json.dumps(st.get('error') or st, ensure_ascii=False)[:300])
            continue
        urls = st.get('result_urls') or []
        if not urls:
            print('  [%s] 无 result_urls' % t['key'])
            continue
        dst = os.path.join(OUT, t['out'])
        with urllib.request.urlopen(urls[0], timeout=180) as r:
            blob = r.read()
        with open(dst, 'wb') as f:
            f.write(blob)
        print('  [%s] %.0fKB  %s' % (t['key'], len(blob) / 1024, dst))

    print()
    print('SUMMARY ok=%d / total=%d' % (sum(1 for t in tasks if done.get(t['id'], {}).get('status') == 'done'), len(tasks)))


if __name__ == '__main__':
    main()
