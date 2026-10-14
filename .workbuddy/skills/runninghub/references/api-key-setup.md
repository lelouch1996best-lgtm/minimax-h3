# API Key 配置

## 检查状态

先运行 `--check`：
```powershell
python "<本技能目录>\scripts\runninghub.py" --check
```

按 `status` 响应：
- `"ready"` → "账号就绪！余额 ¥{balance}，想做点什么？生图、视频、配音都可以找我～"
- `"no_key"` → 引导：1) 注册 runninghub.cn 2) 创建 Key 3) 充值 4) 把 Key 发给助手
- `"no_balance"` → "余额空了～ 充个值就能继续：https://www.runninghub.cn/vip-rights/4"
- `"invalid_key"` → "Key 不太对，去这里看看：https://www.runninghub.cn/enterprise-api/sharedApi"

## 保存 Key

用户发来 Key 后，先用 `--check --api-key THE_KEY` 验证。验证通过再保存：

```powershell
python -c "import json, pathlib; p = pathlib.Path.home() / '.openclaw' / 'openclaw.json'; p.parent.mkdir(exist_ok=True); cfg = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}; cfg.setdefault('skills', {}).setdefault('entries', {}).setdefault('runninghub', {})['apiKey'] = 'THE_KEY'; p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')"
```

把 `THE_KEY` 替换为实际 Key。脚本会自动从 `~/.openclaw/openclaw.json` 读取（`skills.entries.runninghub.apiKey`），后续调用无需再传。

注意：
- 保存成功后提醒用户：Key 存在本机 `~/.openclaw/openclaw.json`，仅用于调用 RunningHub API。
- 也可以每次调用时传 `--api-key THE_KEY`，或设置环境变量 `RUNNINGHUB_API_KEY`，但保存到配置文件最省事。

## 获取 Key 的步骤（引导用户）

1. 注册/登录 https://www.runninghub.cn
2. 在 https://www.runninghub.cn/enterprise-api/sharedApi 点击 "新建" 创建 API Key
3. 在 https://www.runninghub.cn/vip-rights/4 充值（API 调用需要余额）
4. 把 Key 发给助手，助手验证后自动保存
