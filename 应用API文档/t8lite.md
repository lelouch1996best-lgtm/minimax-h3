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
curl --location --request POST 'https://www.runninghub.cn/openapi/v2/run/ai-app/2097935043799896065' \
--header "Content-Type: application/json" \
--header "Authorization: Bearer ${RUNNINGHUB_API_KEY}" \
--data-raw '{
  "nodeInfoList": [
    {
      "nodeId": "64",
      "fieldName": "index",
      "fieldValue": "0",
      "description": "文武戏设置1"
    },
    {
      "nodeId": "69",
      "fieldName": "index",
      "fieldValue": "0",
      "description": "文武戏设置2"
    },
    {
      "nodeId": "27",
      "fieldName": "value",
      "fieldValue": "15",
      "description": "时长（秒）"
    },
    {
      "nodeId": "28",
      "fieldName": "prompt",
      "fieldValue": "subject_definitions:\n<Subject 1>：源自<Picture 1>的年轻女性，留着带暖棕高光的长直发，皮肤白皙，佩戴小巧耳钉，身穿黑色上衣；在视频中坐在床上，以娇羞暧昧的神态直视镜头并说话。\n<Picture 1>：参考肖像图，提供<Subject 1>的五官、发型、耳饰、黑色上衣、暖色轮廓光与深色虚化背景质感；目标视频将背景改为夜晚卧室床铺。\n\nsummary:\n[reference generation, keyframe completion] 15秒浪漫暧昧短视频，以<Picture 1>中女性的外貌与光影为参考，让她坐在夜晚卧室的床上对镜头低语，保留娇羞微笑与亲昵语气，完整说出指定台词，全程不出现字幕。\n\nretention_analysis:\n<Picture 1>: partially_preserved，保留<Subject 1>的五官、长棕发、耳钉、黑色上衣、暖光轮廓与深色虚化氛围，背景由原场景改为卧室床铺。\n<Subject 1>: fully_preserved，面部特征、发型、耳饰与黑色上衣在所有镜头中持续一致。\n\ndetailed_description:\n整体为暖调低照度的电影感近景，浅景深让床头灯与夜色融成柔焦光斑，床品呈深色丝质质感，气氛浪漫、亲昵又带一点娇羞。全片不出现任何字幕或屏幕文字。\n\n[Shot 1] 画面从<Subject 1>胸前的中近景开始，镜头以缓慢稳定的速度向她面部推近，前景保留一缕失焦的柔化遮挡。她坐在床上，肩膀放松，长发垂落肩侧，先是抿唇一笑，随后抬眼直视镜头，(S1)轻声说：<d>[Chinese]夜色这么美……你却只盯着别处看？把视线移过来一点。</d>\n\n[Shot 2] At 00:06.000, 镜头切为更近的面部特写并继续缓慢推近，带有极轻微的环绕弧度。<Subject 1>微微偏头，笑意更深，像在确认对方是否照做，(S1)接着说：<d>[Chinese]对，再近一点……</d> 暖光掠过她的发梢与耳钉。\n\n[Shot 3] At 00:10.800, 镜头推至近特写，<Subject 1>身体微微前倾，目光柔亮，呼吸放轻，(S1)低声说：<d>[Chinese]今晚的时间还很长，我们，有的是耐心慢慢浪费。</d> 说完后她唇角轻扬，继续凝视镜头，画面在暧昧安静的停顿中结束。\n\noverall_soundscape:\n环境音很轻，以夜晚室内的低频静谧感为主，夹杂细微的布料摩擦声和她靠近时的轻柔呼吸声；床品微动与发丝轻擦带来贴近耳边的真实质感。\n\nnon_diegetic_music:\n底层铺有缓慢、低音量的浪漫氛围音乐，暖色调钢琴与柔和弦乐交织，节奏舒展，在最后一句台词后仍留有微弱延音，不盖过人声。",
      "description": "提示词"
    },
    {
      "nodeId": "29",
      "fieldName": "aspect_ratio",
      "fieldData": "[\"COMBO\", {\"default\": \"1:1 (Square)\", \"options\": [\"1:1 (Square)\", \"2:3 (Portrait Photo)\", \"3:2 (Photo)\", \"3:4 (Portrait Standard)\", \"4:3 (Standard)\", \"9:16 (Portrait Widescreen)\", \"16:9 (Widescreen)\", \"21:9 (Ultrawide)\"], \"tooltip\": \"The aspect ratio for the output dimensions.\", \"multiselect\": false}]",
      "fieldValue": "16:9 (Widescreen)",
      "description": "分辨率"
    },
    {
      "nodeId": "6",
      "fieldName": "image",
      "fieldValue": "34e67512265da29076075030b62ba93ec304210a09171ff68e1f44894d15a36c.jpg",
      "description": "image1"
    },
    {
      "nodeId": "35",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image2"
    },
    {
      "nodeId": "36",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image3"
    },
    {
      "nodeId": "37",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image4"
    },
    {
      "nodeId": "38",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image5"
    },
    {
      "nodeId": "39",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image6"
    },
    {
      "nodeId": "40",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image7"
    },
    {
      "nodeId": "41",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image8"
    },
    {
      "nodeId": "42",
      "fieldName": "image",
      "fieldValue": "None",
      "description": "image9"
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

