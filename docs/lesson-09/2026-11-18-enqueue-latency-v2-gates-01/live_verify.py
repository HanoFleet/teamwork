"""Run unchanged verify assertions and copied E2E sources against a new owned project."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import traceback
import uuid
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / sys.argv[1]
OUT.mkdir(exist_ok=False)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_checks
run_checks.OUT = OUT
run_checks.RESULTS = OUT / "results.jsonl"
from run_checks import ENV, run
os.environ.update(ENV)
sys.path.insert(0, str(ROOT / "tests/support"))
from isolated_project import Project
sys.path.insert(0, str(ROOT / "tests/performance"))
from grade_enqueue_latency import run as sample

result = {}
try:
    ids = subprocess.check_output(["docker", "network", "ls", "-q"], text=True).split()
    networks = json.loads(subprocess.check_output(["docker", "network", "inspect", *ids])) if ids else []
    occupied = [ipaddress.ip_network(c["Subnet"]) for network in networks for c in (network.get("IPAM", {}).get("Config") or []) if c.get("Subnet")]
    subnet = next(str(candidate) for i in range(1, 255) if not any((candidate := ipaddress.ip_network(f"10.254.{i}.0/24")).overlaps(n) for n in occupied if n.version == 4))
    result["selected_subnet"] = subnet
    with Project("latency-v2-gates", SimpleNamespace(subnet=subnet, build_proxy=None)) as project:
        result["project"] = project.name
        result["project_output"] = str(project.output.relative_to(ROOT))
        for label, command, timeout in [("verify-build", ["build"], 600), ("verify-up", ["up", "-d", "--wait"], 300)]:
            build_args = ["--build-arg", "GOPROXY=" + sys.argv[2]] if label == "verify-build" and len(sys.argv) > 2 else []
            proc = project.a.compose(*command, *build_args, check=False, timeout=timeout)
            (OUT / (label + ".log")).write_text(proc.stdout + proc.stderr, encoding="utf-8")
            result[label] = proc.returncode
            print(label, proc.returncode, flush=True)
            if proc.returncode:
                if label == "verify-up":
                    diagnostic = project.a.compose("logs", "--no-color", "--tail", "200", "rabbitmq", check=False)
                    (OUT / "rabbitmq-startup.log").write_text(diagnostic.stdout + diagnostic.stderr, encoding="utf-8")
                    state = project.a.compose("ps", "--all", "--format", "json", check=False)
                    (OUT / "compose-startup-state.jsonl").write_text(state.stdout + state.stderr, encoding="utf-8")
                raise RuntimeError(label + " failed")
        v = project.verifier()
        v.write_doc = lambda: (OUT / "verify.md").write_text("\n".join(v.LINES) + "\n", encoding="utf-8")
        try:
            v.main()
            result["verify"] = 0
        except SystemExit as error:
            result["verify"] = error.code
        except Exception:
            result["verify"] = 1
            (OUT / "verify-error.log").write_text(traceback.format_exc(), encoding="utf-8")
        finally:
            v.write_doc()
        # Actual dedicated v2 collector exercises every fresh 202 with the new rule.
        fresh = sample(v, OUT / "live-v2-samples.json")
        result["live_v2"] = 0 if fresh["passed"] else 1
        result["live_v2_p95_ms"] = fresh["p95_ms"]
        result["live_v2_warnings"] = len(fresh["warnings"])
        browser_root = project.output / "browser-copy"
        source = ROOT / "frontend/e2e"
        copy = browser_root / "frontend/e2e"
        shutil.copytree(source, copy, ignore=shutil.ignore_patterns("node_modules", "test-results", "playwright-report"))
        (browser_root / "reports").mkdir()
        result["e2e_copied_sources_match"] = all(hashlib.sha256(p.read_bytes()).digest() == hashlib.sha256((copy / p.relative_to(source)).read_bytes()).digest() for p in source.glob("*") if p.is_file())
        env = {**ENV, **project.env, "E2E_BASE_URL": v.BASE, "PLAYWRIGHT_CHANNEL": "chrome"}
        result["e2e_install"] = run("e2e-install", [str(ROOT / "tests/.runtime/windows-command-adapters/npm.exe"), "ci", "--registry=https://registry.npmjs.org"], timeout=240, env=env, cwd=copy)
        if result["e2e_install"] == 0:
            result["playwright"] = run("playwright", ["E:/node.exe", str(copy / "node_modules/@playwright/test/cli.js"), "test", "--output", str(OUT / "browser-results")], timeout=300, env=env, cwd=copy)
        report = browser_root / "reports/xss-page-source.md"
        if report.exists():
            (OUT / "xss-page-source.md").write_bytes(report.read_bytes())
except Exception as error:
    result["error"] = type(error).__name__ + ": " + str(error)
    (OUT / "live-error.log").write_text(traceback.format_exc(), encoding="utf-8")
finally:
    (OUT / "live-summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result), flush=True)
sys.exit(0 if all(result.get(k) == 0 for k in ["verify", "live_v2", "playwright"]) else 1)
