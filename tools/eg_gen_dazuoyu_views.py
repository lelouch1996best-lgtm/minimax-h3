# -*- coding: utf-8 -*-
"""恶搞素材包 · 大嘴鱼（穿西装妖怪）三视图生成（65535 gpt-image-2 图生图）

原创角色，无官方立绘可参考 → 采用「单参考图配方」：
  参考图 = 凡人包 韩立《人物三视图（真人质感-基础）.png》
           仅用于锁定「左列超精细特写 + 右列正/侧/背三视图」两列版式、
           纯白摄影棚背景、写实电影级生物渲染质感与柔和布光；
           严禁沿用其人脸 / 古装 / 任何古装元素。
  角色本身完全由文字提示词定义。

流程：压缩编码 -> 提交 N 个变体 -> 统一轮询 -> 下载到 generated-images/
输出：D:/work/minimax_h3/generated-images/大嘴鱼_真人质感_三视图基础_{变体}.png
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

# 版式 / 画风基准图：韩立 真人质感三视图（与凡人包同配方）
STYLE_REF = r'D:/work/minimax_h3/assets/凡人/character/韩立/人物三视图（真人质感-基础）.png'

# ---------------------------------------------------------------- 提示词模块

LAYOUT = ('完整角色设定稿，纯白色背景，同画布分左右两列排版：第一列超精细头部特写（占30%宽度），'
          '第二列角色标准三视图（正面 / 侧面 / 背面）（占70%宽度）。'
          '画面中不出现任何文字、字母、数字、标注或水印（包括「正面 / 侧面 / 背面」等视角标签与角色名）。')

STYLE_LOCK = (
    '参考图仅用于确定以下三点，其余一切与它无关，**不要沿用参考图中人物的长相、发型、服装、'
    '配饰与任何古装元素**：'
    '① 两列排版（左列特写 + 右列三视图）；② 纯白摄影棚背景与柔和均匀白光；'
    '③ 写实电影级生物特效渲染质感（photorealistic creature feature），材质有真实次表面散射与湿润反光。')

# 形象核心（全变体共用）—— 只锁头部与物种特征，服装按变体切换
CORE = (
    '角色是一只拟人化直立行走的鱼头妖怪，是一条「穿西装的大嘴鱼」：'
    '头部为一条巨大的、与身体不成比例的鱼头，占整体身高的约三分之一，是全身最强辨识点——'
    '嘴极大且向两侧横向咧开到近乎耳根，上下颌夸张外突，嘴唇厚实饱满、湿润带反光，'
    '嘴内是一整排细密整齐的尖牙与一条厚实的舌头；'
    '嘴大到必须靠夸张的横向撕裂才能张开，此刻微微咧开呈一个憨厚呆滞的笑，'
    '不是凶狠龇牙、不是狰狞表情，眼睛因此被挤成弯月；'
    '鱼眼小而圆、凸出于头部两侧，虹膜呈昏黄琥珀色，眼白布满细小红血丝，眼神木讷憨钝；'
    '头部皮肤为湿润的青灰绿色，布满细密的小鳞片与不规则的深色斑块，'
    '表面有真实的水光与黏液反光，鳃部有一道张合的弧形鳃裂；'
    '头部顶端有一小撮黏湿的深色短须状水草，像刚出水的滑稽发型；'
    '身体其余部分被完全包裹在人类西装里，从颈部以下看不到任何鱼类特征——'
    '肩宽、手臂短粗、双手为正常的五指人类手掌（鳍化程度极低），双腿短，站姿微微内八。')

REALITY = (
    '写实电影质感：这必须是高预算生物特效电影里的**真实存在的一只活物**，被真实摄影机拍到，'
    '而不是卡通、动漫、玩具或游戏建模。'
    '鱼皮有真实的湿润黏液反光与次表面散射，鳞片有真实的厚度与边缘翘起，'
    '皮肤褶皱与毛孔级细节清晰，皮肤上有真实的明暗过渡与柔和阴影；'
    '眼球湿润充血、角膜有真实高光；'
    '西装为真实布料——精纺羊毛有可见织物纹理、褶裥与垂坠感，'
    '金属纽扣与领带夹有真实金属反光而不是塑料高光；'
    '手与手指的数量、关节、长度与握持合理（有五指、无多指粘连）。'
    '面部比例、头身比与身体解剖真实可信（头虽大但符合「卡通化写实」的自然比例，不崩坏、不畸变）。')

SCENE = (
    '场景：纯白色摄影棚背景，柔和均匀的白光，无任何布景、道具与投影。'
    '角色全身直立自然站姿、正面侧面背面三个视角并排，另在左侧排一张头部特写；'
    '双手自然垂放或一只插进西装裤袋，表情放松中性，不做夸张动作与摆拍姿势。')

NEGATIVE = (
    '避免：卡通、动漫、漫画、赛璐璐平涂、线稿描边、Q 版、夸张大眼、表情包画风、'
    '3D 游戏低模、塑料模型感、玩具感、搪胶手办感、廉价 CG、赛璐璐质感；'
    '恐怖、血腥、狰狞、龇牙威慑、伤口、血液、内脏、腐烂、死亡；'
    '影棚大片打光、商业时尚大片、油蜡感高光、过度 HDR、极端背景虚化；'
    '画面中不出现任何文字、字幕、水印、logo、视角标签、角色姓名；'
    '不出现第二个人物、不出现背景场景与任何道具，背景为纯白；'
    '三视图三个视角必须是同一只角色、同一套西装、同一颗鱼头，鱼头造型与鳞片斑纹完全一致；'
    '西装颜色、纽扣数量、领带（如有）三个视角必须完全一致，不得增删配饰。')

# ---------------------------------------------------------------- 变体

VARIANTS = [
    {
        'name': 'A',
        'title': '黑双排扣·敞领',
        'outfit': ('服装为一套剪裁合体的黑色双排扣西装：光面精纺羊毛面料、细密驳头驳线、'
                   '两排共六颗黑曜石般的树脂纽扣、同色西裤与黑色系带皮鞋；'
                   '内搭白色衬衫，最上一颗扣子敞开、不打领带，衬衫领口自然外翻，'
                   '露出一小截青灰色的颈部皮肤与衬衫下方的鱼鳃边缘。'),
    },
    {
        'name': 'B',
        'title': '藏青细条纹·歪领带',
        'outfit': ('服装为一套藏青色细条纹双排扣西装：细白条纹羊毛面料、缎面驳头、'
                   '黑树脂纽扣、同色西裤与黑色系带皮鞋；'
                   '内搭浅蓝色衬衫，打一条深红色斜纹领带但明显打歪、松垮地歪向一侧，'
                   '领带结偏小并略微松开，衬衫领口不那么规整。'),
    },
]

# 变体可覆盖的场景/表情句
EXPR = ''


def build(v):
    return '\n\n'.join([
        LAYOUT,
        STYLE_LOCK,
        CORE + v['outfit'],
        REALITY,
        SCENE,
        NEGATIVE,
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
        with open(os.path.join(OUT, '大嘴鱼_变体%s_三视图_task.json' % v['name']), 'w', encoding='utf-8') as f:
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
                pending.pop(tid)
                done[tid] = st
                nm = pending.get(tid) or next(t['v']['name'] for t in tasks if t['id'] == tid)
                print('    [%02d] %s %s' % (i, nm, s))
        if not pending:
            break

    print('[4/4] 下载')
    for t in tasks:
        st = done.get(t['id'])
        if not st or st.get('status') != 'done':
            print('    [%s] 跳过（%s）' % (t['v']['name'], (st or {}).get('status', 'timeout/no-result')))
            if st and st.get('status') == 'failed':
                print('        error:', json.dumps(st.get('error') or st, ensure_ascii=False)[:400])
            continue
        urls = st.get('result_urls') or []
        if not urls:
            print('    [%s] 无 result_urls' % t['v']['name'])
            continue
        dst = os.path.join(OUT, '大嘴鱼_真人质感_三视图基础_%s.png' % t['v']['name'])
        with urllib.request.urlopen(urls[0], timeout=180) as r:
            blob = r.read()
        with open(dst, 'wb') as f:
            f.write(blob)
        print('    [%s] %.0fKB  %s' % (t['v']['name'], len(blob) / 1024, dst))
        print('    FILE ' + dst)

    ok = sum(1 for t in tasks if done.get(t['id'], {}).get('status') == 'done')
    print('\nSUMMARY ok=%d / total=%d' % (ok, len(tasks)))


if __name__ == '__main__':
    main()