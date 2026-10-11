# -*- coding: utf-8 -*-
"""鬼灭之刃 · 主角团 9 人三视图批量生成（65535 gpt-image-2 图生图）

统一模式：
  第 1 张 = 画风基准（凡人包 韩立三视图：真人质感 3D 渲染 + 白底两列版式）
  第 2 张起 = 身份来源（动画官网立绘 / 官方插画 / 游戏立绘），逐角色定制

流程：压缩编码 -> 顺序提交 -> 统一轮询 -> 下载到 generated-images/
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
ROOT = r'D:/work/minimax_h3/assets/鬼灭之刃/character'
OUT = r'D:/work/minimax_h3/generated-images'
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
            '不出现背景场景与任何特效（不出现火焰、水流、闪电、蝴蝶等呼吸特效），背景为纯白；'
            '手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连）；'
            '三视图三个视角的服装细节（图案、纽扣、腰带、配饰、佩刀）必须完全一致，不得增删配饰。')

# refs: (相对 ROOT 的路径, 该图用途说明)
JOBS = [
    {
        'name': '灶门祢豆子',
        'refs': [('灶门祢豆子/官方参考/灶门祢豆子-官网(hashirageikohen)-img_chara_nezuko.jpg',
                  '该图为动画半身截图（浅色室内背景），只取人物的面部、发型与和服形制，不要沿用背景。')],
        'desc': ('角色为一位年轻的成年女性：黑色长直发，发梢渐染橘红色，头顶以粉色发绳半束；'
                 '粉红色瞳，面容清秀；口中横衔一节浅竹色竹筒，竹筒以红色系带绕至脑后固定（辨识度最高的锚点）；'
                 '身穿粉色麻叶纹和服（浅粉底色＋白色与深粉色麻叶纹），系深色宽腰带；赤足。气质安静内敛。'),
    },
    {
        'name': '我妻善逸',
        'refs': [('我妻善逸/官方参考/我妻善逸-官网(hashirageikohen)-img_chara_zennitsu.jpg',
                  '该图为动画半身截图（黄色背景），只取人物的面部、发型与羽织形制，不要沿用背景与光效。')],
        'desc': ('角色为一位写实化的年轻男性剑士：浅金色短发，中分齐刘海，两侧发梢略翘；琥珀金色瞳，眼型偏圆；'
                 '外披黄底白色三角（鳞）纹羽织，内穿黑色立领制服与黑长裤，白色绑腿、白色腰带；'
                 '腰间佩一把日轮刀。气质略带怯懦。'),
    },
    {
        'name': '嘴平伊之助',
        'refs': [('嘴平伊之助/官方参考/嘴平伊之助-官方参考-03.png',
                  '该图为该角色摘下面具时的露脸全身像（深色背景）：取面部五官、发型与裸上身造型，不要沿用背景与动作。'),
                 ('嘴平伊之助/官方参考/嘴平伊之助-官方参考-02.png',
                  '该图为该角色佩戴野猪头套的战斗造型（深色背景）：只取野猪头套的形制、兽皮与双刀，不要沿用背景与动作。')],
        'desc': ('角色为一位写实化的年轻男性，有两态：'
                 '右列三视图为其战斗造型——佩戴野猪头套（灰褐色粗糙兽毛、粉色猪鼻、蓝色圆眼孔），'
                 '赤裸上身、肌肉线条明显，腰缠灰褐色兽皮，下身穿深色长裤与白色绑腿、草鞋，'
                 '双手各持一把日轮刀（刀身灰白色、带锯齿缺口）；'
                 '左列面部特写为他摘下面具时的真实面容——容貌清秀的年轻男性，深蓝黑色短发，灰绿色瞳。'
                 '两列为同一个角色，头套可摘戴，不是两个人。'),
    },
    {
        'name': '富冈义勇',
        'refs': [('富冈义勇/官方参考/富冈义勇-官网(hashirageikohen)-img_chara_giyu.jpg',
                  '该图为动画半身截图（深色背景），只取人物的面部、发型与羽织形制，不要沿用背景。')],
        'desc': ('角色为一位写实化的年轻男性剑士：深蓝黑色长发，半束（头顶束起一束，余发披散过肩），'
                 '两侧鬓发垂落；靛蓝色瞳，神情冷淡；内穿黑色立领制服，'
                 '外披一件左右花纹不同的羽织——一侧为黄绿与深色相间的龟甲（六角）纹，另一侧为素色深红；'
                 '腰间左侧佩一把日轮刀（水色刀身）。气质冷峻寡言。'),
    },
    {
        'name': '蝴蝶忍',
        'refs': [('蝴蝶忍/官方参考/蝴蝶忍-官网(hashirageikohen)-img_chara_shinobu.jpg',
                  '该图为动画半身截图（室外绿树背景），只取人物的面部、发型与发饰，不要沿用背景。'),
                 ('蝴蝶忍/官方参考/蝴蝶忍-官方参考-01.jpg',
                  '该图为该角色的全身立绘，用于确认「蝶之羽织」的形制与配色（白底＋紫粉绿渐变蝴蝶翅膀纹样、'
                  '下摆做成蝶翼轮廓与尖角），不要沿用其背景与动作。')],
        'desc': ('角色为一位成年女性剑士：深紫黑色中长发，发梢渐浅（微橙色），侧后别一枚蝴蝶形发夹（紫粉色）；'
                 '紫色渐层瞳（上深紫、下浅），细长眼，常驻微笑；内穿黑色立领制服，'
                 '外披「蝶之羽织」——白底＋紫粉绿渐变的蝴蝶翅膀纹样，下摆呈蝶翼轮廓与尖角（最强的辨识点）；'
                 '腰间佩一把细身日轮刀。气质温柔和婉。'),
    },
    {
        'name': '炼狱杏寿郎',
        'refs': [('炼狱杏寿郎/官方参考/炼狱杏寿郎-官方参考-01.webp',
                  '该图为该角色的白底半身插画，用于确认面部、金红火焰状发型与瞳色，不要沿用其画风与背景装饰。'),
                 ('炼狱杏寿郎/官方参考/炼狱杏寿郎-SEGA-chara10(基础).png',
                  '该图为游戏官方全身立绘，用于确认服装形制（黑制服＋白底橙色火焰纹披风、刀柄红白）；'
                  '只取服装款式与配色，绝对不要沿用其动作姿态与环绕的火焰特效。')],
        'desc': ('角色为一位写实化的成年男性剑士：金红相间的火焰状长发，额发与鬓发向上翘起如火焰，'
                 '发色以金色为主、发梢赤红；大眼，金色（琥珀）瞳，浓眉，眉眼上扬有神；'
                 '内穿黑色立领制服，外披白底橙色火焰纹羽织/披风；腰间佩一把日轮刀（赤橙色刀身，刀柄红白）。'
                 '气质热血爽朗、正气凛然。'),
    },
    {
        'name': '栗花落香奈乎',
        'refs': [('栗花落香奈乎/官方参考/栗花落香奈乎-官网(hashirageikohen)-img_chara_kanawo.jpg',
                  '该图为动画半身截图（浅色室内背景），只取人物的面部、发型与发饰，不要沿用背景。'),
                 ('栗花落香奈乎/官方参考/栗花落香奈乎-官方参考-01.png',
                  '该图为该角色的白底全身立绘，用于确认服装形制（白色斗篷＋深紫色连衣裙＋白色及膝长袜＋靴），'
                  '不要沿用其线条画风。')],
        'desc': ('角色为一位成年女性剑士：黑色齐刘海短发，头顶偏后束一束高马尾（余发较短），'
                 '发饰为粉红色蝴蝶结；淡紫色渐层瞳，表情淡薄少变化；'
                 '外披白色斗篷（蝶翅意象，披风下摆略呈圆弧），内穿深紫色连衣裙（长度及膝），'
                 '白色及膝长袜与短靴；腰间佩一把日轮刀（白色刀鞘）。气质安静疏离。'),
    },
    {
        'name': '宇髄天元',
        'refs': [('宇髄天元/官方参考/宇髄天元-官网(hashirageikohen)-img_chara_uzui.jpg',
                  '该图为动画半身截图（浅色背景），只取人物的面部、银白长发、头带宝石与面部浓妆，不要沿用背景。')],
        'desc': ('角色为一位写实化的成年男性剑士：银白色长发，半束（余发披散过肩）；赤红色瞳；'
                 '左眼佩戴白色眼罩（黑色包边）；面部有浓妆——红色眼影与红唇；'
                 '额上系一条白色头带（鉢巻），头带上镶有数颗宝石（红、绿、蓝等色，呈四枚一排，最高辨识度锚点）；'
                 '上身穿鬼杀队制服但无袖且敞开（露出健壮的胸腹肌），双臂与手腕缠白、红两色布条，'
                 '下身穿深色束脚裤，腰间束多条布带，足袋配草鞋；'
                 '双手各持一把日轮刀（两把大刀，刀身有缺口，以锁链相连）。气质华丽张扬、自信张狂。'),
    },
    {
        'name': '甘露寺蜜璃',
        'refs': [('甘露寺蜜璃/官方参考/甘露寺蜜璃-官网(hashirageikohen)-img_chara_mitsuri.jpg',
                  '该图为动画半身截图（浅色室内背景），只取人物的面部、粉绿麻花辫与瞳色，不要沿用背景。'),
                 ('甘露寺蜜璃/官方参考/甘露寺蜜璃-官方参考-03.png',
                  '该图为该角色的全身立绘（深色背景），用于确认服装形制（白色衬衫敞开＋深色百褶短裙＋'
                  '白色长羽织＋绿色及膝长袜），不要沿用其背景。')],
        'desc': ('角色为一位成年女性剑士：长发编成蓬松的麻花辫，发色粉色与绿色相间（上方为粉、辫中夹绿），'
                 '垂于身前；草绿色瞳，右眼下方有一颗痣；'
                 '上身白色衬衫敞开、内搭深色上衣，下身穿深色百褶短裙，外披白色长羽织，'
                 '绿色及膝长袜配短靴；腰间佩一把日轮刀（刀身极薄极软，呈粉白色鞭状）。气质明快热情。'),
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
    os.makedirs(OUT, exist_ok=True)
    tasks = []

    print('=== 阶段 1：提交 %d 个任务 ===' % len(JOBS))
    for job in JOBS:
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
        # 任务快照
        snap = {'task_id': tid, 'prompt': prompt,
                'refs': [os.path.relpath(p, 'D:/work/minimax_h3').replace('\\', '/') for p in refs]}
        with open(os.path.join(OUT, '%s_三视图_task.json' % name), 'w', encoding='utf-8') as f:
            json.dump(snap, f, ensure_ascii=False, indent=2)
        print('  [%s] %d 张参考图 -> %s' % (name, len(refs), tid))
        time.sleep(1)

    if not tasks:
        print('无任务提交成功')
        return

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
