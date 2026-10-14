# -*- coding: utf-8 -*-
"""凡人修仙传 · 韩立「噬金虫甲 + 风雷翅」角色设定稿 v3

v2 问题（2026-10-12 用户第二次反馈）：
  ① 翅膀不像 -> 经查证：风雷翅＝雷鹏骸骨炼成 + 融入鲲鹏之羽与天凤之翎，
     小说原文「一只青光濛濛，一只被五色霞光包裹着，仿若水晶般透明」，
     动画为「暗含金光的灵翅」。**本质是实体羽毛翼 + 雷电特效 + 半透明水晶质感，
     不是火焰状光效**（v2 写成「火焰状」是根上错了）。网络参考图 `_refs_fenglei/r02.jpg`
     印证：深蓝羽色 + 暗金覆羽 + 翼根金鹏首 + 青白电弧。
  ② 不要武器 -> 全部移除（无枪、无武器特写格、双手空置）。
  ③ 位置不够 -> 去掉背面全身格，画幅重新分配为 5 格，
     正面全身格与风雷翅特写格双双放大。

版式：16:9 横版，纯白背景，5 分区
  左列 = 面部超精细特写（竖长格）
  中列 = 正面全身（风雷翅全展，大格）／ 侧面全身（翼收拢）
  右列 = 风雷翅特写（最大翅膀格）／ 噬金虫甲特写

三参考图分工：
  第 1 张 = 韩立/人物三视图（基础）.png       -> 身份五官 + 3D 画风 + 白底版式基准
  第 2 张 = 韩立/参考/噬金虫甲+风雷翅.png     -> 噬金虫甲形制（排除水印/字幕/暗背景）
  第 3 张 = _refs_fenglei/r02.jpg（裁掉水印） -> 风雷翅羽翼结构与配色（只取翼）
"""
import base64
import json
import os
import subprocess
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
NAME = '韩立_噬金虫甲风雷翅_设定稿_v3'

REF1 = 'assets/凡人/character/韩立/人物三视图（基础）.png'
REF2 = 'assets/凡人/character/韩立/参考/噬金虫甲+风雷翅.png'
REF3_RAW = 'assets/凡人/character/韩立/_refs_fenglei/r02.jpg'
REF3 = 'assets/凡人/character/韩立/_refs_fenglei/r02_wing.jpg'

LAYOUT = (
    '完整角色设定稿，纯白色背景，同一画布内分 5 个独立分区排版（左 1 竖长格 + 右侧 4 格，'
    '右侧分出「中列」「右列」两列、每列上下各一格）：\n'
    '左侧一整列为超精细面部特写（竖长构图，占画幅左侧约 23% 宽度，面部朝向正前方，'
    '取景到肩部，不含翅膀）。\n'
    '中列（约占画幅 42% 宽度）上下两格——'
    '上格为正面全身立姿（双脚着地、双臂自然向两侧微张，背后风雷翅向两侧上方完整展开，'
    '本格是全画布中最大的人物格，翅膀必须完整落在格内、不被裁断）；'
    '下格为侧面全身立姿（身体转 90 度朝向画面左侧，风雷翅向上收拢、贴于背后、翼宽明显收窄）。\n'
    '右列（约占画幅 35% 宽度）上下两格——'
    '上格为风雷翅特写（本格是全画布中最大的翅膀格，放大展示单侧翼面的羽片层叠结构、'
    '翼根的金色鹏首甲壳与翼面游走的青白色电弧）；'
    '下格为噬金虫甲特写（胸肩部位中近景，展示尖角肩甲、金色胸甲纹样与腰甲金饰的甲片细节）。\n'
    '五个分区内容互不重叠、不串格，每格元素完整落在本格范围内、不被画幅边缘或相邻格裁断。\n'
    '画面中不出现任何文字、字母、数字、标注或水印（包括各视角标签、角色名与说明文字）。\n'
    '人物双手不持任何武器，两只手都是空的。'
)

IDENTITY = (
    '身份基准：严格保持第 1 张参考图中同一名男性的面部五官、脸型、发际线、发型与发饰完全不变'
    '（黑长发在头顶束髻、额前两侧各垂一绺长刘海，深色长凤眼、高鼻、薄唇，神情沉稳冷峻，'
    '发髻以金色发冠与发簪束住）。五个分区中的人物自始至终是同一个人，五官与发型完全一致，'
    '不得换脸、不得改脸型、不得改发型。'
)

EQUIP = (
    '装备与翼形制照参考图：\n'
    '· 噬金虫甲（照第 2 张参考图）＝通体纯黑为底、大面积金色纹饰与金色包边的重型修仙法甲：'
    '双肩为厚重、外缘带尖角的黑金肩甲；胸甲正面为对称金色纹样与护心结构；'
    '上臂与前臂为分层甲片护臂、金色描边；腰部为金色腰封与垂坠金饰；'
    '下身外罩黑色战袍式战裙、裙面有数道竖直的金色细条纹，裙下露出深色中衣；'
    '脚穿黑色战靴、靴口与脚背带金色饰件。\n'
    '· 风雷翅（照第 3 张参考图，只取翼的形制与配色，不要其背景、人物与构图）＝'
    '一对**巨大的雷鹏羽翼**，由**实体羽毛**构成——'
    '翼形自双肩胛骨向两侧上方大幅展开，翼展极宽（单侧翼展约为身高的 1.7 倍）；'
    '翼面外侧为修长锐利的初级飞羽、内侧为数层短覆羽，羽片边缘锐利、层层叠压、羽序清晰；'
    '主色为**深蓝到蓝黑**，覆羽表面带**暗金色与金棕色的金属光泽**，'
    '羽尖与翼缘由**金色**收边；翼根与翼前缘有**金色鹏鸟首**造型的甲壳结构（金鹏之羽）；'
    '整对翼呈**半透明水晶质感**，羽片内里有青蓝色灵光透出、边缘泛冷白辉光；'
    '翼的近旁与翼尖之间有**青白色电弧与细密雷丝**缠绕游走（辟邪神雷），电光细而不炸、不遮挡羽片结构。\n'
    '· 双手空置：右手与左手均自然垂放或微微张开，**不持有任何武器、长枪、法杖、剑、戟或法宝**。'
)

