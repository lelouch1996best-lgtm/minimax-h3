# -*- coding: utf-8 -*-
"""凡人修仙传 · 韩立「噬金虫甲 + 风雷翅」战斗形态 角色设定稿（多视图 + 特写）

方案：16:9 横版，纯白背景，7 分区排版
  左列  = 面部超精细特写（竖长格）
  右上排 = 正面全身（翼全展）/ 侧面全身（翼收拢）/ 背面全身（翼全展）
  右下排 = 噬金虫甲特写 / 金色长枪完整特写 / 风雷翅特写

双参考图分工：
  第 1 张 = 韩立/人物三视图（基础）.png        -> 身份五官 + 3D 渲染画风 + 白底版式基准
  第 2 张 = 韩立/参考/噬金虫甲+风雷翅.png      -> 只取装备（甲 / 枪 / 翼）形制，且排除水印字幕与暗背景

模型：gpt-image-2.5-flare / 16:9 / 2k / n=1
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
ROOT = r'D:/work/minimax_h3'
OUT = r'D:/work/minimax_h3/generated-images'
MODEL = 'gpt-image-2.5-flare'
NAME = '韩立_噬金虫甲风雷翅_设定稿'

REF1 = 'assets/凡人/character/韩立/人物三视图（基础）.png'
REF2 = 'assets/凡人/character/韩立/参考/噬金虫甲+风雷翅.png'

LAYOUT = (
    '完整角色设定稿，纯白色背景，同一画布内分 7 个独立分区排版（左侧 1 个竖长格 + 右侧 6 个小格）：\n'
    '左侧一整列为超精细面部特写（竖长构图，占画幅左侧约 27% 宽度，面部朝向正前方，占到肩部）。\n'
    '右侧区域分上下两排、每排 3 格，格子之间以明显的白色空隙隔开：\n'
    '上排从左到右依次为——① 正面全身立姿（双脚着地、双臂自然下垂，背后风雷翅完整横向展开）；'
    '② 侧面全身立姿（身体转 90 度朝向画面左侧，风雷翅向上收拢立起、贴合背后、翼宽明显收窄）；'
    '③ 背面全身立姿（背对镜头，风雷翅完整横向展开、露出翼背）；\n'
    '下排从左到右依次为——④ 噬金虫甲特写（胸肩部位中近景，展示尖角肩甲、金色胸甲纹样与腰甲金饰的甲片细节）；'
    '⑤ 金色长枪法宝完整特写（斜向平置于格内，完整展示发光枪刃、盘龙纹枪柄与金色配重端）；'
    '⑥ 风雷翅特写（取单侧翼面的局部放大，展示青蓝发光羽片的层叠结构与金色羽尖）。\n'
    '七格内容互不重叠、不串格，每格元素完整落在本格范围内、不被画幅边缘或相邻格裁断。\n'
    '画面中不出现任何文字、字母、数字、标注或水印（包括各视角标签、角色名与说明文字）。'
)

IDENTITY = (
    '身份基准：严格保持第 1 张参考图中同一名男性的面部五官、脸型、发际线、发型与发饰完全不变'
    '（黑长发在头顶束髻、额前两侧各垂一绺长刘海，深色长凤眼、高鼻、薄唇，神情沉稳冷峻，'
    '发髻以金色发冠与发簪束住）。七个分区中的人物自始至终是同一个人，五官与发型完全一致，'
    '不得换脸、不得改脸型、不得改发型。'
)

EQUIP = (
    '装备与武器形制照第 2 张参考图：\n'
    '· 噬金虫甲＝通体纯黑为底、大面积金色纹饰与金色包边的重型修仙法甲：双肩为厚重、外缘带尖角的黑金肩甲；'
    '胸甲正面为对称金色纹样与护心结构；上臂与前臂为分层甲片护臂、金色描边；腰部为金色腰封与垂坠金饰；'
    '下身外罩黑色战袍式战裙、裙面有数道竖直的金色细条纹，裙下露出深色中衣；'
    '脚穿黑色战靴、靴口与脚背带金色饰件。\n'
    '· 金色长枪＝一柄双手长柄法宝：一端为短而锋利的枪刃、刃身泛蓝白冷光；'
    '另一端为体积厚重的金色配重端（钺／锤形，带浮雕云纹与嵌饰）；'
    '枪柄中段为盘绕的金色龙形装饰与缠绳握把，整体为暗金与高光金双色。\n'
    '· 风雷翅＝一对巨大的凤凰形光翼：主色为青蓝色（湖蓝过渡到青绿）的半透明发光羽片，'
    '层层叠叠、向上翻卷如火焰；翼的上缘与翼尖由金色羽片收边；'
    '翼根连接于双肩胛骨附近，翼展极宽（单侧翼展约为身高的 1.6 倍）。'
)

RENDER = (
    '渲染风格：高品质国漫 3D 动画 CG（次世代游戏建模质感）——不是真人实拍照片，也不是 2D 平涂动漫。'
    '皮肤有次表面散射的柔和通透感与细腻明暗过渡，无毛孔、无胡渣、无皮肤瑕疵；'
    '头发为成束的次世代发丝，有自然的束感与丝缎高光；'
    '甲片为哑光黑底面＋拉丝暗金包边，带真实金属反光与细微划痕；'
    '光翼为半透明自发光能量材质，带青蓝辉光与金色流光、边缘有细密光丝。'
    '整体使用干净的影棚布光：柔和主光＋两侧补光＋顶部轮廓光，明暗过渡平滑，无噪点、无脏色。'
)

SCENE = (
    '场景：纯白色摄影棚背景，无任何布景、道具与投影。'
    '七个分区中的人物均为中性自然站姿、表情平静冷峻，不做夸张动作与摆拍。'
)

NEGATIVE = (
    '避免：真人实拍照片感、写实毛孔与胡渣、2D 平涂动漫、美式卡通、塑料玩具质感、低模粗糙建模、'
    '糊线与锯齿、脸部走形或与参考图不像、七个分区之间人物长相不一致；'
    '避免翅膀越界进入相邻格、翅膀被画幅边缘裁断、翅膀与身体穿模、甲片错位或悬空；'
    '手与手指数量、关节、长度与握持合理（无多指、无缺指、无粘连）；武器不断裂变形；'
    '画面不出现任何文字、字母、字幕、水印、logo 或视角标签；'
    '背景不出现岩石、山体、火光、雾气或任何暗色布景元素，必须保持纯白色背景。'
)

PROMPT = '\n\n'.join([LAYOUT, IDENTITY, EQUIP, RENDER, SCENE, NEGATIVE])


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
    print('  参考图 %s -> %dx%d, %.0fKB' % (os.path.basename(path), img.shape[1], img.shape[0], len(buf) / 1024))
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

    print('=== 阶段 1：编码参考图 ===')
    uri1 = load_b64(os.path.join(ROOT, REF1))
    uri2 = load_b64(os.path.join(ROOT, REF2))

    payload = {
        'kind': 'image',
        'model': MODEL,
        'input': {
            'prompt': PROMPT,
            'size': '16:9',
            'resolution': '2k',
            'n': 1,
            'image': [uri1, uri2],
        },
    }

    print()
    print('=== 阶段 2：提交任务 ===')
    try:
        resp = api('POST', '/v1/tasks', payload)
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', 'replace')[:600]
        print('  提交失败 HTTP %s: %s' % (e.code, body))
        sys.exit(1)
    tid = resp.get('id') or resp.get('task_id')
    print('  task_id =', tid)

    snap = {'task_id': tid, 'model': MODEL, 'prompt': PROMPT, 'refs': [REF1, REF2]}
    with open(os.path.join(OUT, NAME + '_task.json'), 'w', encoding='utf-8') as f:
        json.dump(snap, f, ensure_ascii=False, indent=2)

    print()
    print('=== 阶段 3：轮询 ===')
    st = None
    for rnd in range(120):
        time.sleep(5)
        try:
            st = api('GET', '/v1/tasks/' + str(tid), timeout=60)
        except urllib.error.HTTPError as e:
            print('  poll HTTP %s' % e.code)
            continue
        s = st.get('status')
        print('  [%02d] %s' % (rnd, s))
        if s in ('done', 'failed'):
            break

    if not st or st.get('status') != 'done':
        print('任务未成功:', json.dumps(st, ensure_ascii=False)[:600])
        sys.exit(1)

    urls = st.get('result_urls') or []
    if not urls:
        print('无 result_urls:', json.dumps(st, ensure_ascii=False)[:400])
        sys.exit(1)

    print()
    print('=== 阶段 4：下载 ===')
    dst = os.path.join(OUT, NAME + '.png')
    with urllib.request.urlopen(urls[0], timeout=180) as r:
        blob = r.read()
    with open(dst, 'wb') as f:
        f.write(blob)
    print('  %.0fKB  %s' % (len(blob) / 1024, dst))


if __name__ == '__main__':
    main()
