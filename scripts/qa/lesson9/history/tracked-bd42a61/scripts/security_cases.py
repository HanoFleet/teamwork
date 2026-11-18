#!/usr/bin/env python3
"""加载第 9 课三条注入反例，并在 make check 里执行不依赖 Compose 的部分。

在线请求由 scripts/security_test.py 调用同一份 case.json。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CASES = (
    ("apitest/cases/api/search/POST/case.json", "sqli"),
    ("apitest/cases/api/materials/POST/case.json", "xss"),
    ("apitest/cases/api/skills/grade/PATCH/case.json", "csrf"),
)
FIELDS = ("id", "title", "kind", "precondition", "operation", "expected")
RAW_HTML = ("rehype-raw", "dangerouslySetInnerHTML")
FRONTEND = (
    "frontend/src/App.tsx",
    "frontend/src/Assignments.tsx",
    "frontend/src/Ask.tsx",
    "frontend/src/api.ts",
)


def load_cases() -> list[dict[str, str]]:
    loaded: list[dict[str, str]] = []
    for rel, kind in CASES:
        path = ROOT / rel
        if not path.is_file():
            raise SystemExit(f"缺少注入反例：{rel}")
        data = json.loads(path.read_text(encoding="utf-8"))
        for field in FIELDS:
            if not str(data.get(field, "")).strip():
                raise SystemExit(f"{rel} 缺少三段式字段 {field}")
        if data["kind"] != kind:
            raise SystemExit(f"{rel} 的 kind 应为 {kind}")
        data["path"] = rel
        loaded.append(data)
    return loaded


def assert_static_xss() -> None:
    for rel in FRONTEND:
        text = (ROOT / rel).read_text(encoding="utf-8")
        for token in RAW_HTML:
            if token in text:
                raise SystemExit(f"{rel} 含有 {token}")
        if "campusclaw_token" in text:
            raise SystemExit(f"{rel} 仍保存登录 token")
    api = (ROOT / "frontend/src/api.ts").read_text(encoding="utf-8")
    if "localStorage.setItem" in api:
        raise SystemExit("api.ts 仍把 token 写入 localStorage")


def main() -> int:
    cases = load_cases()
    assert_static_xss()
    for case in cases:
        print(f"PASS {case['kind']} {case['path']}")
        print(f"  前置：{case['precondition']}")
        print(f"  操作：{case['operation']}")
        print(f"  期望：{case['expected']}")
    print("注入反例文件与静态 XSS 检查通过。在线三段式由 python3 scripts/verify.py 执行。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
