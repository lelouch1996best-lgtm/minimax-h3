# 欢迎使用 RunningHub API，轻松调用 RunningHub 云端的 ComfyUI 工作流

## 1. 开始使用

### 注册用户

注册 RunningHub 账号并充值钱包后，即可开始使用 AI 应用 API 和 ComfyUI 工作流 API。
请注意：若您使用 消费级-会员 API Key，需拥有 基础版及以上会员 才能调用上述接口。
使用 企业级-共享 或 企业级-独占 API Key 的用户不受此限制。

### 获取您的 API Key

RunningHub 为每位用户自动生成一个独特的 32 位 API KEY

请妥善保存您的 API KEY，不要外泄，后续步骤将依赖此密钥进行操作

### 提交请求

提交 API 请求。RunningHub API 已为您处理 API Key，您只需提交请求即可

```curl
curl --location --request POST 'https://www.runninghub.cn/openapi/v2/run/ai-app/2095868555916038145' \
--header "Content-Type: application/json" \
--header "Authorization: Bearer ${RUNNINGHUB_API_KEY}" \
--data-raw '{
  "nodeInfoList": [
    {
      "nodeId": "27",
      "fieldName": "value",
      "fieldValue": "15",
      "description": "value"
    },
    {
      "nodeId": "28",
      "fieldName": "prompt",
      "fieldValue": "15秒，高品质美式3D动画电影质感，暗黑哥特荒野古堡废墟，满月照亮枯树林、断裂塔楼、残破石桥与坍塌礼拜堂，冷雾贴地流动。阵型A女枪神(容貌参考图1)对阵阵型B剑神（古装黑衣男子），0秒立即开战；视觉上密集狂烈但攻防因果清楚，超高速连环兵器格斗，全程无对峙、无空镜、无停顿、无重复招式、无重复构图、无重复受力方式。女枪神突出长枪中线压迫、折线追刺、贴身变线与突然回马反杀；剑神以太乙玄门剑、子午剑、白猿二十四剑、玉女十九剑及独孤九剑不断拆线反制。二人始终大范围空间位移：前冲、腾跃、翻转、贴地滑行、空中交错、击飞、追击、回拉、俯冲、横向穿杀连续衔接，绝不原地互殴。枪剑命中、格挡与贴身冲撞均有沉重受力反馈；强碰撞中心炸开环形能量波纹、气浪与放射状碎片，重击后高速倒飞或后撤、明显失衡踉跄，石墙、枯树、断柱和古堡物件持续被波及破坏。女枪神为紫电刀刃状拖尾与凌厉切割劲气，剑神为银灰丝带状缠绕与凌厉切割劲气，能量只从近身枪剑交击中爆发，不能写成纯特效对轰；高速动作保留明显残影和拖尾，角色周身形成强压迫能量场，震撼的打斗音效，禁止动作停顿。\n\n0-3秒：女枪神自坍塌拱门前零前摇突进，长枪中线连续折刺，枪尖紫电在地面留下锐利划痕；剑神以武当太乙玄门剑斜向拦截，银灰丝带状劲气缠住枪杆试图偏转。女枪神立刻贴地滑行穿过断柱阴影，枪尾横扫接肩撞；剑神以峨眉子午剑回切格挡，碰撞中心炸开环形波纹，断柱被震碎，二人向相反方向高速后撤后同时追击。  \n3-6秒：剑神踏上残墙跃入半空，以峨眉白猿二十四剑连续俯斩；女枪神踩碎石阶腾跃迎击，枪杆架住剑锋后空中翻转，借枪身回弹横向穿杀。双方在满月前高速交错，紫电与银灰丝带拖尾缠绕，剑神被击飞掠过枯树枝梢，落在倾斜石桥上踉跄稳住。  \n6-10秒：女枪神沿石桥急速俯冲，武侠枪法连环挑刺、压枪、反挑不断变线；剑神以玉女十九剑轻灵侧闪，从桥栏内外连续切角，剑锋擦过枪尖爆出放射状火花碎片。中段上半身近景极速对招：枪尖短刺、剑锋格挡、枪杆顶肘、剑柄反震连续衔接，环形冲击波一层层推开，石桥裂纹迅速蔓延。剑神抓住空隙一剑震开长枪，女枪神高速后撤数米、脚下石桥崩塌，情势短暂逆转。  \n10-13秒：剑神发动独孤九剑前的压制连招，从高处残塔俯冲追杀，银灰丝带状剑气封锁女枪神前后路线；女枪神借坠落碎石踏墙折返，以修仙枪法压缩紫电于枪尖，连续穿过剑神的封锁线。她从低位废墟滑行至剑神侧后，突然回马一枪挑开剑路，将剑神横向轰入礼拜堂残墙，墙体爆裂、月光与尘雾同时卷起。  \n13-15秒：女枪神以修仙枪法明确终结，剑神强行凝聚独孤九剑反击时，女枪神前冲压住中线，枪势先直刺逼其格挡，随即骤然折线变位、转身回马反杀。紫电刀刃状轨迹切开银灰缠绕剑气，碰撞中心爆发巨大环形能量波纹和放射状碎片，气浪掀断周围枯树；剑神高速倒飞撞穿古堡石门、落地失衡踉跄无法再战。女枪神持枪滑行停在满月下，紫电能量场环绕枪身，阵型A女枪神碾压性胜利。",
      "description": "prompt"
    },
    {
      "nodeId": "29",
      "fieldName": "aspect_ratio",
      "fieldData": "[\"COMBO\", {\"default\": \"1:1 (Square)\", \"options\": [\"1:1 (Square)\", \"2:3 (Portrait Photo)\", \"3:2 (Photo)\", \"3:4 (Portrait Standard)\", \"4:3 (Standard)\", \"9:16 (Portrait Widescreen)\", \"16:9 (Widescreen)\", \"21:9 (Ultrawide)\"], \"tooltip\": \"The aspect ratio for the output dimensions.\", \"multiselect\": false}]",
      "fieldValue": "16:9 (Widescreen)",
      "description": "aspect_ratio"
    },
    {
      "nodeId": "29",
      "fieldName": "megapixels",
      "fieldValue": "0.7000000000000001",
      "description": "megapixels"
    },
    {
      "nodeId": "6",
      "fieldName": "image",
      "fieldValue": "34e67512265da29076075030b62ba93ec304210a09171ff68e1f44894d15a36c.jpg",
      "description": "image"
    },
    {
      "nodeId": "35",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image"
    },
    {
      "nodeId": "36",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image"
    },
    {
      "nodeId": "37",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image"
    },
    {
      "nodeId": "38",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image"
    },
    {
      "nodeId": "39",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image"
    },
    {
      "nodeId": "40",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image"
    },
    {
      "nodeId": "41",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image"
    },
    {
      "nodeId": "42",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image"
    }
  ],
  "instanceType": "default",
  "usePersonalQueue": "false"
}'
```

