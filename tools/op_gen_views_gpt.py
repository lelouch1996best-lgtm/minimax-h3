# -*- coding: utf-8 -*-
r"""海贼王 · 草帽一伙 10 人三视图批量生成（65535 gpt-image-2 图生图 · 16:9）

统一模式（沿用鬼灭之刃包）：
  第 1 张 = 画风基准（凡人包 韩立三视图：真人质感 3D 渲染 + 白底两列版式）
  第 2 张起 = 身份来源（本地官方立绘 / 官方面部特写），逐角色定制
参考图全部本地转 base64 上传，不依赖公网 URL，规避 CDN 防盗链。

流程：压缩编码 -> 顺序提交 -> 统一轮询 -> 下载落盘到 character/{角色}/人物三视图（基础）.png
用法：python tools\op_gen_views_gpt.py [--only 角色名]
"""
import argparse
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
ROOT = r'D:/work/minimax_h3/assets/海贼王/character'
OUT_NAME = '人物三视图（基础）.png'
STYLE_REF = r'D:/work/minimax_h3/assets/凡人/character/韩立/人物三视图（基础）.png'

LAYOUT = ('完整角色设定稿，白色背景，同画布分左右两列排版：第一列超精细面部特写（占30%宽度），'
          '第二列角色标准三视图（正面 / 侧面 / 背面）（占70%宽度）。'
          '画面中不出现任何文字、字母、数字、标注或水印（包括「正面 / 侧面 / 背面」等视角标签与角色名）。')

STYLE_NOTE = ('第 1 张参考图仅用于确定渲染画风、材质、布光、纯白背景与两列版式：写实电影级 3D 渲染质感、'
              '真实皮肤材质与柔和布光；不要沿用该参考图中人物的长相、发型、服装与任何古装元素。')

REALISM = ('写实质感要求：这要像一位真实存在的人，而不是卡通、动漫或 CG 模型。真实亚洲人的皮肤质感，'
           '可见毛孔、细小绒毛、自然泛红与浅淡瑕疵，保留柔和的阴影过渡；面部比例与骨相符合真人，'
           '不放大眼睛、不改脸型、不做磨皮美颜；保留眉眼脸颊左右轻微不对称。'
           '布料要有真实的织物纹理与褶裥，图案为印染质感而非纯色平涂。'
           '头发保留真实发束的体积感与飞散碎发，而非根根分明的发丝。'
           '全身三视图的三个视角必须是同一个人、同一套服装、同一发型。')

NEGATIVE = ('避免：卡通、动漫、漫画、赛璐璐平涂、线稿描边、Q 版、夸张大眼、3D 游戏低模、塑料感皮肤、瓷肌、'
            '过度磨皮、美颜滤镜、影棚打光、商业时尚大片、油蜡感高光、过度 HDR、不真实的解剖比例；'
            '画面中不出现任何文字、字幕、水印、logo、视角标签、人物姓名，不出现第二个人物，'
            '不出现背景场景与任何特效，背景为纯白；'
            '手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连）；'
            '三视图三个视角的服装细节（图案、纽扣、腰带、配饰、武器）必须完全一致，不得增删配饰。')

