#!/usr/bin/env python3
import base64
import json
import os
import sys
import time
import urllib.request
import urllib.error

API_KEY = os.environ.get("S65535_API_KEY", "")
API_BASE = "https://task-api-1-cn.65535.space"

def encode_image(path):
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/png;base64,{data}"

def submit_task(image_data_uri, prompt, model="gpt-image-2", size="16:9", resolution="2k"):
    payload = {
        "kind": "image",
        "model": model,
        "input": {
            "prompt": prompt,
            "image": image_data_uri,
            "size": size,
            "resolution": resolution,
            "n": 1
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{API_BASE}/v1/tasks",
        data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result.get("id")

def poll_task(task_id, interval=2, timeout=600):
    start = time.time()
    while time.time() - start < timeout:
        req = urllib.request.Request(
            f"{API_BASE}/v1/tasks/{task_id}",
            headers={"Authorization": f"Bearer {API_KEY}"}
        )
        try:
            with urllib.request.urlopen(req) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            print(f"Poll error: {e}", file=sys.stderr)
            time.sleep(interval)
            continue

        status = result.get("status", "unknown")
        print(f"Status: {status}")
        sys.stdout.flush()

        if status == "done":
            return result
        elif status == "failed":
            error_code = result.get("error_code", "unknown")
            error_msg = result.get("error_message", "unknown")
            print(f"Task failed: {error_code} - {error_msg}", file=sys.stderr)
            sys.exit(1)

        time.sleep(interval)

    print("Timeout waiting for task", file=sys.stderr)
    sys.exit(1)

def download_image(url, output_path):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
    with open(output_path, "wb") as f:
        f.write(data)
    return output_path

def main():
    if not API_KEY:
        print("Error: S65535_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    image_path = sys.argv[1]
    output_path = sys.argv[2]
    prompt = sys.argv[3]
    model = sys.argv[4] if len(sys.argv) > 4 else "gpt-image-2"
    size = sys.argv[5] if len(sys.argv) > 5 else "16:9"
    resolution = sys.argv[6] if len(sys.argv) > 6 else "2k"

    print("Encoding reference image...")
    sys.stdout.flush()
    img_data = encode_image(image_path)

    print(f"Submitting task with model {model}, size {size}...")
    sys.stdout.flush()
    task_id = submit_task(img_data, prompt, model, size, resolution)
    print(f"Task ID: {task_id}")
    sys.stdout.flush()

    print("Polling for result...")
    sys.stdout.flush()
    result = poll_task(task_id)

    result_urls = result.get("result_urls", [])
    if result_urls:
        url = result_urls[0]
        print(f"Downloading result to {output_path}...")
        download_image(url, output_path)
        print(f"OUTPUT_FILE:{output_path}")
    else:
        data_list = result.get("result", {}).get("data", [])
        if data_list and "b64_json" in data_list[0]:
            b64 = data_list[0]["b64_json"]
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(b64))
            print(f"OUTPUT_FILE:{output_path}")
        else:
            print("No output found in result", file=sys.stderr)
            print(json.dumps(result, indent=2), file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