#### 请求参数说明

| 参数说明 | 类型 | 必填/可选 | AI 应用程序生成的结果。 |
| --- | --- | --- | --- |
| `nodeInfoList` | List | 必填 | 节点参数映射列表，用于动态修改工作流参数 |
| `instanceType` | String | 可选 | 指定运行实例的类型<br>default (24G显存), plus (48G显存), ultra (84G显存) |
| `usePersonalQueue` | Boolean | 可选 | 是否使用个人独占队列 |
| `retainSeconds` | Integer | 可选 | 实例保留时长（秒）。仅企业共享 API Key 生效；任务成功结束后会在指定时长内优先复用同用户同工作流实例，减少冷启动与排队。该保留时段会产生额外费用，按实际保留时长计费。可选范围：10~180 秒。 |
| `webhookUrl` | String | 可选 | Webhook 回调地址，任务完成时会向该地址发送 POST 请求 |

#### 响应示例

```json
{
  "taskId": "2013508786110730241",
  "status": "RUNNING",
  "errorCode": "",
  "errorMessage": "",
  "results": null,
  "clientId": "f828b9af25161bc066ef152db7b29ccc",
  "promptTips": "{\"result\": true, \"error\": null, \"outputs_to_execute\": [\"4\"], \"node_errors\": {}}"
}
```

#### 响应字段说明

