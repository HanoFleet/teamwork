# 第 8 课异步批改自查映射

> 课程自查表的 10 行目前显示“缺失”，指的是**代码、运行结果和证据**缺失，不是规约文件缺失。规约侧已逐行覆盖：10 条 Requirement、31 条 Scenario、30 条 Task。本文件把每一行钉到具体条款，角色二按 Task 实现，角色三按 Scenario 判定；在真实结果产生前，不把任何一行写成“通过”。

## 1. 十行自查表

| # | 自查项 | 规约覆盖 | 实现与证据 |
| ---: | --- | --- | --- |
| 1 | 消息代理、持久队列 | 已覆盖 | 缺失：Compose 仍只有 web/api/db/qdrant |
| 2 | 批改提交与评分业务 | 已覆盖 | 缺失：现有 `/api` 无提交/批改接口 |
| 3 | 提交返回 202 + task_id | 已覆盖 | 缺失：无 202 响应 |
| 4 | 持久化任务与状态机 | 已覆盖 | 缺失：无 `grade_tasks` 表 |
| 5 | 事务性发件箱与可靠补投 | 已覆盖 | 缺失：无 `outbox_messages` 表与 dispatcher |
| 6 | 独立消费者、确认与重投 | 已覆盖 | 缺失：无 `worker` 服务 |
| 7 | 失败分类、退避、死信 | 已覆盖 | 缺失：无重试队列与 `grade.dead` |
| 8 | 重复提交、重复投递幂等 | 已覆盖 | 缺失：无幂等键和唯一约束 |
| 9 | 任务查询、前端轮询 | 已覆盖 | 缺失：无 `/api/tasks/{id}` 与轮询 |
| 10 | 三条判据自动化及报告 | 已覆盖 | 缺失：无 `apitest/cases/async/` 和 `reports/` 实际结果 |

## 2. 逐行映射

### 2.1 消息代理、持久队列

- **Requirement**：`消息代理与持久队列`
- **Scenario**：`队列和 worker 从零启动`、`代理重启消息不丢`、`停止 worker 不丢任务`
- **Task**：1.1 Compose 增加 RabbitMQ 和 worker；1.2 建立队列拓扑；3.4 独立启停/扩容
- **判定口径**：`docker compose config` 只有 web 有宿主 `ports`；`grade.tasks`、`grade.retry.1s` 至 `grade.retry.16s`、`grade.dead` 都是 durable；重启 rabbitmq 后未消费消息仍在。
- **当前状态**：规约已覆盖；实现与证据待角色二、三。

### 2.2 批改提交与评分业务

- **Requirement**：`提交与批改业务`
- **Scenario**：`学生提交并获得 202`、`重复提交相同内容复用版本`、`未登录被拒绝`、`空内容和超长被拒绝`、`重复批改同一版本复用任务`、`教师和其他学生不能提交`
- **Task**：2.1 提交接口；2.3 重复批改复用 task；2.4 无同步模型调用；4.4 权限与同形 404
- **判定口径**：`student_a1` 提交返回 200/201；相同内容再次提交返回同一 submission/version，不新建任务；首次 `POST /api/submissions/{id}/grade` 返回 202；未登录 401；空内容/超长 400；教师 403；同班其他学生和 B 班学生同形 404；请求链路不调用模型。
- **当前状态**：规约已覆盖；实现与证据待角色二、三。

### 2.3 提交返回 202 + task_id

- **Requirement**：`202 与 task_id 契约`
- **Scenario**：`202 响应形状`、`已有结果返回 200`
- **Task**：2.2 批改入口与 202
- **判定口径**：首次请求 202，`Content-Type: application/json`；body 恰好含 `task_id`、`status:"pending"`、`status_url`；`status_url` 为 `/api/tasks/{task_id}`；不含 `score`、`feedback`、`result`。同一版本已有结果时返回 200、同一 `task_id`、`status:"succeeded"` 和已有结果，不新建任务。
- **当前状态**：规约已覆盖；实现与证据待角色二、三。

### 2.4 持久化任务与状态机

- **Requirement**：`持久化任务与状态机`
- **Scenario**：`任务从 pending 到 succeeded`、`瞬时失败回到 pending`、`终态任务不重复执行`
- **Task**：1.3 建表与迁移；1.4 状态字段；4.1 状态机
- **判定口径**：`grade_tasks` 含 `task_id`、`submission_id`、`class_id`、`student_id`、`status`、`attempts`、`max_attempts`、`idempotency_key`、`error`、`next_run_at`、`started_at`、`finished_at`；状态只允许 `pending/running/succeeded/failed/dead`；终态不再调用模型。
- **当前状态**：规约已覆盖；实现与证据待角色二、三。

### 2.5 事务性发件箱与可靠补投

