#!/usr/bin/env python3
"""RunningHub 自建 ComfyUI 工作流直连客户端（workflowId 版）。

用法:
  python run_workflow_api.py --info WORKFLOW_ID
  python run_workflow_api.py --run WORKFLOW_ID \
      [--node "36:prompt=文本"] \
      [--file "37:image=本地路径"] \
      [--instance plus] \
      -o 输出.mp4
"""
import argparse
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    from runninghub import resolve_api_key
    from runninghub_app import upload_file
except ImportError:
    sys.path.insert(0, str(Path.home() / ".trae-cn" / "skills" / "runninghub" / "scripts"))
    from runninghub import resolve_api_key
    from runninghub_app import upload_file

HOST = "https://www.runninghub.cn"
NODE_INFO = "/api/openapi/getJsonApiFormat"
CREATE = "/task/openapi/create"
STATUS = "/task/openapi/status"
OUTPUTS = "/task/openapi/outputs"


def curl_post_json(path, payload, timeout=60, headers=None):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        tmp = f.name
    h_args = []
    if headers:
        for k, v in headers.items():
            h_args.extend(["-H", f"{k}: {v}"])
    try:
        r = subprocess.run(
            ["curl", "-s", "-S", "--fail-with-body", "-X", "POST", HOST + path,
             "--max-time", str(timeout), "-H", "Content-Type: application/json"] +
            h_args + ["-d", f"@{tmp}"],
            capture_output=True, text=True)
    finally:
        Path(tmp).unlink()
    return r


def parse(r, ctx):
    body = r.stdout or r.stderr
    try:
        return json.loads(body)
    except (json.JSONDecodeError, TypeError):
        print(json.dumps({"error": "API_ERROR", "message": f"{ctx}: 非JSON响应 {str(body)[:400]}"},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


def get_node_info(key, wf_id):
    r = curl_post_json(NODE_INFO, {"apiKey": key, "workflowId": int(wf_id)},
                       headers={"Authorization": f"Bearer {key}"})
    resp = parse(r, "查询工作流")
    if resp.get("code") != 0:
        print(json.dumps({"error": "INFO_FAILED", "message": resp.get("msg", str(resp)[:400])},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    wf = json.loads(resp.get("data", {}).get("prompt", "{}"))
    summary = []
    for nid, node in wf.items():
        ct = node.get("class_type", "")
        if ct in ("LoadImage", "CR Prompt Text", "RandomNoise", "PrimitiveFloat", "VHS_VideoCombine",
                  "MiniMaxH3AudioConditioningT8", "UNETLoader", "LoraLoaderBypassModelOnly"):
            summary.append({"nodeId": nid, "class_type": ct,
                            "title": node.get("_meta", {}).get("title", ""),
                            "widget_fields": {k: str(v)[:60] for k, v in node.get("inputs", {}).items()
                                              if not isinstance(v, list)}})
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def create_task(key, wf_id, node_info_list, instance_type=None):
    payload = {"apiKey": key, "workflowId": int(wf_id), "nodeInfoList": node_info_list}
    if instance_type:
        payload["instanceType"] = instance_type
    r = curl_post_json(CREATE, payload)
    resp = parse(r, "创建任务")
    if resp.get("code") != 0:
        print(json.dumps({"error": "CREATE_FAILED", "message": resp.get("msg", str(resp)[:400])},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    task_id = resp.get("data", {}).get("taskId")
    print(f"task created: {task_id}", file=sys.stderr)
    return task_id


def wait_task(key, task_id, max_min=25):
    deadline = time.time() + max_min * 60
    last = ""
    while time.time() < deadline:
        r = curl_post_json(STATUS, {"apiKey": key, "taskId": task_id})
        resp = parse(r, "查询状态")
        if resp.get("code") != 0:
            print(f"status error: {resp.get('msg')}", file=sys.stderr)
            time.sleep(15)
            continue
        state = resp.get("data") or "?"
        line = f"status={state}"
        if line != last:
            print(f"  {line}", file=sys.stderr)
            last = line
        if state == "SUCCESS":
            return {"taskStatus": "SUCCESS"}
        if state in ("FAILED", "CANCEL", "ERROR"):
            r2 = curl_post_json(OUTPUTS, {"apiKey": key, "taskId": task_id})
            reason = ""
            try:
                d2 = json.loads(r2.stdout or "{}").get("data", {})
                reason = str(d2.get("failedReason", ""))[:500]
            except (json.JSONDecodeError, TypeError):
                pass
            print(json.dumps({"error": "TASK_FAILED", "message": state, "reason": reason},
                             ensure_ascii=False), file=sys.stderr)
            sys.exit(1)
        time.sleep(15)
    print(json.dumps({"error": "TIMEOUT"}, ensure_ascii=False), file=sys.stderr)
    sys.exit(1)


def download_outputs(key, task_id, out_path):
    r = curl_post_json(OUTPUTS, {"apiKey": key, "taskId": task_id})
    resp = parse(r, "获取结果")
    if resp.get("code") != 0:
        print(json.dumps({"error": "OUTPUT_FAILED", "message": resp.get("msg")}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
    urls = resp.get("data", [])
    files = []
    for i, item in enumerate(urls if isinstance(urls, list) else [urls]):
        u = item.get("fileUrl") if isinstance(item, dict) else item
        p = out_path if len(urls) == 1 else str(Path(out_path).with_name(f"{Path(out_path).stem}_{i+1}{Path(out_path).suffix}"))
        subprocess.run(["curl", "-s", "-S", "--fail-with-body", "-L", "-o", p, u], check=True)
        files.append(p)
        print(f"downloaded: {p}", file=sys.stderr)
    return files


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--info", dest="info_id")
    ap.add_argument("--run", dest="run_id")
    ap.add_argument("--node", action="append", default=[])
    ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--instance", default=None)
    ap.add_argument("-o", "--output")
    a = ap.parse_args()

    key = resolve_api_key(None)
    if not key:
        print("未找到 RunningHub API Key", file=sys.stderr)
        sys.exit(1)

    if a.info_id:
        get_node_info(key, a.info_id)
        return
    if not a.run_id:
        print("需要 --info 或 --run", file=sys.stderr)
        sys.exit(1)
    if not a.output:
        print("需要 -o 输出路径", file=sys.stderr)
        sys.exit(1)

    node_list = []
    for spec in a.node:
        node_id, field, value = spec.split(":", 2)
        node_list.append({"nodeId": node_id, "fieldName": field, "fieldValue": value})
    for spec in a.file:
        node_id, field, path = spec.split(":", 2)
        fname = upload_file(key, path)
        node_list.append({"nodeId": node_id, "fieldName": field, "fieldValue": fname})
    print(f"nodeInfoList: {json.dumps(node_list, ensure_ascii=False)[:300]}", file=sys.stderr)

    task_id = create_task(key, a.run_id, node_list, instance_type=a.instance)
    d = wait_task(key, task_id)
    print(json.dumps({"taskId": task_id, "elapsed": d.get("taskCostTime"), "credits": d.get("taskCredits")},
                     ensure_ascii=False), file=sys.stderr)
    files = download_outputs(key, task_id, a.output)
    for f in files:
        print(f"OUTPUT_FILE:{f}")


if __name__ == "__main__":
    main()
