#!/usr/bin/env python3
"""Verify generated reports against archived observations; does not approve acceptance."""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
FILES = ("security-precheck.md", "risk-authz.md", "risk-concurrency.md",
         "risk-transaction.md", "security-baseline.md", "review-01.md")

def main():
    errors = []
    latest = json.loads((REPORTS / "evidence/week8/latest.json").read_text(encoding="utf-8"))
    result_path = ROOT / latest["result"]
    result = json.loads(result_path.read_text(encoding="utf-8"))
    for name in FILES:
        if not (REPORTS / name).is_file():
            errors.append("missing " + name)
    text = (REPORTS / FILES[0]).read_text(encoding="utf-8")
    if "| 编号 | 前置条件 | 操作 | 期望 | 当前实际 | 判定 |" not in text:
        errors.append("missing six-column table")
    blocks = re.split(r"^## (SEC-0\d) .+$", text, flags=re.M)
    for id in [f"SEC-0{i}" for i in range(1, 8)]:
        if id not in blocks:
            errors.append("missing detailed " + id)
            continue
        block = blocks[blocks.index(id) + 1]
        for field in ("前置条件", "操作", "可观测结果", "当前实际", "当前判定"):
            if f"**{field}：**" not in block:
                errors.append(id + " missing " + field)
        row = result["checks"][id]
        if row["status"] in ("blocked", "invalid") and row["judgment"] is not None:
            errors.append("unexecuted check has a red/green judgment: " + id)
        if row["status"] == "pass" and row["judgment"] != "绿":
            errors.append("inconsistent pass judgment: " + id)
        if row["status"] == "fail" and row["judgment"] != "红":
            errors.append("inconsistent fail judgment: " + id)
    for name in ("risk-authz.md", "risk-concurrency.md", "risk-transaction.md", "review-01.md"):
        data = (REPORTS / name).read_text(encoding="utf-8")
        for field in ("用什么手段查", "查了什么", "判据", "结果"):
            if f"**{field}：" not in data:
                errors.append(name + " missing " + field)
    review = (REPORTS / "review-01.md").read_text(encoding="utf-8")
    if "**结果：待独立审查。**" not in review or "未满足" not in review:
        errors.append("review state must remain pending and human reproduction unsatisfied")
    for name in FILES + ("llm-review-handoff.md",):
        data = (REPORTS / name).read_text(encoding="utf-8")
        for link in re.findall(r"\]\(([^)]+)\)", data):
            if link.startswith(("https:", "http:")):
                continue
            if not (REPORTS / link.split("#", 1)[0]).exists():
                errors.append(name + " broken link: " + link)
    manifest = json.loads((result_path.parent / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["files"].items():
        p = result_path.parent / name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != expected:
            errors.append("evidence hash mismatch: " + name)
    if result["business_bytes_changed"]:
        errors.append("business source changed during testing")
    info = {"checked_reports": list(FILES), "run_id": result["run_id"], "errors": errors,
            "meaning": "format/evidence consistency only; not final security acceptance"}
    print(json.dumps(info, ensure_ascii=False, indent=2))
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())