- **Requirement**：`事务性发件箱与可靠补投`
- **Scenario**：`事务失败没有孤儿任务`、`broker 不可用时恢复补投`、`重复发布由幂等兜底`
- **Task**：3.1 事务性 outbox；3.2 dispatcher 补投
- **判定口径**：submission、grade_task、outbox 同事务；事务内不调用 RabbitMQ/模型；broker 停止时提交仍 202、outbox pending；恢复后自动发布；注入 outbox 插入失败时三张表都无新增。
- **当前状态**：规约已覆盖；实现与证据待角色二、三。

### 2.6 独立消费者、确认与重投

- **Requirement**：`独立消费者、确认与重投`
- **Scenario**：`停止 worker 后恢复执行`、`ACK 前崩溃触发重投`
- **Task**：3.3 worker 消费与 ACK；3.4 独立启停/扩容
- **判定口径**：worker 可单独 stop/start；结果写库提交后才 ACK；kill 后消息重投；结果表仍只有一行；`attempts` 增加。
- **当前状态**：规约已覆盖；实现与证据待角色二、三。

### 2.7 失败分类、退避、死信

- **Requirement**：`失败分类、退避与死信`
- **Scenario**：`瞬时失败按指数退避`、`永久失败不重试`、`死信保留可追查信息`、`任务日志可追溯`
- **Task**：4.2 失败分类与退避
- **判定口径**：429/5xx/超时最多重试 5 次，间隔 1/2/4/8/16 秒加 0–250ms 抖动；空内容、参数非法、技能未启用、密钥无效直接 `failed`；达到上限进 `grade.dead`；日志含 `task_id/submission_id/student_id/status/attempts/duration_ms`，不含正文和密钥。
- **当前状态**：规约已覆盖；实现与证据待角色二、三。

### 2.8 重复提交、重复投递幂等

- **Requirement**：`重复提交与重复投递幂等`
- **Scenario**：`重复提交只产生一个任务`、`重复投递只产生一份结果`、`编辑后重新批改保留旧结果`
- **Task**：2.3 重复批改复用 task；4.3 重复提交/投递幂等
- **判定口径**：`idempotency_key = grade:<submission_id>:<version>`；`grade_tasks.idempotency_key`、`outbox_messages.idempotency_key`、`grade_results(submission_id,version)` 都有唯一约束；重复请求返回同一 `task_id`；重复消息只一行结果，`attempts` 增加而分数不变。
- **当前状态**：规约已覆盖；实现与证据待角色二、三。

### 2.9 任务查询、前端轮询

- **Requirement**：`任务查询与前端轮询`
- **Scenario**：`本人和本班教师可查`、`前端轮询到终态停止`
- **Task**：5.1 任务查询接口；5.2 前端轮询；5.3 结果展示与错误
- **判定口径**：`GET /api/tasks/{task_id}` 只读；本人和本班教师 200；其他学生、B 班教师、不存在 task_id 返回同形 404（状态码、body、`Content-Type` 相同，仅 `X-Request-ID`/`Date` 可不同）；前端前 10 秒每 1 秒、之后每 2 秒，终态停止，最多 60 秒；60 秒后停止并提示手动刷新；查询不改变 `attempts`；failed/dead 显示原因，不提供前端重试按钮。
- **当前状态**：规约已覆盖；实现与证据待角色二、三。

### 2.10 三条判据自动化及报告

- **Requirement**：`三条判据自动化与报告`
- **Scenario**：`请求时间不随批改时间增长`、`停 worker 任务不丢`、`重复不产生重复结果`
- **Task**：6.1 P95；6.2 停 worker；6.3 重复结果与事务检查；6.4 自动化；6.5 观测与标签
- **判定口径**：
  - 判据一：本地批改固定 2 秒，连续提交 20 份不同内容，P95 < 500ms，响应均 202 且不含分数；证据 `reports/async-grading.md`。
  - 判据二：停 worker 提交，任务 pending；启动 worker 后自动 succeeded，无需重新提交；证据 `reports/async-grading.md`。
  - 判据三：重复请求、重复投递最终只有一行 `grade_results`；证据 `reports/risk-concurrency.md`。
  - 事务判据：提交与任务同事务；停消费者提交，恢复后恰好投递一次、无孤儿任务；证据 `reports/risk-transaction.md`。
  - 权限判据：跨班访问 404、跨班检索空结果，复测命令原样可跑；证据 `reports/risk-authz.md`。
- **当前状态**：规约已覆盖；实现与证据待角色二、三。

## 3. 第 8 课安全自查（SEC-01～SEC-08）

这一节是课程任务清单的验收活动，**不是** `async-grading` 规约的替代品。角色三执行并写 `reports/security-precheck.md`；本文件只说明每条与现有规约的关系，不填造结果。

