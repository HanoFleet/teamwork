# Historical report generator retained for provenance only.
raise SystemExit("Historical output is frozen. Use docs/lesson-09/2026-11-18-observe-enqueue-latency for current evaluations.")
"""Append the measured lesson9 round-02 results without rewriting earlier rounds."""
import collections
import csv
import datetime
import hashlib
import io
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/lesson9-20261118/retest-02"
OUT = REPORT / "fix-round/round-02"
ROUND = "第二轮续修-20261118"
MARKER = "<!-- lesson9-fix-round-02 -->"


def load(path):
    return json.loads(path.read_bytes())


def write_json(path, data):
    path.write_bytes((json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode())


def append_section(path, text):
    old = path.read_text(encoding="utf8") if path.exists() else ""
    old = old.split(MARKER)[0].rstrip()
    path.write_bytes((old + "\n\n" + MARKER + "\n" + text.rstrip() + "\n").encode())


def append_csv(path, rows):
    raw = path.read_bytes()
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""))
    fields = reader.fieldnames
    previous_line = reader.line_num
    for existing in reader:
        if existing.get("轮次") == ROUND:
            # Replace only this generator's appended round. Preserve all earlier
            # CSV bytes, quoting and line endings, including historical failures.
            prefix = "".join(raw.decode("utf8").splitlines(keepends=True)[:previous_line])
            path.write_bytes(prefix.encode())
            break
        previous_line = reader.line_num
    buffer = io.StringIO(newline="")
    csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n").writerows(rows)
    with path.open("ab") as stream: stream.write(buffer.getvalue().encode())


