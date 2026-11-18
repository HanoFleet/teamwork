"""Isolated gate orchestration and read-only environment inventory."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
RESULTS = OUT / "results.jsonl"
ENV = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
       "QA_TOOL_NODE": "E:/node.exe", "QA_TOOL_NPM_CLI": "E:/node_modules/npm/bin/npm-cli.js",
       "QA_TOOL_PYTHON": sys.executable, "npm_config_registry": "https://registry.npmjs.org",
       "GODEBUG": "http2client=0", "MSYS_NO_PATHCONV": "1"}
ENV["PATH"] = str(ROOT / "tests/.runtime/windows-command-adapters") + os.pathsep + "F:/Git/bin" + os.pathsep + "E:/" + os.pathsep + ENV["PATH"]


def run(name, command, timeout=120, env=None, cwd=ROOT):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        result = subprocess.run(command, cwd=cwd, env=env or ENV, capture_output=True, timeout=timeout)
        output = result.stdout + result.stderr
        code = result.returncode
    except subprocess.TimeoutExpired as error:
        output = (error.stdout or b"") + (error.stderr or b"") + b"\nTIMEOUT"
        code = 124
    except OSError as error:
        output = str(error).encode()
        code = 127
    (OUT / (name + ".log")).write_bytes(output)
    row = dict(name=name, command=command, exit_code=code, started=start,
               finished=datetime.datetime.now(datetime.timezone.utc).isoformat(), log=name + ".log")
    with RESULTS.open("a", encoding="utf-8") as log:
        log.write(json.dumps(row) + "\n")
    print(name, "exit", code, flush=True)
    return code


def preflight():
    run("docker-info", ["docker", "info", "--format", "{{json .ServerVersion}}"])
    run("docker-ps-before", ["docker", "ps", "-a", "--format", "{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Label \"com.docker.compose.project\"}}"])
    run("docker-networks-before", ["docker", "network", "ls", "--format", "{{.ID}}\t{{.Name}}"])
    run("acceptance-project-before", ["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=campusclaw-acceptance"])
    run("frontend-check-tag-before", ["docker", "image", "inspect", "campusclaw-frontend-check", "--format", "{{.Id}}"])
    run("docker-images", ["docker", "image", "ls", "--format", "{{.Repository}}:{{.Tag}}\t{{.ID}}"])
    run("node-version", ["E:/node.exe", "--version"])
    run("npm-version", [str(ROOT / "tests/.runtime/windows-command-adapters/npm.exe"), "--version"])
    run("python-version", [sys.executable, "--version"])
    run("make-version", ["mingw32-make", "--version"])
    info = dict(env_exists=(ROOT / ".env").exists(), acceptance_env_exists=(ROOT / ".env.acceptance").exists(),
                mutation_path_exists=(ROOT / "backend/internal/httpapi/zz_violation.go").exists(),
                chrome_exists=Path("C:/Program Files/Google/Chrome/Application/chrome.exe").exists(),
                shell_exists=Path("F:/Git/bin/sh.exe").exists())
    (OUT / "conditions.json").write_text(json.dumps(info, indent=2), encoding="utf-8")


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "preflight":
        preflight()
    elif mode == "check":
        run("make-check", ["mingw32-make", "check"], timeout=1800)
    elif mode == "security":
        run("make-check-security", ["mingw32-make", "check-security"], timeout=900)
    elif mode == "grade":
        assert not (ROOT / ".env.acceptance").exists()
        assert not subprocess.check_output(["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=campusclaw-acceptance"]).strip()
        run("make-grade", ["mingw32-make", "grade"], timeout=1200)
    elif mode == "contracts":
        run("latency-contracts", [sys.executable, "-X", "utf8", "-W", "error::ResourceWarning", "tests/performance/latency_gate_contract.py"])

    elif mode == "grade-retry":
        assert not (ROOT / ".env.acceptance").exists()
        assert not subprocess.check_output(["docker", "ps", "-aq", "--filter", "label=com.docker.compose.project=campusclaw-acceptance"]).strip()
        import ipaddress
        ids = subprocess.check_output(["docker", "network", "ls", "-q"], text=True).split()
        networks = json.loads(subprocess.check_output(["docker", "network", "inspect", *ids]))
        selected = ipaddress.ip_network("10.254.2.0/24")
        occupied = [ipaddress.ip_network(c["Subnet"]) for n in networks for c in (n.get("IPAM", {}).get("Config") or []) if c.get("Subnet")]
        assert not any(selected.overlaps(n) for n in occupied if n.version == 4)
        overlay = OUT / "grade-network-retry.json"
        with overlay.open("x", encoding="utf-8") as output:
            json.dump({"services": {name: {"build": {"args": {"GOPROXY": "https://goproxy.cn,direct"}}} for name in ["api", "worker"]}, "networks": {"default": {"ipam": {"config": [{"subnet": str(selected)}]}}}}, output, indent=2)
        env = {**ENV, "COMPOSE_FILE": os.pathsep.join([str(ROOT / "docker-compose.yml"), str(overlay)])}
        run("make-grade-network-retry", ["mingw32-make", "grade"], timeout=1200, env=env)
