#!/usr/bin/env python3
"""分层静态检查：新代码不得在接口层写 SQL。

现有 auth.go / materials.go / server.go 是迭代 1/2 遗留，登记为例外；
新增的 httpapi 文件一旦出现 SQL，检查失败。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTTPAPI = ROOT / "backend" / "internal" / "httpapi"
LEGACY = {"auth.go", "materials.go", "server.go"}
SQL = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|REPLACE)\b", re.IGNORECASE)

failures: list[str] = []


def main() -> int:
    if not HTTPAPI.is_dir():
        print(f"缺少接口层目录：{HTTPAPI}", file=sys.stderr)
        return 1

    for path in sorted(HTTPAPI.glob("*.go")):
        if path.name in LEGACY:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            if SQL.search(line):
                failures.append(f"{path.relative_to(ROOT)}:{number}: {stripped}")

    if failures:
        print("接口层出现 SQL（新增代码必须放数据访问层）：", file=sys.stderr)
        for item in failures:
            print(f"  ✗ {item}", file=sys.stderr)
        return 1

    print("分层检查通过：新增 httpapi 代码没有 SQL；遗留文件已登记为例外。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
