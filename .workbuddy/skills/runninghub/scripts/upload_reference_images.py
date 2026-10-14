#!/usr/bin/env python3
"""上传本地参考图到 RunningHub，输出 LoadImage 可用的 api/ 路径映射。

用法:
  python upload_reference_images.py <图片1> [图片2 ...]
输出:
  JSON { "<本地路径>": "<api/xxx.png>" }
"""
import json
import sys
from pathlib import Path

try:
    from runninghub import resolve_api_key
    from runninghub_app import upload_file
except ImportError:
    # 命令行独立运行时自动定位 runninghub skill 脚本目录
    sys.path.insert(0, str(Path.home() / ".trae-cn" / "skills" / "runninghub" / "scripts"))
    from runninghub import resolve_api_key
    from runninghub_app import upload_file


def main():
    if len(sys.argv) < 2:
        print("用法: python upload_reference_images.py <图片1> [图片2 ...]", file=sys.stderr)
        sys.exit(1)

    api_key = resolve_api_key(None)
    mapping = {}
    for path in sys.argv[1:]:
        p = Path(path)
        if not p.exists():
            print(f"Error: file not found: {path}", file=sys.stderr)
            sys.exit(1)
        file_name = upload_file(api_key, str(p))
        mapping[str(p)] = file_name

    print(json.dumps(mapping, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
