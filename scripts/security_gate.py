#!/usr/bin/env python3
"""第 9 课资产门禁：密钥扫描 + 前端依赖审计。

--self-test 在临时 git 仓库制造真实密钥命中，证明门禁会退出非 0；正常模式
对当前仓库运行，全部通过才退出 0。输出可原样贴入 reports/gate-red-green.md。
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd or ROOT, text=True, capture_output=True)


def print_result(label: str, proc: subprocess.CompletedProcess[str]) -> None:
    print(f"$ {label}")
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.stderr.strip():
        print(proc.stderr.strip())
    print(f"exit={proc.returncode}")


def temp_repo(with_secret: bool) -> tuple[tempfile.TemporaryDirectory[str], Path]:
    tmp = tempfile.TemporaryDirectory(prefix="campusclaw-gate-")
    root = Path(tmp.name)
    scripts = root / "scripts"
    scripts.mkdir()
    shutil.copy2(ROOT / "scripts" / "secret_scan.py", scripts / "secret_scan.py")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "gate@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "security-gate"], cwd=root, check=True)
    if with_secret:
        (root / "leak.env").write_text("SESSION_SECRET=gate-self-test-secret\n")
    else:
        (root / "safe.env").write_text("SAFE_VALUE=ok\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "gate self-test"], cwd=root, check=True)
    return tmp, root


def self_test() -> int:
    red_tmp, red_root = temp_repo(True)
    try:
        red = run([sys.executable, "scripts/secret_scan.py"], red_root)
        print_result("临时仓库：带假 SESSION_SECRET", red)
        if red.returncode == 0:
            print("SELF-TEST FAILED: 假密钥没有被拦截")
            return 1
    finally:
        red_tmp.cleanup()
    green_tmp, green_root = temp_repo(False)
    try:
        green = run([sys.executable, "scripts/secret_scan.py"], green_root)
        print_result("临时仓库：干净", green)
        if green.returncode != 0:
            print("SELF-TEST FAILED: 干净仓库被误判")
            return 1
    finally:
        green_tmp.cleanup()
    print("SELF-TEST PASSED: 先红后绿")
    return 0


def main() -> int:
    if "--self-test" in sys.argv[1:]:
        return self_test()
    secret = run([sys.executable, "scripts/secret_scan.py"])
    print_result("python3 scripts/secret_scan.py", secret)
    if secret.returncode != 0:
        print("SECURITY GATE FAILED: 密钥扫描命中或执行失败")
        return 1
    audit = run(["npm", "audit", "--audit-level=high"], ROOT / "frontend")
    print_result("npm audit --audit-level=high", audit)
    if audit.returncode != 0:
        print("SECURITY GATE FAILED: 前端依赖存在高危/严重漏洞或审计失败")
        return 1
    print("SECURITY GATE PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
