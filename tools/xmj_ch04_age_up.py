# -*- coding: utf-8 -*-
"""《心魔劫·慕沛灵》CH-04 心魔韩立·暮年 —— 白发老翁三视图

问题：原 CH-04 用青年母本（人物三视图（真人质感-基础））+ identity 误写"二十多岁"，
      导致 H3 出片里韩立完全不老（镜 12A 实测：像 30 岁，白发都不明显）。
本脚本：以同一青年韩立母本为身份基准，做"暮年化"演绎，一次出 2 个变体供人工择一。
  · 变体 A：花白硬朗（约 65 岁）—— 幻境里陪慕沛灵过完一生的丈夫，比她略年轻
  · 变体 B：白发苍老（约 75 岁）—— 备选，若需要更强的"岁月流逝"感
规格 16:9 / 2k，输出 <项目>/assets/三视图/CH-04_暮年版_变体{A,B}.png
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
SRC = r'D:/work/minimax_h3/assets/凡人/character/韩立/人物三视图（真人质感-基础）.png'

LAYOUT = ('完整角色设定稿，纯白色背景，同画布分左右两列排版：第一列超精细面部特写（占 30% 宽度），'
          '第二列角色标准三视图（正面 / 侧面 / 背面）（占 70% 宽度）。'
          '画面中不出现任何文字、字母、数字、标注或水印（包括「正面 / 侧面 / 背面」等视角标签与角色名）。')

LOCK = ('严格保持参考图中同一男性的面部骨相、脸型轮廓、眉形、眼型与瞳色、鼻型、唇形不变，'
        '让人一眼认得出这就是参考图里那位男性的老年版本，绝不能换成另一张脸'
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
            '不要年轻化、不要青壮年感、不要医美式紧致皮肤、不要浓妆遮皱、不要染黑发。')

AGE_A = ('年龄演绎（在参考图基础上老去约四十年，推到六十余岁）：'
         '头发与鬓角大面积花白、发丝由黑转灰白，发量略减但仍束在头顶以金木簪固定、'
         '刘海仍半遮眉但已花白；额头有横向皱纹，眼角鱼尾纹明显，眼下有轻微眼袋，'
         '法令纹加深，下颌线条略松弛，脖子有颈纹；'
         '皮肤尚紧实但已有真实的岁月痕迹与少量老年斑。'
         '眼神依旧沉稳疏离，但比年轻时多了温厚与疲惫，是走过大半生、陪在妻子身边的模样。')

AGE_B = ('年龄演绎（在参考图基础上老去约五十年，推到七十余岁）：'
         '头发几乎全白、稀疏，在头顶以金木簪挽成低髻、鬓角散落细碎白发；'
         '额头与眼周皱纹深密，眼窝凹陷、上眼睑略下垂、眼下有明显老年眼袋，'
         '法令纹深长、双颊略凹、颧骨突出，脖子皮肤松弛下垂、颈纹深刻，'
         '手背青筋与骨节凸出、皮肤薄透。眼神苍老而温厚，是一位暮年老者。')

WARDROBE = ('服装：完整保留参考图中的深海蓝绣金长袍形制——深海蓝底色长袍、'
            '金色云纹肩饰与肩甲、金色腰封、浅灰内衬、红色流苏腰饰、黑色长靴。'
            '衣料有真实的织物纹理、自然褶皱与轻微旧化感。'
            '不要改成现代服装，不要改成喜袍或红金配色，不要改成粗布家常衣。')

IDENTITY_A = '一位六十多岁、须发花白的暮年男性，气质沉稳内敛、温厚疏离。'
IDENTITY_B = '一位七十多岁、白发苍苍的暮年男性，气质沉稳内敛、苍老而温厚。'

SCENE = ('场景：纯白色的摄影棚背景，柔和均匀的白光，无任何布景、道具与投影。\n'
         '人物全身直立自然站姿（可微微弓背、身体不似年轻人挺拔），'
         '正面、侧面、背面三个视角并排，另在左侧排一张面部特写；'
         '表情放松中性，不做夸张表情与摆拍动作。')

VARIANTS = [('A', AGE_A, IDENTITY_A), ('B', AGE_B, IDENTITY_B)]


def build(age, identity):
    return '\n'.join([LAYOUT, '', LOCK, age, WARDROBE, identity, '', REALISM, '', SCENE, '', NEGATIVE])


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
    if not os.path.exists(SRC):
        print('FATAL: 母本不存在 ' + SRC)
        return 1
    uri = load_b64(SRC)

    tasks = []
    for tag, age, identity in VARIANTS:
        dst = os.path.join(OUT, 'CH-04_暮年版_变体%s.png' % tag)
        if os.path.exists(dst):
            print('[变体%s] 已存在，跳过' % tag)
            continue
        prompt = build(age, identity)
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
