"""Verify the final explicit submission set without touching the real Git index."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def git(args, cwd, env=None, data=None):
    p = subprocess.run(["git", *args], cwd=cwd, env=env, input=data, capture_output=True)
    if p.returncode:
        raise RuntimeError(p.stderr.decode(errors="replace"))
    return p.stdout


def main():
    manifest = json.loads((ROOT / "tests/release/lesson9-v2-publication.json").read_text())
    paths = (HERE / "submission-files.txt").read_text().splitlines()
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate submission path")
    before = {name: digest((ROOT / name).read_bytes()) for name in paths}
    index = Path(git(["rev-parse", "--git-path", "index"], ROOT).decode().strip())
    index_hash = digest(index.read_bytes())
    common = Path(git(["rev-parse", "--git-common-dir"], ROOT).decode().strip())
    if not common.is_absolute():
        common = (ROOT / common).resolve()
    with tempfile.TemporaryDirectory(prefix="lesson9-final-stage-") as tmp:
        repo = Path(tmp) / "repo"
        repo.mkdir()
        git(["init", "-q"], repo)
        env = {**os.environ, "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(common / "objects")}
        git(["read-tree", manifest["baseline_commit"]], repo, env)
        for name in paths:
            if name.endswith("/.last-run.json") or "__pycache__" in Path(name).parts:
                raise ValueError("runtime state in submission")
            dest = repo / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes((ROOT / name).read_bytes())
        pathspec = b"\0".join(name.encode() for name in sorted(paths + manifest["deleted"])) + b"\0"
        git(["-c", "core.autocrlf=false", "add", "--all", "--pathspec-from-file=-", "--pathspec-file-nul"], repo, env, pathspec)
        tree = git(["write-tree"], repo, env).decode().strip()
        checkout = Path(tmp) / "checkout"
        checkout.mkdir()
        git(["-c", "core.autocrlf=false", "checkout-index", "--all", "--prefix=" + checkout.as_posix() + "/"], repo, env)
        core = subprocess.run([sys.executable, str(checkout / "scripts/qa/lesson9/verify_release.py"), "--checkout"], capture_output=True)
        if core.returncode:
            raise ValueError(core.stdout.decode())
        proof_prefix = HERE.relative_to(ROOT)
        proof = json.loads((checkout / proof_prefix / "evidence-index.json").read_text())
        for name, expected in proof["files"].items():
            if digest((checkout / proof_prefix / name).read_bytes()) != expected:
                raise ValueError("published proof mismatch: " + name)
        if digest((checkout / "tests/release/lesson9-v2-publication.json").read_bytes()) != proof["release_manifest_sha256"]:
            raise ValueError("current release manifest mismatch")
        output = ROOT / "tests/output/lesson9-final-publication-check"
        output.mkdir(parents=True, exist_ok=False)
        (output / "checkout-verifier.log").write_bytes(core.stdout + core.stderr)
        result = dict(exit_code=0, tree=tree, commit_created=False, submission_files=len(paths),
                      deleted=manifest["deleted"], publication_manifest_verified=True, proof_files_verified=len(proof["files"]),
                      real_index_unchanged=digest(index.read_bytes()) == index_hash)
        if not result["real_index_unchanged"] or any(digest((ROOT / name).read_bytes()) != before[name] for name in paths):
            raise ValueError("original source or index changed")
        (output / "receipt.json").write_bytes(json.dumps(result, indent=2).encode())
        print(json.dumps(result))


if __name__ == "__main__":
    main()
