"""Select real CI Node/npm and resolve Windows command names for original make.

No gate code, arguments or thresholds are rewritten. Build launchers only in the
ignored runtime directory. Requires MinGW GCC and GNU mingw32-make in PATH.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--node", required=True, type=Path)
    p.add_argument("--npm-cli", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    runtime = ROOT / "tests/.runtime/windows-command-adapters"
    runtime.mkdir(parents=True, exist_ok=True)
    subprocess.run(["gcc", "-municode", "-O2", str(ROOT / "tests/environment/windows_tool_launcher.c"), "-o", str(runtime / "npm.exe")], check=True)
    shutil.copy2(runtime / "npm.exe", runtime / "python3.exe")
    env = {**os.environ, "QA_TOOL_NODE": str(args.node.resolve()), "QA_TOOL_NPM_CLI": str(args.npm_cli.resolve()),
           "QA_TOOL_PYTHON": sys.executable, "PATH": str(runtime) + os.pathsep + str(args.node.parent) + os.pathsep + os.environ["PATH"],
           "npm_config_registry": "https://registry.npmjs.org", "PYTHONIOENCODING": "utf-8", "GODEBUG": "http2client=0"}
    summary = {"time": datetime.datetime.now().astimezone().isoformat(), "command": ["mingw32-make", "check-security"], "threshold_changed": False}
    for label, command in [("node", [str(args.node), "--version"]), ("npm", [str(runtime / "npm.exe"), "--version"]), ("python", [str(runtime / "python3.exe"), "--version"])]:
        summary[label] = subprocess.check_output(command, env=env, text=True).strip()
    # Prove failure propagation before invoking the original gate.
    negative = subprocess.run([str(runtime / "python3.exe"), "-c", "raise SystemExit(7)"], env=env)
    assert negative.returncode == 7, "Adapter failed to propagate exit status"
    probe = 'space quote" slash\\ end\\'
    echoed = subprocess.check_output([str(runtime / "npm.exe"), "--version"], env=env, text=True)
    assert echoed.strip() == summary["npm"]
    quoted = subprocess.check_output([str(runtime / "python3.exe"), "-c", "import sys; print(sys.argv[1])", probe], env=env, text=True)
    assert quoted.rstrip("\r\n") == probe, "Adapter altered argument quoting"
    run = subprocess.run(summary["command"], cwd=ROOT, env=env, capture_output=True, timeout=600)
    (args.output / "make-check-security.log").write_bytes(run.stdout + run.stderr)
    summary["exit"] = run.returncode
    (args.output / "result.json").write_bytes((json.dumps(summary, indent=2) + "\n").encode())
    print(json.dumps(summary), flush=True)
    return run.returncode


if __name__ == "__main__":
    raise SystemExit(main())
