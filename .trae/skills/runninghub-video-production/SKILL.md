---
name: runninghub-video-production
description: RunningHub AI video production pipeline guide covering two submission modes (App API direct call vs workflow JSON), Ref2VA prompt structure, image upload, batch concurrency, cost/time display, and troubleshooting. Invoke when user wants to generate videos via RunningHub, submit t8lite/Ref2VA tasks, manage character/scene assets, or troubleshoot API issues.
---

# RunningHub Video Production Pipeline

## Two Submission Modes

Users can choose between two approaches to submit video generation tasks:

### Mode A: AI Application API (Direct)

Call the App API endpoint directly with `nodeInfoList` field overrides. No need to generate or manage workflow JSON files.

```
POST https://www.runninghub.cn/openapi/v2/run/ai-app/{appId}
Authorization: Bearer {API_KEY}
Content-Type: application/json
```

Request body structure:
```json
{
  "nodeInfoList": [
    {"nodeId": "27", "fieldName": "value", "fieldValue": "15", "description": "duration"},
    {"nodeId": "28", "fieldName": "prompt", "fieldValue": "<full prompt text>", "description": "prompt"},
    {"nodeId": "29", "fieldName": "aspect_ratio", "fieldValue": "16:9 (Widescreen)", "description": "resolution"},
    {"nodeId": "6", "fieldName": "image", "fieldValue": "openapi/<hash>.png", "description": "image1"},
    {"nodeId": "35", "fieldName": "image", "fieldValue": "openapi/<hash>.png", "description": "image2"},
    {"nodeId": "36", "fieldName": "image", "fieldValue": "None", "description": "image3 (unused)"},
    ...
  ],
  "instanceType": "plus",
  "usePersonalQueue": "false"
}
```

### Mode B: Workflow JSON

Generate a complete ComfyUI workflow JSON file and submit it via the task submission API. More flexible but requires understanding of the workflow's internal node graph.

### When to Choose Which

| Criteria | Mode A (App API) | Mode B (Workflow JSON) |
|---|---|---|
| Ease of use | Simple, just override fields | Requires full workflow knowledge |
| Flexibility | Limited to app-defined nodes | Full workflow control |
| Prompt editing | Via nodeId 28 fieldValue | Direct in workflow JSON |
| Image binding | Via nodeId 6/35-42 fieldValue | Via workflow image nodes |
| Recommended for | Series production, batch episodes | Custom workflows, experimentation |

## CRITICAL: API Response Format

### Query Response `results` is a LIST, not a DICT

The query API returns `results` as a **list of objects** directly:

```json
{
  "taskId": "...",
  "status": "SUCCESS",
  "results": [
    {"url": "https://...", "nodeId": "21", "outputType": "mp4", "text": null}
  ],
  "usage": {
    "consumeCoins": "164",
    "taskCostTime": "410"
  }
}
```

**Common bug**: Code that treats `results` as a dict with an `output` key will fail silently. Always iterate `results` as a list:

```python
# CORRECT
results_list = result.get("results", [])
if isinstance(results_list, list):
    for o in results_list:
        url = o.get("url", "")

# WRONG - results is NOT a dict
result.get("results", {}).get("output", [])  # This fails!
```

### Status Values

- `QUEUED` - Task in queue
- `RUNNING` - Task executing
- `SUCCESS` - Task completed (NOT "COMPLETED")
- `FAILED` - Task failed

## Cost and Time Transparency

**Always show users the cost and time of each generated video.** The query API response includes a `usage` object:

| Field | Description |
|---|---|
| `usage.consumeCoins` | RH coins consumed |
| `usage.taskCostTime` | Execution time in seconds |
| `usage.consumeMoney` | Monetary cost |
| `usage.thirdPartyConsumeMoney` | Third-party API cost |

Display format example:
```
E06: DONE (410s, 164 coins)
```

## Concurrency and Retry

### Concurrent Limit

- Maximum **3 concurrent tasks** per account
- Exceeding returns errorCode `421` with message "api queue limit reached"
- Must wait for a running task to complete before submitting more

### Retry Strategy

```python
for attempt in range(max_retries):
    result = submit(payload)
    if result.get("taskId"):
        return result["taskId"]  # Success
    if "queue limit" in result.get("errorMessage", ""):
        time.sleep(30)  # Wait for slot
        continue
```

### Batch Submission for N Episodes

For 6 episodes with 3-concurrent limit:
1. Submit episodes 1-3 (or 1-2 if cautious)
2. Poll until at least one completes and download
3. Submit next episode to fill the freed slot
4. Repeat until all submitted
5. Download remaining results

## HTTP Client Reliability