def main():
    now = datetime.datetime.now().astimezone().isoformat()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    initial = load(OUT / "initial-state.json")
    audit = load(OUT / "logs/audit-after.txt")
    before = load(OUT / "audit-before.json")
    comparison = load(OUT / "controlled-comparison/summary.json")
    native = load(OUT / "native-security-gate/result.json")
    regression = load(OUT / "final-regression/summary.json")
    grade = load(OUT / "grade-report.json")
    assert audit["metadata"]["vulnerabilities"]["total"] == 0
    assert native["exit"] == 0 and regression["verify"] == 0 and regression["playwright"] == 0
    assert grade["counts"] == {"passed": 18, "failed": 0, "total": 18}
    gates = dict(line.split("\t") for line in (OUT / "logs/original-gates-results.tsv").read_text().splitlines())
    assert gates == {"check": "0", "grade": "0"}
    fingerprint_files = ["Makefile", ".github/workflows/check.yml", "frontend/package.json", "frontend/package-lock.json", "frontend/toolchain.mjs", "frontend/src/assets.d.ts", "backend/Dockerfile", "backend/internal/outbox/dispatcher.go", "scripts/security_gate.py", "scripts/govuln_check.py", "scripts/spec_check.py"]
    fingerprint_files += [str(p.relative_to(ROOT)).replace("\\", "/") for folder in ["tests/environment", "tests/performance", "tests/regression", "tests/security", "tests/support", "openspec/changes/2026-11-18-fix-lesson9-retest"] for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts]
    fingerprints = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in sorted(set(fingerprint_files))}
    write_json(OUT / "code-fingerprint.json", {"head": head, "uncommitted": True, "files": fingerprints})
    (OUT / "code-diff.patch").write_bytes(subprocess.check_output(["git", "diff", "--binary"], cwd=ROOT))
    version = head + " + 未提交差异（R2/code-fingerprint.json）"
    case_specs = [
        ("DEP-CI", "npm ci", 0, "干净锁文件安装成功", "logs/npm-ci.txt"),
        ("DEP-AUDIT", "npm audit --json --audit-level=high", 0, "全量审计 total/high/critical=0", "logs/audit-after.txt"),
        ("FRONTEND-BUILD", "npm run build", 0, "TypeScript noEmit与生产构建通过", "logs/frontend-build-final.txt"),
        ("FRONTEND-TOOLCHAIN", "node --test tests/regression/frontend_toolchain.test.mjs", 0, "资源/深链接/双代理/Host拒绝/503断依赖断言通过", "logs/toolchain-regression-final.txt"),
        ("MAKE-SECURITY", "mingw32-make check-security（原Makefile目标）", native["exit"], "密钥扫描、官方全量审计和实时govulncheck均通过", "native-security-gate/make-check-security.log"),
        ("MAKE-CHECK", "make check", int(gates["check"]), "规约/静态/Go测试vet/前端构建通过", "logs/make-check.txt"),
        ("MAKE-GRADE", "make grade", int(gates["grade"]), "18/18，失败0", "grade-report.json"),
        ("VERIFY", "原scripts/verify.py main（仅环境/输出适配）", regression["verify"], "全部原断言通过，含事务回滚/幂等/补投/SEC03/04/07", "final-regression/verify.md"),
        ("PLAYWRIGHT", "frontend/e2e: npx playwright test", regression["playwright"], "作业提交轮询、XSS页面源码：2/2，跳过0", "final-regression/playwright.txt"),
        ("PERF-LOCK", "同Compose镜像对照 + data_lock_waits", 0, "修复前outbox锁边27/6，修复后0/0", "performance-analysis.json"),
        ("PERF-100", "python scripts/qa/lesson9/check_performance.py <两个after样本文件>", 1, "修复后max122.062/77.581ms，超100ms为1/0；严格失败", "logs/performance-gate.txt"),
    ]
    cases = [{"用例编号": name, "关联需求": "security-hardening/复测整改证据；async-grading/事务性发件箱与可靠补投", "前置条件": "独立工作树；合成账号；Node24.22.2/npm11.19.1审计；环境与源码指纹见R2", "输入与操作": command, "预期结果": "原入口退出0；性能任一单次>100ms失败；功能正常且数据边界不变", "实际结果": f"exit={code}；{actual}", "状态": "通过" if code == 0 else "失败", "证据位置": "fix-round/round-02/" + evidence, "执行时间": now + "（具体采样/命令时间见证据）", "被测提交": version, "轮次": ROUND} for name, command, code, actual, evidence in case_specs]
    for row, spec in zip(cases, case_specs):
        row["执行时间"] = datetime.datetime.fromtimestamp((OUT / spec[4]).stat().st_mtime).astimezone().isoformat() + "（该次结果落盘；窗口见summary）"
    append_csv(REPORT / "用例执行表.csv", cases)
    defect_rows = []
    for package in ["@vitejs/plugin-react", "fdir", "picomatch", "tinyglobby", "vite"]:
        defect_rows.append({"缺陷编号": "L9-DEP-001", "首测来源": "复测发现的前端依赖缺陷", "原失败用例": "SEC-06/DEP-AUDIT", "首次提交": initial["head"], "首次实际": "high5 critical0；同根GHSA-fc5q-39xc-vjpf传播", "首次证据": "fix-round/round-02/audit-before.json", "修复提交": "未提交（本地工作树）", "实际复测提交": version, "执行时间": now, "预期": "原make check-security退出0；全量high0 critical0", "实际": f"{package}链从正式锁文件移除；esbuild0.28.2替代实际构建能力；最终原入口exit0，audit total0；构建/Playwright通过", "复测状态": "复测通过", "本轮证据": "fix-round/round-02/logs/audit-after.txt；native-security-gate/result.json；final-regression/", "所需材料": "开发体验由Fast Refresh改为整页刷新，待用户评审；未提交", "修复文件路径": "frontend/package.json；frontend/package-lock.json；frontend/toolchain.mjs；frontend/src/assets.d.ts", "防御性核验": "未omit/白名单/overrides/降低阈值；原安全门禁通过", "轮次": ROUND, "子项": package})
    defect_rows.append({"缺陷编号": "L9-PERF-001", "原失败用例": "PERF-100", "首次提交": "bd42a6149e975c1ed217fb9349621443a3be53d5 + 历史未提交差异", "首次实际": "179.6、253.7、349.7ms原样保留", "首次证据": "fix-round/performance-1.json；performance-2.json；qa/lesson9/retest-02/recovery/summary.json", "修复提交": "未提交（仅dispatcher事务READ COMMITTED）", "实际复测提交": version, "执行时间": now, "预期": "每轮20个202，所有单次<=100ms", "实际": "同Compose：before max317.573/109.244ms，after122.062/77.581ms；超限1/1→1/0。outbox锁边27/6→0/0；剩余122ms请求API117ms、重叠COMMIT87.352ms及持久化sync等待。原verify另20次max70.4ms不抵消失败。", "复测状态": "复测失败", "本轮证据": "fix-round/round-02/controlled-comparison/；performance-analysis.json；logs/performance-gate.txt", "所需材料": "保持持久化的存储I/O排查与同口径再验；不能以取消刷盘或提高门槛修复", "修复文件路径": "backend/internal/outbox/dispatcher.go", "防御性核验": "保留行锁/SKIP LOCKED/消息确认/唯一约束；MySQL flush_at_commit=1、sync_binlog=1；完整verify通过", "轮次": ROUND, "子项": "单次100ms；部分根因已修复但整项未通过"})
    for row in defect_rows:
        row["执行时间"] = native["time"] if row["缺陷编号"] == "L9-DEP-001" else comparison["started"] + " 至 " + comparison["finished"]
        if row["缺陷编号"] == "L9-DEP-001":
            row["本轮证据"] = "fix-round/round-02/logs/audit-after.txt；fix-round/round-02/native-security-gate/result.json；fix-round/round-02/final-regression/"
        else:
            row["本轮证据"] = "fix-round/round-02/controlled-comparison/；fix-round/round-02/performance-analysis.json；fix-round/round-02/logs/performance-gate.txt"
    append_csv(REPORT / "缺陷复测表.csv", defect_rows)
    counts = dict(collections.Counter(x["状态"] for x in cases))
    summary = {"time": now, "head": head, "origin_main": subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=ROOT, text=True).strip(), "branch": "change/2026-11-18-fix-lesson9-retest", "uncommitted": True, "dependency": {"status": "复测通过", "before": before["metadata"]["vulnerabilities"], "after": audit["metadata"]["vulnerabilities"], "original_security_gate": native}, "performance": {"status": "复测失败", "threshold_ms": 100, "comparison": comparison, "original_verify_extra_samples": regression.get("verify_latency")}, "cases_this_round": counts, "case_total": len(cases), "defects_latest": {"复测通过": 1, "复测失败": 1}, "grade": grade["counts"], "verify": regression["verify"], "playwright": regression["playwright"], "conclusion": "依赖修复验收通过；性能部分改善但原100ms门槛仍失败；整体未完成，不提交不推送"}
    write_json(OUT / "summary.json", summary)
    report = f"""# 第二轮续修实测结论

记录时间 {now}。基线/最新main `{head}`，沿用 change/2026-11-18-fix-lesson9-retest；本轮把原bd42工作树快进到只新增测试归档的main，原未提交改动先保存 initial-state.json / initial-tracked-diff.patch，再继续修改。所有本轮修改未提交、未推送。

## 当前结论

- **L9-DEP-001：复测通过。** 修复前5 high同根picomatch链；替换实际使用的Vite/React插件为esbuild0.28.2，所有产品运行时依赖范围不变；锁文件重装、构建、业务与XSS回归、原make check-security通过。Windows GNU make命令为mingw32-make check-security，Node24.22.2/npm11.19.1/Python3.12.7，由真实工具启动适配转发，退出码0。LinuxNode22/npm10同门禁也有一次通过，后续TLS及旧quick端点失败独立保留，不删除。
- **L9-PERF-001：复测失败（部分根因已修复）。** 仅将dispatcher批次事务设为READ COMMITTED，outbox锁边27/6降为0/0。相同Compose/DB/broker/前端与2×20协议，before最大317.573/109.244ms，after122.062/77.581ms，超100次数1/1→1/0；仍有一次超限，严格门槛退出1。
- make check=0，make grade=0（18/18），完整verify=0，Playwright=0（2/2，无跳过）。后续verify另20样本最大70.4ms，与受控对比独立，不能抵消122.062ms。**整体整改仍未通过，不归档change、不发布。**

## 根因、方案与限制

1. 5 high为picomatch及fdir/tinyglobby/Vite/React插件的传播节点，不是5个独立公告。官方picomatch<=4.0.7受影响且无安全发布；最新Vite8.3.8仍5 high，Vite6.2.7引入其他high（历史证据保留）。Rsbuild2.3.3虽audit=0，实际dist/tinyglobby.js内嵌picomatch4.0.5，已拒绝。esbuild候选及最终全量audit均0，没有force、override、omit或改阈值。实际源码仅React/TSX/CSS，没有Vite专属import.meta使用；补CSS声明，构建保留tsc与静态Nginx部署，dev/preview保留深链接与代理。开发刷新改为整页刷新，Fast Refresh状态保留不再提供，已写入规约和frontend/README.md，待审阅。
2. 修改前317.573ms请求的API耗时312ms，重叠outbox插入等待273.217ms；data_lock_waits直接捕获PRIMARY supremum X锁。默认REPEATABLE READ下dispatcher取批次后等待broker confirm时保持间隙锁。仅dispatcher使用READ COMMITTED，API/worker事务、行锁、确认、唯一约束不变。依据[MySQL隔离文档](https://dev.mysql.com/doc/refman/8.0/en/innodb-transaction-isolation-levels.html)。修复后122.062ms请求的API117ms，重叠COMMIT87.352ms及redo/binlog/doublewrite sync；本轮把剩余瓶颈缩小到数据库持久化I/O，尚未证明宿主设备/VM内具体原因，不猜改业务。不关闭持久化：前后MySQL8.0.46、flush_at_trx_commit=1、sync_binlog=1、flush_method=fsync均相同。全部原始样本、SQL和资源快照保留，历史179.6/253.7/349.7ms文件不变。

## 证据与运行

本目录即 reports/lesson9-20261118/retest-02/fix-round/round-02/；主要证据如下，全部位于项目内：

|内容|路径|
|---|---|
|初始工作现场与实际差异|initial-state.json、initial-tracked-diff.patch、code-diff.patch、code-fingerprint.json|
|精确CI工具链审计、锁文件重装/构建|audit-before.json、logs/audit-after.txt、logs/npm-ci.txt、logs/frontend-build-final.txt|
|候选与拒绝原因|esbuild-*.txt、rsbuild-*.txt、rsbuild-rejection.json；上一轮fix-round/logs/audit-rejected-vite6.json|
|原安全门禁（最终同版Node/npm）|native-security-gate/result.json、make-check-security.log|
|原make check/grade|logs/make-check.txt、make-grade.txt、original-gates-results.tsv、grade-report.json|
|首次诊断、锁证据与受控前后80样本|diagnostic-retry/、before-lock-fix/、controlled-comparison/before/、after/|
|慢请求到API/数据库关联及严格判定|performance-analysis.json、logs/performance-gate.txt、performance-gate.exit.txt|
|最终完整业务/防御性回归与页面源码|final-regression/verify.md、playwright.txt、xss-page-source.md、summary.json|

测试功能、步骤、运行入口、依赖和归档状态见仓库tests/README.md的续修节。主要复现命令见该索引与脚本--help。前后对比命令为 `python -X utf8 tests/performance/compare_outbox_isolation.py --subnet <未占用子网> --build-proxy <本地下载代理> --before-image <已验证原镜像> --after-image <修复镜像> --output <证据目录>`；修复镜像必须从本工作树实际构建，不可套用旧后端镜像。后端构建增加可选GOPROXY build arg，默认值不变；本地用仓库已有goproxy.cn,direct恢复模块下载，不关闭go.sum校验，代理不注入应用。

Windows源文件UTF8导致首次verify部分执行后UnicodeDecodeError，后续明确使用python -X utf8完整复跑通过；旧部分输出未当通过。首次命令名适配自检发现引号丢失，失败C源码已归档，最终转发空格/引号/反斜线和退出7自检通过后才执行原门禁。既有xss-page-source.md未提交内容已按初始快照恢复，新浏览器证据独立保存。仅清理本轮生成的隔离资源/凭据，所有测试源码在清理前已保存在tests/。

## 汇总口径与待办

本轮最终检查行共{len(cases)}行：{counts}。通过率如需使用为10/11（通过检查行/本轮全部最终检查行），不把18个grade子项、2个浏览器用例、80个性能样本或5个依赖传播节点重复计入。缺陷按编号去重：1项通过、1项失败；旧轮行保留。

尚需：保持刷盘语义的存储/VM I/O定位和原100ms再验；用户审阅工具链迁移的开发体验变化；真人独立复现至少2条、正式演示录像与真人返工签字。AI实测记录不替代真人材料，已准备的复现/录屏清单仍在父fix-round/。
"""
    (OUT / "复测结论.md").write_bytes(report.encode())
    append_section(REPORT / "复测报告.md", "## 第二轮续修最新结果\n\n本节替代前文的当前状态，历史数据全部保留。L9-DEP-001原安全门禁通过、全量审计0；L9-PERF-001锁等待改善但仍122.062ms超100，整体未通过。make check/grade、完整verify与2条Playwright通过。\n\n详见[本轮结论与完整证据](fix-round/round-02/复测结论.md)、[汇总](fix-round/round-02/summary.json)，实际被测版本为main 2d2900b + 未提交源码指纹。")
    append_section(REPORT / "证据索引.md", "## 第二轮续修证据\n\n[结论与运行/证据表](fix-round/round-02/复测结论.md)、[源码与实际差异](fix-round/round-02/code-fingerprint.json)、[慢请求关联](fix-round/round-02/performance-analysis.json)、[汇总](fix-round/round-02/summary.json)。全部新增/修改测试入口逐项见[tests索引](../../../tests/README.md)。本轮原安全门禁通过，100ms门槛失败，不能用后续单轮通过覆盖失败。")
    append_section(REPORT / "课程要求映射.md", "## 第二轮续修补充\n\n依赖安全门禁现已实际通过，完整业务/安全回归和18项grade通过，证据见[本轮结论](fix-round/round-02/复测结论.md)。性能原100ms门槛仍失败，课程整体完成结论仍为未完成。真人独立复现、正式录像、真人返工签字仍需补齐；本地AI实测记录不替代。材料准备在reports下，未提交或发布。")
    append_section(REPORT / "fix-round/返工记录.md", f"## 第二轮实际返工（{now}）\n\n- 开始现场见round-02/initial-state.json；实际执行窗口以各summary时间为准，不编造净人工分钟数。\n- 依赖：识别Vite工具依赖用途，拒绝仍高危的升级/降级及内嵌受影响代码的Rsbuild，迁移esbuild；补CSS类型声明、工具HTTP回归；原门禁最终0。Fast Refresh改整页刷新写明。\n- 性能：补API/SQL/锁观测，抓到outbox supremum锁；先补规约，再只改dispatcher隔离级别；同环境前后对比锁边降为0，但122.062ms仍失败，保留部分修复。\n- 环境：Go模块EOF后用原仓库Go代理build arg恢复构建；Go漏洞TLS、npm旧端点/断连失败保留。Windows命令适配首次参数自检失败，归档失败源码，修正引用与退出码转发后同CI版本原门禁通过。\n- 回归：make check0、grade0/18项、完整verify0、Playwright0/2项；首次UnicodeDecodeError独立保留，UTF8重跑。原脏XSS报告恢复，新证据另存。\n- 数据：原始179.6/253.7/349.7ms及历轮报告不变，新样本不删除。不提交、不推送、不替真人签字。详细[结论](round-02/复测结论.md)。")
    append_section(ROOT / "docs/lesson-09/fix-20261118.md", "## 第二轮续修\n\n当前基线已快进main 2d2900b，仍为未提交工作树。[最新报告](../../reports/lesson9-20261118/retest-02/fix-round/round-02/复测结论.md)：依赖原门禁通过，性能锁根因部分修复但122.062ms超100，整体未通过。开发体验变化及原始失败均有记录，不发布。")
    # Keep the archive hash index current, excluding runtime/output and itself.
    manifest = {}
    for path in (ROOT / "tests").rglob("*"):
        if not path.is_file() or path.name == "manifest.json" or any(x in path.parts for x in [".runtime", "output", "__pycache__"]): continue
        manifest[str(path.relative_to(ROOT)).replace("\\", "/")] = hashlib.sha256(path.read_bytes()).hexdigest()
    write_json(ROOT / "tests/manifest.json", manifest)
    write_json(OUT / "manifest.json", {str(p.relative_to(OUT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.rglob("*") if p.is_file() and p != OUT / "manifest.json"})
    print(json.dumps({"cases": counts, "dependency": "复测通过", "performance": "复测失败", "head": head}, ensure_ascii=False))


if __name__ == "__main__":
    main()
