#!/usr/bin/env python3
"""活动 change 的规约结构自查。

只读脚本：逐个检查 openspec/changes/ 下未归档的 change，验证四份文件、
需求/场景结构、失败路径覆盖、能力与场景对应表、任务清单顺序。退出码 0
表示全部通过；任何一项缺失或数量不一致都会失败。
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHANGES_ROOT = ROOT / "openspec" / "changes"
BASE_SPECS = ROOT / "openspec" / "specs"

# 每个活动 change 的专属检查项。新增 change 时必须在这里登记，避免漏检。
CHANGE_RULES: dict[str, dict[str, object]] = {
    "2026-10-14-upgrade-material-library": {
        "capabilities": [
            "platform-foundation",
            "material-library",
            "auth-upload",
            "knowledge-retrieval",
        ],
        "anchors": ["20", "800", "80", "0.35", "k=60", "409", "413", "503"],
        "min_tasks": 20,
    },
    "2026-11-05-add-async-grading": {
        "capabilities": ["async-grading"],
        "anchors": ["202", "task_id", "P95", "500ms", "async-202", "20,000", "GRADE_MAX_ATTEMPTS=5"],
        "min_tasks": 20,
    },
}

failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)


def read(path: Path) -> str:
    if not path.is_file():
        fail(f"缺少文件：{path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def section(text: str, heading: str) -> str:
    """Return a level-2 section body, allowing a Chinese parenthetical suffix."""
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}(?:\s*（[^）]*）)?\s*$", re.MULTILINE
    )
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    next_heading = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_heading.start() if next_heading else len(text)
    return text[start:end]


def has_heading(text: str, heading: str) -> bool:
    return bool(section(text, heading))


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


def check_proposal(proposal: str, change_name: str) -> None:
    for heading in [
        "Why",
        "What Changes",
        "Out of Scope",
        "Alternatives Considered",
        "Capabilities",
        "Capability–Scenario Map",
        "Failure Path Coverage",
        "Success Criteria",
    ]:
        if not has_heading(proposal, heading):
            fail(f"{change_name}/proposal.md 缺少章节：{heading}")

    out_of_scope = section(proposal, "Out of Scope")
    non_goals = len(re.findall(r"^- ", out_of_scope, re.MULTILINE))
    if non_goals < 3:
        fail(f"{change_name}/proposal.md 的“本次不做”只有 {non_goals} 条，至少需要 3 条")

    alternatives = section(proposal, "Alternatives Considered")
    alt_rows = len(re.findall(r"^\|.+\|$", alternatives, re.MULTILINE)) - 2
    if alt_rows < 1:
        fail(f"{change_name}/proposal.md 没有列出被放弃的候选方案")

    success = section(proposal, "Success Criteria")
    if len(re.findall(r"^- ", success, re.MULTILINE)) < 3:
        fail(f"{change_name}/proposal.md 的“完成现象”少于 3 条")


def check_design(design: str, change_name: str) -> None:
    if not has_heading(design, "Context"):
        fail(f"{change_name}/design.md 缺少 Context")
    if not (has_heading(design, "Decisions") or has_heading(design, "3. 关键取舍")):
        fail(f"{change_name}/design.md 缺少 Decisions 或“3. 关键取舍”")
    if not (has_heading(design, "Interfaces") or has_heading(design, "4. 接口契约")):
        fail(f"{change_name}/design.md 缺少 Interfaces 或“4. 接口契约”")
    if not (has_heading(design, "Data Model") or has_heading(design, "5. 数据模型")):
        fail(f"{change_name}/design.md 缺少 Data Model 或“5. 数据模型”")
    if not (has_heading(design, "Migration Plan") or has_heading(design, "11. 迁移计划")):
        fail(f"{change_name}/design.md 缺少 Migration Plan 或“11. 迁移计划”")
    if not (has_heading(design, "Risks / Trade-offs") or has_heading(design, "12. 风险与代价")):
        fail(f"{change_name}/design.md 缺少 Risks / Trade-offs 或“12. 风险与代价”")

    tradeoffs = re.findall(r"^### (?:取舍\s+\d+|D\d+)[：:. ].*$", design, re.MULTILINE)
    if len(tradeoffs) < 2:
        fail(f"{change_name}/design.md 至少需要 2 条关键取舍")
    for title in tradeoffs:
        start = design.index(title)
        next_tradeoff = re.search(
            r"^### (?:取舍\s+\d+|D\d+)[：:. ].*$",
            design[start + len(title):],
            re.MULTILINE,
        )
        end = start + len(title) + next_tradeoff.start() if next_tradeoff else len(design)
        block = design[start:end]
        for marker in ["选了什么", "放弃了什么", "代价由谁承担"]:
            if marker not in block:
                fail(f"{change_name}/design.md 的「{title.strip()}」缺少「{marker}」")


def check_specs(change: Path, change_name: str, rules: dict[str, object]) -> tuple[int, int]:
    specs = change / "specs"
    spec_files = sorted(specs.glob("*/spec.md"))
    if not spec_files:
        fail(f"{change_name}/specs/ 下没有 capability 规约")
        return 0, 0

    total_requirements = 0
    total_scenarios = 0
    failure_codes: Counter[str] = Counter()
    computed: dict[str, tuple[int, int]] = {}

    for spec_file in spec_files:
        capability = spec_file.parent.name
        text = read(spec_file)
        if "## ADDED Requirements" not in text and "## MODIFIED Requirements" not in text:
            fail(f"{change_name}/{capability}/spec.md 既没有 ADDED，也没有 MODIFIED Requirements")
        requirements = parse_requirements(text)
        if not requirements:
            fail(f"{change_name}/{capability}/spec.md 没有 Requirement")

        base_file = BASE_SPECS / capability / "spec.md"
        base_titles: set[str] = set()
        if base_file.is_file():
            base_titles = {
                title for title, _ in parse_requirements(base_file.read_text(encoding="utf-8"))
            }
        modified = section(text, "MODIFIED Requirements")
        if modified and base_titles:
            for title, _ in parse_requirements(modified):
                if title not in base_titles:
                    fail(f"{change_name}/{capability}/spec.md 的 MODIFIED 需求在主规约中不存在：{title}")

        seen: set[str] = set()
        scenario_count = 0
        for title, block in requirements:
            if title in seen:
                fail(f"{change_name}/{capability}/spec.md 重复 Requirement：{title}")
            seen.add(title)
            scenarios = parse_scenarios(block)
            if not scenarios:
                fail(f"{change_name}/{capability}/spec.md 的「{title}」没有 Scenario")
            for scenario_title, scenario_block in scenarios:
                scenario_count += 1
                for marker in ["**GIVEN**", "**WHEN**", "**THEN**"]:
                    if marker not in scenario_block:
                        fail(
                            f"{change_name}/{capability}/spec.md 的"
                            f"「{title} / {scenario_title}」缺少 {marker}"
                        )
                for code in ["400", "401", "403", "404", "409", "413", "503"]:
                    if re.search(rf"(?<!\d){code}(?!\d)", scenario_block):
                        failure_codes[code] += 1
        computed[capability] = (len(requirements), scenario_count)
        total_requirements += len(requirements)
        total_scenarios += scenario_count

    for code in ["400", "403", "404", "503"]:
        if failure_codes[code] == 0:
            fail(f"{change_name} 的场景中没有覆盖失败状态码 {code}")

    map_section = section(
        read(change / "proposal.md"), "Capability–Scenario Map"
    )
    map_counts = count_table(map_section)
    for capability in rules["capabilities"]:
        if capability not in map_counts:
            fail(f"{change_name}/proposal.md 的能力与场景表缺少 {capability}")
            continue
        if capability in computed and map_counts[capability] != computed[capability]:
            fail(
                f"{change_name}/proposal.md 的能力与场景表与规约不一致：{capability} "
                f"表中 {map_counts[capability]}，实际 {computed[capability]}"
            )

    return total_requirements, total_scenarios


def check_tasks(tasks: str, change_name: str, rules: dict[str, object]) -> int:
    task_lines = re.findall(r"^- \[ \].+$", tasks, re.MULTILINE)
    min_tasks = int(rules["min_tasks"])
    if len(task_lines) < min_tasks:
        fail(f"{change_name}/tasks.md 只有 {len(task_lines)} 条任务，至少需要 {min_tasks} 条")
    if "## 完成定义" not in tasks:
        fail(f"{change_name}/tasks.md 缺少“完成定义”")
    first_task = re.search(r"^- \[ \].+$", tasks, re.MULTILINE)
    if first_task:
        before = tasks[: first_task.start()]
        headings = re.findall(r"^##\s+(.+)$", before, re.MULTILINE)
        if not headings or not headings[-1].startswith("0."):
            fail(f"{change_name}/tasks.md 的第一个任务组不是基线/骨架组")
    for line in task_lines:
        if "verify:" not in line:
            fail(f"{change_name}/tasks.md 任务缺少 verify：{line[:60]}")
    return len(task_lines)


def check_change(change: Path) -> dict[str, int]:
    name = change.name
    print(f"变更：{name}")
    if not re.match(r"^\d{4}-\d{2}-\d{2}-[a-z0-9-]+$", name):
        fail(f"变更目录名不符合 YYYY-MM-DD-短横小写英文名：{name}")
    if name not in CHANGE_RULES:
        fail(f"活动 change 未在 scripts/spec_check.py 的 CHANGE_RULES 中登记：{name}")
        rules: dict[str, object] = {
            "capabilities": [],
            "anchors": [],
            "min_tasks": 20,
        }
    else:
        rules = CHANGE_RULES[name]

    required = [
        change / ".openspec.yaml",
        change / "proposal.md",
        change / "design.md",
        change / "tasks.md",
    ]
    for path in required:
        if not path.is_file():
            fail(f"缺少四份文件之一：{path.relative_to(ROOT)}")

    proposal = read(change / "proposal.md")
    design = read(change / "design.md")
    tasks = read(change / "tasks.md")

    check_proposal(proposal, name)
    check_design(design, name)
    total_requirements, total_scenarios = check_specs(change, name, rules)
    total_tasks = check_tasks(tasks, name, rules)

    all_text = proposal + design + tasks + "".join(
        read(path) for path in sorted((change / "specs").glob("*/spec.md"))
    )
    for anchor in rules["anchors"]:
        if str(anchor) not in all_text:
            fail(f"{name} 的规约中缺少数值/字段锚点：{anchor}")

    print(
        f"  需求 {total_requirements} / 场景 {total_scenarios} / 任务 {total_tasks} / "
        f"能力 {len(list((change / 'specs').glob('*/spec.md')))}"
    )
    return {
        "requirements": total_requirements,
        "scenarios": total_scenarios,
        "tasks": total_tasks,
    }


def main() -> int:
    print("活动 change 规约自查")
    print(f"仓库：{ROOT}")
    active = sorted(
        path
        for path in CHANGES_ROOT.iterdir()
        if path.is_dir() and path.name != "archive" and not path.name.startswith(".")
    )
    print(f"活动 change：{len(active)}")
    print("-" * 60)

    totals = {"requirements": 0, "scenarios": 0, "tasks": 0}
    for change in active:
        stats = check_change(change)
        for key in totals:
            totals[key] += stats[key]
        print("-" * 60)

    print(
        f"汇总：{len(active)} 个活动 change，"
        f"{totals['requirements']} 条需求，{totals['scenarios']} 个场景，"
        f"{totals['tasks']} 条任务"
    )
    if failures:
        print(f"未通过：{len(failures)} 项")
        for item in failures:
            print(f"  ✗ {item}")
        return 1
    print("通过：四份文件、需求/场景结构、失败路径、对应表和任务清单均符合要求。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
