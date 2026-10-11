# -*- coding: utf-8 -*-
"""恶搞素材包 · 猴头（西装妖怪·同类）三视图生成（65535 gpt-image-2 图生图）

复用 `eg_gen_dazuoyu_views.py` 的「原创包单参考图配方」：
  参考图 = 凡人包 韩立《人物三视图（真人质感-基础）.png》
           只锁两列版式 + 纯白棚拍 + 写实电影级生物渲染质感，
           严禁沿用其人脸 / 古装。
  角色形象完全由文字定义。

设计要点：与大嘴鱼同属「恶搞西装妖怪」系列，因此**西装形制必须一致**
（黑双排扣羊毛西装 + 敞领白衬衫 + 不打领带），便于同一集里与法天象地巨像同框。
物种改为猕猴：宽扁猴脸、金色圆环瞳孔、无眉骨高光、短棕毛。
用于替换原片 S10 的「凡人女青年反应镜头」。

输出：generated-images/猴头_真人质感_三视图基础_{A|B}.png
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
OUT = r'D:/work/minimax_h3/generated-images'

# 版式 / 画风基准：与大嘴鱼同源，保持「恶搞包」统一画风
STYLE_REF = r'D:/work/minimax_h3/assets/凡人/character/韩立/人物三视图（真人质感-基础）.png'

LAYOUT = ('完整角色设定稿，纯白色背景，同画布分左右两列排版：第一列超精细头部特写（占30%宽度），'
          '第二列角色标准三视图（正面 / 侧面 / 背面）（占70%宽度）。'
          '画面中不出现任何文字、字母、数字、标注或水印（包括「正面 / 侧面 / 背面」等视角标签与角色名）。')

STYLE_LOCK = (
    '参考图仅用于确定以下三点，其余一切与它无关，**不要沿用参考图中人物的长相、发型、服装、'
    '配饰与任何古装元素**：'
    '① 两列排版（左列特写 + 右列三视图）；② 纯白摄影棚背景与柔和均匀白光；'
    '③ 写实电影级生物特效渲染质感（photorealistic creature feature），材质有真实次表面散射与反光。')

CORE = (
    '角色是一只拟人化直立行走的猴头妖怪，是一只「穿西装的大嘴鱼的同类」——'
    '头部为一只猕猴的头，与身体不成比例地大，占整体身高的约三分之一，是全身最强辨识点：'
    '脸型宽扁而略呈倒三角，吻部短而宽、向前微突，鼻孔清晰外翻成两个圆孔；'
    '**眼睛为大而圆的动物眼，虹膜是明亮的琥珀金色、瞳孔为圆形黑色大环**（不是人类的竖瞳或细长眼缝），'
    '眼白略带浑浊、眼角有细微皱纹，眼神机敏而带一点不安分的狡黠；'
    '眉骨低平、无眉毛，鼻梁上方有一道浅浅的横向褶皱；'
    '毛发为短而密的深棕灰色猴毛，毛流自然向脑后梳，头顶有一小撮微微翘起的呆毛，'
    '颊侧与下巴的毛发稍长、质地蓬松；'
    '双耳圆小、贴在头侧，耳内可见淡粉色耳廓；'
    '嘴部宽大，唇薄，微微张开露出上下两排整齐的浅黄色牙，神情是一派被抓包后的尴尬又强装镇定的呆滞；'
    '身体其余部分被完全包裹在人类西装里，从颈部以下看不到任何猴类特征——'
    '肩宽、手臂短粗、双手为正常的五指人类手掌（握持姿态自然），双腿短，站姿微微内八。')

REALITY = (
    '写实电影质感：这必须是高预算动物特效电影里的**真实存在的一只活猴**，被真实摄影机拍到，'
    '而不是卡通、动漫、玩具或游戏建模。'
    '猴毛有真实的毛流走向与逐根体积感，可见细小的绒毛飞散、蓬松的颊侧毛与颈后毛簇；'
    '面部皮肤（鼻孔、眼周、嘴唇）无毛且湿润，有真实的次表面散射、油脂反光与毛孔级细节，'
    '皮肤有真实的明暗过渡与柔和阴影；'
    '眼球湿润、角膜有真实高光；'
    '西装为与同系列「穿西装的大嘴鱼」**完全一致**的形制——黑色光面精纺羊毛面料、'
    '可见织物纹理与褶裥与垂坠感，金属质感纽扣与皮鞋有真实反光而不是塑料高光；'
    '手与手指的数量、关节、长度与握持合理（有五指、无多指粘连）。'
    '面部比例、头身比与身体解剖真实可信（头虽大但符合「卡通化写实」的自然比例，不崩坏、不畸变）。')

SCENE = ('场景：纯白色摄影棚背景，柔和均匀的白光，无任何布景、道具与投影。'
         '角色全身直立自然站姿，正面、侧面、背面三个视角并排，另在左侧排一张头部特写；'
         '表情放松中性，略带呆滞，不做夸张动作与摆拍姿势。')

NEGATIVE = (
    '避免：卡通、动漫、漫画、赛璐璐平涂、线稿描边、Q 版、夸张大眼、表情包画风、'
    '3D 游戏低模、塑料模型感、玩具感、搪胶手办感、廉价 CG；'
    '恐怖、血腥、狰狞、龇牙威慑、獠牙外露、伤口、血液、腐烂；'
    '猕猴以外的动物（猴子的五官必须严格是猕猴：宽扁脸、短吻、圆眼金虹膜）；'
    '毛发过长或呈狮子/老虎/熊/犬科的蓬松长毛；'
    '影棚大片打光、商业时尚大片、油蜡感高光、过度 HDR、极端背景虚化；'
    '画面中不出现任何文字、字幕、水印、logo、视角标签、角色姓名；'
    '不出现第二个人物、不出现背景场景与任何道具，背景为纯白；'
    '三视图三个视角必须是同一只角色、同一套西装、同一颗猴头，毛色与西装细节完全一致；'
    '西装颜色、纽扣数量三个视角必须完全一致，不得增删配饰；'
    '手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连）。')

# 变体：只差气质与领口，与大嘴鱼包保持同一西装形制
VARIANTS = [
    {
        'name': 'A',
        'title': '黑双排扣·敞领（与大嘴鱼同款）',
        'outfit': ('服装与同系列「穿西装的大嘴鱼」完全一致：黑色光面精纺羊毛双排扣西装、'
                   '细密驳头驳线、两排共六颗黑树脂纽扣、同色西裤与黑色系带皮鞋；'
                   '内搭白色衬衫，最上一颗扣子敞开、不打领带，衬衫领口自然外翻。'),
        'expr': '表情为被抓包后的尴尬：嘴角僵硬地抽动一下，眼神斜向别处，不敢直视镜头。',
    },
    {
        'name': 'B',
        'title': '黑双排扣·歪领带（更滑稽）',
        'outfit': ('服装仍为黑色光面精纺羊毛双排扣西装、细密驳头驳线、两排共六颗黑树脂纽扣、'
                   '同色西裤与黑色系带皮鞋；'
                   '内搭浅蓝色衬衫，打一条深红色斜纹领带但明显打歪、松垮地歪向一侧，结偏小并略微松开。'),
        'expr': '表情为强装镇定的呆板：一动不动地直视镜头，嘴巴微张，眼神木讷。',
    },
]


def build(v):
    return '\n\n'.join([
        LAYOUT, STYLE_LOCK, CORE + v['outfit'], REALITY, SCENE, v['expr'], NEGATIVE,
    ])


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
    b = buf.tobytes()
    print('    %s  %dx%d  %.0fKB' % (os.path.basename(path), img.shape[1], img.shape[0], len(b) / 1024))
    return 'data:image/jpeg;base64,' + base64.b64encode(b).decode('ascii')


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

    print('[1/4] 编码画风参考图')
    uri_style = load_b64(STYLE_REF)

    tasks = []
    print('[2/4] 提交 %d 个变体' % len(VARIANTS))
    for v in VARIANTS:
        prompt = build(v)
        payload = {
            'kind': 'image', 'model': 'gpt-image-2',
            'input': {'prompt': prompt, 'size': '16:9', 'resolution': '2k', 'n': 1, 'image': [uri_style]},
        }
        try:
            resp = api('POST', '/v1/tasks', payload)
        except urllib.error.HTTPError as e:
            print('    [%s] 提交失败 HTTP %s: %s' % (v['name'], e.code, e.read().decode('utf-8', 'replace')[:400]))
            continue
        tid = resp.get('id') or resp.get('task_id')
        if not tid:
            print('    [%s] 无 task id: %s' % (v['name'], json.dumps(resp, ensure_ascii=False)[:400]))
            continue
        tasks.append({'v': v, 'id': tid})
        with open(os.path.join(OUT, '猴头_变体%s_三视图_task.json' % v['name']), 'w', encoding='utf-8') as f:
            json.dump({'task_id': tid, 'variant': v['title'], 'prompt': prompt,
                       'style_ref': STYLE_REF}, f, ensure_ascii=False, indent=2)
        print('    [%s] %s -> %s' % (v['name'], v['title'], tid))
        time.sleep(1)

    if not tasks:
        print('无任务提交成功')
        return

    print('[3/4] 轮询（每 5s，最多 120 次）')
    pending = {t['id']: t for t in tasks}
    done = {}
    for i in range(120):
        time.sleep(5)
        for tid in list(pending):
            try:
                st = api('GET', '/v1/tasks/' + str(tid), timeout=60)
            except urllib.error.HTTPError:
                continue
            s = st.get('status')
            if s in ('done', 'failed'):
                nm = pending[tid]['v']['name']
                pending.pop(tid)
                done[tid] = st
                print('    [%02d] %s %s' % (i, nm, s))
        if not pending:
            break

    print('[4/4] 下载')
    for t in tasks:
        st = done.get(t['id'])
        if not st or st.get('status') != 'done':
            print('    [%s] 跳过（%s）' % (t['v']['name'], (st or {}).get('status', 'timeout/no-result')))
            if st and st.get('status') == 'failed':
                print('        error:', json.dumps(st.get('error') or st, ensure_ascii=False)[:500])
            continue
        urls = st.get('result_urls') or []
        if not urls:
            print('    [%s] 无 result_urls' % t['v']['name'])
            continue
        dst = os.path.join(OUT, '猴头_真人质感_三视图基础_%s.png' % t['v']['name'])
        with urllib.request.urlopen(urls[0], timeout=180) as r:
            blob = r.read()
        with open(dst, 'wb') as f:
            f.write(blob)
        print('    [%s] %.0fKB  %s' % (t['v']['name'], len(blob) / 1024, dst))

    ok = sum(1 for t in tasks if done.get(t['id'], {}).get('status') == 'done')
    print('\nSUMMARY ok=%d / total=%d' % (ok, len(tasks)))


if __name__ == '__main__':
    main()