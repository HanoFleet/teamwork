# 变更提案：2026-11-05-add-async-grading

| 项目 | 内容 |
| --- | --- |
| 变更名 | `2026-11-05-add-async-grading` |
| 阶段 | 第 8 课：异步任务与消息队列 |
| 负责人 | 李斯坦（角色一：制定规约） |
| 评审 | 韩雅慧（角色二：开发系统）、禹霖（角色三：项目验收） |
| 基线 | `v0.1.0-skeleton` + `2026-10-14-upgrade-material-library` 规约 |
| 状态 | 规约已交付，实现与验收待角色二、三 |

## Why

作业批改如果放在提交请求里同步执行，会同时暴露六类问题：

1. 模型调用常要数十秒，网关读超时可能先返回 504，服务端却还在计算。
2. 线程、数据库连接和处理单元被长任务占用，提交高峰会拖慢整站。
3. 刷新或断网后没有执行标识，用户无法区分“还在跑”和“已经失败”。
4. 执行状态只在内存里，进程重启后既不能继续也不能追查。
5. 批改和 Web 实例绑在一起，算力无法独立伸缩。
6. 截止前的瞬时峰值直接压向模型服务，队列没有缓冲。

本 change 把执行从请求链路迁移到独立 worker，并用持久任务、事务性发件箱、队列确认和幂等约束把两个阶段连接起来。提交请求只承诺“已接收”，不承诺“已完成”。

## What Changes

1. **增加消息代理和 worker 服务**：Compose 新增 RabbitMQ 和独立 worker，队列持久化，只有 web 映射宿主端口。
2. **建立最小提交/批改业务**：新增 `assignments`（复用既有占位表）、`submissions`、`grade_results`，提供提交和批改入口；`submissions` 按版本追加，内容变化返回新的 `submission_id`。
3. **提交返回 202 + task_id**：`POST /api/submissions/{id}/grade` 首次立即返回 202、`task_id`、`status:"pending"` 和 `status_url`，响应体不含分数；同一版本已有结果时返回 200、同一 `task_id` 和已有结果。
4. **持久化任务与状态机**：`grade_tasks` 记录 `task_id`、`submission_id`、`submission_version`、状态、`attempts`、`idempotency_key`、错误、起止时间、下次重试时间。
5. **事务性发件箱**：提交记录、任务记录、outbox 记录在同一事务写入；outbox payload 带 `task_id`、`submission_id`、`submission_version`；独立投递器扫描 pending 并发布，失败下轮继续，保证“有提交就有任务”。
6. **独立消费者与确认重投**：worker 按任务中的 `submission_version` 读对应正文、调用模型、写入结果、确认；崩溃未确认时由代理重投，靠幂等兜底。
7. **失败分类、退避与死信**：瞬时失败按 1/2/4/8/16 秒加抖动重试，最多 5 次；永久失败不重试；达到上限进入死信并保留原因。
8. **重复提交/重复投递幂等**：幂等键由 `submission_id + version` 派生，任务、outbox 和结果表都落唯一约束；同一提交最终只有一份结果。
9. **任务查询与前端轮询**：`GET /api/tasks/{task_id}` 只读返回状态、次数、结果/错误；学生从 `/assignments` 页面提交，前端按 1 秒（前 10 秒）再 2 秒轮询，终态停止，最多 60 秒。
10. **三条判据自动化**：提交 P95 不随批改耗时增长、停 worker 任务不丢、重复提交/投递只出一份结果；落 `apitest/cases/async/`、`reports/` 和 `git tag async-202`。

## Out of Scope（本次不做）

- 不做完整模块三：作业编辑/截止/附件、练习与错题本、公告通知、学情统计、课程单元编排。
- 不做教师手工评分 UI 或 AI 批改的评分规则训练；本 change 只处理“提交 → 异步批改 → 结果”的链路。
- 不做 SSE/WebSocket 推送；本课采用轮询。
- 不承诺端到端恰好一次；采用至少一次投递加幂等结果。
- 不改现有登录、材料库、检索和问答接口。
- 不实现 SEC-01～SEC-08 安全自查本身；那是第 8 课任务清单的验收活动，按 `reports/security-precheck.md` 由角色三执行。

