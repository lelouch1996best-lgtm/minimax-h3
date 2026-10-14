"""临时：直接查询 RunningHub 任务真实状态（不动 run-state，不重提）。"""
import json
import sys
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, ".workbuddy", "skills", "runninghub", "scripts"))
from runninghub import require_api_key  # noqa: E402
from run_t8balance import query  # noqa: E402

TID = sys.argv[1] if len(sys.argv) > 1 else "2108800189149179906"
key = require_api_key(None)
r = query(TID, key)
print(json.dumps(r, ensure_ascii=False, indent=2))
