#!/usr/bin/env python3
"""第 9 课静态安全回归：前端 raw HTML / localStorage token / 测试文件。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
failures: list[str] = []

for rel in ("frontend/src/App.tsx", "frontend/src/Assignments.tsx", "frontend/src/Ask.tsx"):
    path = ROOT / rel
    if not path.is_file():
        failures.append(f"缺少 {rel}")
        continue
    text = path.read_text(encoding="utf-8")
    if "rehype-raw" in text or "dangerouslySetInnerHTML" in text:
        failures.append(f"{rel} 使用 raw HTML")
    if "campusclaw_token" in text:
        failures.append(f"{rel} 仍引用 localStorage token")

api = ROOT / "frontend/src/api.ts"
if not api.is_file():
    failures.append("缺少 frontend/src/api.ts")
else:
    text = api.read_text(encoding="utf-8")
    if "campusclaw_token" in text or "localStorage.setItem" in text:
        failures.append("api.ts 仍保存 token")
    if "X-CSRF-Token" not in text:
        failures.append("api.ts 没有发送 X-CSRF-Token")

for rel in ("scripts/security_test.py", "apitest/cases/security/README.md"):
    if not (ROOT / rel).is_file():
        failures.append(f"缺少 {rel}")

if failures:
    print("静态安全回归失败：", file=sys.stderr)
    for item in failures:
        print(f"  ✗ {item}", file=sys.stderr)
    sys.exit(1)
print("静态安全回归通过：无 raw HTML、无 localStorage token、CSRF/用例文件存在。")
