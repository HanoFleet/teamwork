"""Prepare once, then verify release bytes in an independent temporary Git repository."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
MANIFEST = "tests/release/lesson9-v2-publication.json"
SUGGESTED = HERE / "suggested-source-reference.txt"
IMMUTABLE = ("qa/lesson9/", "reports/lesson9-20261118/", "scripts/qa/lesson9/history/",
             "tests/environment/history/", "docs/lesson-09/2026-11-18-observe-enqueue-latency/",
             "docs/lesson-09/2026-11-18-enqueue-latency-v2-gates-01/")


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(value, output, ensure_ascii=False, indent=2)


def git(args, cwd, env=None, data=None):
    result = subprocess.run(["git", *args], cwd=cwd, env=env, input=data, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id:
        raise ValueError("run-id must be a single directory name")
    out = HERE / args.run_id
    out.mkdir(exist_ok=False)
    head = git(["rev-parse", "HEAD"], ROOT).decode().strip()
    index_path = Path(git(["rev-parse", "--git-path", "index"], ROOT).decode().strip())
    if not index_path.is_absolute():
        index_path = ROOT / index_path
    index_before = digest(index_path.read_bytes())
    protected = json.loads((HERE / "preservation-before.json").read_text(encoding="utf-8"))
    before = {name: digest((ROOT / name).read_bytes()) for name in protected}
    if before != protected:
        raise ValueError("historical evidence changed before release validation")

    if args.prepare:
        suggested = [line.split("\t")[-1] for line in SUGGESTED.read_text(encoding="utf-8").splitlines()[1:] if line.strip()]
        if len(suggested) != 44:
            raise ValueError("expected the reviewed 44 source paths")
        status = [(row[:2], row[3:]) for row in git(["status", "--porcelain=v1", "-uall", "-z"], ROOT).decode().split("\0") if row]
        deleted = sorted(name for name in suggested if not (ROOT / name).is_file())
        if deleted != ["frontend/src/vite-env.d.ts", "frontend/vite.config.ts"]:
            raise ValueError("unexpected source deletion")
        selected = {name for name in suggested if name not in deleted}
        selected.update(name for status_code, name in status if name.startswith(IMMUTABLE) and not name.endswith("/.last-run.json"))
        selected.update(["scripts/qa/lesson9/README.md", "scripts/qa/lesson9/verify_release.py", "tests/manifest.json",
                         "tests/release/README.md", "tests/release/history-context.json", "tests/release/history/browser-run-state.json"])
        excluded = [dict(path=name, reason="not in reviewed sources or frozen lesson-9 evidence; retained locally")
                    for status_code, name in status if name not in selected and name not in deleted]
        excluded.append(dict(path="docs/lesson-09/2026-11-18-enqueue-latency-v2-gates-01/live-attempt-04/browser-results/.last-run.json",
                             reason="ignored browser state; immutable alias in history-context.json"))
    else:
        current = json.loads((ROOT / MANIFEST).read_text(encoding="utf-8"))
        selected = {entry["path"] for entry in current["files"]}
        deleted = current["deleted"]
        excluded = current["excluded"]

    common = Path(git(["rev-parse", "--git-common-dir"], ROOT).decode().strip())
    if not common.is_absolute():
        common = (ROOT / common).resolve()
    with tempfile.TemporaryDirectory(prefix="lesson9-git-roundtrip-") as tmp:
        sandbox = Path(tmp) / "repository"
        sandbox.mkdir()
        git(["init", "-q"], sandbox)
        env = {**os.environ, "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(common / "objects")}
        git(["-c", "core.autocrlf=false", "read-tree", head], sandbox, env)
        for name in sorted(selected):
            path = sandbox / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((ROOT / name).read_bytes())
        pathspec = b"\0".join(name.encode() for name in sorted(selected | set(deleted))) + b"\0"
        git(["-c", "core.autocrlf=false", "add", "--all", "--pathspec-from-file=-", "--pathspec-file-nul"], sandbox, env, pathspec)
        files = []
        for name in sorted(selected):
            raw = (ROOT / name).read_bytes()
            blob = git(["show", ":" + name], sandbox, env)
            immutable = name.startswith(IMMUTABLE) or name == "tests/manifest.json" or name.startswith("tests/release/history/")
            if immutable and raw != blob:
                raise ValueError("Git converted immutable evidence: " + name)
            files.append(dict(path=name, immutable=immutable, worktree_sha256=digest(raw), git_blob_sha256=digest(blob)))
        release = dict(schema=1, baseline_commit=head, scope="explicit working-tree delta over baseline", files=files,
                       deleted=deleted, excluded=excluded, self=MANIFEST,
                       derived_evidence="docs/lesson-09/2026-11-18-submission-preparation/evidence-index.json")
        if args.prepare:
            write_json(ROOT / MANIFEST, release)
        else:
            if release["files"] != current["files"]:
                raise ValueError("release files changed since manifest creation")
        path = sandbox / MANIFEST
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((ROOT / MANIFEST).read_bytes())
        git(["add", "--", MANIFEST], sandbox, env)
        tree = git(["write-tree"], sandbox, env).decode().strip()
        checkout = Path(tmp) / "checkout"
        checkout.mkdir()
        git(["-c", "core.autocrlf=false", "checkout-index", "--all", "--prefix=" + checkout.as_posix() + "/"], sandbox, env)
        mismatches = [entry["path"] for entry in files if digest((checkout / entry["path"]).read_bytes()) != entry["git_blob_sha256"]]
        if mismatches:
            raise ValueError("checkout changed release bytes: " + str(mismatches))
        runtime = "docs/lesson-09/2026-11-18-enqueue-latency-v2-gates-01/live-attempt-04/browser-results/.last-run.json"
        if git(["check-ignore", "--", runtime], sandbox, env).decode().strip() != runtime:
            raise ValueError("browser runtime file is not ignored")
        if git(["ls-files", "--", runtime], sandbox, env):
            raise ValueError("browser runtime file entered isolated index")
        checks = []
        for label, root, mode in [("worktree", ROOT, []), ("checkout", checkout, ["--checkout"])]:
            command = [sys.executable, str(root / "scripts/qa/lesson9/verify_release.py"), *mode]
            result = subprocess.run(command, cwd=root, capture_output=True)
            (out / (label + ".log")).write_bytes(result.stdout + result.stderr)
            checks.append(dict(name=label, command=command, exit_code=result.returncode))
            if result.returncode:
                raise ValueError(label + " manifest verification failed")
        # Corrupt only the disposable checkout, proving digest failure propagation.
        victim = checkout / "tests/release/history/browser-run-state.json"
        original = victim.read_bytes()
        victim.write_bytes(original + b"tampered")
        command = [sys.executable, str(checkout / "scripts/qa/lesson9/verify_release.py"), "--checkout"]
        negative = subprocess.run(command, cwd=checkout, capture_output=True)
        (out / "tamper-negative.log").write_bytes(negative.stdout + negative.stderr)
        if negative.returncode != 1:
            raise ValueError("tampered checkout was not rejected")
        victim.write_bytes(original)
        negative_checks = []
        victim.unlink()
        missing = subprocess.run(command, cwd=checkout, capture_output=True)
        (out / "missing-negative.log").write_bytes(missing.stdout + missing.stderr)
        victim.write_bytes(original)
        if missing.returncode != 1:
            raise ValueError("missing checkout file was not rejected")
        negative_checks.append(dict(name="missing", exit_code=missing.returncode))
        manifest_copy = checkout / MANIFEST
        manifest_bytes = manifest_copy.read_bytes()
        for label, illegal in [("escape", "../../escape"), ("runtime", ".last-run.json")]:
            modified = json.loads(manifest_bytes)
            modified["files"][0]["path"] = illegal
            manifest_copy.write_bytes(json.dumps(modified).encode())
            failed = subprocess.run(command, cwd=checkout, capture_output=True)
            (out / (label + "-negative.log")).write_bytes(failed.stdout + failed.stderr)
            manifest_copy.write_bytes(manifest_bytes)
            if failed.returncode != 1:
                raise ValueError("illegal release path was not rejected")
            negative_checks.append(dict(name=label, exit_code=failed.returncode))
        if any(name.endswith("/.last-run.json") for name in selected):
            raise ValueError("runtime state selected for publication")
        aliases = json.loads((ROOT / "tests/release/history-context.json").read_text())["aliases"]
        summary = dict(tree=tree, git_commit_created=False, real_index_sha256_before=index_before,
                       real_index_sha256_after=digest(index_path.read_bytes()), selected_files=len(files),
                       immutable_files=sum(entry["immutable"] for entry in files), checkout_mismatches=mismatches,
                       checks=checks, tamper_negative_exit=negative.returncode, historical_aliases=len(aliases),
                       historical_manifest_sha256=digest((ROOT / "tests/manifest.json").read_bytes()), negative_checks=negative_checks)
    after = {name: digest((ROOT / name).read_bytes()) for name in protected}
    summary["protected_files"] = len(after)
    summary["protected_changed"] = [name for name in after if before[name] != after[name]]
    if summary["protected_changed"] or summary["real_index_sha256_before"] != summary["real_index_sha256_after"]:
        raise ValueError("real index or protected evidence changed")
    write_json(out / "roundtrip.json", summary)
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    main()
