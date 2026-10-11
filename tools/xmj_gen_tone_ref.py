# -*- coding: utf-8 -*-
"""《心魔劫·慕沛灵》全片基调基准图（Tone Reference Key Visual）

用途：产出「中国电影感古风」定调基准图，作为下一步 MJ sref 的**风格源**，
      为全片所有镜头锁定 色调 / 光感 / 质感风格。

内容：镜 15 —— 落云宗洞府石室，红衣女子（慕沛灵真身）盘膝端坐蒲团。
参考图（双参考图分工）：
  第 1 张 = SC-05 石室场景（定空间、冷青灯位）
  第 2 张 = CH-01 慕沛灵红嫁衣（定人物身份与红衣形制）

规格：16:9 / 2k。出 2 变体（A 写实电影感 / B 更重水墨意境），人工核验后择一定调。
输出：<项目>/assets/基调/TONE-01_全片基调基准图_变体{X}.png
"""
import argparse
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
OUT = os.path.join(PROJ, 'assets', '基调')
REF_SCENE = os.path.join(PROJ, 'assets', '场景', 'SC-05_落云宗洞府石室.png')
REF_CHAR = os.path.join(PROJ, 'assets', '三视图', 'CH-01_慕沛灵·真身_三视图.png')

# ---------------------------------------------------------------- 共享段
# 中国电影感的定义：这是全片基调的灵魂，写得具体而克制
CINEMATIC = (
    '【影像基调 · 中国电影感古风】整体呈现当代中国电影摄影的写实质感，不是电视剧、不是游戏CG、不是动漫：\n'
    '· 色彩：低饱和、低对比的"高级灰"基底，全局统一青蓝色调（teal-blue）与冷灰，'
    '只在夜明珠光晕与红衣上保留极克制的暖色点缀，形成冷暖微差；色彩克制内敛，不要鲜艳、不要高饱和；\n'
    '· 光影：单一光源、大光比、深阴影，光从侧后方斜切进来（伦勃朗式侧逆光），'
    '人物半边脸沉入暗部；光线有明确的体积感，空气中有细微的雾霭与尘埃；\n'
    '· 质感：真实物理材质——岩石的颗粒与凿痕、丝绸的厚重光泽与自然褶皱、皮肤的细腻毛孔；'
    '拒绝一切塑料感与磨皮感；\n'
    '· 影调：暗部不死黑、保留细节（lifted blacks），高光柔和不溢出，'
    '整体偏暗、偏闷、有呼吸感的低照度影调；\n'
    '· 镜头：电影级大画幅摄影质感，轻微胶片颗粒与柔和微反差，浅景深但背景仍可读，'
    '像用大画幅镜头在真实空间里拍下的一格画面。'
)

COMPOSE = (
    '构图：中景偏全景的稳定构图，人物位于画面中下部偏左，盘膝端坐于石室中央的圆形草编蒲团上，'
    '画面右侧与上方留出大面积的石壁与黑暗空间，形成"人在巨大空旷空间中显得渺小孤寂"的压迫感；'
    '机位平视略微俯视，摄影机静止不动。'
)

SUBJECT = (
    '人物：一位中国古典美的青年女性，盘膝端坐、双目紧闭、脊背挺直，双手结印轻放膝上。'
    '严格保持第 2 张参考图中该女性的面部五官、脸型、发型与发饰完全一致'
    '（黑发高盘髻、金色花钿发簪、垂坠珍珠金流苏发饰、白皙肤色）；'
    '身着正红色织金大袖嫁衣（形制同第 2 张参考图：立领中衣、红锦缎腰封、正红长裙绣金线祥云），'
    '红衣在冷调环境中是画面唯一的暖色重音。面容苍白、眉心微蹙，'
    '神情是隐忍的痛苦与决绝，像正在承受心魔劫的煎熬。'
    '画面中只有这一个人物。'
)

NEG = (
    '避免：现代物品与服装、游戏CG感、3D国漫渲染感、二次元动漫感、电视剧感、'
    '高饱和色彩、艳俗配色、过度HDR、塑料皮肤、磨皮美颜、过曝溢出的高光、'
    '死黑无细节的暗部、廉价特效光效、光斑眩光泛滥、'
    '文字、字幕、水印、logo、牌匾、书法题字、'
    '多个人物、多余的手、畸形手指、'
    '鱼眼畸变、构图歪斜。'
)

VARS = {
    'A': (
        '【本变体侧重】写实电影质感优先：强调真实岩石与丝绸的物理材质、'
        '真实光影的衰减与体积感、夜明珠青白光的柔和过渡；'
        '像《刺客聂隐娘》《影》那一类当代中国电影摄影的实拍质感——沉静、克制、有物质重量。'
    ),
    'B': (
        '【本变体侧重】水墨意境优先：在写实基础上加强"留白"与"虚实相生"的东方美学——'
        '石壁暗部大面积沉入幽深的墨蓝，雾气更浓，光线更像一束舞台追光；'
        '整体更空、更静、更写意，像一幅被摄影机拍活的水墨画。'
    ),
}


def build(tag):
    return '\n\n'.join([CINEMATIC, COMPOSE, SUBJECT, VARS[tag],
                        '比例：16:9 横屏，2K 分辨率。', NEG])


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
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--var', default='', help='A,B')
    args = ap.parse_args()

    vfilter = [x.strip() for x in args.var.split(',') if x.strip()]

    if args.dry_run:
        for tag in VARS:
            if vfilter and tag not in vfilter:
                continue
            print('=' * 78)
            print('TONE-01 全片基调基准图 变体%s' % tag)
            print('=' * 78)
            print(build(tag))
            print()
        return 0

    if not API:
        print('FATAL: S65535_API_KEY 未设置')
        return 1
    os.makedirs(OUT, exist_ok=True)

    scene_uri = load_b64(REF_SCENE)
    char_uri = load_b64(REF_CHAR)

    tasks = []
    for tag in VARS:
        if vfilter and tag not in vfilter:
            continue
        dst = os.path.join(OUT, 'TONE-01_全片基调基准图_变体%s.png' % tag)
        if os.path.exists(dst):
            print('[变体%s] 已存在，跳过' % tag)
            continue
        prompt = build(tag)
        payload = {'kind': 'image', 'model': MODEL,
                   'input': {'prompt': prompt, 'size': '16:9', 'resolution': '2k', 'n': 1,
                             'image': [scene_uri, char_uri]}}
        try:
            resp = api('POST', '/v1/tasks', payload)
        except urllib.error.HTTPError as e:
            print('[变体%s] 提交失败 HTTP %s: %s' % (tag, e.code,
                                                     e.read().decode('utf-8', 'replace')[:500]))
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
                tg = [x['tag'] for x in tasks if x['task_id'] == tid][0]
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
                print('      error:', json.dumps(st.get('error') or st, ensure_ascii=False)[:500])
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
