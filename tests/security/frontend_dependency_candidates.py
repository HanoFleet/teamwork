"""Archive of this round's inline dependency experiment, made portable.

The original run used the pre-migration frontend package (Vite 8.3.8). Use an
explicit saved package JSON for replay; current package.json already uses esbuild.
All candidates live in ignored tests/.runtime, never modify the real frontend.
CLI entry was archived after the original inline execution; do not confuse its
creation time with the timestamps in the retained original audit outputs.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--node", type=Path, required=True)
    p.add_argument("--npm-cli", type=Path, required=True)
    p.add_argument("--package", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "npm_config_registry": "https://registry.npmjs.org", "PATH": str(args.node.parent) + os.pathsep + os.environ["PATH"]}
    for name, dev in [("esbuild", {"esbuild": "0.28.2"}), ("rsbuild", {"@rsbuild/core": "2.3.3", "@rsbuild/plugin-react": "2.1.1"})]:
        folder = ROOT / "tests/.runtime/replayed-dependency-candidates" / name
        folder.mkdir(parents=True, exist_ok=True)
        package = json.loads(args.package.read_bytes())
        package["devDependencies"] = {k: v for k, v in package["devDependencies"].items() if k not in ["vite", "@vitejs/plugin-react", "esbuild"]}
        package["devDependencies"].update(dev)
        (folder / "package.json").write_bytes((json.dumps(package, indent=2) + "\n").encode())
        for label, command in [("resolve", ["install", "--package-lock-only", "--ignore-scripts"]), ("audit", ["audit", "--json", "--audit-level=high"])]:
            run = subprocess.run([str(args.node), str(args.npm_cli), *command], cwd=folder, env=env, capture_output=True, timeout=180)
            (args.output / (name + "-" + label + ".txt")).write_bytes(run.stdout + run.stderr)
            print(name, label, run.returncode)


if __name__ == "__main__":
    main()