## Alternatives Considered（放弃的候选方案）

| 候选方案 | 为什么放弃 |
| --- | --- |
| Redis 列表当队列 | 需要自行实现可见性超时、重投和死信；本课要求完整队列语义，RabbitMQ 的持久化、ACK、DLX 更直接。 |
| 提交事务里直接 publish | 事务回滚但消息已发出会产生孤儿任务；消息发出失败但事务提交会丢任务。outbox 用本地事务保证“有提交必有任务”。 |
| 端到端恰好一次 | 跨数据库和消息代理实现复杂，代价高；本课选择至少一次 + 幂等唯一约束，重复不会产生第二份结果。 |
| 批改放在 API 进程 goroutine | 进程重启任务丢失，无法独立扩缩容；独立 worker 可单独启停和扩实例。 |
| 状态只放内存 | 重启后无法查询和重试；`grade_tasks` 持久化状态机。 |
| SSE/WebSocket 推送 | 本课明确采用轮询，前端和验收都更简单；推送留作可选扩展。 |
| 失败无限重试 | 永久失败会长期占用队列、消耗模型额度；必须有次数上限、分类和死信。 |

## Capabilities

### New Capabilities

- `async-grading`：提交/批改业务、202 + task_id、持久任务与状态机、事务性发件箱、RabbitMQ 队列、独立 worker、确认/重投/退避/死信、幂等、任务查询与轮询、三条判据自动化。

### Modified Capabilities

- 无既有 capability 的行为修改；本 change 在 foundation 的四服务基线上增加 `rabbitmq` 和 `worker`，属于部署增量，不改变已有登录、材料、检索和问答契约。

## Capability–Scenario Map（能力与场景对应）

| Capability | 类型 | Requirement 数 | Scenario 数 | 主要失败路径 | 验收证据 |
| --- | --- | ---: | ---: | --- | --- |
| `async-grading` | 新增 | 10 | 32 | 未登录 401、教师/他人 403、跨班同形 404、数据库不可达 503、broker 不可达 202+pending、瞬时失败重试、永久失败与死信 | `reports/async-grading.md`、`reports/risk-concurrency.md`、`reports/risk-transaction.md`、`apitest/cases/async/`、`make check`、CI |

## Failure Path Coverage（失败路径覆盖）

- **参数非法**：空内容、超过 20,000 字符、非法 `task_id` 返回 400 或 404；不创建 submission、task 或 outbox。
- **无权限**：未登录返回 401；教师以学生身份提交返回 403；同班其他学生和跨班用户返回同形 404；不泄露分数、评语或资源是否存在。
- **资源不存在**：不存在的 assignment、submission、task 与无权访问使用相同状态码和响应形状；查询不创建任务。
- **依赖不可达**：RabbitMQ 停止时提交仍返回 202、outbox 保持 pending，恢复后自动补投；模型 5xx/超时按瞬时失败重试，达到上限进入死信；数据库不可用返回 503，事务回滚后无半截记录。

## Evidence

- `reports/async-grading.md`：三条判据的命令、输出和结论。
- `reports/risk-concurrency.md`：重复提交/重复投递的检查和结果。
- `reports/risk-transaction.md`：提交/任务/outbox 同事务、停消费者、恢复后恰好投递一次、无孤儿任务的记录。
- `apitest/cases/async/`：三条判据的自动化用例，随 `make check` 和 CI 运行。
- `git tag async-202`：本 change 的版本标记。
- `docs/lesson-08/self-check.md`：自查表逐项到 Scenario/Task 的映射。

## Success Criteria（完成现象）

- `npx -y @fission-ai/openspec@1.15.0 validate 2026-11-05-add-async-grading --strict` 退出码 0。
- 每条能力至少一组 Scenario，失败路径覆盖参数非法、无权限、资源不存在、依赖不可达四类。
- 三条判据可被别人按报告中的命令复现，结论一致。
- 重复提交和重复投递只留一份 `grade_results`，`attempts` 增加而分数不变。
- 停 worker 提交返回 202 且任务停在 pending；恢复 worker 后自动完成，无需重新提交。
- 提交响应 P95 显著小于一次批改执行时间，响应体不含分数。
- 实现完成并验收通过后才归档；本阶段只交付规约。
