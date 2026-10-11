# -*- coding: utf-8 -*-
"""恶搞素材包 · 大嘴鱼「法天象地」形态图生成（65535 gpt-image-2 图生图）

双参考图分工（按 SKILL.md「一张定画风、一张定形象」原则调整）：
  第 1 张 = assets/恶搞/character/大嘴鱼/人物三视图（基础）.png
           → 唯一身份基准：只取鱼头造型（横咧巨嘴/厚唇/细密尖牙/凸出鱼眼/头顶水草短须/
             青灰绿湿润鳞片）与黑色双排扣西装，不得改变其体型比例以外的特征。
  第 2 张 = 用户提供的「法天象地」仙侠参考图（clipboard-2026-10-08T14-08-29-156Z-5616e4e2.jpg）
           → 画风 / 氛围 / 构图基准：国风仙侠厚涂CG、青绿灵气光柱、云海缭绕、
             金色黄昏逆光、悬浮仙山岩峰、古松剪影、巨大神祇般的体量感。
             ⚠️ 明确排除原图中的人物外形（不要长耳朵、不要长发仙袍、不要仙侠美男子脸）。

输出：generated-images/大嘴鱼_法天象地_{变体}.png
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

# ---------------------------------------------------------------- 提示词模块

IDENTITY_LOCK = (
    '第 1 张参考图是「穿西装的大嘴鱼」的唯一身份基准，请严格照搬以下特征，一个都不能改：'
    '（1）头部是一条与身体不成比例的巨型鱼头，占整体身高的约三分之一——'
    '嘴极大、横向咧开到近乎耳根，上下颌夸张外突，厚实饱满湿润的粉灰色嘴唇'
    '微张成一派憨厚呆滞的傻笑（不是凶狠龇牙、不是狰狞威慑），'
    '口内一整排细密整齐的尖牙与一条厚舌；'
    '（2）小而圆、凸出于头部两侧的鱼眼，昏黄琥珀色虹膜，眼白布满细红血丝，眼神木讷憨钝；'
    '（3）头顶一小撮黏湿的深色水草状短须；'
    '（4）皮肤为湿润的青灰绿色，布满细密小鳞片与不规则深色斑块，鳃部有一道弧形鳃裂，'
    '表面有真实水光与黏液反光；'
    '（5）颈部以下是正常人类身躯，肩宽、手臂短粗、双手为正常的五指人类手掌、双腿短。'
    '**必须保留的服装：一套黑色光面精纺羊毛双排扣西装（细密驳头驳线、两排共六颗黑树脂纽扣）、'
    '同色西裤、黑色系带皮鞋，内搭白色衬衫、最上一颗扣子敞开、不打领带。**'
    '西装在这张图里就是这套，不得改成铠甲、长袍、披风或任何古装，也不得改颜色。')

STYLE_LOCK = (
    '第 2 张参考图仅用于确定**画风、氛围、配色与构图**，其余一切与它无关：'
    '**绝对不要**沿用图中的角色外形（不要长耳朵、不要长发仙袍、不要仙侠美男子面孔、'
    '不要古装配饰、不要悬浮的仙岛建筑群作为主体）；'
    '要借用的是它的——国风仙侠厚涂CG质感、青绿与墨蓝的灵气主色、金色黄昏逆光、'
    '翻涌的云海与雾岚、体量惊人的巨大神祇与渺小山岳的尺度对比、'
    '国风仙山岩峰与古松剪影的层叠构图、能量粒子与流光的氛围。')

COMPOSITION = (
    '构图：横版 16:9 大全景，横向宽幅。'
    '「大嘴鱼法天象地」——同一条穿黑西装的巨型大嘴鱼化作顶天立地的法相，'
    '身体立于群山之巅、云海之上，以山为阶、以云为袍，体量如山岳般庞大，'
    '双臂自然垂放、一手虚抬作「法天象地」式的施法姿态，肩背挺直，'
    '巨大的鱼头低垂俯视人间，神情依旧是那副憨厚呆滞的傻笑——'
    '庄严的仙侠法相与滑稽的西装大嘴鱼形成荒诞反差，这就是画面的笑点所在。'
    '比例参照：山脚下有极小的古松、悬空栈道与 miniature 般的古建筑屋脊，'
    '天空有几只飞鸟环绕其肩头，以此强烈反衬法相的巨大体量。'
    '画面下三分之一是翻涌的云海与若隐若现的仙山岩峰，上三分之一是金色黄昏天光与逆光云层，'
    '青绿色灵气自法相体内透出并向四周扩散，空中漂浮着细碎的光尘与流光丝线。')

REALITY = (
    '质感要求：国风仙侠厚涂CG动画电影级质感（不是真人实拍、不是照片写实）。'
    '鱼皮保留半透明的次表面散射与湿润黏液反光，鳞片有真实厚度与边缘翘起，'
    '眼球湿润充血、有角膜高光；青绿色灵气为半透明体积光，能看到光在云雾中的散射与丁达尔效应；'
    '西装羊毛有可见织物纹理与褶裥，黑树脂纽扣与皮鞋有真实反光；'
    '云海有真实的体积与层次，云的边缘被金色逆光镶上一圈亮边。')

NEGATIVE = (
    '避免：横版画面中出现任何文字、字幕、水印、logo、题字、印章、落款；'
    '避免：仙侠美男子面孔、人类面孔、人类五官、长发、耳朵、尖耳、飘逸长发、'
    '仙袍、铠甲、披风、斗笠、束发冠、古装配饰、金童玉女、仙鹤、巨龙、'
    '以及任何其他人物或生物；第二张参考图里的悬浮仙岛与宫殿群不要照搬；'
    '避免：卡通、动漫赛璐璐平涂、线稿描边、Q版、3D游戏低模、塑料感、搪胶手办感、廉价CG；'
    '避免：恐怖、血腥、狰狞、龇牙威慑、獠牙外露的血盆大口、伤口、血液；'
    '避免：手部畸变（无多指、无粘连、无指节反折）；'
    '避免：把西装改掉（禁止铠甲/长袍/披风/僧袍/任何古装）。')

# ---------------------------------------------------------------- 变体

VARIANTS = [
    {
        'name': 'A',
        'title': '云海法相·黄昏逆光',
        'extra': '时间设定为黄昏：金橙色的低角度逆光从画面右后方穿透云层，'
                 '为法相的鱼头轮廓镶上一圈金边；主色为青绿灵气与墨蓝云海。',
    },
    {
        'name': 'B',
        'title': '雷暴天威·翠绿强光',
        'extra': '时间设定为雷雨将至：更深的墨蓝天幕，青绿灵气光柱从法相体内冲天而起，'
                 '云层间有电弧游走，灵气以更浓烈的翠绿色为主，光尘与流光更密集；'
                 '整体压暗、对比更强，法相更具压迫感。',
    },
]


def build(v):
    return '\n\n'.join([
        IDENTITY_LOCK, STYLE_LOCK, COMPOSITION, v['extra'], REALITY, NEGATIVE,
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
        with open(os.path.join(OUT, '大嘴鱼_法天象地_变体%s_task.json' % v['name']), 'w', encoding='utf-8') as f:
            json.dump({'task_id': tid, 'variant': v['title'], 'prompt': prompt,
                       'refs': ['大嘴鱼 人物三视图（基础）.png（身份）',
                                'clipboard-2026-10-08T14-08-29-156Z-5616e4e2.jpg（画风/氛围）']},
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
        dst = os.path.join(OUT, '大嘴鱼_法天象地_%s.png' % t['v']['name'])
        with urllib.request.urlopen(urls[0], timeout=180) as r:
            blob = r.read()
        with open(dst, 'wb') as f:
            f.write(blob)
        print('    [%s] %.0fKB  %s' % (t['v']['name'], len(blob) / 1024, dst))

    ok = sum(1 for t in tasks if done.get(t['id'], {}).get('status') == 'done')
    print('\nSUMMARY ok=%d / total=%d' % (ok, len(tasks)))


if __name__ == '__main__':
    main()
