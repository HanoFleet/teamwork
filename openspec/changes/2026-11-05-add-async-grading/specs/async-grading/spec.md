# async-grading Specification

## Purpose

规定 CampusClaw 2.0 的异步批改链路：提交只返回 202 + task_id，任务持久化，事务性 outbox 投递到 RabbitMQ，独立 worker 执行并确认，失败按分类退避/死信，重复提交和重复投递只产生一份结果；任务状态可查询，前端轮询到终态。它不扩展完整模块三。

## ADDED Requirements

### Requirement: 消息代理与持久队列

系统 MUST 在 Compose 中增加 RabbitMQ 和独立 worker；只有 web MUST 映射宿主端口，RabbitMQ 与 worker MUST NOT 映射宿主端口。队列 MUST 持久化：exchange `grade`、主队列 `grade.tasks`、重试队列 `grade.retry.1s` 至 `grade.retry.16s`、死信队列 `grade.dead` 都是 durable；发布 MUST 以 persistent delivery mode 发送并等 publisher confirm，消费 MUST 手动 ACK。代理重启后未确认消息 MUST 仍可投递；没有消费者时消息 MUST 留在队列，不得丢失。

#### Scenario: 队列和 worker 从零启动

- **GIVEN** 已填好 `.env`、Docker Compose 可用
- **WHEN** 执行 `docker compose up --build -d --wait`
- **THEN** web、api、db、qdrant、rabbitmq、worker 都启动
- **AND** `docker compose config` 中只有 web 有宿主 `ports`
- **AND** `grade.tasks`、重试队列和 `grade.dead` 都存在且 durable

#### Scenario: 代理重启消息不丢

- **GIVEN** 一条任务消息已发布到 `grade.tasks`，worker 尚未消费
- **WHEN** 重启 rabbitmq 容器
- **THEN** 消息仍在队列中
- **AND** worker 启动后能消费该消息并执行任务

#### Scenario: 停止 worker 不丢任务

- **GIVEN** worker 已停止
- **WHEN** 学生提交并请求批改
- **THEN** 接口仍返回 202，任务状态为 pending
- **AND** 消息留在 `grade.tasks`，没有丢失；启动 worker 后继续执行

### Requirement: 提交与批改业务

系统 MUST 提供 `POST /api/assignments/{id}/submissions`（本班学生本人）和 `POST /api/submissions/{id}/grade`（提交本人）。提交内容去除首尾空白后 MUST 为 1 至 20,000 字符，保存和比较也 MUST 使用去除首尾空白后的正文；内容不变复用当前 submission 行；内容变化 MUST 插入新的 submission 行，`version+1`，并返回新的 `submission_id`，旧行和旧任务 MUST 保留。首次批改请求 MUST 在提交记录、任务记录和 outbox 事务提交后返回 202，响应 MUST NOT 含 `score` 或 `feedback`；同一版本已有结果时按 202 契约返回 200。未登录访问提交、批改和任务查询 MUST 返回 401，响应体 MUST NOT 含提交正文、分数或评语。教师 MUST NOT 以学生身份提交；其他学生（包括跨班）MUST 返回同形 404。

#### Scenario: 学生提交并获得 202

- **GIVEN** `student_a1` 已登录，本班有一份已发布作业
- **WHEN** 提交 1,000 字内容，再调用 `POST /api/submissions/{id}/grade`
- **THEN** 提交返回 200/201 `{submission_id,version:1,status:"submitted"}`
- **AND** 批改返回 202 `{task_id,status:"pending",status_url}`
- **AND** 响应体不含分数或评语

#### Scenario: 重复提交相同内容复用版本

- **GIVEN** `student_a1` 已经有 version 1
- **WHEN** 再次提交完全相同的内容
- **THEN** 返回 200、同一 `submission_id`、`version:1` 和当前状态
- **AND** `submissions` 不新增 version 2，`grade_tasks` 不新增任务

#### Scenario: 未登录被拒绝

- **GIVEN** 请求不带会话 Cookie 或 Bearer 令牌
- **WHEN** 调用提交、批改或任务查询接口
- **THEN** 每个响应都是 401
- **AND** 响应体不含提交正文、分数、评语或任务状态

#### Scenario: 空内容和超长被拒绝

- **GIVEN** `student_a1` 已登录并有一份已发布作业
- **WHEN** 提交空内容、只含空白的内容或 20,001 字内容
- **THEN** 响应状态为 400
- **AND** 不创建 submission、grade_task 或 outbox，也不返回 task_id

