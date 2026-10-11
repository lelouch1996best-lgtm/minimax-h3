# -*- coding: utf-8 -*-
"""恶搞素材包 · 大嘴鱼「法天象地」形态图 —— 线条虚影版（v2）

用户反馈修正：第 1 版把法相画成了「实体」，而参考图中的人物是**由发光线条勾勒的
半透明灵气虚影**。v2 严格照参考图的画法重做：
  · 人物 = 线条构成、非实体、半透明，能透出身后云海山岳
  · 轮廓由细密发光流线勾勒，内部中空，部分部位已虚化分解为飘散线条
  · 青绿灵气光柱自头顶倾泻而下贯通全身
  · 构图也照参考图：仰视巨人举臂向上、衣袍向右飘散、下方云海仙山、上方黄昏逆光

双参考图分工（身份 / 画风+形态）：
  第 1 张 = assets/恶搞/character/大嘴鱼/人物三视图（基础）.png → 唯一身份基准
  第 2 张 = 用户提供的仙侠法天象地图          → 画风 + 人物形态 + 构图 + 配色 全基准

输出：generated-images/大嘴鱼_法天象地_线条虚影_{A|B}.png
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

IDENTITY_REF = r'D:/work/minimax_h3/assets/恶搞/character/大嘴鱼/人物三视图（基础）.png'
STYLE_REF = (r'C:\Users\Administrator\.workbuddy\clipboard-images'
             r'\clipboard-2026-10-08T14-08-29-156Z-5616e4e2.jpg')

# ================================================================ 身份：唯一不变

IDENTITY_LOCK = (
    '第 1 张参考图是「穿西装的大嘴鱼」的唯一身份基准。'
    '**画面中这个由线条构成的虚影，其内部轮廓所勾勒的正是第 1 张图里那只大嘴鱼**，'
    '也就是说：把第 1 张图里的角色整体替换成线条虚影后再叠进这个仙侠场景。'
    '必须照搬的特征一个都不能改：'
    '（1）巨型鱼头与身体不成比例，嘴极大、横向咧开到近乎耳根，上下颌夸张外突，'
    '厚实湿润的嘴唇微张成一派憨厚呆滞的傻笑（不是凶狠龇牙、不是狰狞威慑），口内一整排细密尖牙；'
    '（2）小而圆、凸出于头部两侧的鱼眼，昏黄琥珀色虹膜，眼白布满细红血丝，眼神木讷憨钝；'
    '（3）头顶一小撮黏湿的深色水草状短须；'
    '（4）青灰绿色湿润鱼皮、细密小鳞片与不规则深色斑块、鳃部一道弧形鳃裂；'
    '（5）颈部以下为正常人类身躯，肩宽、手臂短粗、双手五指人类手掌、双腿短；'
    '**（6）服装：一套黑色光面精纺羊毛双排扣西装（细密驳头驳线、两排共六颗黑树脂纽扣）、'
    '同色西裤、黑色系带皮鞋，内搭白色衬衫、最上一颗扣子敞开、不打领带。**'
    '西装在这一版里同样只以**发光的线条网格**呈现（驳头线、纽扣、双排扣的排线都要勾出来），'
    '但绝不允许改成铠甲、长袍、披风或任何古装，也绝不允许变成不透明的实体布料。')

# ================================================================ 形态：严格照参考图

FIGURE_FORM = (
    '【最重要】画面中的人物**不是实体，而是一道完全由光线与线条构成的超自然虚影**，'
    '请严格照搬第 2 张参考图里人物的画法，一比一复现那种材质：'
    '（1）人物**半透明、非实体**：整体像一道被点亮的青绿色光之幻影，'
    '身体内部大面积中空透空，能清楚看见身后的云海、山岳与天光透过虚影内部；'
    '没有皮肤、没有血肉、没有实体厚度、没有不透明的黑色块面。'
    '（2）**轮廓与结构由成百上千根极细的发光线条勾勒**：'
    '外轮廓、鱼头轮廓、眉眼、嘴线、西装的驳头线、纽扣、排扣线、袖口与裤缝、'
    '手指与脚趾的关节线，全部由细如发丝的青绿色流线一根根描出，线条有粗细浓淡变化、'
    '有轻微抖动与波动，像被风吹起的一束束发丝在流动中定型，而不是一条均匀的描边。'
    '（3）**虚化与消散**：虚影的外缘、肩部、上臂、衣摆与下身高处，'
    '线条逐渐失去形状，散成无数细碎的光点与飘散的丝絮，正在被风吹散、融入云雾；'
    '部分衣摆已经彻底化作向右飘扬的长长流线；并非全身都是完整实线。'
    '（4）**法相的光柱**：一道强烈的青白色灵气光柱自天而降、贯穿法相全身，'
    '在虚影内部形成更亮的发光核心与丁达尔散射；虚影的亮度以被光柱击中的部位最高，'
    '向四周递减；体表有细碎的光尘与流光丝线向外飘散。'
    '（5）虚影有真实的辉光（bloom）与体积感（半透明层会叠加出更亮的交叠区），'
    '线条本身是青绿到近白的渐变高光，不是纯色平涂。')

COMPOSITION = (
    '构图严格照搬第 2 张参考图（横版 16:9 大全景，仰视机位）：'
    '巨大的线条虚影位于画面中央、占据画面上四分之三的高度，'
    '**镜头自下向上仰视**，视角对着这尊顶天立地的法相，'
    '强调它与云海山岳的悬殊尺度对比；'
    '法相**双臂向上举起**（一手高高举向头顶，另一手侧向平举），'
    '衣袍与线条向右前方大幅飘扬成一束束长流线；'
    '画面下方三分之一为翻涌的云海与层层叠叠的仙山岩峰剪影，'
    '山脊上有极小的古松与悬空栈道、天空中有几只飞鸟环绕虚影肩部，用它们反衬法相的巨大体量；'
    '画面上三分之一为金橙色的黄昏天光与逆光云层，'
    '青绿色灵气自法相体内透出并向四周扩散，空中漂浮着细碎光尘与流光丝线。')

STYLE_LOCK = (
    '第 2 张参考图是**画风、人物形态、构图与配色的总基准**，'
    '必须严格照它复现：国风仙侠厚涂CG质感、青绿与墨蓝的灵气主色、金色黄昏逆光、'
    '翻涌的云海与雾岚、体量惊人的巨大线条虚影、能量粒子与流光氛围。'
    '但**绝不要**沿用图中的角色外形细节：不要长发、不要长耳朵、不要仙袍与飘带、'
    '不要仙侠美男子面孔、不要古装配饰；也不要把图里悬浮的仙岛与宫殿群照搬为主体。')

REALITY = (
    '质感：国风仙侠厚涂CG动画电影级（不是真人实拍、不是照片写实）。'
    '云海有真实的体积与层次，云的边缘被金色逆光镶上一圈亮边；'
    '青绿色灵气为半透明体积光，能看到光在云雾中的散射与丁达尔效应；'
    '线条有真实的辉光溢出与能量感，线条交叠处更亮、线条散开处更淡；'
    '整尊虚影像一道被风吹拂的、发光的、随时会消散的巨大幻影。')

NEGATIVE = (
    '【本版最重要的排除项】避免把人物画成实体：不要不透明的实体人物、'
    '不要厚重的三维实体、不要真实皮肤与血肉质感、不要结实的肌肉块面、不要实体布料与褶皱阴影、'
    '不要暗部黑块、不要卡通、动漫赛璐璐平涂、线稿描边、Q 版、3D 游戏低模、塑料感、'
    '搪胶手办感、廉价 CG；人物必须始终是半透明的线条虚影。\n'
    '避免横版画面中出现任何文字、字幕、水印、logo、题字、印章、落款；\n'
    '避免：仙侠美男子面孔、人类面孔、人类五官、长发、尖耳、飘带、'
    '仙袍、铠甲、披风、斗笠、束发冠、古装配饰、金童玉女、仙鹤、巨龙、'
    '以及任何其他人物或生物；第二张参考图里的悬浮仙岛与宫殿群不要照搬；\n'
    '避免：恐怖、血腥、狰狞、龇牙威慑、血盆大口、伤口、血液；\n'
    '避免：手部畸变（无多指、无粘连、无指节反折）；'
    '避免：把西装改掉（禁止铠甲/长袍/披风/僧袍/任何古装）。')

# ================================================================ 变体

VARIANTS = [
    {
        'name': 'A',
        'title': '雷暴翠绿·高对比',
        'extra': ('氛围：墨蓝近黑的天幕压暗，云层间有电弧游走；'
                  '青绿灵气光柱自头顶强势倾泻，线条以浓烈的翠绿与近白高光为主，'
                  '光尘与流光丝线更密集；整体对比强、压迫感重。'),
    },
    {
        'name': 'B',
        'title': '云海暖金·柔光',
        'extra': ('氛围：金橙色的低角度黄昏逆光从画面右后方穿透云层，'
                  '为虚影的线条勾出一道金边；青绿与暖金交织，'
                  '线条稍柔和、光晕更大、边缘更柔；整体明亮通透。'),
    },
]


def build(v):
    return '\n\n'.join([
        IDENTITY_LOCK, FIGURE_FORM, COMPOSITION, v['extra'], STYLE_LOCK, REALITY, NEGATIVE,
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

    print('[1/4] 编码两张参考图')
    uri_id = load_b64(IDENTITY_REF)
    uri_style = load_b64(STYLE_REF)

    tasks = []
    print('[2/4] 提交 %d 个变体' % len(VARIANTS))
    for v in VARIANTS:
        prompt = build(v)
        payload = {
            'kind': 'image', 'model': 'gpt-image-2',
            'input': {'prompt': prompt, 'size': '16:9', 'resolution': '2k', 'n': 1,
                      'image': [uri_id, uri_style]},
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
        with open(os.path.join(OUT, '大嘴鱼_法天象地_线条虚影_变体%s_task.json' % v['name']),
                  'w', encoding='utf-8') as f:
            json.dump({'task_id': tid, 'variant': v['title'], 'rev': 'v2-线条虚影', 'prompt': prompt,
                       'refs': ['大嘴鱼 人物三视图（基础）.png（身份）',
                                'clipboard-2026-10-08T14-08-29-156Z-5616e4e2.jpg（画风/形态/构图）']},
                      f, ensure_ascii=False, indent=2)
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
        dst = os.path.join(OUT, '大嘴鱼_法天象地_线条虚影_%s.png' % t['v']['name'])
        with urllib.request.urlopen(urls[0], timeout=180) as r:
            blob = r.read()
        with open(dst, 'wb') as f:
            f.write(blob)
        print('    [%s] %.0fKB  %s' % (t['v']['name'], len(blob) / 1024, dst))

    ok = sum(1 for t in tasks if done.get(t['id'], {}).get('status') == 'done')
    print('\nSUMMARY ok=%d / total=%d' % (ok, len(tasks)))


if __name__ == '__main__':
    main()
