# -*- coding: utf-8 -*-
"""凡人修仙传 · 穆兰圣女「基础（3D 国漫 CG 画风）· 无头饰 + 脸部受伤」三视图

需求（2026-10-12 用户，跟随真人质感版之后）：
  与 `fr_mulan_injured_views.py` 同一套改动，但**画风换成「基础」的 3D 国漫 CG 渲染**：
    ① 去掉头饰 —— 摘掉青色头纱与额前银冠（含镶翠绿宝石额饰），乌黑长发披散、露出完整额头
    ② 脸部受伤 —— 画面左侧脸颊（人物自己的右脸颊）一道斜向浅表划伤结痂细线
  其余（五官/脸型/耳饰/银项饰/青绿孔雀羽交领上衣/白色羽片护肩/长裙/腰带/靴/白底版式）一律不变。

双参考图分工：
  REF1 = 穆兰圣女/人物三视图（基础）.png          -> 身份五官 + 全身服装形制 + 白底影棚版式 + **3D 国漫 CG 画风基准**
  REF2 = 穆兰圣女/参考/无头饰+脸部受伤.png        -> 只取「无头饰的发型状态」与「脸颊伤痕形态」，
                                                     其真人实拍质感、山林瀑布背景、冷蓝环境光一律不沿用

版式：16:9 横版，纯白背景，同画布左右两列（左 30% 面部特写 + 右 70% 正/侧/背三视）
参数：65535 / gpt-image-2.5-flare / 16:9 / 2k / n=1
下载：curl（Python urllib 对 result_urls 直链会 403）
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
NAME = '穆兰圣女_基础CG画风_三视图_无头饰受伤'

REF1 = 'assets/凡人/character/穆兰圣女/人物三视图（基础）.png'
REF2 = 'assets/凡人/character/穆兰圣女/参考/无头饰+脸部受伤.png'

LAYOUT = (
    '完整角色设定稿，纯白色背景，同一画布内分左右两列排版，列间留明显白色空隙：\n'
    '左列为一整格超精细面部特写（占画幅左侧约 30% 宽度，竖长构图，取景到胸口上方，'
    '面部正对镜头、五官清晰）。\n'
    '右列为一整格角色标准三视图（占画幅右侧约 70% 宽度），内部横向并排三个全身立姿：'
    '① 正面全身（面向镜头、双臂自然垂于身侧）；'
    '② 侧面全身（身体转 90 度朝向画面左侧）；'
    '③ 背面全身（背对镜头）。三视角为同一人物、同一服装、同一姿态基准，人物全身完整入画、'
    '头顶与脚底不被画幅边缘裁断。\n'
    '四个分区内容互不重叠、不串格。\n'
    '画面中不出现任何文字、字母、数字、标注或水印（包括「面部特写 / 正面 / 侧面 / 背面」等视角标签与角色名）。'
)

IDENTITY = (
    '身份基准：严格保持第 1 张参考图中同一名成年女性的面部五官、脸型、眉形、眼型、唇形与颈部比例完全不变'
    '（三十出头、面容清丽的东方美人，鹅蛋脸、细长柳叶眉、杏眼、薄唇），气质神圣清冷。'
    '四个分区中的人物自始至终是同一个人，五官完全一致，不得换脸、不得改脸型、不得增减五官特征。'
)

CHANGE = (
    '本次**唯一的两处改动**（其余一切照第 1 张参考图不变）：\n'
    '改动一 · 去除头饰：第 1 张参考图中覆盖头部与双肩的**青绿色头纱**、以及**额前银色金属头冠**'
    '（连同头冠正中镶嵌的翠绿宝石额饰）在本设定稿中**全部去除、完全不存在**；'
    '头顶、额前、两侧鬓角与肩背上不再有任何头纱、头巾、头冠、额饰、发箍或头饰件。'
    '取而代之的是**乌黑长发自然披散**：头发自头顶中分（略偏），发量丰厚、蓬松，'
    '带成束发丝与柔和光泽，完整露出光洁的额头与完整发际线，'
    '两侧长发自然垂落至胸前与肩前，背后长发披垂至腰际、盖住后背（第 2 张参考图即为去除头饰后的发型状态）。\n'
    '改动二 · 脸部受伤：在**画面左侧的那半张脸**上——即**人物自己的右脸颊**——有一道清晰的**斜向浅表划伤**：'
    '伤口自颧骨外下方起始，斜向内下延伸至脸颊中段（走向约与鼻梁平行、略带弧度），'
    '长约 3 厘米、宽约 2 毫米，呈**暗红褐色的结痂细线**，伤口边缘有轻微泛红；'
    '创面干净利落，**无血渍、无渗液、无肿胀、无淤血、无青紫、无纱布与创可贴**（第 2 张参考图即为该伤痕的形态基准）。'
    '该伤痕在左列**面部特写**格与右列**正面全身**格中均清晰可见，位置、长度、走向与形态完全一致；'
    '右列**侧面全身**格中可见其沿颊面转向的侧面走向；'
    '右列**背面全身**格中因背对镜头而不可见。\n'
    '除上述两处外，其余一律**严格不变**：面部五官与脸型、耳饰（银色长坠耳环）、'
    '颈部的**银质纹饰项饰（choker）**、青绿色孔雀羽纹交领上衣、肩部白色羽片护肩、'
    '青绿与深色层叠长裙、腰封与垂坠腰饰、腕部银环、黑色短靴——全部与第 1 张参考图完全一致，'
    '配色、纹样与形制不得改动。'
)

RENDER = (
    '渲染风格：**高品质国漫 3D 动画 CG 渲染**（影视级三维动画质感）——'
    '**不是真人实拍照片、不是真人摄影，也不是 2D 平涂动漫**。'
    '画风完全以第 1 张参考图为唯一基准：皮肤有细腻通透的次表面散射感与平滑明暗过渡，'
    '无毛孔、无绒毛、无皮肤瑕疵、无写实肌理；面部为三维动画的干净造型，五官轮廓清晰、边缘干净；'
    '头发为成束的三维发丝，有自然的束感与丝缎高光；'
    '衣料有三维渲染的织物质感、厚实垂坠与清晰褶皱；'
    '金属饰件有干净的金属反光而不是照片级磨损。'
    '整体使用干净的影棚布光：柔和主光＋两侧补光＋顶部轮廓光，明暗过渡平滑，无噪点、无脏色。'
    '第 2 张参考图仅用于确认「无头饰后的发型状态」与「脸颊伤痕的位置与形态」这两项信息，'
    '**其真人实拍质感、山林瀑布背景、冷蓝环境光与暗色调一律不沿用**。'
)

SCENE = (
    '场景：纯白色的摄影棚背景，柔和均匀的白光，无任何布景、道具与投影。\n'
    '人物全身直立自然站姿，正面、侧面、背面三个视角并排，另在左侧排一张面部特写；'
    '表情放松中性、略带清冷，不做夸张表情与摆拍动作。'
)

NEGATIVE = (
    '避免：真人实拍照片感、真人摄影质感、写实毛孔与皮肤肌理、写实绒毛与胡渣、'
    '照片级皮肤瑕疵、影视级写实打光、真人演员感；'
    '避免：2D 平涂动漫、美式卡通、塑料玩具质感、低模粗糙建模、糊线与锯齿；'
    '避免：保留或残留任何头饰——不得出现青色头纱、头巾、头冠、银冠、额饰、镶宝石头饰、发箍、'
    '发带或任何覆盖头顶与额头的饰件；额头与发际线必须完全露出、不被任何头饰遮挡；'
    '避免：伤痕画成狰狞大伤口、撕裂伤、流血、血渍、渗液、化脓、肿胀、淤青、青紫、疤痕增生、'
    '绷带、纱布、创可贴、药膏；避免伤痕出现在错误位置（人物的左脸颊、鼻梁、额头、下巴、颈部、'
    '手臂或身体其他部位），伤痕必须且仅在人物右脸颊（画面左侧那半张脸）；'
    '避免四个分区之间伤痕的有无、位置或形态不一致；'
    '避免：脸部走形或与参考图不像、四个分区之间人物长相不一致；'
    '避免：沿用第 2 张参考图的背景元素——不出现山林、树木、瀑布、岩石、雾气、水汽、暗色布景、'
    '冷蓝环境光与暗色调，背景必须保持纯白色；'
    '避免：面部标记乱加——不出现第 1 张参考图以外的痣、斑点、印记、纹身或饰点；'
    '画面无任何文字、字母、字幕、水印、logo、视角标签；'
    '手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连）；'
    '发饰与腰饰不重复不悬空、不穿模。'
)

PROMPT = '\n\n'.join([LAYOUT, IDENTITY, CHANGE, RENDER, SCENE, NEGATIVE])


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

    with open(r'D:/work/minimax_h3/logs/_mulan_injured_cg_prompt.txt', 'w', encoding='utf-8') as f:
        f.write(PROMPT)

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
    print('=== 阶段 4：下载（走 curl）===')
    dst = os.path.join(OUT, NAME + '.png')
    r = subprocess.run(['curl', '-sS', '--max-time', '300', '-o', dst, urls[0]],
                       capture_output=True, text=True)
    if r.returncode != 0 or not os.path.exists(dst) or os.path.getsize(dst) == 0:
        print('  下载失败: %s' % (r.stderr or r.stdout).strip()[:300])
        sys.exit(1)
    print('  %.0fKB  %s' % (os.path.getsize(dst) / 1024, dst))


if __name__ == '__main__':
    main()