#### Scenario: 重复批改同一版本复用任务

- **GIVEN** 同一 submission 已有一个 pending 任务
- **WHEN** 再次调用 `POST /api/submissions/{id}/grade`
- **THEN** 返回同一个 `task_id`，状态仍为 pending
- **AND** `grade_tasks` 和 `outbox_messages` 都不新增第二行

#### Scenario: 教师和其他学生不能提交

- **GIVEN** `teacher_a` 和 `student_b1` 已登录
- **WHEN** 教师对 A 班作业提交，`student_b1` 对 A 班作业提交或对 `student_a1` 的 submission 请求批改
- **THEN** 教师返回 403，`student_b1` 返回同形 404
- **AND** 不创建 submission、task 或 outbox

### Requirement: 202 与 task_id 契约

`POST /api/submissions/{id}/grade` 首次请求 MUST 返回 `202 Accepted`，响应体 MUST 含 `task_id`、`status:"pending"` 和 `status_url`；`status_url` MUST 为 `/api/tasks/{task_id}`。同一 submission/version 已有结果时 MUST 返回 200、同一 `task_id`、`status:"succeeded"` 和 `result`，且 MUST NOT 新建任务。`task_id` MUST 是 ULID，并在 `grade_tasks` 中唯一。202 MUST NOT 表示已完成，MUST NOT 含分数、评语或模型输出。

#### Scenario: 202 响应形状

- **GIVEN** 一份可以批改的提交
- **WHEN** 请求批改
- **THEN** 状态码为 202，`Content-Type` 为 JSON
- **AND** body 恰好含 `task_id`、`status:"pending"`、`status_url`
- **AND** body 不含 `score`、`feedback` 或 `result`

#### Scenario: 已有结果返回 200

- **GIVEN** 同一 submission/version 已经 succeeded
- **WHEN** 再次请求批改
- **THEN** 状态码为 200，返回同一 `task_id`、`status:"succeeded"` 和已有 `result`
- **AND** 不新建 `grade_task`、`outbox_message` 或第二份 `grade_result`

### Requirement: 持久化任务与状态机

系统 MUST 在 `grade_tasks` 中保存 `task_id`、`submission_id`、`submission_version`、`class_id`、`student_id`、`status`、`attempts`、`max_attempts`、`idempotency_key`、`error`、`next_run_at`、`started_at`、`finished_at` 和时间戳。允许状态为 `pending`、`running`、`succeeded`、`failed`、`dead`；终态 MUST NOT 再次调用模型。每次执行 MUST 增加 `attempts` 并写 `started_at`，成功写 `finished_at`；成功结果 MUST 含 0–100 的 `score` 和非空 `feedback`。

#### Scenario: 任务从 pending 到 succeeded

- **GIVEN** 一条 pending 任务
- **WHEN** worker 取走并成功完成
- **THEN** 状态依次为 running、succeeded
- **AND** `attempts=1`，`started_at`、`finished_at` 非空，`error` 为空
- **AND** `grade_results` 有对应 submission/version 的一行，`score` 在 0–100 之间且 `feedback` 非空

#### Scenario: 瞬时失败回到 pending

- **GIVEN** 一次批改遇到模型超时
- **WHEN** worker 完成第 1 次尝试
- **THEN** 任务回到 pending，`attempts=1`，`error` 非空
- **AND** `next_run_at` 为当前时间之后的退避时间

#### Scenario: 终态任务不重复执行

- **GIVEN** 任务已经 succeeded
- **WHEN** 同一条消息被再次投递
- **THEN** worker 直接 ACK，不再调用模型
- **AND** `attempts` 和结果都不变

### Requirement: 事务性发件箱与可靠补投

提交/批改请求 MUST 在同一个数据库事务中写 submission、grade_task 和 outbox_message；MUST NOT 在事务内调用 RabbitMQ 或模型。独立 dispatcher MUST 轮询 pending outbox，使用 `FOR UPDATE SKIP LOCKED` 取批次，发布并等 confirm，成功后标 `published`；失败 MUST 增加 `attempts`、写 `next_attempt_at`，下轮继续。broker 不可用时接口仍 MUST 返回 202，任务保持 pending，恢复后自动补投。

#### Scenario: 事务失败没有孤儿任务

