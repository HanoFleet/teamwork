#!/usr/bin/env python3
"""阶段一规约结构自查。

只读脚本：检查 2026-10-14-upgrade-material-library 的四份文件、需求/场景结构、
失败路径覆盖、能力与场景对应表、任务清单顺序。退出码 0 表示全部通过。
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGE = ROOT / "openspec" / "changes" / "2026-10-14-upgrade-material-library"
SPECS = CHANGE / "specs"
BASE_SPECS = ROOT / "openspec" / "specs"

CAPABILITIES = [
    "platform-foundation",
    "material-library",
    "auth-upload",
    "knowledge-retrieval",
]

failures: list[str] = []
notes: list[str] = []


def fail(message: str) -> None:
    failures.append(message)


def read(path: Path) -> str:
    if not path.is_file():
        fail(f"缺少文件：{path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Return the body of a level-2 heading up to the next level-2 heading."""
    pattern = re.compile(rf"^{re.escape(heading)}\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def parse_requirements(text: str) -> list[tuple[str, str]]:
    """Return [(requirement title, block text)] for one spec file."""
    matches = list(re.finditer(r"^### Requirement:\s*(.+?)\s*$", text, re.MULTILINE))
    result: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        result.append((match.group(1).strip(), text[start:end]))
    return result


def parse_scenarios(block: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^#### Scenario:\s*(.+?)\s*$", block, re.MULTILINE))
    result: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        result.append((match.group(1).strip(), block[start:end]))
    return result


def count_table(text: str) -> dict[str, tuple[int, int]]:
    counts: dict[str, tuple[int, int]] = {}
    pattern = re.compile(
        r"^\|\s*`([a-z-]+)`\s*\|[^|]*\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        counts[match.group(1)] = (int(match.group(2)), int(match.group(3)))
    return counts


def main() -> int:
    print("阶段一规约自查")
    print(f"仓库：{ROOT}")
    print(f"变更：{CHANGE.relative_to(ROOT)}")
    print("-" * 60)

    if not re.match(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$", CHANGE.name):
        fail(f"变更目录名不符合 YYYY-MM-DD-短横小写英文名：{CHANGE.name}")

    required = [
        CHANGE / ".openspec.yaml",
        CHANGE / "proposal.md",
        CHANGE / "design.md",
        CHANGE / "tasks.md",
    ]
    for path in required:
        if not path.is_file():
            fail(f"缺少四份文件之一：{path.relative_to(ROOT)}")

    proposal = read(CHANGE / "proposal.md")
    design = read(CHANGE / "design.md")
    tasks = read(CHANGE / "tasks.md")

    # proposal 结构
    for heading in [
        "## Why",
        "## What Changes",
        "## Out of Scope（本次不做）",
        "## Alternatives Considered（放弃的候选方案）",
        "## Capability–Scenario Map（能力与场景对应）",
        "## Failure Path Coverage（失败路径覆盖）",
        "## Success Criteria（完成现象）",
    ]:
        if heading not in proposal:
            fail(f"proposal.md 缺少章节：{heading}")
    out_of_scope = section(proposal, "## Out of Scope（本次不做）")
    non_goals = len(re.findall(r"^- ", out_of_scope, re.MULTILINE))
    if non_goals < 3:
        fail(f"proposal.md 的“本次不做”只有 {non_goals} 条，至少需要 3 条")
    alternatives = section(proposal, "## Alternatives Considered（放弃的候选方案）")
    alt_rows = len(re.findall(r"^\|.+\|$", alternatives, re.MULTILINE)) - 2
    if alt_rows < 1:
        fail("proposal.md 没有列出被放弃的候选方案")

    # design 结构
    for heading in ["## 1. 选型", "## 3. 关键取舍", "## 4. 接口契约", "## 5. 数据模型"]:
        if heading not in design:
            fail(f"design.md 缺少章节：{heading}")
    tradeoffs = re.findall(r"^### 取舍\s+\d+：.+$", design, re.MULTILINE)
    if len(tradeoffs) < 2:
        fail("design.md 至少需要 2 条关键取舍")
    for title in tradeoffs:
        start = design.index(title)
        next_tradeoff = re.search(r"^### 取舍\s+\d+：", design[start + len(title):], re.MULTILINE)
        end = start + len(title) + next_tradeoff.start() if next_tradeoff else len(design)
        block = design[start:end]
        for marker in ["选了什么", "放弃了什么", "代价由谁承担"]:
            if marker not in block:
                fail(f"design.md 的「{title.strip()}」缺少「{marker}」")

    # specs 结构
    total_requirements = 0
    total_scenarios = 0
    failure_codes: Counter[str] = Counter()
    computed: dict[str, tuple[int, int]] = {}
    seen_global: set[tuple[str, str]] = set()

    spec_files = sorted(SPECS.glob("*/spec.md"))
    if not spec_files:
        fail("specs/ 下没有 capability 规约")
    for spec_file in spec_files:
        capability = spec_file.parent.name
        text = read(spec_file)
        if "## ADDED Requirements" not in text and "## MODIFIED Requirements" not in text:
            fail(f"{capability}/spec.md 既没有 ADDED Requirements，也没有 MODIFIED Requirements")
        requirements = parse_requirements(text)
        if not requirements:
            fail(f"{capability}/spec.md 没有 Requirement")
        base_file = BASE_SPECS / capability / "spec.md"
        base_titles = set()
        if base_file.is_file():
            base_titles = {
                title for title, _ in parse_requirements(base_file.read_text(encoding="utf-8"))
            }
        requirement_count = len(requirements)
        scenario_count = 0
        for title, block in requirements:
            if (capability, title) in seen_global:
                fail(f"{capability}/spec.md 重复 Requirement：{title}")
            seen_global.add((capability, title))
            if "## MODIFIED Requirements" in text and title not in base_titles and base_titles:
                fail(f"{capability}/spec.md 的 MODIFIED 需求在主规约中不存在：{title}")
            scenarios = parse_scenarios(block)
            if not scenarios:
                fail(f"{capability}/spec.md 的「{title}」没有 Scenario")
            for scenario_title, scenario_block in scenarios:
                scenario_count += 1
                for marker in ["**GIVEN**", "**WHEN**", "**THEN**"]:
                    if marker not in scenario_block:
                        fail(
                            f"{capability}/spec.md 的「{title} / {scenario_title}」缺少 {marker}"
                        )
                for code in ["400", "401", "403", "404", "409", "413", "503"]:
                    if re.search(rf"(?<!\d){code}(?!\d)", scenario_block):
                        failure_codes[code] += 1
        computed[capability] = (requirement_count, scenario_count)
        total_requirements += requirement_count
        total_scenarios += scenario_count

    for code in ["400", "403", "404", "503"]:
        if failure_codes[code] == 0:
            fail(f"场景中没有覆盖失败状态码 {code}")

    map_counts = count_table(section(proposal, "## Capability–Scenario Map（能力与场景对应）"))
    for capability in CAPABILITIES:
        if capability not in map_counts:
            fail(f"proposal.md 的能力与场景表缺少 {capability}")
            continue
        if capability in computed and map_counts[capability] != computed[capability]:
            fail(
                f"proposal.md 的能力与场景表与规约不一致：{capability} "
                f"表中 {map_counts[capability]}，实际 {computed[capability]}"
            )

    # tasks 结构
    task_lines = re.findall(r"^- \[ \].+$", tasks, re.MULTILINE)
    if len(task_lines) < 20:
        fail(f"tasks.md 只有 {len(task_lines)} 条任务，至少需要 20 条")
    if "## 完成定义" not in tasks:
        fail("tasks.md 缺少“完成定义”")
    first_task = re.search(r"^- \[ \].+$", tasks, re.MULTILINE)
    if first_task:
        before = tasks[: first_task.start()]
        headings = re.findall(r"^##\s+(.+)$", before, re.MULTILINE)
        if not headings or not headings[-1].startswith("0."):
            fail("tasks.md 的第一个任务组不是基线/骨架组")
    for line in task_lines:
        if "verify:" not in line:
            fail(f"tasks.md 任务缺少 verify：{line[:60]}")

    # 数值锚点
    all_text = proposal + design + tasks + "".join(
        read(path) for path in spec_files
    )
    for anchor in ["20", "800", "80", "0.35", "k=60", "409", "413", "503"]:
        if anchor not in all_text:
            fail(f"规约中缺少数值判据锚点：{anchor}")

    # 输出
    print(f"四份文件：{'齐全' if all(path.is_file() for path in required) else '缺失'}")
    print(f"能力数：{len(spec_files)}")
    print(f"需求数：{total_requirements}")
    print(f"场景数：{total_scenarios}")
    print(f"任务数：{len(task_lines)}")
    print("失败状态码覆盖：" + ", ".join(f"{code}={failure_codes[code]}" for code in sorted(failure_codes)))
    print("能力明细：")
    for capability in sorted(computed):
        print(f"  - {capability}: {computed[capability][0]} 需求 / {computed[capability][1]} 场景")
    print("-" * 60)
    if failures:
        print(f"未通过：{len(failures)} 项")
        for item in failures:
            print(f"  ✗ {item}")
        return 1
    print("通过：四份文件、需求/场景结构、失败路径、对应表和任务清单均符合要求。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