### CRITICAL: Timeout Does NOT Mean Request Not Delivered

When an HTTP POST to the RunningHub submission API hangs or times out, **the request body may have already been fully transmitted to the server**. The server receives the complete payload, creates a task, and starts generating video -- but the client never receives the response containing the `taskId`.

This means:
- The client thinks submission "failed" and retries
- Each retry sends another complete payload
- The server creates a new task each time
- **Each duplicate task consumes RH coins for a full video generation**
- The client has no way to discover the orphaned tasks (no "list my tasks" API)

**Real-world example**: E06 was submitted 4 times due to repeated hangs. Only the last attempt (via curl.exe) returned a taskId. The 3 earlier hung submissions all created tasks on the server, resulting in 4x coin consumption for a single video.

### Submission Safety Rules

1. **Never immediately resubmit after a hang/timeout** -- the task may already be running
2. **Always use `curl.exe --max-time`** for submission, never Python `requests` or `urllib`
3. **If a hang occurs, wait at least 2-3 minutes** before any retry attempt
4. **Log every submission attempt** with timestamp, so you can correlate with server-side tasks
5. **Consider using `webhookUrl`** in the payload to receive async completion notifications
6. **If multiple attempts were made, check the RunningHub dashboard** for orphaned tasks

### Recommended: `curl.exe` Only

