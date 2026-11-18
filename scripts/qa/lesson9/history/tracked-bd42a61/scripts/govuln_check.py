#!/usr/bin/env python3
"""第 9 课 Go 依赖门禁。

有 Go 或可用的 Docker 时，用 Go 1.26.11 跑 govulncheck，出现通报就退出 1。
两者都没有时，核对已提交的扫描快照和 backend/go.sum 是否仍是同一次扫描。
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
SNAPSHOT = ROOT / "reports" / "govuln-snapshot.txt"
TOOLCHAIN = "go1.26.11"
GOVULN = "golang.org/x/vuln/cmd/govulncheck@v1.9.0"
CLEAN = "No vulnerabilities found."


def gosum_sha256() -> str:
    return hashlib.sha256((BACKEND / "go.sum").read_bytes()).hexdigest()


def run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = None
    if env is not None:
        merged = os.environ.copy()
        merged.update(env)
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, env=merged)


def docker_ready() -> bool:
    if shutil.which("docker") is None:
        return False
    proc = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return proc.returncode == 0


def live_scan() -> subprocess.CompletedProcess[str] | None:
    env = {
        "GOTOOLCHAIN": TOOLCHAIN,
        "GOPROXY": "https://goproxy.cn,direct",
        "GOSUMDB": "sum.golang.org",
    }
    go = shutil.which("go")
    if go:
        print(f"$ GOTOOLCHAIN={TOOLCHAIN} go run {GOVULN} ./...")
        return run([go, "run", GOVULN, "./..."], BACKEND, env)
    if docker_ready():
        print(f"$ docker run golang:{TOOLCHAIN.removeprefix('go')}-alpine go run {GOVULN} ./...")
        return run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{BACKEND}:/src",
                "-w",
                "/src",
                "-e",
                f"GOTOOLCHAIN={TOOLCHAIN}",
                "-e",
                "GOPROXY=https://goproxy.cn,direct",
                "-e",
                "GOSUMDB=sum.golang.org",
                f"golang:{TOOLCHAIN.removeprefix('go')}-alpine",
                "go",
                "run",
                GOVULN,
                "./...",
            ],
            ROOT,
        )
    return None


def snapshot_ok() -> bool:
    if not SNAPSHOT.is_file():
        print("缺少 reports/govuln-snapshot.txt，且本机没有 Go 或 Docker，无法复扫", file=sys.stderr)
        return False
    text = SNAPSHOT.read_text(encoding="utf-8")
    digest = gosum_sha256()
    if f"gosum_sha256={digest}" not in text:
        print("backend/go.sum 已变化，已归档的 govulncheck 快照不能继续当作证据", file=sys.stderr)
        return False
    if CLEAN not in text or f"toolchain={TOOLCHAIN}" not in text:
        print("govulncheck 快照不是 Go 1.26.11 的零通报结果", file=sys.stderr)
        return False
    print(text.strip())
    print("GOVULN CHECK PASSED: 使用与 go.sum 匹配的零通报快照")
    return True


def main() -> int:
    proc = live_scan()
    if proc is None:
        return 0 if snapshot_ok() else 1
    output = "\n".join(part.strip() for part in (proc.stdout, proc.stderr) if part.strip())
    if output:
        print(output)
    print(f"exit={proc.returncode}")
    if proc.returncode != 0 or CLEAN not in proc.stdout:
        print("GOVULN CHECK FAILED: govulncheck 发现通报或没有跑完", file=sys.stderr)
        return 1
    print("GOVULN CHECK PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
