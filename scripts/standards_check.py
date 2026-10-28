#!/usr/bin/env python3
"""八类工程规范结构自查。

只读脚本：检查规范文件、常驻规则入口、数据字典、四步核对和 README 链接。
退出码 0 表示全部通过。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STANDARDS = ROOT / "docs" / "standards"

STANDARDS_LIST = [
    ("01-product.md", "产品设计（含前端）"),
    ("02-backend.md", "后端开发"),
    ("03-security.md", "安全开发"),
    ("04-testing.md", "测试"),
    ("05-ops.md", "部署运维"),
    ("06-ai.md", "AI 应用"),
    ("07-data.md", "数据"),
    ("08-review.md", "评审与完成定义"),
]

failures: list[str] = []


def fail(message: str) -> None:
    failures.append(message)


def read(path: Path) -> str:
    if not path.is_file():
        fail(f"缺少文件：{path.relative_to(ROOT)}")
        return ""
    return path.read_text(encoding="utf-8")


def table_rows(text: str) -> int:
    """Count data rows in the first markdown table that has a 怎么检查 column."""
    lines = text.splitlines()
    rows = 0
    in_table = False
    for index, line in enumerate(lines):
        if line.strip().startswith("|") and "怎么检查" in line:
            in_table = True
            continue
        if in_table:
            if not line.strip().startswith("|"):
                break
            if re.match(r"^\|\s*-+", line.strip()):
                continue
            if line.strip().startswith("|"):
                rows += 1
    return rows


def main() -> int:
    print("八类工程规范自查")
    print(f"仓库：{ROOT}")
    print("-" * 60)

    for filename, label in STANDARDS_LIST:
        path = STANDARDS / filename
        text = read(path)
        if not text:
            continue
        for heading in ["## 这一页管什么", "## 项目事实", "## 规范条目", "## 本课最小集合", "## 违反时怎么处理"]:
            if heading not in text:
                fail(f"{filename} 缺少章节：{heading}")
        if "怎么检查" not in text:
            fail(f"{filename} 的规范条目表缺少“怎么检查”列")
        rows = table_rows(text)
        if rows < 5:
            fail(f"{filename} 的规范条目只有 {rows} 行，至少需要 5 行")
        print(f"  ✓ {label}: {rows} 条规范")

    agents = read(ROOT / "AGENTS.md")
    for filename, _ in STANDARDS_LIST:
        if f"docs/standards/{filename}" not in agents:
            fail(f"AGENTS.md 没有引用 docs/standards/{filename}")
    for keyword in ["默认拒绝", "逐资源授权", "完成定义", "门禁"]:
        if keyword not in agents:
            fail(f"AGENTS.md 缺少安全/评审关键规则：{keyword}")

    rule = read(ROOT / ".cursor" / "rules" / "campusclaw-standards.mdc")
    if "alwaysApply: true" not in rule:
        fail(".cursor/rules/campusclaw-standards.mdc 缺少 alwaysApply: true")
    for filename, _ in STANDARDS_LIST:
        if filename not in rule:
            fail(f"常驻规则没有列出 {filename}")

    skill = read(ROOT / ".cursor" / "skills" / "campusclaw-engineering" / "SKILL.md")
    for workflow in ["加一个页面", "加一个后端接口", "补一组测试", "发一次版本"]:
        if workflow not in skill:
            fail(f"工程技能缺少动作：{workflow}")

    data_dict = read(ROOT / "docs" / "data-dictionary.md")
    for table in [
        "schema_migrations",
        "login_failures",
        "materials",
        "material_versions",
        "knowledge_entries",
        "knowledge_chunks",
        "tags",
        "material_reads",
        "favorites",
    ]:
        if f"`{table}`" not in data_dict:
            fail(f"数据字典缺少表：{table}")

    four_steps = read(ROOT / "docs" / "项目启动-四步核对.md")
    for step in ["建仓库", "定规约", "立规范", "落骨架"]:
        if step not in four_steps:
            fail(f"四步核对缺少步骤：{step}")

    readme = read(ROOT / "README.md")
    for filename, _ in STANDARDS_LIST:
        if f"docs/standards/{filename}" not in readme:
            fail(f"README 没有链接 docs/standards/{filename}")
    if "standards_check.py" not in readme:
        fail("README 没有提到 standards_check.py")
    if "项目启动四步" not in readme:
        fail("README 缺少“项目启动四步”章节")

    spec_entry = read(ROOT / "SPEC.md")
    for filename in ["proposal.md", "design.md", "specs/", "tasks.md"]:
        if filename not in spec_entry:
            fail(f"SPEC.md 没有链接规约文件：{filename}")
    if "archive/campusclaw-baseline.zip" not in spec_entry:
        fail("SPEC.md 没有说明旧实现归档位置")

    archive_zip = ROOT / "archive" / "campusclaw-baseline.zip"
    if not archive_zip.is_file() or archive_zip.stat().st_size == 0:
        fail("缺少 archive/campusclaw-baseline.zip")
    if not (ROOT / "archive" / "campusclaw-baseline.sha256").is_file():
        fail("缺少 archive/campusclaw-baseline.sha256")

    print("-" * 60)
    if failures:
        print(f"未通过：{len(failures)} 项")
        for item in failures:
            print(f"  ✗ {item}")
        return 1
    print("通过：八类规范、常驻规则、工程技能、数据字典、四步核对、SPEC 入口和归档包均齐备。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
