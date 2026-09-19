# BGM 曲库（全局共享，跨剧集复用）

> 由 palace-girlfriend-trending Step 5B 维护：合成视频统一配乐**先查本表**，无合适条目用 get-music 生成并登记入库；复用时在「使用记录」列追加集号。
>
> 音频文件存本目录 `d:\work\minimax_h3\assets\bgm\`，命名 `bgm_风格_情绪_序号.m4a`。

| 文件 | 风格/情绪标签 | BPM | 时长 | 来源 | 生成提示词 | 首次用于 | 使用记录 |
|---|---|---|---|---|---|---|---|
| bgm_国风甜妹_温馨撒娇_001.m4a（同存 .wav） | 国风甜妹 / 温馨俏皮 / 古筝+曲笛+木吉他+轻打击 / 纯音乐 acoustic | 96 | 母带 30.0s（原始 149.56s，候选变体2） | Suno V6 instrumental，task_id `task_01M2TT1Q5QJGXZNJ371WNH9GS9`，audio_id `1f90b3bd-a816-481c-b44b-98f68948f507`，$0.05/0.5 credits（Flow Music 当日服务异常连续 3 次失败后改道 Suno） | Playful sweet Chinese-style instrumental, guzheng and soft dizi flute melody with warm acoustic guitar plucks, light gentle percussion, cozy warm autumn evening mood, 96 bpm, no vocals | E08《秋日火锅》合集（E08A+E08B 合并正片，元瑶宫装），0.25 音量垫底混音 | 2026-09-19 E08 合集；**2026-09-19 E11《中秋鳌鱼灯》**（40.531s 成片，源曲仅 30.0s → `aloop=loop=-1` 循环铺满 + 片尾 1.6s 淡出，0.25 音量垫底；因新曲生成时 APIMart 提交网络中断、按规矩不重发以免重复扣费，故复用本曲） |
