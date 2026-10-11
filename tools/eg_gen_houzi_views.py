# -*- coding: utf-8 -*-
"""恶搞素材包 · 猴头（穿西装妖怪）三视图生成（65535 gpt-image-2 图生图）

与《大嘴鱼》同系列的「西装妖怪」角色，配方沿用单参考图路线：
  参考图 = 凡人包 韩立《人物三视图（真人质感-基础）.png》
           仅锁定「左列超精细特写 + 右列正/侧/背三视图」两列版式、
           纯白摄影棚背景、写实电影级生物渲染质感与柔和布光；
           严禁沿用其人脸 / 长发 / 古装 / 仙侠元素。

五官神态：来自用户提供的参考脸（76x75 低分辨率小图，**不做图生图输入**，
避免糊脸 + 避免生成真人肖像），改为把观察到的五官特征逐条文字锁定：
  圆扁脸、小而细长的单眼皮眼、宽厚外翻的嘴唇、露整排牙的憨厚傻笑。

输出：generated-images/猴头_真人质感_三视图基础_{变体}.png
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

# 版式 / 画风基准图（与凡人包、大嘴鱼同配方）
STYLE_REF = r'D:/work/minimax_h3/assets/凡人/character/韩立/人物三视图（真人质感-基础）.png'

# ---------------------------------------------------------------- 提示词模块

LAYOUT = ('完整角色设定稿，纯白色背景，同画布分左右两列排版：第一列超精细头部特写（占30%宽度），'
          '第二列角色标准三视图（正面 / 侧面 / 背面）（占70%宽度）。'
          '画面中不出现任何文字、字母、数字、标注或水印（包括「正面 / 侧面 / 背面」等视角标签与角色名）。')

STYLE_LOCK = (
    '参考图仅用于确定以下三点，其余一切与它无关，**不要沿用参考图人物的长相、发型、服装、'
    '配饰与任何古装仙侠元素**：'
    '① 两列排版（左列特写 + 右列三视图）；② 纯白摄影棚背景与柔和均匀白光；'
    '③ 写实电影级生物特效渲染质感（photorealistic creature feature），材质有真实次表面散射与湿润反光。')

# 五官神态：参考用户给的低分辨率参考脸，逐条文字锁定（这是本角色最强辨识点）
FACE = (
    '**五官神态（最重要，务必精确照做）**：这是一张憨厚圆钝、毫无攻击性的猴脸，'
    '脸型是横向偏宽的圆扁脸，颧骨与下颌都圆滑饱满、没有尖角，下巴圆钝略前突，面颊带厚实的肉感；'
    '眼睛小而细长、单眼皮、眼型狭长微眯，眼尾自然下垂，眼距偏宽，瞳色深棕近黑，眼白干净、眼神憨钝温和；'
    '眉毛稀疏细短、颜色与毛色一致，几乎被毛流盖住；'
    '鼻子是扁平鼻梁配一个圆钝的鼻头、鼻翼厚实，鼻孔小且朝下，几乎看不到鼻孔；'
    '嘴唇是本角色的第二辨识点——上唇薄、下唇厚且饱满外翻，唇色偏淡、唇线清晰，嘴角天然上扬；'
    '此刻正咧开一个憨厚到极点的傻笑，**上排与下排整整齐齐的人形牙齿全部露出**（不是獠牙、不是尖牙），'
    '门齿略宽，嘴角两侧有明显的笑纹与法令纹；'
    '上唇与下巴处有一层稀疏可见的短胡茬感，与毛色相同。')

CORE = (
    '角色是一只拟人化直立行走的猴子头妖怪，是一条「穿西装的猴头」：'
    '头部为一只与身体不成比例的猴头，占整体身高的约三分之一，是全身最强辨识点——'
    '**脸部是裸露的粉褐色皮肤（无毛），皮肤质感细腻、有毛孔级细节与真实次表面散射、油脂反光**；'
    '毛发只长在头部轮廓一圈：浓密的深棕近黑色短毛覆盖头顶、后脑与两侧鬓角，'
    '毛流自然向后伏贴、发丝根根分明、边缘有细碎飞毛；'
    '鬓角的毛发向前收窄，与裸露皮肤的交界线自然柔和、不是一条生硬的边界；'
    '下巴与下颌轮廓也是一圈短毛，其余面部全裸；'
    '耳朵是人类的圆耳但略大、位置偏侧向外，边缘有一圈短毛；'
    + FACE +
    '身体其余部分被完全包裹在人类西装里，从颈部以下看不到任何猴类特征——'
    '**身材明显纤瘦高挑：身高约九头身，肩窄、腰线收窄、四肢修长而偏细，'
    '手臂与腿都是细长条而不是短粗，整体像一根被拉长的竹竿，明显不是壮实敦厚的身形；'
    '西装因此是明显的修身窄版，肩线利落、袖子偏长、袖口露出一截细手腕、裤管笔直修长；**'
    '双手为正常的五指人类手掌（猴化程度极低，指甲干净短圆），双腿修长，站姿微微内八。')

REALITY = (
    '写实电影质感：这必须是高预算生物特效电影里的**真实存在的一只活物**，被真实摄影机拍到，'
    '而不是卡通、动漫、玩具或游戏建模。'
    '毛发有真实的逐根发丝与二级绒毛层次、真实的方向性与重力垂坠，'
    '毛根处皮肤与毛之间有真实的过渡与阴影；'
    '裸露面部皮肤有真实的毛孔、细纹、油脂反光与明暗过渡，颧骨与鼻梁高光自然；'
    '眼球湿润、角膜有真实高光与细微血丝；'
    '西装为真实布料——精纺羊毛有可见织物纹理、褶裥与垂坠感，'
    '金属纽扣与领带夹有真实金属反光而不是塑料高光；'
    '手与手指的数量、关节、长度与握持合理（有五指、无多指粘连）。'
    '面部比例、头身比与身体解剖真实可信（头虽大但符合「卡通化写实」的自然比例，不崩坏、不畸变）。'
    '**身高与比例：整体高挑、九头身以上，头相对身体偏小，重心高、双腿占身高一半以上，形似长腿的衣架子。**')

SCENE = (
    '场景：纯白色摄影棚背景，柔和均匀的白光，无任何布景、道具与投影。'
    '角色全身直立自然站姿、正面侧面背面三个视角并排，另在左侧排一张头部特写；'
    '双手自然垂放或一只插进西装裤袋，咧着嘴笑，表情放松，不做夸张动作与摆拍姿势。')

NEGATIVE = (
    '避免：卡通、动漫、漫画、赛璐璐平涂、线稿描边、Q 版、夸张大眼、圆大眼、狐狸眼、'
    '表情包画风、3D 游戏低模、塑料模型感、玩具感、搪胶手办感、廉价 CG、赛璐璐质感；'
    '恐怖、血腥、狰狞、龇牙威慑、獠牙、尖牙、伤口、血液、内脏、腐烂、死亡、发光的眼睛；'
    '**避免真实人类面孔**（不要生成照片里的人脸、不要写实真人皮肤质感的人类五官），'
    '这张脸必须明确是猴脸而不是人脸；'
    '避免尖耳朵、狐狸口鼻、兽化鼻孔、整张脸被毛覆盖、猴子全身长毛、爪子、长指、猴尾；'
    '**避免矮胖敦实的身形**：不要矮个子、不要圆胖肚子、不要粗壮四肢、不要短腿短手臂、不要壮汉体型、不要臃肿西装，'
    '身体必须纤瘦高挑、四肢修长；'
    '影棚大片打光、商业时尚大片、油蜡感高光、过度 HDR、极端背景虚化；'
    '画面中不出现任何文字、字幕、水印、logo、视角标签、角色姓名；'
    '不出现第二个人物、不出现背景场景与任何道具，背景为纯白；'
    '三视图三个视角必须是同一只角色、同一套西装、同一颗猴头，毛色、毛流方向与五官比例完全一致；'
    '西装颜色、纽扣数量、领带（如有）三个视角必须完全一致，不得增删配饰。')

# ---------------------------------------------------------------- 变体

VARIANTS = [
    {
        'name': 'A',
        'title': '黑双排扣·敞领',
        'outfit': ('服装为一套修身窄版的黑色双排扣西装：光面精纺羊毛面料、细密驳头驳线、'
                   '两排共六颗黑曜石般的树脂纽扣；'
                   '西裤为一条修身窄版的长直西裤（裤管笔直细长、裤脚略微收窄）与黑色系带皮鞋；'
                   '内搭白色衬衫，最上一颗扣子敞开、不打领带，衬衫领口自然外翻，'
                   '露出一小截粉褐色的颈部皮肤与领口边缘的短毛。'),
    },
]


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
                pending.pop(tid)
                done[tid] = st
                nm = next(t['v']['name'] for t in tasks if t['id'] == tid)
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
        dst = os.path.join(OUT, '猴头_真人质感_三视图基础_高瘦_%s.png' % t['v']['name'])
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