| 检查项 | 与规约的关系 | 执行方式 | 当前状态 |
| --- | --- | --- | --- |
| SEC-01 未登录访问受保护接口 | `async-grading` / `提交与批改业务` 的 `未登录被拒绝`；沿用 `auth-upload` 的 401 | 不带 Cookie/Bearer 逐个调用清单接口，记录实际状态码 | 待角色三执行 |
| SEC-02 跨班访问与跨班检索 | `async-grading` / `教师和其他学生不能提交`、`本人和本班教师可查`；`auth-upload` / 班级隔离 | A 班学生访问 B 班作业/提交/任务，B 班身份检索 A 班；期望 404 和空结果 | 待角色三执行 |
| SEC-03 学生修改技能与提示词 | 本 change 没有技能/提示词写接口；不能把“无接口”写成 403 绿 | 先列写入类接口；无接口的条目按“不可测/缺口”记红 | 待角色二补接口或角色三记红 |
| SEC-04 技能工具绕过鉴权 | `async-grading` / `提交与批改业务`、`202 与 task_id 契约`；学生直接调批改写入 | 学生直接调用提交/批改/任务写入，记录是否执行、库中留下什么 | 待角色三执行 |
| SEC-05 密钥明文泄漏扫描 | 与规约无关，属资产检查 | `make check-security` 或 `python3 scripts/secret_scan.py`；命中立即轮换并清历史 | 待角色三执行 |
| SEC-06 依赖漏洞基线 | 与规约无关，属资产检查 | `make check-security` 或 `cd frontend && npm audit --audit-level=high`；保存基线报告 | 待角色三执行 |
| SEC-07 审计日志可追溯 | `async-grading` / `失败分类、退避与死信` 的 `任务日志可追溯` | 任选一次任务调用，按 `task_id` 回查日志；列出实际字段和缺口 | 待角色三执行 |
| SEC-08 恶意文档/提示词注入（选做） | 不试；只准备素材 | 1 份含“忽略以上指令”的讲义 + 3 条诱导提问，打包进 `reports/` 或素材目录 | 未准备；待角色三 |

**至少保留 1 条红项。** 当前最可能的红项是 SEC-03（没有技能/提示词写接口）和 SEC-08（仅素材，未试）。不得为了“全绿”把“无接口”写成“已拒绝”。

## 4. 报告与责任人

| 交付物 | 内容 | 责任人 | 当前状态 |
| --- | --- | --- | --- |
| `reports/async-grading.md` | 判据一、判据二、观测值、复跑命令 | 角色三 | 待执行 |
| `reports/risk-concurrency.md` | 重复提交/重复投递只出一份结果 | 角色三 | 待执行 |
| `reports/risk-transaction.md` | 提交/任务/outbox 同事务、停消费者恢复、无孤儿任务 | 角色三 | 待执行 |
| `reports/risk-authz.md` | SEC-02 跨班一条，命令可原样复跑 | 角色三 | 待执行 |
| `reports/security-precheck.md` | SEC-01～SEC-07 三段式记录与红/绿判定 | 角色三 | 待执行 |
| `reports/security-baseline.md` | 密钥扫描、依赖审计基线 | 角色三 | 待执行 |
| `reports/review-01.md` | 交叉评审“手段/查了什么/判据/结果” | 角色二或角色三 | 待执行 |
| `apitest/cases/async/` | 三条判据自动化，随 `make check`/CI | 角色二 | 待实现 |
| `git tag async-202` | 验收通过后的版本标记 | 角色三 | 待打 |

## 5. 复跑命令

```bash
npx -y @fission-ai/openspec@1.15.0 validate 2026-11-05-add-async-grading --strict
python3 scripts/spec_check.py
make check
make check-security
```

- `make check` 中的 `spec_check.py` 会同时检查 material-library 和 async-grading 两个活动 change。
- `make check-security` 只覆盖 SEC-05、SEC-06；其余 SEC 条目仍需角色三按清单人工执行。
- 所有报告写实际命令、实际输出和实际时间；命令失败就写失败，不用“应该可以”代替。

## 6. 完成顺序

1. 角色二按 `tasks.md` 的 0→3 组实现队列、表、提交接口和 worker；每组勾选前跑对应 verify。
2. 角色三在实现后执行三条判据和 SEC-01～SEC-07，先写实际结果，再判定红/绿；至少保留 1 条红。
3. 角色三独立复现至少 2 条 SEC，判定一致后写 `reports/review-01.md`。
4. 全部通过后角色一才把本 change 归档，把 delta 合入 `openspec/specs/`；未通过前不改长期规约。
5. 本文件的状态列由角色三在证据产生后更新；规约条款由角色一维护，实现者不得为了通过而改 Scenario。
