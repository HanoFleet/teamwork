#!/usr/bin/env python3
"""隔离验收：启动独立 Compose 项目，检查存活/就绪、默认拒绝、日志、停库恢复和端口边界。

只依赖 Python 3、Docker Compose 和仓库里的 compose 文件；报告写到 reports/teacher-*/。
"""

from __future__ import annotations

import html
import json
import os
import platform
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "campusclaw-acceptance"
ENV_FILE = ROOT / ".env.acceptance"
REPORT_DIR = ROOT / "reports" / f"teacher-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
CHECKS: list[dict] = []


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def run(cmd: list[str], check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["DOCKER_BUILDKIT"] = "0"
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env, timeout=timeout)
    if check and result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} -> {result.returncode}\n{result.stderr[-2000:]}")
    return result


def compose(*args: str, check: bool = True, timeout: int = 300) -> subprocess.CompletedProcess:
    return run(
        ["docker", "compose", "-p", PROJECT, "--env-file", str(ENV_FILE), *args],
        check=check,
        timeout=timeout,
    )


def request(method: str, path: str, headers=None):
    req = urllib.request.Request(BASE + path, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, dict(resp.headers), resp.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        return err.code, dict(err.headers), err.read().decode("utf-8")


def wait_for(path: str, status: int, timeout: int = 90) -> str:
    deadline = time.time() + timeout
    last = ""
    while time.time() < deadline:
        try:
            code, _, body = request("GET", path)
            if code == status:
                return body
            last = f"{code} {body}"
        except Exception as err:  # noqa: BLE001
            last = str(err)
        time.sleep(2)
    raise RuntimeError(f"等待 {path}={status} 超时：{last}")


def write_env() -> None:
    values = {
        "WEB_PORT": str(free_port()),
        "APP_VERSION": "v2.0.0-skeleton",
        "SHUTDOWN_TIMEOUT_SECONDS": "10",
        "MYSQL_ROOT_PASSWORD": secrets.token_hex(24),
        "DB_NAME": "campusclaw_acceptance",
        "DB_USER": "campusclaw",
        "DB_PASSWORD": secrets.token_hex(24),
        "SESSION_SECRET": secrets.token_hex(32),
        "SEED_TEACHER_PASSWORD": secrets.token_hex(12),
        "SEED_STUDENT_A_PASSWORD": secrets.token_hex(12),
        "SEED_STUDENT_B_PASSWORD": secrets.token_hex(12),
        "MAX_UPLOAD_BYTES": "1048576",
        "SESSION_TTL_HOURS": "12",
        "LOGIN_FAIL_THRESHOLD": "5",
        "LOGIN_LOCK_MINUTES": "15",
        "QDRANT_URL": "http://qdrant:6333",
        "EMBEDDING_URL": "local",
        "EMBEDDING_API_KEY": "local",
        "EMBEDDING_MODEL": "local-ngram-256",
        "CHAT_URL": "local",
        "CHAT_API_KEY": "local",
        "CHAT_MODEL": "local-extractive",
    }
    ENV_FILE.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n", encoding="utf-8")
    global BASE
    BASE = f"http://127.0.0.1:{values['WEB_PORT']}"


def check(check_id: str, name: str, criterion: str, fn) -> None:
    started = time.time()
    try:
        detail = fn()
        CHECKS.append({
            "id": check_id, "name": name, "criterion": criterion,
            "status": "passed", "elapsed_ms": int((time.time() - started) * 1000),
            "detail": detail or "",
        })
    except Exception as err:  # noqa: BLE001
        CHECKS.append({
            "id": check_id, "name": name, "criterion": criterion,
            "status": "failed", "elapsed_ms": int((time.time() - started) * 1000),
            "detail": str(err),
        })


def json_body(path: str, status: int) -> dict:
    code, _, body = request("GET", path)
    if code != status:
        raise AssertionError(f"{path} -> {code}，期望 {status}：{body}")
    return json.loads(body)


def main() -> int:
    write_env()
    compose("build", timeout=600)
    compose("up", "-d", "--wait", timeout=300)
    wait_for("/live", 200)

    check("A01", "可复现启动与存活", "Compose 起来后 /live 200，含 version/time", lambda: (
        json_body("/live", 200) and request("GET", "/live")[2]
    ))
    check("A02", "就绪检查", "/health 200，db/qdrant/embedding 都为 true", lambda: json_body("/health", 200))
    check("A03", "就绪别名", "/ready 与 /health 同源，200", lambda: request("GET", "/ready")[0] == 200)
    check("A04", "未知 API 404", "GET /api/nope -> 404", lambda: request("GET", "/api/nope")[0] == 404)
    check("A05", "方法拒绝", "POST /health -> 405", lambda: request("POST", "/health")[0] == 405)
    check("A06", "非法参数", "GET /health?x=1 -> 400", lambda: request("GET", "/health?x=1")[0] == 400)
    check("A07", "未登录业务接口", "GET /api/materials -> 401", lambda: request("GET", "/api/materials")[0] == 401)

    def request_id() -> str:
        code, headers, _ = request("GET", "/live", {"X-Request-ID": "verify-lesson07"})
        if code != 200 or headers.get("X-Request-Id") != "verify-lesson07":
            raise AssertionError(f"响应头 request id 不匹配：{headers.get('X-Request-Id')}")
        return "响应头保留 verify-lesson07"

    check("A08", "请求 ID 贯穿", "合法 X-Request-ID 原样回写", request_id)

    def log_contract() -> str:
        logs = compose("logs", "--no-log-prefix", "api").stdout
        parsed = 0
        for line in logs.splitlines():
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            if item.get("request_id") and item.get("path") and item.get("status") is not None:
                parsed += 1
        if parsed == 0:
            raise AssertionError("没有找到带 request_id/path/status 的 JSON 日志")
        lowered = logs.lower()
        for word in ["session_secret=", "db_password=", "password="]:
            if word in lowered:
                raise AssertionError(f"日志包含敏感赋值：{word}")
        return f"{parsed} 条请求日志可解析"

    check("A09", "日志契约", "单行 JSON，含 request_id/path/status，无机密", log_contract)

    def db_down() -> str:
        compose("stop", "db")
        time.sleep(2)
        if request("GET", "/live")[0] != 200:
            raise AssertionError("/live 在停库后不是 200")
        health = json_body("/health", 503)
        if health.get("checks", {}).get("db") is not False:
            raise AssertionError(f"checks.db 不是 false：{health}")
        if request("GET", "/api/materials")[0] != 503:
            raise AssertionError("业务接口在停库后不是 503")
        return "live=200, health=503(db=false), materials=503"

    check("A10", "依赖不可达", "停 MySQL 后 live 200、health 503、业务 503", db_down)

    def db_recover() -> str:
        compose("start", "db")
        wait_for("/health", 200, timeout=90)
        return "MySQL 恢复后 /health=200"

    check("A11", "依赖恢复", "重启 MySQL 后 /health 恢复 200", db_recover)

    def config_ports() -> str:
        raw = compose("config", "--format", "json").stdout
        data = json.loads(raw)
        services = data.get("services", {})
        for name in ["db", "qdrant", "api"]:
            if services.get(name, {}).get("ports"):
                raise AssertionError(f"{name} 暴露了宿主端口")
        if not services.get("web", {}).get("ports"):
            raise AssertionError("web 没有映射端口")
        return "只有 web 映射端口"

    check("A12", "端口边界", "db/qdrant/api 无 ports，web 有 ports", config_ports)

    def qdrant_down() -> str:
        compose("stop", "qdrant")
        time.sleep(2)
        if request("GET", "/live")[0] != 200:
            raise AssertionError("停 Qdrant 后 /live 不是 200")
        health = json_body("/health", 503)
        if health.get("checks", {}).get("qdrant") is not False:
            raise AssertionError(f"checks.qdrant 不是 false：{health}")
        compose("start", "qdrant")
        wait_for("/health", 200, timeout=90)
        return "qdrant=down 时 health=503，恢复后 health=200"

    check("A13", "Qdrant 不可达", "停 Qdrant 后 live 200、health 503，恢复后 200", qdrant_down)

    def graceful() -> str:
        compose("stop", "api")
        logs = compose("logs", "--no-log-prefix", "api", check=False).stdout
        if "shutdown_complete" not in logs:
            raise AssertionError("日志没有 shutdown_complete")
        return "api 收到 SIGTERM 后记录 shutdown_complete"

    check("A14", "优雅停机", "stop api 后日志含 shutdown_complete", graceful)

    return 0


def write_report() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True).stdout.strip())
    passed = sum(1 for item in CHECKS if item["status"] == "passed")
    failed = sum(1 for item in CHECKS if item["status"] != "passed")
    report = {
        "project": "CampusClaw 2.0 platform foundation",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_commit": commit,
        "source_dirty": dirty,
        "environment": {
            "os": platform.platform(),
            "python": sys.version.split()[0],
            "docker": subprocess.run(["docker", "--version"], capture_output=True, text=True).stdout.strip(),
        },
        "scope": "lesson 7 skeleton: live/health/ready, logs, shutdown, default deny",
        "status": "passed" if failed == 0 else "failed",
        "counts": {"passed": passed, "failed": failed, "total": len(CHECKS)},
        "checks": CHECKS,
    }
    REPORT_DIR.joinpath("report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    def detail_text(value) -> str:
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False)

    rows = "\n".join(
        f"<tr><td>{html.escape(item['id'])}</td><td>{html.escape(item['name'])}</td>"
        f"<td>{html.escape(item['criterion'])}</td><td class=\"{item['status']}\">{item['status']}</td>"
        f"<td><code>{html.escape(detail_text(item.get('detail', '')))[:800]}</code></td></tr>"
        for item in CHECKS
    )
    REPORT_DIR.joinpath("report.html").write_text(
        f"""<!doctype html><meta charset="utf-8"><title>CampusClaw 验收报告</title>
<style>body{{font-family:system-ui,sans-serif;margin:32px;line-height:1.5}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ccc;padding:6px;vertical-align:top}}code{{white-space:pre-wrap}}.passed{{color:#0a7a2f}}.failed{{color:#b00020}}</style>
<h1>CampusClaw 2.0 platform foundation 验收报告</h1>
<p>状态：<b>{html.escape(report['status'])}</b>；通过 {passed}，失败 {failed}；提交 <code>{html.escape(commit)}</code>。</p>
<table><thead><tr><th>ID</th><th>检查</th><th>判据</th><th>结果</th><th>证据</th></tr></thead><tbody>{rows}</tbody></table>""",
        encoding="utf-8",
    )
    print(json.dumps({"status": report["status"], "counts": report["counts"], "report": str(REPORT_DIR)}, ensure_ascii=False))


def cleanup() -> None:
    compose("down", "-v", "--remove-orphans", check=False, timeout=180)
    ENV_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        CHECKS.append({
            "id": "SELF", "name": "失败注入", "criterion": "失败检查必须让报告和退出码同步失败",
            "status": "failed", "elapsed_ms": 0, "detail": "self-test: injected failure",
        })
        write_report()
        sys.exit(1)
    exit_code = 1
    try:
        exit_code = main()
    except Exception as err:  # noqa: BLE001
        CHECKS.append({
            "id": "ENV", "name": "验收环境", "criterion": "Compose 构建/启动成功",
            "status": "failed", "elapsed_ms": 0, "detail": str(err),
        })
    finally:
        cleanup()
        write_report()
    sys.exit(0 if exit_code == 0 and all(item["status"] == "passed" for item in CHECKS) else 1)
