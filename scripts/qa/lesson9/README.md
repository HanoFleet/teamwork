# 第9课测试代码与复现

从仓库根目录运行。`history/` 是原始源码快照，不直接在快照内执行（其相对路径仍按原工作目录设计）。原项目脚本保留在 `scripts/`、`apitest/cases/`、`backend/`、`frontend/e2e/`。

- `python scripts/qa/lesson9/run_fix_validation.py`：Docker Desktop、官方缓存Go1.26.11、Node22、MySQL/RabbitMQ/Qdrant；构建修订前端，独立Compose，20次采样两轮、原verify、Playwright。Windows本机Chrome；只清理自己创建的资源。此调度器记录各阶段结果，整体验收必须再检查performance gate和npm audit，不能以调度器进程0替代。
- `python scripts/qa/lesson9/check_performance.py reports/lesson9-20261118/retest-02/fix-round/performance-1.json reports/lesson9-20261118/retest-02/fix-round/performance-2.json`：采用enqueue-latency-v2。恰好20次提交全部202，P95取第19小值并严格小于500ms为硬性判据；单次>100ms仅输出WARN及序号、request_id和完整耗时，不直接导致整轮失败。非法样本、非202或P95>=500ms仍退出1。
- `performance_probe.py`：从现有async_test.py提取同口径探针，附request_id用于关联API耗时；这是新增代码，不冒称历史丢失脚本。由调度器调用，不打印Cookie/令牌。
- `Dockerfile.tools`：容器化GNU make/Python/Node/Go/Docker CLI，不安装到宿主；原Makefile未修改。
- `finalize.py`：历史报告生成器已冻结，仅保留源码追溯。当前发布内容使用`python scripts/qa/lesson9/verify_release.py`校验，当前索引为`tests/release/lesson9-v2-publication.json`。

历史精确版本：`history/tracked-bd42a61/` 是原工作树真实字节，基线bd42a614；`history/session-final/` 是会话脚本最终落盘版本。原脚本SHA256及当时tracked/untracked/ignored状态在history/inventory.json。早期包装器被覆盖的修订没有可恢复文件，明确记作“原脚本缺失（早期包装器执行版本）”；不得用最终版本冒充原版本，也未按日志重新编写历史版本。

测试数据仅为项目预置合成账号和临时生成内容。凭据运行时随机生成，`.env`与`.env.qa-fix`不提交。输出位于reports/lesson9-20261118/retest-02/fix-round/；历次输出保留在qa/lesson9/，大镜像/二进制不提交。

## 当前发布与历史索引

`tests/manifest.json`属于2d2900b基线加第9课round-02未提交修订的历史快照，原字节保留。旧索引的8个路径已在后续v2阶段变化，其值不用于验证现行路径。版本、原SHA256及证据别名详见`tests/release/history-context.json`和`tests/release/README.md`。

当前发布索引显式列出选定源文件、证据、删除项和排除项，分别记录工作树字节与Git blob的SHA256。浏览器.last-run.json保留在本地并被忽略，其冻结副本通过历史别名解析。旧会话调度器保留为历史工具，重新运行前应核对其环境与输出路径；本轮验证报告位于`docs/lesson-09/2026-11-18-submission-preparation/`。