- **GIVEN** 提交请求在插入 outbox 时数据库报错
- **WHEN** 请求返回 503
- **THEN** submission、grade_task 和 outbox 都没有新增行
- **AND** 重试成功后只产生一组记录

#### Scenario: broker 不可用时恢复补投

- **GIVEN** RabbitMQ 已停止
- **WHEN** 学生请求批改，随后启动 RabbitMQ
- **THEN** 请求返回 202，任务为 pending，outbox 为 pending
- **AND** dispatcher 恢复后自动发布，worker 最终把任务变为 succeeded，无需重新提交

#### Scenario: 重复发布由幂等兜底

- **GIVEN** dispatcher 已发布消息但在标记 published 前崩溃
- **WHEN** dispatcher 重启并再次发布同一消息
- **THEN** 至少一次投递允许两条相同消息
- **AND** worker 只保留一份 `grade_results`，任务最终 succeeded

### Requirement: 独立消费者、确认与重投

系统 MUST 提供独立 worker 服务；worker MUST 从 `grade.tasks` 取消息，执行批改，写入结果，并在数据库提交后 ACK。worker MUST NOT 在结果写入前 ACK；进程在 ACK 前终止时，消息 MUST 被代理重投。worker 可独立 stop/start/scale，MUST NOT 接受宿主请求。

#### Scenario: 停止 worker 后恢复执行

- **GIVEN** worker 已停止，任务处于 pending
- **WHEN** 启动 worker
- **THEN** 任务被自动消费并变为 succeeded
- **AND** 学生无需重新提交

#### Scenario: ACK 前崩溃触发重投

- **GIVEN** worker 已调用模型并写入结果，但尚未 ACK
- **WHEN** worker 进程被 kill
- **THEN** 代理重投同一消息
- **AND** 结果表仍只有一行，新一次执行把任务补成 succeeded，`attempts` 增加

### Requirement: 失败分类、退避与死信

worker MUST 区分瞬时失败（模型超时、429、5xx、网络抖动）和永久失败（内容为空、参数非法、技能未启用、密钥无效）。瞬时失败 MUST 重试，最多 `GRADE_MAX_ATTEMPTS=5` 次，间隔 1/2/4/8/16 秒并加 0–250ms 抖动；永久失败 MUST NOT 重试，直接 `failed`。达到上限 MUST 进入 `dead` 并投递 `grade.dead`，保留最后错误和 payload。队列长度、`attempts`、执行耗时和死信数量 MUST 可观测；每条任务日志 MUST 含 `task_id`、`submission_id`、`student_id`、`status`、`attempts`、`duration_ms`，MUST NOT 含提交正文、密钥或模型原始输出。

#### Scenario: 瞬时失败按指数退避

- **GIVEN** 模型连续返回 429
- **WHEN** worker 执行 5 次
- **THEN** 前 4 次回到 pending，`attempts` 递增，间隔递增
- **AND** 第 5 次后状态为 dead，消息进入 `grade.dead`

#### Scenario: 永久失败不重试

- **GIVEN** 提交内容为空或模型密钥无效
- **WHEN** worker 执行
- **THEN** 任务直接变为 failed，`attempts=1`
- **AND** 消息进入 `grade.dead`，不排下一次重试

#### Scenario: 死信保留可追查信息

- **GIVEN** 一条达到上限的任务
- **WHEN** 查看 `grade.dead`
- **THEN** payload 含 task_id、submission_id、submission_version 和最后错误
- **AND** `attempts` 为 5，队列长度可查询

#### Scenario: 任务日志可追溯

- **GIVEN** worker 完成一次任务
- **WHEN** 按 `task_id` 检索单行 JSON 日志
- **THEN** 日志含 `task_id`、`submission_id`、`student_id`、`status`、`attempts`、`duration_ms`
- **AND** 日志不含提交正文、密钥或模型原始输出

### Requirement: 重复提交与重复投递幂等

幂等键 MUST 由 `grade:<submission_id>:<submission_version>` 派生。`grade_tasks.idempotency_key`、`outbox_messages.idempotency_key` 和 `grade_results(submission_id, version)` MUST 有唯一约束。重复提交 MUST 复用同一 task_id；重复投递 MUST 只产生一份结果；结果写入 MUST 用数据库唯一约束/upsert，MUST NOT 只靠先查后写。内容变化产生新 version 和新键，旧结果保留。