| 参数说明 | 类型 | AI 应用程序生成的结果。 |
| --- | --- | --- |
| `taskId` | String | 任务ID，用于后续查询任务状态 |
| `status` | String | 当前任务状态，常见状态：QUEUED (排队中), RUNNING (运行中), SUCCESS (成功), FAILED (失败) |
| `errorCode` | String | 错误码，仅在失败时返回 |
| `errorMessage` | String | 错误具体信息 |
| `results` | List | 生成结果（提交时为 null） |
| ├ `url` | String | 重要提醒：该链接有效期仅为 24 小时。任务生成结束后，请务必在此时间窗口内将视频文件下载或转存至您的服务器。逾期后链接将永久失效且无法恢复。 |
| ├ `nodeId` | String | 生成该结果的工作流节点 ID |
| ├ `outputType` | String | 文件扩展名 (如 png, mp4, txt) |
| └ `text` | String | 如果输出是纯文本，内容将显示在此字段 |
| `clientId` | String | 客户端会话ID，用于标识本次连接 |
| `promptTips` | String (JSON) | ComfyUI 后端的校验信息，包含需执行的节点ID等调试信息 |

### 查询结果与 Webhook

如果在提交时添加了 "webhookUrl": "https://example.com/webhook" 请求体参数，RunningHub 会在任务完成时向您的URL发送POST请求

#### 请求示例

```curl
curl --location --request POST 'https://www.runninghub.cn/openapi/v2/query' \
--header "Content-Type: application/json" \
--header "Authorization: Bearer ${RUNNINGHUB_API_KEY}" \
--data-raw '{
  "taskId": "${RUNNINGHUB_TASKID}"
}'
```

#### 响应示例

```json
{
  "taskId": "2013508786110730241",
  "status": "SUCCESS",
  "errorCode": "",
  "errorMessage": "",
  "failedReason": {},
  "usage": {
    "consumeMoney": null,
    "consumeCoins": null,
    "taskCostTime": "0",
    "thirdPartyConsumeMoney": null
  },
  "results": [
    {
      "url": "https://rh-images-1252422369.cos.ap-beijing.myqcloud.com/b04e28cad0ee39193921a30a2eb4dc00/output/ComfyUI_00001_plhjr_1768892915.png",
      "nodeId": "2",
      "outputType": "png",
      "text": null
    }
  ],
  "clientId": "",
  "promptTips": ""
}
```

#### 响应字段说明

| 参数说明 | 类型 | AI 应用程序生成的结果。 |
| --- | --- | --- |
| `taskId` | String | 任务 ID |
| `status` | String | 任务最终状态，SUCCESS 表示生成成功 |
| `results` | List | 生成结果列表，包含图片、视频或文本等输出 |
| ├ `url` | String | 重要提醒：该链接有效期仅为 24 小时。任务生成结束后，请务必在此时间窗口内将视频文件下载或转存至您的服务器。逾期后链接将永久失效且无法恢复。 |
| ├ `nodeId` | String | 生成该结果的工作流节点 ID |
| ├ `outputType` | String | 文件扩展名 (如 png, mp4, txt) |
| └ `text` | String | 如果输出是纯文本，内容将显示在此字段 |
| `errorCode` | String | 错误码 (如有) |
| `errorMessage` | String | 错误信息 (如有) |
| `failedReason` | Object | ComfyUI 相关的失败原因 |
| `usage` | Object | 任务消耗信息 |
| ├ `thirdPartyConsumeMoney` | String | 三方API消费金额 |
| ├ `consumeMoney` | String | 运行时长消耗金额 |
| ├ `consumeCoins` | String | 运行消耗的RH币 |
| └ `taskCostTime` | String | 运行耗时（ComfyUI 工作流运行时长） |
### 文件上传

资源文件（如 imageUrls）参数支持传入文件 URL 或 Base64 Data URI。

#### 公共 URL

直接传递可公开访问的 URL：

```json
{
  "imageUrls": [
    "https://example.com/image.png"
  ]
}
```

#### Base64 data URI

以 Base64 格式嵌入图片：

```json
{
  "images": [
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
  ]
}
```

#### RH 上传接口

上传本地文件以获取一个 URL。

**Endpoint:** `https://www.runninghub.cn/openapi/v2/media/upload/binary`

**请求**

```curl
curl --location --request POST 'https://www.runninghub.cn/openapi/v2/media/upload/binary' \
--header 'Authorization: Bearer [Your API KEY]' \
--form 'file=@/path/to/image.png'
```

**响应**

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "type": "image",
    "download_url": "xxxx.png",
    "fileName": "openapi/xxxx.png",
    "size": "3490"
  }
}
```

**备注:** 上传后获得的链接有效期为 1 天，超期将无法通过 URL 直接访问。

