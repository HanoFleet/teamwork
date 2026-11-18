# 入队延迟观察规则设计

## Context
实施位于第9课复测工作树。本change替代2026-11-18-fix-lesson9-retest中单次100ms阻断条款。主规约与归档保留，用户确认后再归档delta。

## Decisions
### D1 统计口径
选了什么：固定20次，nearest-rank P95取第19小值，严格小于500ms。100ms恰好相等无警告，大于时逐条WARN含index、request_id及完整elapsed_ms。
放弃了什么：单次100ms阻断整轮。
代价由谁承担：测试负责人检查警告及环境，第10课依据吞吐、P95、错误率、饱和点和改进前后对比验收。

### D2 证据与范围
选了什么：仅第9课异步批改复测使用enqueue-latency-v2。其他接口保留原项目门槛。只读原samples重算，历史passed和single_request_pass原样保留，新结果独立写入。
放弃了什么：覆盖历史失败、将离线重评称为新实测。
代价由谁承担：报告作者区分旧标准失败与新标准评估。历史生成器finalize.py和update_lesson9_round2_report.py冻结入口，保留源码追溯。

## Interfaces
共用tests/performance/check_single_request_limit.py的evaluate_samples和print_evaluation，兼容CLI调用同一函数。可选--output独占创建结果文件，现存路径退出1。全部入口以passed决定退出码。
恰好20条、有限非负数值耗时、每条202为硬条件，accepted_without_result存在时必须为true。现场采样继续断言响应无score/feedback。缺失或畸形JSON、NaN、Infinity、负数、非数值及400/403/404/503均失败。

## Data Model
新增rule、warnings、over_100_ms、p95_ms、async_p95_pass、passed，业务数据模型无变化。

## Migration Plan
先写delta，再更新规范与脚本，增加边界及采样入口测试。保留历史tests/manifest.json，当前源码另列哈希。历史证据及业务源码执行前后SHA256逐项比较。待用户确认，保持change活动。

## Risks / Trade-offs
20次顺序样本仅验证原异步响应判据，第10课吞吐与饱和点需单独实测。功能、权限、并发、事务、幂等、broker恢复与任务状态流转继续按既有规约验收。本规则为正式修订，持续生效至后续正式变更替代。

## 提交准备与索引版本

本轮发布基线为2d2900bf34b52d8df21513c6ef2ebc873df9f345加明确选定的工作树差异。根.gitattributes对两个既有docs证据目录及本轮验证记录目录使用-text，保持原字节；tests目录沿用既有-text。Git实验仅在独立临时仓库写index/tree并checkout-index，原仓库不暂存、不创建提交。

保留tests/manifest.json及两个旧docs目录内所有索引字节。tests/release/lesson9-v2-publication.json是现行发布增量索引，记录worktree_sha256与git_blob_sha256，区分源代码正常LF转换与不可变证据。索引自身通过独立校验命令读取，不包含自引用哈希。新验证日志与最终报告由独立证据索引记录，避免自引用。历史8项哈希属于round-02未提交快照，不能将未知原字节重建后冒充历史源文件。

浏览器原.last-run.json留在本地并忽略，内容相同的tests/release/history/browser-run-state.json作为冻结证据保留。历史gate manifest通过tests/release/history-context.json显式路径别名解析，旧JSON不修改。现行发布索引不收录任何.last-run.json、凭据、运行缓存及会话专用包装器。根据上轮44项建议精确核对源码，额外收录本轮README、验证脚本、索引说明和明确列出的冻结证据。

隔离验证进一步发现旧gate manifest含1个被忽略的CPython缓存引用。本轮将其显式记为历史excluded_runtime，保留旧JSON与本地缓存字节，不复制编译缓存入库。98个历史条目中97个解析为发布证据，1个为非发布缓存；当前索引必须验证全部现行文件。首次验证草稿不发布，验证结果原样保留。