RENDER = (
    '渲染风格：高品质国漫 3D 动画 CG（次世代游戏建模质感）——不是真人实拍照片，也不是 2D 平涂动漫。'
    '皮肤有次表面散射的柔和通透感与细腻明暗过渡，无毛孔、无胡渣、无皮肤瑕疵；'
    '头发为成束的次世代发丝，有自然的束感与丝缎高光；'
    '甲片为哑光黑底面＋拉丝暗金包边，带真实金属反光与细微划痕；'
    '羽翼为半透明发光材质，羽片可有内透光与边缘辉光，但**羽毛的片状结构必须清晰可辨**。'
    '整体使用干净的影棚布光：柔和主光＋两侧补光＋顶部轮廓光，明暗过渡平滑，无噪点、无脏色。'
)

SCENE = (
    '场景：纯白色摄影棚背景，无任何布景、道具与投影。'
    '五个分区中的人物均为中性自然站姿、表情平静冷峻，不做夸张动作与摆拍。'
)

NEGATIVE = (
    '避免：真人实拍照片感、写实毛孔与胡渣、2D 平涂动漫、美式卡通、塑料玩具质感、低模粗糙建模、'
    '糊线与锯齿、脸部走形或与参考图不像、五个分区之间人物长相不一致；'
    '避免人物手持任何武器（枪／剑／戟／杖／法宝），避免手中握有任何长柄物体；'
    '避免翅膀画成火焰状、光团状、烟雾状或纯能量光带，避免翅膀没有羽毛片状结构；'
    '避免翅膀羽片排列杂乱、翼色过浅或偏灰白、缺少深蓝主色、缺少金色覆羽与金色羽尖、'
    '缺少翼根金色鹏首、缺少青白色电弧；避免翅膀越界进入相邻格、翅膀被画幅边缘裁断、'
    '翅膀与身体穿模、甲片错位或悬空；'
    '手与手指数量、关节、长度合理（无多指、无缺指、无粘连）；'
    '画面不出现任何文字、字母、字幕、水印、logo 或视角标签；'
    '背景不出现岩石、山体、火光、雾气或任何暗色布景元素，必须保持纯白色背景。'
)

PROMPT = '\n\n'.join([LAYOUT, IDENTITY, EQUIP, RENDER, SCENE, NEGATIVE])


def prep_ref3():
    """裁掉网络参考图右下角的「3G壁纸」水印带（保上部 80%，翼完整且无水印）。"""
    src = os.path.join(ROOT, REF3_RAW)
    img = cv2.imdecode(np.fromfile(src, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise RuntimeError('REF3 解码失败: ' + src)
    h, w = img.shape[:2]
    sub = img[0:int(h * 0.80), :]
    dst = os.path.join(ROOT, REF3)
    ok, buf = cv2.imencode('.jpg', sub, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    buf.tofile(dst)
    if not os.path.exists(dst) or os.path.getsize(dst) == 0:
        raise RuntimeError('REF3 写出失败: ' + dst)
    print('  REF3 裁切 %dx%d -> %dx%d  %.0fKB' % (w, h, sub.shape[1], sub.shape[0],
                                                  os.path.getsize(dst) / 1024))


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
    print('  参考图 %s -> %dx%d, %.0fKB' % (os.path.basename(path), img.shape[1], img.shape[0],
                                            len(buf) / 1024))
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

    print('=== 阶段 1：预处理 + 编码参考图 ===')
    prep_ref3()
    uri1 = load_b64(os.path.join(ROOT, REF1))
    uri2 = load_b64(os.path.join(ROOT, REF2))
    uri3 = load_b64(os.path.join(ROOT, REF3))

    payload = {
        'kind': 'image',
        'model': MODEL,
        'input': {
            'prompt': PROMPT,
            'size': '16:9',
            'resolution': '2k',
            'n': 1,
            'image': [uri1, uri2, uri3],
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

    snap = {'task_id': tid, 'model': MODEL, 'version': 'v3', 'prompt': PROMPT,
            'refs': [REF1, REF2, REF3]}
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
    print('=== 阶段 4：下载（走 curl，Python urllib 会 403）===')
    dst = os.path.join(OUT, NAME + '.png')
    r = subprocess.run(['curl', '-sS', '--max-time', '300', '-o', dst, urls[0]],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dst) or os.path.getsize(dst) == 0:
        print('  下载失败: %s' % (r.stderr or r.stdout).strip()[:300])
        sys.exit(1)
    print('  %.0fKB  %s' % (os.path.getsize(dst) / 1024, dst))


if __name__ == '__main__':
    main()