# refs: (相对 ROOT 的路径, 该图用途说明)
JOBS = [
    {
        'name': '蒙奇D路飞',
        'refs': [
            ('蒙奇D路飞/官方参考/蒙奇D路飞-官方参考-02.png',
             '该图为该角色的全身立绘，用于确认服装形制（红色无袖背心、蓝色及膝短裤、草鞋）与草帽，不要沿用其画风与背景。'),
            ('蒙奇D路飞/官方参考/蒙奇D路飞-官网(luffy)-face.jpg',
             '该图为官方面部特写，用于确认面部五官、发型与眼下刀疤，不要沿用其背景。'),
        ],
        'desc': ('角色为一位写实化的年轻男性（约19岁）：黑色蓬乱短发、发梢翘起；深褐色瞳，浓眉，眼神明亮热血；'
                 '左眼下方有一道横向短疤（辨识度锚点）；头戴一顶浅草色草帽，帽檐缠一圈红色缎带（最强辨识点）；'
                 '身穿红色无袖开襟背心（露出胸膛）、蓝色及膝短裤（裤脚有白色绒毛边），脚穿草鞋。'
                 '气质热血莽撞、笑容爽朗。'),
    },
    {
        'name': '罗罗诺亚索隆',
        'refs': [
            ('罗罗诺亚索隆/官方参考/罗罗诺亚索隆-官方参考-02.webp',
             '该图为该角色的全身立绘，用于确认服装形制（开襟外套、腹卷、长裤长靴）与三把刀，不要沿用其画风与背景。'),
            ('罗罗诺亚索隆/官方参考/罗罗诺亚索隆-官网(zoro)-face.jpg',
             '该图为官方面部特写，用于确认面部五官、绿发与左眼竖向长疤，不要沿用其背景。'),
        ],
        'desc': ('角色为一位写实化的成年男性剑士：绿色短刺发；深色瞳，左眼一道竖直长疤且左眼闭合（辨识度锚点）；'
                 '左耳佩戴三枚金色圆环耳饰；腰间缠绿色腹卷；身穿深绿色开襟长外套、内搭深色上衣，'
                 '下身穿深色长裤与黑色长靴；腰佩三把日本刀（刀鞘黑 / 白 / 红各一）。气质冷峻寡言、武人风范。'),
    },
    {
        'name': '娜美',
        'refs': [
            ('娜美/官方参考/娜美-官网(nami)-face.jpg',
             '该图为官方面部特写，用于确认面部五官、瞳色与橘色长发，不要沿用其背景。'),
        ],
        'desc': ('角色为一位写实化的年轻女性：橘色波浪长发披肩；褐色瞳，眼神精明；'
                 '左肩有一枚风车与橘子组合的刺青（辨识度锚点）；上身穿蓝白配色的短款上衣，'
                 '下身穿蓝色牛仔裤。气质精明泼辣。着装为日常休闲风格，端庄得体。'),
    },
    {
        'name': '乌索普',
        'refs': [
            ('乌索普/官方参考/乌索普-官方参考-02.webp',
             '该图为该角色的全身立绘，用于确认服装形制（头巾、背带裤）与长鼻子，不要沿用其画风与背景。'),
            ('乌索普/官方参考/乌索普-官网(usopp)-face.jpg',
             '该图为官方面部特写，用于确认面部五官与长鼻子，不要沿用其背景。'),
        ],
        'desc': ('角色为一位写实化的成年男性：黑色卷发束成一小束辫子垂在脑后；'
                 '最显著的特征是长鼻子（长度约为普通人的两倍，辨识度锚点）；深色瞳，留短须；'
                 '头戴黄色头巾，身穿工装背带裤与深色长袖上衣。气质诙谐胆怯。'),
    },
    {
        'name': '山治',
        'refs': [
            ('山治/官方参考/山治-官方参考-04.webp',
             '该图为该角色的半身立绘，用于确认面部、金发遮眼发型与卷眉，不要沿用其画风与背景。'),
            ('山治/官方参考/山治-官方参考-05.jpg',
             '该图为该角色的全身立绘，用于确认西装形制（黑西装、蓝衬衫、领带）与长裤，不要沿用其画风与背景。'),
            ('山治/官方参考/山治-官网(sanji)-face.jpg',
             '该图为官方面部特写，用于确认面部五官与卷眉，不要沿用其背景。'),
        ],
        'desc': ('角色为一位写实化的成年男性：金色短发，刘海偏向一侧遮住右眼（辨识度锚点）；'
                 '蓝色瞳，左侧眉毛向外卷曲；下巴有短须；身穿黑色西装、内搭蓝色衬衫并系领带。'
                 '气质绅士优雅。'),
    },
    {
        'name': '托尼托尼乔巴',
        'refs': [
            ('托尼托尼乔巴/官方参考/托尼托尼乔巴-官方参考-01.webp',
             '该图为该角色的全身立绘，用于确认粉色礼帽、鹿角与红短裤造型，不要沿用其画风与背景。'),
            ('托尼托尼乔巴/官方参考/托尼托尼乔巴-官网(chopper)-face.jpg',
             '该图为官方面部特写，用于确认面部五官与蓝鼻子，不要沿用其背景。'),
        ],
        'desc': ('角色为一只写实化的驯鹿人（非人类，体型小巧，约相当于人类孩童身高）：蓝鼻子，头顶生有鹿角；'
                 '头戴一顶粉色大礼帽，帽上有一个白色十字标记（辨识度锚点）；上身赤裸，下身穿红色短裤，四肢为鹿蹄。'
                 '注意：这是驯鹿拟人形态，不是普通人类，也不是完全四足行走的驯鹿。气质天真害羞。'),
    },
    {
        'name': '妮可罗宾',
        'refs': [
            ('妮可罗宾/官方参考/妮可罗宾-官方参考-02.jpg',
             '该图为该角色的全身立绘，用于确认服装形制与身材比例，不要沿用其画风与背景。'),
            ('妮可罗宾/官方参考/妮可罗宾-官方参考-04.jpg',
             '该图为该角色的全身立绘（另一套服装），用于辅助确认面部与发型，不要沿用其画风与背景。'),
            ('妮可罗宾/官方参考/妮可罗宾-官网(robin)-face.jpg',
             '该图为官方面部特写，用于确认面部五官与黑色长发，不要沿用其背景。'),
        ],
        'desc': ('角色为一位写实化的成年女性：黑色长发垂肩微卷；深色瞳，神情沉稳从容；'
                 '身穿深紫色连衣裙。气质知性冷静。'),
    },
    {
        'name': '弗兰奇',
        'refs': [
            ('弗兰奇/官方参考/弗兰奇-官方参考-02.webp',
             '该图为该角色的全身立绘，用于确认改造人机械结构（红色金属双臂、球形肩关节、胸口动力炉）与花衬衫，不要沿用其画风与背景。'),
            ('弗兰奇/官方参考/弗兰奇-官网(franky)-face.jpg',
             '该图为官方面部特写，用于确认面部五官与蓝色短发，不要沿用其背景。'),
        ],
        'desc': ('角色为一位写实化的成年男性改造人（体型高大健硕，远超常人）：蓝色短发；'
                 '双臂为裸露的红色金属机械结构（辨识度锚点），肩部为球形关节；胸口有一个圆形动力炉；'
                 '身穿夏威夷风格花衬衫。注意：这是改造人，不是普通人类。气质豪爽。'),
    },
    {
        'name': '布鲁克',
        'refs': [
            ('布鲁克/官方参考/布鲁克-官方参考-01.png',
             '该图为该角色的全身立绘，用于确认骷髅形态、爆炸头、高礼帽与燕尾服，不要沿用其画风与背景。'),
            ('布鲁克/官方参考/布鲁克-官网(brook)-face.jpg',
             '该图为官方面部特写，用于确认骷髅头骨形态与爆炸头发型，不要沿用其背景。'),
        ],
        'desc': ('角色为一位写实化的骷髅（活着的骷髅，全身为白色骨骼，无血肉、无皮肤，辨识度锚点）：'
                 '头骨上生有黑色爆炸状卷发，头戴深色高礼帽；身穿深色燕尾服与长裤；手持一把手杖剑。'
                 '注意：这是骷髅，不是普通人类，面部为骷髅头骨而非人脸。气质优雅绅士。'),
    },
    {
        'name': '甚平',
        'refs': [
            ('甚平/官方参考/甚平-官方参考-01.png',
             '该图为该角色的全身立绘，用于确认鱼人形态、橙黄发髻、和服形制与体型，不要沿用其画风与背景。'),
            ('甚平/官方参考/甚平-官方参考-03.png',
             '该图为该角色的全身立绘（另一角度），用于辅助确认面部、獠牙与服装，不要沿用其画风与背景。'),
            ('甚平/官方参考/甚平-官网(Jinbe)-face.jpg',
             '该图为官方面部特写，用于确认面部五官、獠牙与发色，不要沿用其背景。'),
        ],
        'desc': ('角色为一位写实化的鲸鲨鱼人（非人类，体型庞大魁梧）：蓝色皮肤，橙黄色头发束成发髻；'
                 '面部有獠牙，颈部有鳃；身穿和服式上衣并系宽腰带。'
                 '注意：这是鱼人，不是普通人类。气质沉稳义气、武人风范。'),
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
    refs = [STYLE_REF] + [os.path.join(ROOT, r[0]) for r in job['refs']]
    lines = [LAYOUT, '', STYLE_NOTE]
    for i, (_p, note) in enumerate(job['refs']):
        lines.append('第 %d 张参考图：%s' % (i + 2, note))
    lines += ['', job['desc'], '', REALISM, '', NEGATIVE]
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
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', default=None)
    args = ap.parse_args()

    jobs = [j for j in JOBS if (not args.only or j['name'] == args.only)]
    if not jobs:
        print('无匹配角色')
        return 2

    tasks = []
    print('=== 阶段 1：提交 %d 个任务（16:9 / 2k）===' % len(jobs))
    for job in jobs:
        name = job['name']
        prompt, refs = build(job)
        try:
            uris = [load_b64(p) for p in refs]
        except Exception as e:
            print('  [%s] 编码失败: %s' % (name, e))
            continue
        payload = {
            'kind': 'image', 'model': 'gpt-image-2',
            'input': {'prompt': prompt, 'size': '16:9', 'resolution': '2k', 'n': 1, 'image': uris},
        }
        try:
            resp = api('POST', '/v1/tasks', payload)
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', 'replace')[:400]
            print('  [%s] 提交失败 HTTP %s: %s' % (name, e.code, body))
            continue
        tid = resp.get('id') or resp.get('task_id')
        tasks.append({'name': name, 'id': tid, 'refs': len(refs)})
        print('  [%s] %d 张参考图 -> %s' % (name, len(refs), tid))
        time.sleep(1)

    if not tasks:
        print('无任务提交成功')
        return 1

    print()
    print('=== 阶段 2：统一轮询（每 5s，最多 90 轮）===')
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
                nm = [t['name'] for t in tasks if t['id'] == tid][0]
                print('  [%02d] %-8s %s' % (rnd, nm, s))
        if not pending:
            break
    for tid, t in pending.items():
        print('  超时未完成:', t['name'], tid)

    print()
    print('=== 阶段 3：下载落盘 ===')
    okn = 0
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
        dst_dir = os.path.join(ROOT, t['name'])
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, OUT_NAME)
        with urllib.request.urlopen(urls[0], timeout=180) as r:
            blob = r.read()
        with open(dst, 'wb') as f:
            f.write(blob)
        okn += 1
        print('  [%s] %.0fKB  %s' % (t['name'], len(blob) / 1024, dst))

    print()
    print('SUMMARY ok=%d / total=%d' % (okn, len(tasks)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
