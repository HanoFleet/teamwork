#!/usr/bin/env python3
"""证明分层门禁真的会失败：临时注入 SQL，检查失败后还原。"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIOLATION = ROOT / "backend" / "internal" / "httpapi" / "zz_violation.go"


def run() -> int:
    return subprocess.run([sys.executable, "scripts/layer_check.py"], cwd=ROOT).returncode


def main() -> int:
    VIOLATION.write_text('package httpapi\n\nconst violation = "SELECT * FROM users"\n', encoding="utf-8")
    try:
        injected = run()
    finally:
        VIOLATION.unlink(missing_ok=True)
    restored = run()
    if injected == 0:
        print("变异检查失败：注入 SQL 后门禁仍然通过。", file=sys.stderr)
        return 1
    if restored != 0:
        print("变异检查失败：还原后门禁没有恢复通过。", file=sys.stderr)
        return 1
    print("变异检查通过：注入 SQL 时失败，还原后通过。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
