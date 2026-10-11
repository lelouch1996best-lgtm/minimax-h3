# -*- coding: utf-8 -*-
"""恶搞系列 · 第五集基调图 —— 一脚踹碎法天象地

剧情：一只印着黄色标识的巨型大脚从天而降，一脚把大嘴鱼的「法天象地」线条虚影踹碎。
基调：荒诞喜剧（slapstick），不是暴力拆迁。

双参考图分工：
  第1 张 = 大嘴鱼 法天象地（线条虚影·雷暴）.png → 被踹者的身份 + 线条虚影材质
  第 2 张 = props/大脚标识.png                 → 大脚上那枚黄底黑图案标识的唯一基准

已踩过的坑，本脚本重点压制：
  1. 虚影绝不实体化（v1 曾把法相画成实体，被用户打回重做）
  2. 打戏防伤化：slapstick，不流一滴血
  3. 标识必须写足四件事（形态/位置/比例/清晰度），且声明"纯图形非文字"
  4. 模型默认模型已更新为 gpt-image-2.5-flare

输出：generated-images/第五集_踹碎法天象地_{A|B|C}.png
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
MODEL = 'gpt-image-2.5-flare'
OUT = r'D:/work/minimax_h3/generated-images'

REF_GHOST = r'D:/work/minimax_h3/assets/恶搞/character/大嘴鱼/法天象地（线条虚影·雷暴）.png'
REF_LOGO = r'D:/work/minimax_h3/assets/恶搞/props/大脚标识.png'

# ================================================================ 被踹者：身份锁定

IDENTITY_LOCK = (
    '第 1 张参考图是「穿西装的大嘴鱼法天象地」的唯一身份基准，'
    '画面中被踹碎的那尊巨大虚影必须严格照搬它，一个特征都不能改：'
    '（1）巨型鱼头与身体不成比例，嘴极大、横向咧开到近乎耳根，上下颌夸张外突，'
    '厚实湿润的嘴唇微张成一派憨厚呆滞的傻笑（不是凶狠龇牙、不是狰狞威慑），口内一整排细密尖牙；'
    '（2）小而圆、凸出于头部两侧的鱼眼，昏黄琥珀色虹膜，眼白布满细红血丝，眼神木讷憨钝；'
    '（3）头顶一小撮黏湿的深色水草状短须；'
    '（4）青灰绿色湿润鱼皮、细密小鳞片与不规则深色斑块、鳃部一道弧形鳃裂；'
    '（5）颈部以下为正常人类身躯，肩宽、手臂短粗、双手五指人类手掌、双腿短；'
    '**（6）服装：一套黑色光面精纺羊毛双排扣西装（细密驳头驳线、两排共六颗黑树脂纽扣）、'
    '同色西裤、黑色系带皮鞋，内搭白色衬衫、最上一颗扣子敞开、不打领带。**'
    '西装同样只以**发光的线条网格**呈现（驳头线、纽扣、双排扣的排线都要勾出来），'
    '绝不允许改成铠甲、长袍、披风或任何古装。'
)

# ================================================================ 材质：虚影（硬约束）

FIGURE_FORM = (
    '【最重要】被踹的这尊巨大身影**不是实体，而是一道完全由光线与线条构成的超自然虚影**，'
    '请严格照搬第 1 张参考图里人物的画法，一比一复现那种材质：'
    '（1）人物**半透明、非实体**：整体像一道被点亮的青绿色光之幻影，身体内部大面积中空透空，'
    '能清楚看见身后的云海、山岳与天光透过虚影内部；'
    '没有皮肤、没有血肉、没有实体厚度、没有不透明的黑色块面。'
    '（2）**轮廓与结构由成百上千根极细的发光线条勾勒**：'
    '外轮廓、鱼头轮廓、眉眼、嘴线、西装的驳头线、纽扣、排扣线、袖口与裤缝、'
    '手指与脚趾的关节线，全部由细如发丝的青绿色流线一根根描出，'
    '线条有粗粗浓淡变化、有轻微抖动与波动，像被风吹起的一束束发丝在流动中定型，'
    '而不是一条均匀的描边。'
    '（3）**被踹中的部位正在崩解**：那只大脚落点上，虚影的线条被冲击撕开一个明显的破口，'
    '断线向四周飞散、失去形状，散成无数细碎的光点、飞散的丝絮与长长飘扬的发光碎线；'
    '破口周围的线条被拉长、扭曲、卷曲，亮度瞬间过曝成白；'
    '沿着破口向全身蔓延，虚影的整体轮廓正在瓦解、变淡、消散。'
    '（4）虚影整体有真实的辉光（bloom）与体积感（半透明层交叠处更亮），'
    '线条本身是青绿到近白的渐变高光，不是纯色平涂；'
    '体表有细碎光尘与流光丝线向外飘散。'
)

# ================================================================ 大脚设定

BOOT_LOCK = (
    '这只大脚是**一只巨大的正装皮鞋**，属于一个身高远超常人的巨人，'
    '（1）**鞋型**：黑色光面小牛皮正装皮鞋，鞋面光洁、鞋头圆润饱满、'
    '鞋帮有整排细密的鞋带孔与鞋带、鞋底边缘有一道浅浅的沿条；'
    '**鞋底正对镜头**，鞋底纹路为规整的人字形防滑纹（不是运动鞋、不是靴子、不是拖鞋、不是光脚）；'
    '（2）**鞋上穿的是黑色西裤裤脚**：鞋口上方露出一截与鞋同色系的深色西裤裤管，'
    '裤管笔直、裤线笔挺，与被踹的虚影那身黑西装成配套；'
    '画面中**只出现这一只脚、这一条腿**，从画面上方伸入，'
    '**画面外不得出现踹腿者的上半身、脸、手或任何其他身体部位**。'
)

# ================================================================ 标识（写足四件事）

LOGO_LOCK = (
    '**那只巨大皮鞋的鞋底正中，印着一枚清晰的方形标识**——'
    '严格照搬第 2 张参考图（那张黄底黑图）的形态，一比一复现：'
    '（1）**形态**：一枚正方形的徽章，底色为**温暖的明黄色**（近似 #F4CB4F），'
    '徽章四边留一道极窄的黄边；'
    '徽章正中只有**一个**纯黑色的粗线条抽象符号——'
    '形状是一条**横向的黑色粗弧带**（弧顶朝上隆起，像一座小桥），'
    '这条弧带的两端各自**向下弯垂收笔**，形成两条短粗的黑色垂脚，'
    '整体读作一个圆润厚重的、类似倒扣的"∩"接上两条短腿的图形；'
    '除这一个符号外，徽章内**不得有任何其他图形、字符、文字、字母、数字或标记**。'
    '（2）**这不是文字**：这个符号是一个纯几何图形徽标，'
    '**绝对不能**被画成汉字、英文字母、阿拉伯数字、拼音或任何可读的字符。'
    '（3）**位置**：标识位于鞋底**正中偏后（鞋跟与鞋掌之间的中线位置）**，'
    '随鞋底透视一起被压扁，正对镜头、居中醒目，绝不偏到鞋边或被裁掉。'
    '（4）**比例与清晰度**：标识宽度约占鞋底宽度的四分之一，'
    '黄底与黑色符号的对比强烈锐利，边界干净不虚化；'
    '打印为平面贴花质感（像丝网印刷的商标贴），随鞋底的弧度有轻微的自然变形，'
    '但符号本身的几何形状必须完整可辨——不得多笔画、不得少笔画、不得糊成一团黑块。'
)

# ================================================================ 基调：荒诞喜剧

TONE_LOCK = (
    '【本集的基调：荒诞无厘头喜剧，不是暴力拆迁、不是灾难片】'
    '这是一场**滑稽的、举重若轻的破坏**，整体气氛是'
    '「那么顶天立地的神佛，被一只从天而降的皮鞋，一脚就踹碎了，就这么简单」：'
    '（1）画面里**没有一滴血、没有伤口、没有淤青、没有骨裂、没有惨叫的惨烈感**；'
    '虚影碎裂的方式是**光粒与线条的崩散**（像肥皂泡破裂、像烟花熄灭、'
    '像全息投影被拔掉电源），不是血肉横飞。'
    '（2）踹击的瞬间带着**游戏式的爽快与漫画式的夸张**：'
    '冲击点画成干净利落的圆形冲击波环、放射状速度线、一圈白色冲击闪光与飞溅的光斑，'
    '像卡通动画里那一击的定格。'
    '（3）被踹的虚影的姿态是**狼狈而滑稽的**——上半身被踹得向后仰、'
    '双臂甩开、双腿离地、手足乱蹬，整体像被一脚踢飞的巨大布偶，'
    '而非庄严悲壮的神像陨落。虚影的脸仍保持那副憨厚呆滞的傻笑，'
    '完全没有惊恐或痛苦的表情，这点务必保留。'
    '（4）除了那只巨大的皮鞋，画面中**只有这一尊被踹的虚影，不出现任何其他人物、生物或旁观者**。'
)

SCENE_LOCK = (
    '场景延续同系列前四段：**高空翻涌的墨蓝近黑云层天幕，云间有青白色灵气光流与飞散光尘**，'
    '画面下方三分之一为翻涌云海与层层叠叠的仙山岩峰剪影，'
    '山脊上有极小的古松与飞鸟，用它们反衬两者的悬殊尺度对比；'
    '云层被青绿灵气与金色天光从内部点亮，边缘镶着亮边；'
    '云海有真实的体积与层次，能看到光在云雾中的散射。'
)

REALITY = (
    '质感：国风仙侠厚涂CG动画电影级（不是真人实拍、不是照片写实）。'
    '皮鞋是真实的高级皮革质感：油润的反光、可见的细微毛孔与皮纹、鞋底沿条略哑光；'
    '线条虚影有真实的辉光溢出与能量感；'
    '整幅画面要有强烈的景深与体积光，人物与脚的尺度对比一眼读懂。'
)

NEGATIVE = (
    '【最重要的排除项】避免把虚影画成实体：不要不透明的实体人物、'
    '不要厚重的三维实体、不要真实皮肤与血肉质感、不要结实的肌肉块面、'
    '不要实体布料与褶皱阴影、不要暗部黑块；虚影必须始终是半透明的线条光影。\n'
    '避免血腥：不要血、不要伤口、不要淤青、不要骨裂、不要残肢、'
    '不要喷血、不要狰狞的痛苦表情、不要恐怖氛围。\n'
    '避免：卡通、动漫赛璐璐平涂、线稿描边、Q 版、3D 游戏低模、塑料感、'
    '搪胶手办感、廉价 CG。\n'
    '避免出现第二只脚、第二条腿、踹腿者的身体其它部位、旁观者、'
    '任何其他人物或生物；**画面中有且只有一只皮鞋和一条裤管**。\n'
    '避免：运动鞋、球鞋、靴子、拖鞋、光脚、丝袜、高跟鞋、洞洞鞋；'
    '避免把西装改掉（禁止铠甲/长袍/披风/僧袍/任何古装）；'
    '避免手部畸变（无多指、无粘连、无指节反折）；'
    '避免把黄色标识画成文字、汉字、字母、数字或拼音；'
    '避免标识变形、糊成一团黑块、或被画面边缘裁掉；'
    '避免画面中出现任何其他文字、字幕、水印、落款、印章（**黄色标识是唯一允许的图形标记**）。'
)

# ================================================================ 三个构图变体

VARIANTS = [
    {
        'name': 'A',
        'title': '天外飞脚·正中胸口（主推）',
        'extra': (
            '构图：竖幅，**中近景仰视**。'
            '那只巨大的黑皮鞋连同黑色西裤裤管，从画面**右上角斜插进来**，'
            '鞋底朝向镜头、占据画面中央偏右上，'
            '正踹在虚影的胸口正中——黄底黑图案的方形标识在画面中心醒目可见。'
            '被踹的线条虚影位于画面中央偏左下方，占据画面下三分之二，'
            '头肩胸被踹中、上半身向后仰起、双臂甩开，'
            '胸口线条破口处的青绿线条被撕成飞散的光点与丝絮，'
            '冲击点画成干净的圆形冲击波环与放射状速度线；'
            '下方云海与仙山剪影在画面最底部，压住画面下缘。'
        ),
    },
    {
        'name': 'B',
        'title': '鞋底大特写·压满画面（标识最清晰）',
        'extra': (
            '构图：竖幅，**极端仰视特写**。'
            '那只巨大的黑皮鞋的**鞋底几乎占满整个画面中央**，'
            '黄底黑图案的方形标识位于鞋底正中、占据画面中央约三分之一，'
            '是全画面的绝对视觉焦点，图案完整清晰不畸变；'
            '鞋底的人字形防滑纹清晰可辨，鞋面与黑色西裤裤管只露出上缘一小截；'
            '鞋底下方极远处，才露出被踹中的那尊发光线条虚影的顶部——'
            '只见鱼头与头顶水草短须的轮廓、以及胸口破口崩散的光点，'
            '强调两者的悬殊尺度；'
            '画面四周是墨蓝近黑的雷暴云层与青绿灵气流光。'
        ),
    },
    {
        'name': 'C',
        'title': '迎面踹脸·仰面倒飞（喜剧感最强）',
        'extra': (
            '构图：竖幅，**正面中景仰视**。'
            '那只巨大的黑皮鞋从画面**正中上方直直踏下**，'
            '鞋底正对镜头、微微透视压缩，鞋底的黄底黑标识清晰居中，'
            '正踹在虚影的面门与上胸——把整尊巨大虚影**踹得向后仰面倒飞出去**；'
            '虚影的身体已经向后折成一个滑稽的角度（像被踢飞的布偶），'
            '双臂上举乱甩、双腿离地后蹬、短小的西装裤脚与皮鞋离地飘起，'
            '被踹中的面门与胸口位置线条大面积崩散成漫天飞舞的青绿光点与长长丝絮；'
            '虚影的脸仍是一派憨厚呆滞的傻笑，没有痛苦表情；'
            '下方云海与仙山剪影在画面底部翻涌。'
        ),
    },
]


def build(v):
    return '\n\n'.join([
        BOOT_LOCK, LOGO_LOCK, TONE_LOCK, IDENTITY_LOCK, FIGURE_FORM,
        v['extra'], SCENE_LOCK, REALITY, NEGATIVE,
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
    uri_ghost = load_b64(REF_GHOST)
    uri_logo = load_b64(REF_LOGO)

    tasks = []
    print('[2/4] 提交 %d 个变体（模型 %s）' % (len(VARIANTS), MODEL))
    for v in VARIANTS:
        prompt = build(v)
        payload = {
            'kind': 'image', 'model': MODEL,
            'input': {'prompt': prompt, 'size': '9:16', 'resolution': '2k', 'n': 1,
                      'image': [uri_ghost, uri_logo]},
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
        with open(os.path.join(OUT, '第五集_踹碎法天象地_%s_task.json' % v['name']),
                  'w', encoding='utf-8') as f:
            json.dump({'task_id': tid, 'variant': v['title'], 'episode': '第五集',
                       'model': MODEL, 'size': '9:16', 'resolution': '2k',
                       'prompt': prompt,
                       'refs': ['大嘴鱼 法天象地（线条虚影·雷暴）.png（被踹者身份+材质）',
                                '大脚标识.png（皮鞋上那枚标识的唯一基准）']},
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
        dst = os.path.join(OUT, '第五集_踹碎法天象地_%s.png' % t['v']['name'])
        with urllib.request.urlopen(urls[0], timeout=180) as r:
            blob = r.read()
        with open(dst, 'wb') as f:
            f.write(blob)
        print('    [%s] %.0fKB  %s' % (t['v']['name'], len(blob) / 1024, dst))

    ok = sum(1 for t in tasks if done.get(t['id'], {}).get('status') == 'done')
    print('\nSUMMARY ok=%d / total=%d' % (ok, len(tasks)))


if __name__ == '__main__':
    main()