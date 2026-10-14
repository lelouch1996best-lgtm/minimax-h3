# 输出与交付

## 进度通知（慢任务）

视频、AI 应用、3D、音乐生成：**运行脚本前必须先用文字告知用户**。这些任务耗时 1-10+ 分钟，用户需要知道任务已经开始。

> 开始生成啦，视频一般需要几分钟，请稍等～ 🎬

然后再执行脚本（建议后台运行，脚本会自动轮询直到完成）。快任务（文生图、图片放大、TTS）通知可选。

## 媒体文件（图片/视频/音频/3D）

脚本输出 `OUTPUT_FILE:<路径>`，可能还有 `COST:¥X.XX`。

**交付方式：用 computer:// 链接把文件给用户**，附一句自然的话：

```markdown
搞定啦！花了 ¥0.12～ 要不要做成视频？🐱

[cat_20260829_153000.png](computer://<项目目录>\runninghub-output\cat_20260829_153000.png)
```

要点：
- 链接显示名用有意义的文件名，不要只打印裸路径。
- 有 `COST:` 时必须自然地报告花费（"花了 ¥X.XX"）。
- 视频/音频同样用 computer:// 链接交付。
- 如果文件下载失败（脚本没输出 `OUTPUT_FILE`），把脚本的错误信息用友好口吻转述，并提供重试或换模型的选项。

**绝不要做这些：**
- 把 `runninghub.cn` 的 URL 展示给用户（内部地址，打不开）
- 只打印 `OUTPUT_FILE:` 路径当成交付
- 说 "已发送" 但没有实际给出文件链接

## 文本结果

直接把文字展示给用户。有 `COST:` 时一并报告花费。

## 错误与重试

| 错误 | 处理 |
|-------|--------|
| `NO_API_KEY` | 引导配置 Key → 读 `references/api-key-setup.md` |
| `AUTH_FAILED` | Key 失效 → https://www.runninghub.cn/enterprise-api/sharedApi |
| `INSUFFICIENT_BALANCE` | "余额不够啦～" → https://www.runninghub.cn/vip-rights/4 |
| `TASK_FAILED` | 视频类：主动提供备选模型。其他：友好报错并提供重试选项 |

## 一般说明

- 视频较慢（1-5 分钟）；脚本自动轮询最长 20 分钟。
- 图片 < 5MB 走 base64；更大的先上传。
- Key 优先级：`--api-key` 参数 → `RUNNINGHUB_API_KEY` 环境变量 → `~/.openclaw/openclaw.json` 配置文件。
