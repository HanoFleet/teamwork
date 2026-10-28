#!/usr/bin/env python3
"""密钥边界检查：工作树和全部提交历史里不能出现非空 .env 赋值。"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(
    r"^(SESSION_SECRET|DB_PASSWORD|MYSQL_ROOT_PASSWORD|SEED_[A-Z_]*PASSWORD)=(\S+)\s*$",
    re.MULTILINE,
)
SKIP_SUFFIXES = {".zip", ".png", ".jpg", ".jpeg", ".gif", ".pdf", ".docx", ".woff", ".woff2"}


def main() -> int:
    findings: list[str] = []

    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    for raw in files:
        if not raw:
            continue
        path = ROOT / raw.decode("utf-8", errors="replace")
        if path.suffix.lower() in SKIP_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for match in PATTERN.finditer(text):
            key = match.group(1)
            if match.group(2) in {"${" + key + "}", ""}:
                continue
            findings.append(f"{path.relative_to(ROOT)}: {key} 有非空值")

    history = subprocess.run(
        ["git", "log", "--all", "-p", "--no-color", "--", ".", ":!*.md", ":!*.example", ":!*.zip"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        errors="replace",
    ).stdout
    for match in PATTERN.finditer(history):
        key = match.group(1)
        value = match.group(2)
        if value.startswith("${") or value in {"<redacted>", "..."}:
            continue
        findings.append(f"Git 历史中出现非空赋值：{key}")

    if findings:
        print("密钥边界检查失败：", file=sys.stderr)
        for item in findings:
            print(f"  ✗ {item}", file=sys.stderr)
        return 1
    print("密钥边界检查通过：工作树和提交历史都没有非空密钥赋值。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
