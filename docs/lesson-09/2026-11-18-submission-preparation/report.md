# 第9课最终提交准备报告

已完成本轮四项准备。以submission-files.txt的精确清单提交，技术上的安全提交条件已满足。原工作树未暂存、未创建提交、未推送，两个活动OpenSpec change保持活动。本轮没有修改业务代码、前端依赖或历史证据。

## 修改范围

- .gitattributes新增两个既有docs证据目录及本轮记录目录的-text属性，保护原始字节。
- .gitignore忽略所有.last-run.json及首次失败的本地发布草稿。
- scripts/qa/lesson9/README.md更新为单次>100ms仅WARN，恰好20次全部202且P95严格小于500ms为硬性判据，并注明历史生成器已冻结。
- tests/README.md说明现行发布索引与历史快照边界。
- 活动v2 change的proposal、design、spec和tasks补入发布证据与索引要求，共2条Requirement、12组Scenario。
- 新增scripts/qa/lesson9/verify_release.py及tests/release中的当前索引、历史版本映射、说明和浏览器状态冻结副本。
- 本目录保存本轮独立验证与提交清单，保留验证失败、修正和成功记录。

## 发布与历史索引

当前核心增量索引为tests/release/lesson9-v2-publication.json，以2d2900bf34b52d8df21513c6ef2ebc873df9f345为基线，列出604个选定文件、2个删除项、排除项及工作树/Git blob各自SHA256。上轮建议的44个源路径全部核对，42个现存源文件纳入，2个删除项明确记录。额外内容为本轮索引工具与说明、对应历史manifest和明确枚举的冻结证据，详见source-reconciliation.json。

本目录作为独立验证证据包，通过evidence-index.json校验，submission-files.txt枚举核心文件、现行索引和独立证据包的全部拟提交路径。源索引不自引用自身哈希，证据索引另行记录源索引SHA256。未选中的旧会话专用包装器和既有单独XSS改动保留本地，不通过git add .混入提交。

历史tests/manifest.json原SHA256保持3ff95248c2089532f04d6ea0a1023c2f0aeca3bb8be9f4c8979d18b80304d05a。它对应2d2900b基线加round-02未提交快照，8项旧路径不作为当前文件判据；其中7项由round-02/code-fingerprint.json印证，README旧记录原样保留，未伪造旧源文件。

原浏览器.last-run.json仍在本地，被Git忽略且未进入拟提交清单。内容相同的tests/release/history/browser-run-state.json通过history-context.json别名解析旧gate manifest，旧JSON和原运行文件均未改写。

隔离检出还暴露了旧gate manifest的1个CPython缓存引用。首次验证退出1，记录在validation-01/checkout.log。该缓存被显式列为历史非发布项，保留本地；工作树可验证其原哈希，发布检出不携带缓存。98个旧gate条目中97个解析并验证，1个明确记为非发布缓存。该差异已经写入design和索引说明，不把98项宣称为全部随发布检出。

首次发布草稿tests/release/lesson9-v2.json保留本地并忽略。最终入口使用lesson9-v2-publication.json。后续仅修正新索引的当前路径说明和独立证据包关系，之前的索引草稿也在validation-02/03原样保存；历史manifest的任何预期哈希都未改写。

## 验证结果

|命令或检查|退出码|结果与证据|
|---|---|---|
|python scripts/qa/lesson9/verify_release.py|0|604项核心发布文件通过，52项历史tests索引按版本解释，97个旧gate引用校验；release-verifier.log|
|python docs/lesson-09/2026-11-18-submission-preparation/build_release.py --run-id validation-03|0|独立临时仓库暂存、write-tree、checkout-index，604文件、558不可变证据零差异；validation-03/roundtrip.json|
|篡改、缺失、越界、临时文件四个反例|各1|均按预期拒绝，只改动临时检出；validation-03/*-negative.log|
|72个原换行风险文件|0|逐项工作树SHA256=Git blob SHA256=检出SHA256；eol-72-verification.json|
|639个保护文件|0|历史证据、业务源码、前端依赖及历史manifest均未变化；preservation-after.json|
|python scripts/spec_check.py|0|活动change结构通过；spec-final.log|
|python scripts/standards_check.py|0|八类规范通过；checks/standards-check.log|
|python tests/performance/latency_gate_contract.py|0|13项合同测试通过，包含100ms警告和P95=500ms失败；checks/latency-contracts.log|
|node 官方缓存OpenSpec1.15.0 CLI validate --all --strict|0|全部8项通过；checks/openspec-strict.log，实际命令见checks/results.json|
|npm audit --audit-level=high --json，官方npm源|0|漏洞总数及high/critical均0，原五包未出现在锁文件，依赖文件未改变；npm-audit.json、npm-audit-result.json|
|git diff --check|0|通过；diff-final.log|
|python docs/lesson-09/2026-11-18-submission-preparation/verify_submission.py|见本地receipt|对最终submission-files.txt全清单再次在临时Git中暂存、检出并校验核心和证据索引。receipt保存至被忽略的tests/output/lesson9-final-publication-check，不将校验自身结果递归加入发布哈希|

临时Git实验只写独立临时目录的index和tree对象，没有运行git commit。write-tree验证的是未来提交引用的同一组blob，真实工作树index前后SHA256均为87b339e73fa70fa33d664294894254c63e6f65c55d32887b74e782d7d05d9068。

本轮变更限于说明、Git属性、发布索引及验证工具，因此重跑相关测试、规约和审计，沿用上轮完整make check/check-security/grade/verify/Playwright通过记录，未重复启动Docker或浏览器。

## 安全检查与提交建议

当前604项清单排除了.last-run.json、CPython缓存、失败初始草稿、会话运行目录和凭据文件。前轮完整凭据审阅涉及的冻结文件保持原字节，本轮另扫描选定文件及ZIP文本，未发现真实Token或私钥。测试假口令和合成RabbitMQ连接仍按历史原文保留，不属于运行凭据。

建议按以下边界提交，正文包含Change、Task、Spec、Verify。

1. docs(security-hardening): 0.1 明确整改与v2发布规约，包含两份活动change、04-testing及spec_check登记。
2. fix(security-hardening): 0.2 替换受影响前端工具链，成组提交package.json、lock、toolchain、类型声明、README、删除旧Vite配置及对应回归。
3. fix(async-grading): 0.3 缩小dispatcher事务锁范围，单列既有实现和诊断证据。
4. test(async-grading): 1.1 接入v2观察与P95硬门禁，包含检查、采样、兼容入口及13项合同测试。
5. test(security-hardening): 2.2 准备不可变证据和现行发布索引，包含本轮.gitattributes/.gitignore、README、verify_release、tests/release、明确选定的工具及证据包。共享文件按hunk和依赖顺序处理。

必须按submission-files.txt显式选择文件，另按源索引中的deleted处理2个删除项。未选文件保持原状。四项遗留问题已处理，额外缓存引用已有明确非发布说明；本轮技术准备无未解决阻断项。GitHub Actions新提交的实际结果仍需授权推送后验证，提交、推送和归档本轮均未执行。
