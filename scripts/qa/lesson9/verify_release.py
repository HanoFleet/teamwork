"""Verify the explicitly selected lesson-9 release and immutable history references."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = "tests/release/lesson9-v2-publication.json"


def file_path(root, name):
    if not isinstance(name, str) or "\\" in name or Path(name).is_absolute():
        raise ValueError("invalid release path")
    path = (root / name).resolve()
    if path == root.resolve() or not path.is_relative_to(root.resolve()):
        raise ValueError("release path escapes root")
    return path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(root, name):
    return json.loads(file_path(root, name).read_text(encoding="utf-8"))


def forbidden(name):
    parts = Path(name).parts
    return (any(part in {"node_modules", "__pycache__", ".runtime", "dist", ".dev-dist", ".last-run.json"} for part in parts)
            or any(part == ".env" or part.startswith(".env.") for part in parts)
            or Path(name).suffix.lower() in {".exe", ".dll", ".pyc", ".db", ".sqlite", ".sqlite3"})


def verify(root, manifest_name=DEFAULT_MANIFEST, checkout=False):
    manifest = read_json(root, manifest_name)
    if manifest.get("schema") != 1 or not manifest.get("files"):
        raise ValueError("invalid or empty release manifest")
    seen = set()
    key = "git_blob_sha256" if checkout else "worktree_sha256"
    for entry in manifest["files"]:
        name = entry["path"]
        if name in seen or name == manifest_name or forbidden(name):
            raise ValueError("duplicate, self-referencing or forbidden release file: " + name)
        seen.add(name)
        path = file_path(root, name)
        if not path.is_file() or sha256(path) != entry[key]:
            raise ValueError("release SHA256 mismatch: " + name)
        if entry.get("immutable") and entry["worktree_sha256"] != entry["git_blob_sha256"]:
            raise ValueError("immutable evidence would be converted: " + name)
    for name in manifest["deleted"]:
        if file_path(root, name).exists():
            raise ValueError("deleted release path still exists: " + name)

    context = read_json(root, "tests/release/history-context.json")
    historical = context["history_manifest"]
    if sha256(file_path(root, historical["path"])) != historical["sha256"]:
        raise ValueError("historical tests manifest was changed")
    old_files = read_json(root, historical["path"])
    changed = {entry["path"]: entry["sha256"] for entry in historical["changed_since_snapshot"]}
    for name, expected in old_files.items():
        if name in changed:
            if changed[name] != expected:
                raise ValueError("historical version mapping mismatch: " + name)
        elif sha256(file_path(root, name)) != expected:
            raise ValueError("unchanged historical file mismatch: " + name)

    gate_name = context["gate_manifest"]
    gate_files = read_json(root, gate_name)
    omitted = context.get("excluded_runtime", {})
    present_runtime = 0
    for name, expected in gate_files.items():
        original = str(Path(gate_name).parent / name).replace("\\", "/")
        if original in omitted:
            if original in seen or omitted[original]["sha256"] != expected:
                raise ValueError("invalid historical runtime omission")
            local = file_path(root, original)
            if local.exists():
                if sha256(local) != expected:
                    raise ValueError("historical local runtime bytes changed")
                present_runtime += 1
            continue
        alias = context["aliases"].get(original)
        resolved = alias["path"] if alias else original
        if alias and alias["sha256"] != expected:
            raise ValueError("historical alias digest mismatch: " + original)
        if sha256(file_path(root, resolved)) != expected:
            raise ValueError("historical gate reference mismatch: " + original)
    for original, alias in context["aliases"].items():
        if original in seen or alias["path"] not in seen:
            raise ValueError("historical runtime alias is not correctly published")
    return dict(files=len(seen), historical_tests_entries=len(old_files),
                historical_changed_paths=len(changed), historical_gate_entries=len(gate_files),
                aliases=len(context["aliases"]), historical_gate_verified=len(gate_files)-len(omitted),
                historical_runtime_omitted=len(omitted), local_runtime_verified=present_runtime, checkout=checkout)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--checkout", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = verify(args.root, args.manifest, args.checkout)
        print("PASS " + json.dumps(result))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print("ERROR " + str(error))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
