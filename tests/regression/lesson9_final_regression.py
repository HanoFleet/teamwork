"""Run original verify.py and Playwright on the actual final Dockerfile builds.

Use Python -X utf8 on Windows. Generated XSS evidence is copied into this round's
output and the pre-existing report is restored, including uncommitted contents.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/support"))
from isolated_project import Project


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--subnet", required=True)
    p.add_argument("--build-proxy")
    p.add_argument("--goproxy")
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    result = {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "uncommitted": True}
    try:
        with Project("lesson9-final", args) as project:
            result["project"] = project.name
            build = ["build"]
            if args.goproxy: build += ["--build-arg", "GOPROXY=" + args.goproxy]
            for label, command, timeout in [("build", build, 600), ("up", ["up", "-d", "--wait"], 300)]:
                run = project.a.compose(*command, check=False, timeout=timeout)
                (args.output / (label + ".txt")).write_bytes((run.stdout + run.stderr).encode())
                result[label] = run.returncode
                if run.returncode: raise RuntimeError(label + " failed; see saved output")
            v = project.verifier()
            v.write_doc = lambda: (args.output / "verify.md").write_bytes(("\n".join(v.LINES) + "\n").encode())
            try: v.main(); result["verify"] = 0
            except SystemExit as error: result["verify"] = error.code
            except Exception:
                result["verify"] = 1
                (args.output / "verify-error.txt").write_bytes(traceback.format_exc().encode())
            finally: v.write_doc()
            match = re.search(r"times=\[([^\]]+)\]", "\n".join(v.LINES))
            if match:
                values = [float(x) for x in match[1].split(",")]
                result["verify_latency"] = {"samples_ms": values, "max_ms": max(values), "over_100_ms": sum(x > 100 for x in values), "note": "original verifier prints rounded 0.1ms values; independent from controlled comparison"}
            env = {**os.environ, **project.env, "E2E_BASE_URL": v.BASE, "PLAYWRIGHT_CHANNEL": "chrome"}
            report = ROOT / "reports/xss-page-source.md"
            old = report.read_bytes() if report.exists() else None
            try:
                for name, command in [("e2e-install", ["cmd", "/c", "npm ci --registry=https://registry.npmjs.org"]), ("playwright", ["cmd", "/c", "npx playwright test"])]:
                    run = subprocess.run(command, cwd=ROOT / "frontend/e2e", env=env, capture_output=True, timeout=240)
                    (args.output / (name + ".txt")).write_bytes(run.stdout + run.stderr)
                    result[name] = run.returncode
                if report.exists(): (args.output / "xss-page-source.md").write_bytes(report.read_bytes())
            finally:
                if old is None: report.unlink(missing_ok=True)
                else: report.write_bytes(old)
    finally:
        (args.output / "summary.json").write_bytes((json.dumps(result, indent=2) + "\n").encode())
    return 0 if all(result.get(x) == 0 for x in ["build", "up", "verify", "e2e-install", "playwright"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