On Windows, use `curl.exe` (not PowerShell's `curl` alias) with `--max-time` for ALL RunningHub API calls. Python `requests` and `urllib` both exhibit indefinite hangs on this API, even with timeout parameters set:

```powershell
# Submit task
curl.exe -s -X POST 'https://www.runninghub.cn/openapi/v2/run/ai-app/{appId}' \
  -H 'Authorization: Bearer {API_KEY}' \
  -H 'Content-Type: application/json' \
  --data-binary '@payload.json' \
  --max-time 60

# Query task
curl.exe -s -X POST 'https://www.runninghub.cn/openapi/v2/query' \
  -H 'Authorization: Bearer {API_KEY}' \
  -H 'Content-Type: application/json' \
  -d '{\"taskId\":\"...\"}' \
  --max-time 30
```

**Note**: PowerShell aliases `curl` to `Invoke-WebRequest`. Always use `curl.exe` explicitly.

### Why Not Python requests/urllib

| Issue | `requests` | `urllib` | `curl.exe` |
|---|---|---|---|
| Hangs on submission POST | Yes, indefinite | Yes, indefinite | No, `--max-time` is hard limit |
| Hangs on query POST | Yes | Yes | No |
| `timeout` parameter respected | Unreliable | Per-socket, not overall | Reliable |
| Risk of duplicate submission | **High** | **High** | Low |

### If You Must Use Python

If curl.exe is unavailable, use this pattern to minimize duplicate submission risk:

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Disable retries entirely -- we handle them manually
session = requests.Session()
adapter = HTTPAdapter(max_retries=0)  # No automatic retries!
session.mount("https://", adapter)

try:
    resp = session.post(url, json=payload, timeout=(10, 30))  # (connect, read)
    result = resp.json()
    task_id = result.get("taskId")
    if task_id:
        log_submission(episode, task_id)  # Record immediately
        return task_id
except Exception:
    # DO NOT immediately retry -- the task may already be running
    # Wait 2-3 minutes, then check RunningHub dashboard for orphaned tasks
    log_failed_attempt(episode)
    time.sleep(180)  # Long delay before any retry
```

## Image Upload

### Upload Endpoint

```
POST https://www.runninghub.cn/openapi/v2/media/upload/binary
Authorization: Bearer {API_KEY}
Content-Type: multipart/form-data
Form field: file=@/path/to/image.png
```

Response:
```json
{
  "code": 0,
  "data": {
    "fileName": "openapi/<content_hash>.png",
    "download_url": "...",
    "size": "3490"
  }
}
```

### Content-Addressed Uploads

The same file content always produces the same hash filename. This means:
- Returning characters across episodes reuse the same openapi path (no re-upload needed)
- Only new characters/scenes require uploading
- Cache the path mapping in a JSON file for reuse across seasons

### Upload Link Expiry

Both upload download URLs and task result URLs expire in **24 hours**. Always download videos immediately after generation.

## Image-to-NodeId Mapping (t8lite Workflow)

For the t8lite AI Application (appId: `2097935043799896065`):

| Image Slot | nodeId | fieldName | Description |
|---|---|---|---|
| image1 | 6 | image | Primary character/subject |
| image2 | 35 | image | Second character/scene |
| image3 | 36 | image | Third character/scene |
| image4 | 37 | image | Fourth character/scene |
| image5 | 38 | image | Fifth character/scene |
| image6 | 39 | image | Sixth character/scene |
| image7 | 40 | image | Seventh (rarely used) |
| image8 | 41 | image | Eighth (rarely used) |
| image9 | 42 | image | Ninth (rarely used) |

Other important nodes:

| nodeId | fieldName | Description |
|---|---|---|
| 27 | value | Duration in seconds (e.g. "15") |
| 28 | prompt | Full Ref2VA prompt text |
| 29 | aspect_ratio | Resolution (e.g. "16:9 (Widescreen)") |
| 64 | index |文武戏 setting 1 (0=文, 1=武) |
| 69 | index | 文武戏 setting 2 |

## Instance Type

| Type | VRAM | Use Case |
|---|---|---|
| `default` | 24G | Simple tasks, may OOM on complex Ref2VA |
| `plus` | 48G | **Required for Ref2VA** multi-image workflows |
| `ultra` | 84G | Maximum capacity, highest cost |

**Always use `instanceType: "plus"` for Ref2VA workflows with multiple reference images.** The `default` instance causes OOM errors.

## Ref2VA Prompt Structure

Ref2VA uses six sections in fixed order. Each section serves a specific purpose:

1. **subject_definitions** - Define each subject with reference to a Picture label
2. **summary** - One-paragraph overview with [reference generation, keyframe completion] tag
3. **retention_analysis** - Specify what to preserve/change from each reference image
4. **detailed_description** - Shot-by-shot timeline with timestamps and dialogue
5. **overall_soundscape** - Environmental audio description
6. **non_diegetic_music** - Background music description

### Dialogue Language Rules

For multilingual character settings:
- Self-talk/internal monologue: character's native language
- Dialogue with others: story setting language
- Use `<d>[Language]dialogue text</d>` tags
- No subtitles should appear in frame

### Audio Control Rules

When generating videos that require **only sound effects and human voice** (no subtitles, no background music), apply the following rules across all Ref2VA audio sections:

| Rule | Implementation |
|---|---|
| No subtitles | Do NOT include any `<d>` dialogue text as on-screen text. Dialogue exists only as audio via `<d>[Language]text</d>` in `detailed_description`. Explicitly state "No subtitles or captions appear on screen at any time." |
| No background music | Set `non_diegetic_music` to `N/A`. Do NOT describe any instrumental, score, or audience-only music. |
| Only sound effects | Describe environmental and physical sounds in `overall_soundscape` (e.g., wind, footsteps, fabric rustling, crowd murmurs, platform hum). |
| Only human voice | All dialogue goes in `detailed_description` using `<Subject N> (Sx)` speaker IDs and `<d>[Language]text</d>` tags. No narration or voice-over unless explicitly requested. |

**Template for audio-minimal prompts:**

```text
overall_soundscape: [Environmental ambience and physical sound effects only. Examples: wind across the plaza, fabric rustling, footsteps on stone, distant crowd murmurs, platform energy hum. No music instruments, no score, no audience-only audio.]

non_diegetic_music: N/A
```

**Critical**: Add this anti-subtitle clause to the end of `summary` or the beginning of `detailed_description`:
```text
No subtitles, captions, or on-screen text appear at any point in the video. All dialogue is delivered as spoken audio only.
```

## Character Consistency Across Episodes

### Three-View Reference Images

Each character should have a "three-view" (三视图) reference image showing front, side, and back views. This image is uploaded once and reused across all episodes featuring that character.

### Asset Management

Maintain an asset inventory file tracking:
- Character roster with three-view image paths
- Scene images with descriptions
- OpenAPI path mappings (content-addressed)
- Episode-to-image reference tables
- Task IDs and result paths

### Cross-Episode Anchors

Design narrative anchors that connect episodes:
- Relationship escalation patterns
- Weather/season progression
- Recurring sound motifs
- Scene geography consistency

## Workflow Checklist

1. **Story Design** - Write episode outlines with character arcs
2. **Asset Check** - Verify all character/scene images exist
3. **Image Upload** - Upload new images to RunningHub, cache openapi paths
4. **Payload Building** - Generate nodeInfoList JSON for each episode
5. **User Review** - Show payloads to user for approval before submission
6. **Batch Submission** - Submit in groups of 3 (concurrent limit), retry on 421
7. **Polling** - Query task status every 20-30 seconds
8. **Download** - Download videos immediately (24h link expiry)
9. **Cost Display** - Show consumeCoins and taskCostTime for each episode
10. **Asset Update** - Update inventory with task IDs and video paths

## API Documentation Reference

Full API documentation is available at: `应用API文档/t8lite.md` in the project workspace.
