# -*- coding: utf-8 -*-
"""《心魔劫·慕沛灵》CH-02 慕沛灵·幻境暮年 —— 二级老化（80+ 岁病容）

母本 = 上一轮生成的 CH-02（约 70 岁）；本次在同源骨相上继续老化到 80+ 岁、加病容。
一次提交 2 个变体（A 常规加深 / B 病榻气若游丝），人工肉眼核验后择一。
规格 16:9 / 2k，输出 <项目>/assets/三视图/CH-02b_暮年加深_变体{A,B}.png
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
BASE = 'https://task-api-1-cn.65535.space'
MODEL = 'gpt-image-2.5-flare'

PROJ = r'D:/work/minimax_h3/心魔劫_穆沛灵'
OUT = os.path.join(PROJ, 'assets', '三视图')
SRC = os.path.join(OUT, 'CH-02_慕沛灵·幻境暮年_三视图.png')

LAYOUT = ('完整角色设定稿，纯白色背景，同画布分左右两列排版：第一列超精细面部特写（占 30% 宽度），'
          '第二列角色标准三视图（正面 / 侧面 / 背面）（占 70% 宽度）。'
          '画面中不出现任何文字、字母、数字、标注或水印（包括「正面 / 侧面 / 背面」等视角标签与角色名）。')

LOCK = ('严格保持参考图中同一女性的面部骨相、脸型轮廓、眼睛形状与瞳色（蓝色）、眉形、鼻型、唇形不变，'
        '让人一眼认得出这就是参考图里那位女性的老年版本，绝不能换成另一张脸'
        '（以参考图为唯一身份基准）。')

REALISM = ('这不是 3D 渲染，而是一位真实的真人演员：真实亚洲人皮肤质感，可见毛孔、细小绒毛、'
           '自然泛红与微小瑕疵，皮肤有真实的明暗过渡与柔和阴影；面部比例与骨相真实，不放大眼睛、'
           '不改脸型、不做磨皮美颜，保留眉/眼/脸颊/嘴部的左右轻微不对称；头发有飞散碎发、'
           '不均匀发束与轻微毛躁；身材与身体比例真实、符合真人解剖，手脚结构正确、十指清晰不粘连。'
           '参考图中的一切须按真人实拍重新演绎——皮肤是真实皮肤，衣料是真实衣料'
           '（可见织物纹理、褶皱与垂坠感）。')

NEGATIVE = ('避免：CGI、3D 渲染、游戏建模感、娃娃皮肤、瓷肌、塑料感、过度磨皮、美颜 App、'
            '眼睛过大、面部完全对称、睫毛过度锐化、油蜡感高光、极端背景虚化、过度 HDR、'
            '不真实的解剖比例；画面无任何文字、字母、字幕、水印、logo、视角标签；'
            '手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连）；'
            '不要年轻化、不要医美式紧致皮肤、不要浓妆遮皱。')

AGE_A = ('年龄演绎（在参考图基础上继续老化一档，推到八十岁以上）：'
         '头发几乎全白、稀疏，在脑后挽成低髻、鬓角散落细碎白发；'
         '额头与眼周皱纹更深更密，眼窝明显凹陷、上眼睑下垂、眼下有明显的老年眼袋与黑眼圈，'
         '法令纹深长、嘴角下垂，双颊凹陷、颧骨突出，脖子皮肤松弛下垂、颈纹深刻，'
         '手背青筋与骨节凸出、皮肤薄透。眼神温和但疲惫，是一位走到生命尽头的老人。')

AGE_B = ('年龄演绎（在参考图基础上继续老化一档，推到八十岁以上，且身处弥留之际）：'
         '头发几乎全白、稀疏凌乱，在脑后松散挽起、鬓角散落细碎白发；'
         '额头与眼周皱纹更深更密，眼窝明显凹陷、上眼睑下垂、眼下有深重眼袋与青黑眼圈，'
         '法令纹深长、双颊凹陷、面色苍白带一点灰败的蜡黄，唇色淡而干裂，'
         '脖子皮肤松弛下垂、颈纹深刻，手背青筋凸起、皮肤薄透如纸。'
         '神情极尽温柔却透着虚弱与倦怠，是弥留之际、气若游丝的模样。')

WARDROBE = ('服装：朴素家常粗布衣——米白色粗麻交领上衣，外罩靛蓝色素面粗布对襟褂子，'
            '深灰色粗布长裤，布鞋。衣料有真实的粗糙织物纹理、自然褶皱与旧化磨损感，'
            '衣料略宽松、自然垂坠。不要华丽刺绣、不要纱质、不要金饰，'
            '不要照抄任何仙侠短裙或宫装形制。')

IDENTITY = '一位八十多岁、气若游丝的暮年女性，气质温厚慈祥、饱经岁月。'

SCENE = ('场景：纯白色的摄影棚背景，柔和均匀的白光，无任何布景、道具与投影。\n'
         '人物全身直立自然站姿（可微微弓背、身体不似年轻人挺拔），'
         '正面、侧面、背面三个视角并排，另在左侧排一张面部特写；'
         '表情放松中性，不做夸张表情与摆拍动作。')

VARIANTS = [('A', AGE_A), ('B', AGE_B)]


def build(age):
    return '\n'.join([LAYOUT, '', LOCK, age, WARDROBE, IDENTITY, '', REALISM, '', SCENE, '', NEGATIVE])


def load_b64(path, max_side=1536):
    im = cv2.imdecode(np.fromfile(path, dtype='uint8'), cv2.IMREAD_COLOR)
    if im is None:
        raise RuntimeError('无法读取: ' + path)
    h, w = im.shape[:2]
    s = max_side / float(max(h, w))
    if s < 1.0:
        im = cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode('.jpg', im, [int(cv2.IMWRITE_JPEG_QUALITY), 86])
    return 'data:image/jpeg;base64,' + base64.b64encode(buf.tobytes()).decode('ascii')


def api(method, path, payload=None, timeout=180):
    data = json.dumps(payload, ensure_ascii=False).encode('utf-8') if payload is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + API)
    if data:
        req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))


def main():
    if not API:
        print('FATAL: S65535_API_KEY 未设置')
        return 1
    os.makedirs(OUT, exist_ok=True)
    uri = load_b64(SRC)

    tasks = []
    for tag, age in VARIANTS:
        dst = os.path.join(OUT, 'CH-02b_暮年加深_变体%s.png' % tag)
        if os.path.exists(dst):
            print('[变体%s] 已存在，跳过' % tag)
            continue
        prompt = build(age)
        payload = {'kind': 'image', 'model': MODEL,
                   'input': {'prompt': prompt, 'size': '16:9', 'resolution': '2k', 'n': 1, 'image': [uri]}}
        try:
            resp = api('POST', '/v1/tasks', payload)
        except urllib.error.HTTPError as e:
            print('[变体%s] 提交失败 HTTP %s: %s' % (tag, e.code, e.read().decode('utf-8', 'replace')[:400]))
            continue
        tid = resp.get('id') or resp.get('task_id')
        tasks.append({'tag': tag, 'task_id': tid, 'dst': dst, 'prompt': prompt})
        print('[变体%s] -> %s' % (tag, tid))
        time.sleep(1)

    if not tasks:
        print('无新任务提交。')
        return 0

    print('\n=== 轮询 ===')
    pending = {t['task_id']: t for t in tasks}
    done = {}
    for rnd in range(90):
        time.sleep(6)
        for tid in list(pending.keys()):
            try:
                st = api('GET', '/v1/tasks/' + str(tid), timeout=60)
            except Exception:
                continue
            s = st.get('status')
            if s in ('done', 'failed'):
                pending.pop(tid)
                done[tid] = st
                tg = [t['tag'] for t in tasks if t['task_id'] == tid][0]
                print('  [%02d] 变体%s %s' % (rnd, tg, s))
        if not pending:
            break
        print('  [%02d] 剩余 %d' % (rnd, len(pending)))
        sys.stdout.flush()

    print('\n=== 下载 ===')
    for t in tasks:
        st = done.get(t['task_id'])
        if not st or st.get('status') != 'done':
            print('  [变体%s] 跳过（%s）' % (t['tag'], (st or {}).get('status', 'no-result')))
            if st:
                print('      error:', json.dumps(st.get('error') or st, ensure_ascii=False)[:400])
            continue
        urls = st.get('result_urls') or []
        if not urls:
            print('  [变体%s] 无 result_urls' % t['tag'])
            continue
        with urllib.request.urlopen(urls[0], timeout=180) as r:
            blob = r.read()
        with open(t['dst'], 'wb') as f:
            f.write(blob)
        print('  [变体%s] %.0fKB  %s' % (t['tag'], len(blob) / 1024, t['dst']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
