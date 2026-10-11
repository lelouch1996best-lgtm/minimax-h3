# -*- coding: utf-8 -*-
"""《心魔劫·慕沛灵》角色三视图批量生成（65535 gpt-image-2.5-flare 图生图）

配方 = 项目已验证的「真人质感-基础」两列版式配方（tools/fr_real_views_batch.py）
  - 单参考图 = 该角色现有三视图
  - 提示词   = 版式 -> 身份锁定 -> 特征保护 -> 真人实拍演绎 -> 场景 -> 负面清单
  - 规格     = 16:9 / 2k / n=1

输出：<项目>/assets/三视图/<资产ID>_<名称>_三视图.png
断点续跑：已存在输出文件的任务自动跳过。

用法：
  python tools/xmj_gen_real_views.py --dry-run     # 只打印提示词，不提交
  python tools/xmj_gen_real_views.py               # 提交全部未完成任务
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

ROOT = r'D:/work/minimax_h3/assets/凡人/character'
PROJ = r'D:/work/minimax_h3/心魔劫_穆沛灵'
OUT = os.path.join(PROJ, 'assets', '三视图')

LAYOUT = ('完整角色设定稿，纯白色背景，同画布分左右两列排版：第一列超精细面部特写（占 30% 宽度），'
          '第二列角色标准三视图（正面 / 侧面 / 背面）（占 70% 宽度）。'
          '画面中不出现任何文字、字母、数字、标注或水印（包括「正面 / 侧面 / 背面」等视角标签与角色名）。')

REALISM = ('这不是 3D 渲染，而是一位真实的真人演员：真实亚洲人皮肤质感，可见毛孔、细小绒毛、'
           '自然泛红与微小瑕疵，皮肤有真实的明暗过渡与柔和阴影；面部比例与骨相真实，不放大眼睛、'
           '不改脸型、不做磨皮美颜，保留眉/眼/脸颊/嘴部的左右轻微不对称；头发有飞散碎发、'
           '不均匀发束与轻微毛躁，不是根根分明的发丝；身材与身体比例真实、符合真人解剖，'
           '手脚结构正确、十指清晰不粘连。'
           '参考图中的一切须按真人实拍重新演绎——皮肤是真实皮肤，衣料是真实衣料'
           '（可见织物纹理、褶皱与垂坠感），金属饰件有真实反光而不是塑料高光。')

NEGATIVE = ('避免：CGI、3D 渲染、游戏建模感、娃娃皮肤、瓷肌、塑料感、过度磨皮、美颜 App 瘦脸大眼、'
            '眼睛过大、面部完全对称、睫毛过度锐化、油蜡感高光、极端背景虚化、过度 HDR、'
            '不真实的解剖比例；画面无任何文字、字母、字幕、水印、logo、视角标签；'
            '手与手指的数量、关节、长度、交叠与握持合理（无多指、无粘连）；'
            '发饰与腰饰不重复不悬空、不穿模。')

# ---------------------------------------------------------------- 任务定义
JOBS = [
    {
        'id': 'CH-01',
        'name': '慕沛灵·真身',
        'role': '慕沛灵',
        'ref': '幕沛灵/人物三视图（红宫装）.png',
        'lock': ('严格保持参考图中同一女性的面部五官、脸型、瞳色、发型与发饰完全不变'
                 '（以参考图为唯一身份基准，不换人、不改五官与脸型）。'),
        'features': ('特征保护：黑发高盘发髻、金色花钿发簪与垂坠珍珠金流苏发饰、蓝色眼眸、'
                     '白皙肤色，均为核心辨识点，数量与位置不得增减或漂移。'),
        'wardrobe': ('服装：把参考图中的红色古风纱衣改为【落云宗修真洞府内室的正统大红嫁衣 / 喜服】——'
                     '正红色织金对襟大袖外袍，领口与袖口绣金色云纹与缠枝莲，内衬正红立领中衣，'
                     '红色锦缎腰封系金色丝绦，下衬正红长裙，裙摆绣金线祥云。'
                     '服装严整端庄、覆盖得体，是修真世家新娘的正式婚服；'
                     '不要露腰、不要高开衩露腿、不要纱质透视、不要泳装化设计，'
                     '不要照抄参考图里的仙侠短裙形制。'),
        'identity': '一位二十多岁的成年东方女性，气质高冷端庄、沉静美艳。',
    },
    {
        'id': 'CH-02',
        'name': '慕沛灵·幻境暮年',
        'role': '慕沛灵',
        'ref': '幕沛灵/人物三视图（真人质感-基础）.png',
        'lock': ('严格保持参考图中同一女性的面部骨相、脸型轮廓、眼睛形状与瞳色、眉形、鼻型、唇形不变，'
                 '让人一眼认得出这是同一个人的老年版本（以参考图为唯一身份基准，不换人）。'),
        'features': ('年龄演绎：在同一个人骨相基础上自然老化为七十多岁的暮年女性——'
                     '头发全白、在脑后挽成低髻、鬓角有散落碎发；面颊与眼角有真实皱纹，'
                     '皮肤松弛、有老年斑与手背静脉可见的真实衰老痕迹，眼神却温润慈祥。'
                     '不要靠浓妆遮盖皱纹，不要做医美式的年轻化处理。'),
        'wardrobe': ('服装：换成朴素的家常粗布衣——米白色粗麻交领上衣，外罩一件靛蓝色素面粗布对襟褂子，'
                     '深灰色粗布长裤，布鞋。衣料有真实的粗糙织物纹理、自然褶皱与旧化磨损感。'
                     '不要华丽刺绣、不要纱质、不要金饰，不要照抄参考图里的红色仙侠短裙。'),
        'identity': '一位七十多岁的暮年女性，气质温厚慈祥、饱经岁月。',
    },
    {
        'id': 'CH-04',
        'name': '韩立·基础古风（心魔母本）',
        'role': '韩立',
        'ref': '韩立/人物三视图（真人质感-基础）.png',
        'lock': ('严格保持参考图中同一男性的面部五官、脸型、眉形、眼神与发型完全不变'
                 '（以参考图为唯一身份基准，不换人、不改脸型与发型）。'),
        'features': ('特征保护：黑长发头顶束金木簪、刘海半遮眉、深棕窄凤眼、高鼻薄唇、'
                     '神情沉稳疏离面瘫，均为核心辨识点，不得增减。'),
        'wardrobe': ('服装：完整保留参考图中的深海蓝绣金长袍形制——深海蓝底色长袍、'
                     '金色云纹肩饰与肩甲、金色腰封、浅灰内衬、红色流苏腰饰、黑色长靴。'
                     '不要改成现代服装，不要改成喜袍或红金配色。'),
        # ⚠️ 2026-10-10 修正：原写「一位二十多岁的成年东方男性」与资产清单「心魔韩立·暮年（白发老翁）」
        #    直接矛盾，导致 CH-04 出图是青年态、镜 12A 里韩立不老。CH-04 的正解是「暮年版」，
        #    由 tools/xmj_ch04_age_up.py 以本脚本的青年三视图为身份基准做暮年化生成。
        #    本条目保留供「青年锚点」或其它项目使用；跑 CH-04 请改用 xmj_ch04_age_up.py。
        'identity': '一位二十多岁的成年东方男性，气质沉稳内敛、疏离寡言。（注意：《心魔劫》的 CH-04 需暮年版，见 xmj_ch04_age_up.py）',
    },
    {
        'id': 'CH-05',
        'name': '韩立·喜袍（闪回新郎）',
        'role': '韩立',
        'ref': '韩立/人物三视图（喜袍）.png',
        'lock': ('严格保持参考图中同一男性的面部五官、脸型、眉形、眼神与发型完全不变'
                 '（以参考图为唯一身份基准，不换人、不改脸型与发型）。'),
        'features': ('特征保护：黑发束簪、刘海半遮眉、深棕窄凤眼、高鼻薄唇、神情沉稳不苟言笑，'
                     '均为核心辨识点，不得增减。'),
        'wardrobe': ('服装：完整保留参考图中的玄色喜袍形制——黑丝绸底大红金线绣龙纹喜袍、'
                     '大红交领内衬、金色云纹肩饰、红色腰封、黑色婚靴。'
                     '不要改成蓝色常服，不要改成现代西装，不要去掉龙纹刺绣。'),
        'identity': '一位二十多岁的成年东方男性，气质沉稳庄重、面瘫寡言的新郎。',
    },
]


def build(job):
    lines = [
        LAYOUT, '',
        job['lock'], job['features'], job['wardrobe'], job['identity'], '',
        REALISM, '',
        '场景：纯白色的摄影棚背景，柔和均匀的白光，无任何布景、道具与投影。',
        '人物全身直立自然站姿，正面、侧面、背面三个视角并排，另在左侧排一张面部特写；'
        '表情放松中性，不做夸张表情与摆拍动作。', '',
        NEGATIVE,
    ]
    return '\n'.join(lines)


def load_b64(path, max_side=1536):
    im = cv2.imdecode(np.fromfile(path, dtype='uint8'), cv2.IMREAD_COLOR)
    if im is None:
        raise RuntimeError('无法读取图片: ' + path)
    h, w = im.shape[:2]
    s = max_side / float(max(h, w))
    if s < 1.0:
        im = cv2.resize(im, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode('.jpg', im, [int(cv2.IMWRITE_JPEG_QUALITY), 86])
    if not ok:
        raise RuntimeError('JPEG 编码失败: ' + path)
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
    ap.add_argument('--only', default='', help='只跑指定资产ID，逗号分隔，如 CH-01,CH-04')
    args = ap.parse_args()

    if not API:
        print('FATAL: S65535_API_KEY 未设置')
        return 1

    only = [x.strip() for x in args.only.split(',') if x.strip()]
    jobs = [j for j in JOBS if (not only or j['id'] in only)]

    if args.dry_run:
        for j in jobs:
            print('=' * 78)
            print('%s  %s   ref=%s' % (j['id'], j['name'], j['ref']))
            print('=' * 78)
            print(build(j))
            print()
        return 0

    os.makedirs(OUT, exist_ok=True)
    submitted = []

    for j in jobs:
        dst = os.path.join(OUT, '%s_%s_三视图.png' % (j['id'], j['name']))
        if os.path.exists(dst):
            print('[%s] 已存在，跳过：%s' % (j['id'], dst))
            continue
        ref_path = os.path.join(ROOT, j['ref'])
        try:
            uri = load_b64(ref_path)
        except Exception as e:
            print('[%s] 参考图编码失败：%s' % (j['id'], e))
            continue
        prompt = build(j)
        payload = {
            'kind': 'image', 'model': MODEL,
            'input': {'prompt': prompt, 'size': '16:9', 'resolution': '2k', 'n': 1, 'image': [uri]},
        }
        try:
            resp = api('POST', '/v1/tasks', payload)
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', 'replace')[:500]
            print('[%s] 提交失败 HTTP %s: %s' % (j['id'], e.code, body))
            continue
        tid = resp.get('id') or resp.get('task_id')
        submitted.append({'id': j['id'], 'name': j['name'], 'task_id': tid, 'dst': dst,
                          'prompt': prompt, 'ref': j['ref']})
        print('[%s] %-24s -> %s' % (j['id'], j['name'], tid))
        time.sleep(1)

    if not submitted:
        print('无新任务提交（可能已全部存在）。')
        return 0

    with open(os.path.join(OUT, '_state.json'), 'w', encoding='utf-8') as f:
        json.dump(submitted, f, ensure_ascii=False, indent=2)

    print('\n=== 轮询（每 6s，最多 90 轮）===')
    pending = {t['task_id']: t for t in submitted}
    done = {}
    for rnd in range(90):
        time.sleep(6)
        for tid in list(pending.keys()):
            try:
                st = api('GET', '/v1/tasks/' + str(tid), timeout=60)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print('  poll 404', tid)
                continue
            except Exception:
                continue
            s = st.get('status')
            if s in ('done', 'failed'):
                pending.pop(tid)
                done[tid] = st
                print('  [%02d] %-8s %s' % (rnd, pending.get(tid, {}).get('id', tid), s))
        print('  [%02d] 剩余 %d' % (rnd, len(pending)))
        sys.stdout.flush()
        if not pending:
            break

    print('\n=== 下载 ===')
    ok = 0
    for t in submitted:
        st = done.get(t['task_id'])
        if not st or st.get('status') != 'done':
            print('  [%s] 跳过（%s）' % (t['id'], (st or {}).get('status', 'no-result')))
            if st:
                print('      error:', json.dumps(st.get('error') or st, ensure_ascii=False)[:400])
            continue
        urls = st.get('result_urls') or []
        if not urls:
            print('  [%s] 无 result_urls：%s' % (t['id'], json.dumps(st, ensure_ascii=False)[:300]))
            continue
        with urllib.request.urlopen(urls[0], timeout=180) as r:
            blob = r.read()
        with open(t['dst'], 'wb') as f:
            f.write(blob)
        ok += 1
        print('  [%s] %.0fKB  %s' % (t['id'], len(blob) / 1024, t['dst']))

    print('\nSUMMARY ok=%d / total=%d' % (ok, len(submitted)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