#### Scenario: 重复提交只产生一个任务

- **GIVEN** 同一 submission/version 连发两次批改请求
- **WHEN** 两个请求都完成
- **THEN** 两次返回同一个 `task_id`
- **AND** `grade_tasks` 和 `outbox_messages` 各只有一行

#### Scenario: 重复投递只产生一份结果

- **GIVEN** 同一条消息被投递两次，第一次 worker 在写结果前中断，第二次执行完成
- **WHEN** worker 执行两次
- **THEN** `grade_results` 只有一行，`attempts=2`
- **AND** 分数和评语保持不变

#### Scenario: 编辑后重新批改保留旧结果

- **GIVEN** submission/version 1 已 succeeded，记录其 `submission_id`
- **WHEN** 学生修改内容生成 version 2 并再次批改
- **THEN** `submissions` 新增一行、返回新的 `submission_id`，产生 version 2 的新 task 和结果
- **AND** version 1 的 submission 行、task 和结果仍保留，查询旧 task_id 返回旧结果

### Requirement: 任务查询与前端轮询

`GET /api/tasks/{task_id}` MUST 只读返回任务状态、次数、结果/错误和时间；提交本人和本班教师 MUST 可查；跨班、他人和不存在 task_id MUST 返回同形 404（状态码、body、`Content-Type` 相同，仅 `X-Request-ID`/`Date` 可不同）；查询 MUST NOT 触发任务。学生 MUST 能从 `/assignments` 提交并请求批改，终态前 MUST NOT 显示分数；前端 MUST 前 10 秒每 1 秒、之后每 2 秒轮询，终态停止，最多 60 秒；60 秒仍非终态 MUST 停止并提示手动刷新，MUST NOT 无限请求。

#### Scenario: 本人和本班教师可查

- **GIVEN** 一份 submission 和它的 task
- **WHEN** 提交学生和本班教师查询，其他学生和 B 班教师也查询
- **THEN** 前两者返回 200 和完整字段
- **AND** 后两者与不存在的 task_id 返回同形 404，状态码、body 和 `Content-Type` 相同，不含分数或评语

#### Scenario: 前端轮询到终态停止

- **GIVEN** 一个 pending 任务
- **WHEN** 前端按 1 秒/2 秒间隔轮询，直到 succeeded
- **THEN** 终态后不再请求
- **AND** 页面显示 pending、running、succeeded 的可读状态
- **AND** 查询本身不改变 attempts 或任务状态

#### Scenario: 从作业页提交并轮询

- **GIVEN** `student_a1` 已登录，A 班有一份已发布作业
- **WHEN** 打开 `/assignments`，选择作业，提交并请求批改
- **THEN** 页面显示 pending 或 running，且不显示分数
- **AND** 轮询到 succeeded 后显示分数、评语和出处，并停止请求

### Requirement: 三条判据自动化与报告

验收 MUST 落三条判据：① 连续提交 20 份不同内容，P95 响应时间显著小于一次批改执行时间，且响应不含分数；② 停止 worker 后提交返回 202、任务 pending，启动 worker 后自动 succeeded，无需重新提交；③ 同一提交重复请求、同一消息重复投递，最终只有一份结果。三条判据 MUST 转为 `apitest/cases/async/` 用例并随 `make check`/CI 运行；证据 MUST 写入 `reports/async-grading.md`、`reports/risk-concurrency.md`、`reports/risk-transaction.md`；发布 MUST 打 `async-202` 标签。

#### Scenario: 请求时间不随批改时间增长

- **GIVEN** 本地模式通过 `GRADE_LOCAL_DELAY_MS=2000` 固定每次批改耗时 2 秒
- **WHEN** 连续提交 20 份不同内容并各请求一次批改，记录 `time_total`
- **THEN** 提交响应 P95 小于 500ms
- **AND** 每次响应都是 202 且不含分数

#### Scenario: 停 worker 任务不丢

- **GIVEN** worker 已停止
- **WHEN** 提交后查询任务，再启动 worker
- **THEN** 查询为 pending，启动后无需重新提交即可变为 succeeded

#### Scenario: 重复不产生重复结果

- **GIVEN** 同一提交和同一消息各重复一次
- **WHEN** 所有执行完成
- **THEN** `grade_results` 只有一行
- **AND** `reports/risk-concurrency.md` 和 `apitest/cases/async/` 有对应记录/用例
