# 第9课100ms规则正式调整验证记录

变更为 `2026-11-18-observe-enqueue-latency`，实施工作树为 `qa/lesson9/fix-worktree`，分支为 `change/2026-11-18-fix-lesson9-retest`。change保持活动，等待用户确认。新任务清单保持未勾选，供独立验收确认。业务源码与历史证据572个文件SHA256全部一致。

## 来源与引用检查

100ms最早由2026-10-28提交29e3851写入04-testing第41行，原文标注项目值。b3f2cab归档采样与100ms合同测试。课程PDF未在本工作树发现，课程依据采用用户已核对结论。

现行引用清单保存在references.json。两个检查入口为tests/performance/check_single_request_limit.py和scripts/qa/lesson9/check_performance.py；两个采样入口为tests/performance/grade_enqueue_latency.py和scripts/qa/lesson9/performance_probe.py；诊断和对照为grade_latency_diagnostics.py和compare_outbox_isolation.py。它们现在共用evaluate_samples，100ms警告与P95硬断言统一。analyze_grade_waits.py按100ms挑选慢样本的逻辑继续作为诊断过滤。

工程规范04-testing增加第9课专用规则，其他接口保留原项目门槛。原活动整改proposal/design保留旧决策并添加替代关系，两个delta场景与tasks按新规则同步。主规约及已归档change保留原文。

历史history、reports、tests/evidence、tests/validation以及旧档案中的100ms文字和断言保留为来源与证据。两个直接写历史报告的生成器finalize.py和update_lesson9_round2_report.py增加冻结入口提示，保留其历史生成代码供追溯，新评估使用独立目录。历史tests/manifest.json保留为旧源码索引，本轮源码哈希另存current-source-sha256.json。

## 标准区别

|项目|旧规则|enqueue-latency-v2|
|---|---|---|
|样本|20条202|20条202，现场继续检查无score/feedback|
|单次100ms|任一大于100ms整轮失败|大于100ms逐条WARN及保存完整样本，恰好100ms无警告|
|P95|严格小于500ms|严格小于500ms，第19小值|
|非法样本/非202|失败|失败，补充有限非负耗时校验|
|功能、授权、并发、事务、状态|原规约约束|原规约继续约束|

第10课性能验收优先依据老师明确要求的吞吐、P95、错误率、饱和点及改进前后对比。此次20条顺序样本仅覆盖原异步响应判据。

## 原样本离线评估

输入来自reports/lesson9-20261118/retest-02/fix-round/round-02/controlled-comparison/after的performance-1.json和performance-2.json。

|轮次|P95 ms|最大值 ms|100ms警告数|旧规则结果|新规则离线评估|
|---|---|---|---|---|---|
|after 1|64.5362000032037|122.06220000007306|1|失败，原passed=false保留|通过并记录警告|
|after 2|50.45669999890379|77.58109999849694|0|通过|通过|

警告样本index=3，request_id=l9-diagnostic-1-1794991296370412900-3，elapsed_ms=122.06220000007306。新结果在new-rule-evaluation.json和historical-readonly-evaluation.log。旧失败与失败日志继续作为旧标准的真实结果，此次为只读离线重评。未新增现场压测，未据此宣布整项整改验收完成。

## 测试与校验

- 13项合同测试退出0，覆盖100/100.001ms、原始精度、P95=499.999/500/500.001ms、单次900ms、条数0/19/21、200/400/403/404/503、负数/非数值/NaN/Infinity、非法JSON、已有输出保护、现场采样函数复用。两个CLI均验证边界。
- spec_check.py、standards_check.py、security_static.py、security_cases.py、layer_check.py全部退出0。
- OpenSpec 1.15.0 strict全部8项通过，0失败。npx首次在线尝试因缓存写入及网络EACCES失败，随后直接运行已缓存的官方1.15.0 CLI完成同参数校验，版本输出与日志单独保存。
- preservation-before.json与preservation-after.json逐文件一致，572项，changed=[]。包含backend/frontend源码及原始证据，业务差异由既有工作树继承，本轮新增业务修改为0。
- make check已接入合同测试。本轮执行了上述相关测试和结构/静态校验，未重新执行完整make check、check-security、grade、verify或Playwright。它们已有记录保留，合并前仍须按项目要求完整验收。

命令及退出码见checks.json，各项输出在同目录。首次结构检查暴露了PowerShell管道编码问题，修正新增文本后最终结构检查通过；首次合同测试中的文件句柄警告也已修正，最终以ResourceWarning作为错误运行通过。

## 评审状态

规则边界、失败输入、计时口径与历史保护已通过自动化检查。等待用户确认及角色三独立验收，保持活动change和未勾选任务。未提交、推送、归档，未执行额外业务性能优化。
