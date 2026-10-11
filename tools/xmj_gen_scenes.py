# -*- coding: utf-8 -*-
"""《心魔劫·慕沛灵》B 类场景生成（65535 gpt-image-2.5-flare 文生图 · 无母本）

资源包 assets/凡人/scene/ 只有现代场景，古风空镜为零 -> 纯文生图（不传参考图）。
出 2 个场景 × 各 2 变体（A/B），人工核验后择一。

SC-03 幻境·内室卧榻（日内·暖黄昏暗·窗棂侧光）  -> 镜 8-14
SC-05 落云宗·慕沛灵洞府石室（夜内·冷青幽蓝·夜明珠微光）-> 镜 15-23

规格：16:9 / 2k。输出 <项目>/assets/场景/{ID}_{名}_变体{X}.png
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

API = os.environ.get('S65535_API_KEY')
BASE = 'https://task-api-1-cn.65535.space'
MODEL = 'gpt-image-2.5-flare'

PROJ = r'D:/work/minimax_h3/心魔劫_穆沛灵'
OUT = os.path.join(PROJ, 'assets', '场景')

# ---------------------------------------------------------------- 通用段
COMMON_NEG = ('避免：现代物品穿帮（电线、插座、空调、塑料、玻璃幕墙、牛仔裤、运动鞋）、'
              '人物、人手、动物、文字、字母、汉字、书法题字、牌匾、字幕、水印、logo、'
              'CGI 塑料感、过度 HDR、过饱和、廉价游戏渲染、鱼眼畸变、画面结构错乱。')

# 古装正片统一画风：电影感实拍，非 3D 国漫
STYLE = ('画风：电影级实拍质感，中国古代（修仙世界）场景，非 3D 国漫、非游戏场景渲染；'
         '真实材质与自然光照——木料有真实木纹与包浆、石面有真实凿痕与风化、织物有真实织物纹理与褶皱；'
         '构图端正、透视正常，像真实存在的空间被摄影机拍下来。')

# ---------------------------------------------------------------- 场景定义
JOBS = [
    {
        'id': 'SC-01',
        'name': '幻境山间小院',
        'vars': {
            'A': (
                '中国古代（修仙世界）深山中的一处简朴农家小院，清晨时分。'
                '一座低矮的茅草屋舍占据画面右后方，茅檐低垂、草茎参差，屋檐下是夯土墙面与原木立柱；'
                '院中地面铺着大小不一的青石板，石缝间生着青苔与细草，被晨露打湿而微微反光；'
                '院墙一角立着一棵枝干虬结的老树，树皮皲裂、枝叶稀疏，树下放着一只石凳；'
                '院门是一道半开的木栅栏，门外一条石阶小路向下延伸，远处层叠的青山隐没在晨雾中。'
                '屋顶烟囱升起一线极淡的炊烟，笔直地向上升起、在高处散开；'
                '整个院子被薄薄的晨雾笼罩，雾中可见远处山影与几株疏树，层层退去、由浓到淡。'
                '光线来自画面前方偏左侧的清晨低角度暖阳，斜切进院子，在青石板与茅檐上拉出长而柔的影子，'
                '空气中有大量悬浮的细小尘埃与水汽颗粒在光中缓慢浮动。'
                '基调：暖金橙主调（约 3000K 感），米白、驼褐、旧木黄层层过渡，暖色通铺全画面但饱和度克制，'
                '暗部含低饱和暖褐而非纯黑；高调偏亮的暖柔影调，高光柔和带轻微过曝的梦幻感；'
                '真实物理材质（茅草的干枯草茎、青石的凿痕与湿润反光、木料的真实木纹与包浆、夯土墙的颗粒与细裂纹）；'
                '电影级大画幅摄影质感，轻微胶片颗粒，浅景深但背景可读，像蒙了一层薄雾的柔焦。'
                '院子空无一人，是一个真实存在的空间被摄影机拍下来；温柔、眷恋、不真实得像一场梦。'
            ),
            'B': (
                '中国古代（修仙世界）深山中的农家小院，站在院子中央向外望去，清晨。'
                '画面左侧是茅草屋的侧墙与一扇木质格栅窗，茅檐低垂，墙面是细腻的夯土质地；'
                '右侧是斑驳的土院墙，墙头覆着枯草，墙根有一条石砌的排水浅沟；'
                '院子中央铺着旧青石，一块石磨盘与一只木桶静置在角落，陈设极简、别无他物；'
                '院中一棵老树从画面右侧伸入，粗壮的枝干斜跨画面上缘，树下落着一层枯叶；'
                '正前方是敞开的院门，门外可见层叠远山与一条蜿蜒的石阶小路，通向雾中的山谷。'
                '一缕炊烟自画面左上的屋后升起，在高处被风吹散成一团淡影；'
                '晨雾贴地流动，从院门外涌进来，在青石板上铺开一层薄薄的白气。'
                '光线是清晨的低角度暖阳，从院门外斜照进来，逆光下青石板边缘泛着柔和的金边，'
                '雾气与尘埃被逆光穿透，形成朦胧的光晕与体积光。'
                '基调：暖金橙主调（约 3000K 感），米白、驼褐、旧木黄层层过渡，暖色通铺全画面但饱和度克制；'
                '高调偏亮的暖柔影调，高光柔和不割裂、带轻微过曝的梦幻感，暗部偏暖并保留细节；'
                '真实物理材质（茅草的干枯草茎、青石的凿痕与苔痕、木料的木纹包浆、夯土与旧木的颗粒）；'
                '电影级大画幅摄影质感，轻微胶片颗粒与柔和微反差，画面像蒙了一层薄雾般的柔焦。'
                '院中空无一人，远处山影层层退去、由浓到淡；温柔、克制，像回忆里的画面。'
            ),
        },
    },
    {
        'id': 'SC-03',
        'name': '幻境内室卧榻',
        'vars': {
            'A': (
                '中国古代（修仙世界）的简朴内室，一间供人静养的素雅卧房。'
                '空间中央是一张木质素色床榻，榻上铺着米白色粗布被褥、叠放两只素面布枕，'
                '床榻一侧垂下半旧的素色布帐，帐幔自然垂落有褶皱。'
                '墙面为夯土与木构，一侧是一扇木质格栅窗棂（细木条交错成规整的方格），'
                '窗外透进午后斜射的暖黄色阳光，光柱穿过窗格在地面与床榻上投下清晰的窗棂影子；'
                '窗边木几上放着一只粗陶茶碗与一盏将熄未熄的油灯。'
                '地面是打磨过的旧木地板，房间陈设极简，只有床榻、木几、一只矮凳与墙上挂着的一件粗布外衣。'
                '基调：暖黄、昏暗、柔焦，午后逆光带轻微过曝，空气中悬浮着细小的尘埃颗粒，'
                '整体温柔、眷恋、不真实得像一场梦。'
            ),
            'B': (
                '中国古代（修仙世界）的简朴内室卧房，视线略微俯视看向一张木质素色床榻。'
                '床榻占据画面中下部，米白色粗布被褥揉出自然的褶皱与凹陷，一只素面布枕歪斜，'
                '床榻边缘垂着半旧的素色布帐。'
                '房间左侧是一扇木质竖条格栅长窗，暖黄色天光从窗外斜洒进来，'
                '在水磨石地面与被褥上拉出长长的光带与窗格阴影；'
                '木质房梁与横梁在画面上缘可见，土墙上有细微的裂纹与旧痕；'
                '榻边木几上一只粗陶碗、一盏铜油灯，火苗将熄。'
                '基调：暖黄偏橙、光线昏暗柔和、柔和过曝，空气中有细尘，'
                '情绪沉静、温暖而带一丝离别感，像回忆里的房间。'
            ),
        },
    },
    {
        'id': 'SC-05',
        'name': '落云宗洞府石室',
        'vars': {
            'A': (
                '中国古代（修仙世界）深山宗门修士的洞府内室——一座幽深开阔的天然石室。'
                '四壁是粗糙的天然岩石与人工凿刻的平整石面，可见清晰的凿痕与风化纹理；'
                '石壁内凹的壁龛中嵌着数颗**拳头大的夜明珠**，散出清冷的青白色微光，是室内唯一光源；'
                '光线自上而下、自壁龛向外扩散，在石壁上形成冷青与幽蓝的层次与浓重阴影，'
                '石室中央地面平整，放着一只圆形草编蒲团，蒲团上空无一人。'
                '空间高远空旷，画面上缘可见石室顶部隐入黑暗；'
                '石壁上有修真宗门风格的简单阴刻云纹线条（纯几何纹样，**不得出现任何汉字、经文或题字**）。'
                '基调：冷青、幽蓝、低照度、干燥冷硬，幽深压抑，静得能听见自己的呼吸。'
            ),
            'B': (
                '中国古代（修仙世界）修士的闭关洞府石室，幽深而空旷。'
                '空间由粗粝的天然岩壁围合，地面是一整块打磨过的青灰石板，光洁、冰冷、有细密纹路；'
                '四壁高处嵌着若干颗散发**青白色冷光**的夜明珠，光晕柔和但照度很低，'
                '珠光所及之处石壁呈冷青，未及之处沉入深幽蓝黑，形成强烈明暗对比；'
                '室内陈设极简：正中一块方形青石台面，其上放着一只圆形草编蒲团，别无他物；'
                '画面深处有一道通向外部的窄石门洞，门洞里透不进光，只见一片更深的黑；'
                '石壁表面有自然的矿物纹理与淡淡的反光。'
                '基调：极冷、极静、幽蓝，孤独、死亡即将降临般的澄澈与空寂。'
            ),
        },
    },
]


def build(job_id, body):
    return '\n'.join([body, '', STYLE, '', '比例：16:9 横屏，2K 分辨率。', '', COMMON_NEG])


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
    ap.add_argument('--only', default='', help='SC-03,SC-05')
    ap.add_argument('--var', default='', help='A,B')
    args = ap.parse_args()

    only = [x.strip() for x in args.only.split(',') if x.strip()]
    vfilter = [x.strip() for x in args.var.split(',') if x.strip()]

    if args.dry_run:
        for j in JOBS:
            if only and j['id'] not in only:
                continue
            for tag, body in j['vars'].items():
                if vfilter and tag not in vfilter:
                    continue
                print('=' * 78)
                print('%s %s 变体%s' % (j['id'], j['name'], tag))
                print('=' * 78)
                print(build(j['id'], body))
                print()
        return 0

    if not API:
        print('FATAL: S65535_API_KEY 未设置')
        return 1
    os.makedirs(OUT, exist_ok=True)

    tasks = []
    for j in JOBS:
        if only and j['id'] not in only:
            continue
        for tag, body in j['vars'].items():
            if vfilter and tag not in vfilter:
                continue
            dst = os.path.join(OUT, '%s_%s_变体%s.png' % (j['id'], j['name'], tag))
            if os.path.exists(dst):
                print('[%s-%s] 已存在，跳过' % (j['id'], tag))
                continue
            payload = {'kind': 'image', 'model': MODEL,
                       'input': {'prompt': build(j['id'], body), 'size': '16:9', 'resolution': '2k', 'n': 1}}
            try:
                resp = api('POST', '/v1/tasks', payload)
            except urllib.error.HTTPError as e:
                print('[%s-%s] 提交失败 HTTP %s: %s' % (j['id'], tag, e.code,
                                                        e.read().decode('utf-8', 'replace')[:400]))
                continue
            tid = resp.get('id') or resp.get('task_id')
            tasks.append({'id': j['id'], 'tag': tag, 'task_id': tid, 'dst': dst})
            print('[%s-%s] -> %s' % (j['id'], tag, tid))
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
                t = [x for x in tasks if x['task_id'] == tid][0]
                print('  [%02d] %s-%s %s' % (rnd, t['id'], t['tag'], s))
        if not pending:
            break
        print('  [%02d] 剩余 %d' % (rnd, len(pending)))
        sys.stdout.flush()

    print('\n=== 下载 ===')
    for t in tasks:
        st = done.get(t['task_id'])
        if not st or st.get('status') != 'done':
            print('  [%s-%s] 跳过（%s）' % (t['id'], t['tag'], (st or {}).get('status', 'no-result')))
            if st:
                print('      error:', json.dumps(st.get('error') or st, ensure_ascii=False)[:400])
            continue
        urls = st.get('result_urls') or []
        if not urls:
            print('  [%s-%s] 无 result_urls' % (t['id'], t['tag']))
            continue
        with urllib.request.urlopen(urls[0], timeout=180) as r:
            blob = r.read()
        with open(t['dst'], 'wb') as f:
            f.write(blob)
        print('  [%s-%s] %.0fKB  %s' % (t['id'], t['tag'], len(blob) / 1024, t['dst']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
