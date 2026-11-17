# 设计：2026-11-05-add-async-grading

## Context

当前仓库已有 foundation 骨架（Compose、`/live`、`/health`、JSON 日志、优雅停机）和材料库规约；作业提交/批改业务还没有实现。第 8 课要求把批改执行从请求链路迁移到独立 worker，用持久任务和消息队列连接两个阶段。本 change 只设计这条最小链路，不扩展完整模块三。

## Goals / Non-Goals

**Goals:**

- 提交接口只写入并返回 202 + `task_id`，不等待模型。
- 任务、outbox 和结果都持久化；worker 可独立启停、确认和重投。
- 瞬时失败按指数退避重试，达到上限进入死信；永久失败不重试。
- 重复提交和重复投递最终只产生一份结果。
- 三条判据可复现、可自动化、可归档。

**Non-Goals:**

- 不做完整作业编辑、截止、附件、通知、学情、错题本和课程单元。
- 不做 SSE/WebSocket、教师手工评分 UI、模型评分规则训练。
- 不承诺恰好一次；采用至少一次 + 幂等。
- 不实现 SEC-01～SEC-08 安全自查，只提供 `reports/security-precheck.md` 的清单位置。

## Decisions

### D1 RabbitMQ 而不是 Redis 列表

- **选了什么**：RabbitMQ 3.13，durable direct exchange `grade`，durable queue `grade.tasks`，DLX `grade.dlx`；publisher confirms、consumer manual ack、prefetch 1。
- **放弃了什么**：Redis list + 可见性超时，或直接用数据库轮询当队列。
- **代价由谁承担**：Compose 多一个 broker 和运维面；收益是持久化、ACK、重投、死信语义现成，验收只需 Docker。

### D2 事务性发件箱，而不是事务内直接 publish

- **选了什么**：提交事务同时写 `submissions`、`grade_tasks`、`outbox_messages`；api 内的 dispatcher 每秒扫描 `outbox_messages.status='pending'`，用 `SELECT ... FOR UPDATE SKIP LOCKED` 取一批，发布并收到 confirm 后标 `published`；失败写 `attempts`/`next_attempt_at`，下轮继续。
- **放弃了什么**：在提交事务里直接调用 RabbitMQ；事务外先写任务再 publish。
- **代价由谁承担**：多一张 outbox 表和一次扫描；收益是“有提交必有任务”，不会出现孤儿任务或丢消息。

### D3 至少一次 + 幂等，而不是端到端恰好一次

- **选了什么**：代理和 worker 允许重复投递；`grade_tasks.idempotency_key`、`outbox_messages.idempotency_key`、`grade_results(submission_id, version)` 都加唯一约束；结果写入用 `INSERT IGNORE`（或 `ON DUPLICATE KEY UPDATE id=id`），已存在结果时保留首次 `score`/`feedback`，重复执行不改变分数。
- **放弃了什么**：分布式事务/两阶段提交/去重表加查询。
- **代价由谁承担**：结果写入必须幂等，重复消息会多一次模型调用；收益是实现简单、不会丢任务。

### D4 独立 worker，而不是 API goroutine

- **选了什么**：`cmd/worker` 独立进程/镜像，Compose `worker` 服务；从 `grade.tasks` 取消息，调模型、写结果、ACK；可独立 stop/start/scale，无宿主端口。
- **放弃了什么**：API 进程内 goroutine 或定时轮询数据库直接执行。
- **代价由谁承担**：多一个服务和部署单元；收益是重启不丢任务、批改算力与 Web 解耦、判据二可复现。

### D5 持久状态机，而不是内存状态

- **选了什么**：`grade_tasks.status` 为 `pending/running/succeeded/failed/dead`；每次执行 `attempts+1`，记录 `started_at/finished_at/error/next_run_at`；终态 `succeeded/failed/dead` 不再执行。
- **放弃了什么**：内存 map 或只靠队列消息状态。
- **代价由谁承担**：每次状态变化多一次数据库写；收益是重启可查、可重试、可审计。

### D6 轮询，而不是 SSE/WebSocket

- **选了什么**：`GET /api/tasks/{task_id}` 只读；前端前 10 秒每 1 秒查询，之后每 2 秒，终态停止，最多 60 秒。
- **放弃了什么**：SSE、WebSocket、长轮询。
- **代价由谁承担**：查询频率和延迟有上限；收益是实现简单，验收可在命令行复现。

### D7 幂等键由业务派生

- **选了什么**：`idempotency_key = grade:<submission_id>:<submission_version>`；同一 submission 内容不变不升版本，重复 `POST grade` 复用同一 task_id；内容变化升版本，产生新键和新结果，旧结果保留。
- **放弃了什么**：随机 UUID 作为幂等键；只在入口去重。
- **代价由谁承担**：提交内容变化要维护版本；收益是重复点击、网络重试和重复投递都收敛到同一结果。

### D8 失败分类与固定退避

- **选了什么**：瞬时失败（模型超时、429、5xx、网络抖动）重试，最多 5 次，间隔 1/2/4/8/16 秒 + 0–250ms 抖动；永久失败（空内容、参数非法、技能未启用、密钥无效）不重试，直接 `failed`；达到上限进入 `grade.dead` 死信，保留 payload 和最后错误。
- **放弃了什么**：无限重试；所有失败同一处理。
- **代价由谁承担**：队列多一组 retry queue 和 DLQ；收益是不会长期占用队列，也不会把永久缺陷刷屏。

## Architecture

```text
browser
  │ POST /api/.../submissions, /grade
  ▼
nginx (web) ──► api (Go)
                  ├─ DB transaction: submissions + grade_tasks + outbox_messages
                  ├─ outbox dispatcher (1s): publish with confirms ──► RabbitMQ
                  └─ GET /api/tasks/{id}
                                                                       │
                                                        grade.tasks ◄──┘
                                                             │
                                                        worker (Go)
                                                          ├─ call model
                                                          ├─ upsert grade_results
                                                          └─ ACK / retry / DLQ
```

## Data Model

### `submissions`

- `id BIGINT PK AUTO_INCREMENT`
- `assignment_id BIGINT NOT NULL`
- `student_id BIGINT NOT NULL`
- `class_id BIGINT NOT NULL`
- `body MEDIUMTEXT NOT NULL`
- `version INT NOT NULL DEFAULT 1`
- `status ENUM('submitted','grading','graded') NOT NULL DEFAULT 'submitted'`
- `created_at`、`updated_at DATETIME NOT NULL`
- `UNIQUE(assignment_id, student_id, version)`，`INDEX(class_id, student_id)`

`submissions` 是**按版本追加**的：每个版本一行，`id` 就是返回给前端的 `submission_id`；内容变化时插入新行并返回新 id，旧行、旧任务和旧结果都保留。不能更新同一行的 `body/version`，否则旧任务会读到新正文。

### `grade_tasks`

- `id BIGINT PK AUTO_INCREMENT`
- `task_id CHAR(26) NOT NULL UNIQUE`（ULID）
- `submission_id BIGINT NOT NULL`
- `submission_version INT NOT NULL`
- `class_id`、`student_id BIGINT NOT NULL`
- `status ENUM('pending','running','succeeded','failed','dead') NOT NULL DEFAULT 'pending'`
- `attempts INT NOT NULL DEFAULT 0`
- `max_attempts INT NOT NULL DEFAULT 5`
- `idempotency_key VARCHAR(128) NOT NULL UNIQUE`
- `error VARCHAR(512) NULL`
- `next_run_at DATETIME NULL`
- `started_at`、`finished_at`、`created_at`、`updated_at DATETIME NULL/NOT NULL`
- `INDEX(status, next_run_at)`，`INDEX(submission_id)`

### `outbox_messages`

- `id BIGINT PK AUTO_INCREMENT`
- `message_id CHAR(26) NOT NULL UNIQUE`
- `idempotency_key VARCHAR(128) NOT NULL UNIQUE`
- `topic VARCHAR(64) NOT NULL`
- `payload JSON NOT NULL`（含 `task_id`、`submission_id`、`submission_version`）
- `status ENUM('pending','published') NOT NULL DEFAULT 'pending'`
- `attempts INT NOT NULL DEFAULT 0`
- `next_attempt_at DATETIME NULL`
- `created_at`、`published_at DATETIME`
- `INDEX(status, next_attempt_at)`

### `grade_results`

- `id BIGINT PK AUTO_INCREMENT`
- `submission_id BIGINT NOT NULL`
- `version INT NOT NULL`
- `idempotency_key VARCHAR(128) NOT NULL UNIQUE`
- `score DECIMAL(5,2) NOT NULL`
- `feedback TEXT NOT NULL`
- `task_id CHAR(26) NOT NULL`
- `graded_at DATETIME NOT NULL`
- `UNIQUE(submission_id, version)`

### `assignments`

复用现有占位表，补充 `published BOOLEAN NOT NULL DEFAULT 0`、`created_by BIGINT NULL`、`created_at DATETIME NULL`。已有数据库通过 `db.ensureColumn` 查 `information_schema.COLUMNS` 后幂等 `ALTER TABLE`，不能只改 `CREATE TABLE IF NOT EXISTS`；新库仍可直接建全。种子按 `class_id` 分别给 A/B 各插入一份 `published=1` 的作业，条件是“该班还没有作业”，不开放作业编辑接口。

## Queue Topology

- exchange：`grade`（direct、durable）
- 主队列：`grade.tasks`（durable，`x-dead-letter-exchange=grade.dlx`）
- 重试队列：`grade.retry.1s`、`grade.retry.2s`、`grade.retry.4s`、`grade.retry.8s`、`grade.retry.16s`（durable，TTL 到期后经 DLX 回 `grade.tasks`）
- 死信队列：`grade.dead`（durable）
- 发布：persistent delivery mode + publisher confirm；消费：manual ack，prefetch 1
- 不映射 RabbitMQ 宿主端口；management 不暴露

## State Machine

```text
pending ──worker 取走──► running
   ▲                        │
   │                        ├─ 成功：写结果、任务 succeeded、ACK
   │                        ├─ 瞬时失败且 attempts<5：pending + next_run_at，投 retry queue，ACK 原消息
   │                        ├─ 永久失败：failed，投 grade.dead，ACK
   │                        └─ attempts>=5：dead，投 grade.dead，ACK
   │
   └─ 重启补排 pending / 过期 running（next_run_at 已到）
```

- 终态：`succeeded`、`failed`、`dead`；终态任务不再调用模型。
- 重复消息：若任务已是终态，直接 ACK；若结果已存在，直接补状态并 ACK。

## Transaction Sequences

### 提交/批改请求

1. 校验学生身份、作业和班级；去除首尾空白后内容非空且不超过 20,000 字符。
2. `BEGIN`：按 `(assignment_id, student_id)` 以 `ORDER BY version DESC LIMIT 1 FOR UPDATE` 找当前 submission；用去除首尾空白后的正文比较。内容相同复用该行；内容变化插入新行 `version+1`，得到新的 `submission_id`；旧行不改。按 `idempotency_key` 查/插 `grade_tasks`（写 `submission_id`、`submission_version`）；插入 `outbox_messages`（同一 key，payload 含 `task_id`、`submission_id`、`submission_version`）。
3. `COMMIT`；提交接口返回 200/201，批改接口返回 202 `{task_id,status:"pending",status_url}`；不在事务内调用模型或 RabbitMQ。

### 投递器

1. `SELECT ... WHERE status='pending' AND (next_attempt_at IS NULL OR next_attempt_at<=NOW()) ORDER BY id LIMIT 20 FOR UPDATE SKIP LOCKED`。
2. 逐条以 persistent 模式 publish 到 `grade`，等 confirm；成功更新 `published`；失败 `attempts+1`、`next_attempt_at=now+backoff`，下轮继续。
3. 已 publish 但未标 published 时崩溃，重启后会重复 publish；worker 幂等。

### Worker

1. 收到消息，按 `task_id` 读任务；用 `submission_id + submission_version` 定位版本行；终态直接 ACK。
2. `attempts+1`、`status='running'`、`started_at=now`，同时把该 submission 行状态置为 `grading`，提交。
3. 读取该版本的 `body` 调模型（本地或网关），得到 0–100 分和非空评语；MUST NOT 读取当前最新版本代替任务版本。
4. 同一事务：`INSERT IGNORE` 写 `grade_results`（`submission_id`、`version=submission_version`；已存在则保留首次分数/评语）；`grade_tasks.status='succeeded'`、`finished_at=now`；该 submission 行状态置为 `graded`。
5. 提交后 ACK；若中途崩溃，未 ACK 的消息被重投，结果唯一约束兜底。瞬时失败回 `pending` 时 submission 状态回 `submitted`；永久失败或 dead 时 task 记录失败原因，submission 也回 `submitted`，不产生结果。

## Interfaces

| 方法与路径 | 权限 | 成功 | 失败 |
| --- | --- | --- | --- |
| `POST /api/assignments/{id}/submissions` | 本班学生本人 | 201/200 `{submission_id,version,status}` | 400 空/超长；403 教师；404 跨班/不存在 |
| `POST /api/submissions/{id}/grade` | 提交本人 | 首次 202 `{task_id,status:"pending",status_url}`；已有结果时 200 `{task_id,status:"succeeded",result}` | 400；403；404；503 数据库不可用 |
| `GET /api/tasks/{task_id}` | 提交本人或本班教师 | 200 `{task_id,type,status,attempts,result?,error?,created_at,started_at,finished_at}` | 404 跨班/他人/不存在 |

- 202 的 `status_url` 固定为 `/api/tasks/{task_id}`；响应体 MUST NOT 含 `score`/`feedback`。
- 重复 `POST grade` 对同一版本 MUST 返回同一 `task_id`，不新建任务或 outbox。
- 内容变化时 `POST submissions` 返回新的 `submission_id`；前端必须用新 id 请求批改，不能复用旧 id 猜测当前版本。
- `GET /api/tasks/{task_id}` 只读，不触发任何任务。
- 任务/结果查询的访问权：跨班、他人、不存在 task_id 统一同形 404；教师只能看本班。

## Frontend

- 新增学生页面 `/assignments`：列出本班已发布作业，提供正文输入、提交、请求批改和状态区；不实现教师布置/编辑作业页面。
- 提交成功后保存响应里的 `submission_id`；请求批改后按 1 秒/2 秒轮询 `/api/tasks/{task_id}`，终态停止。
- `pending/running` 不显示分数；`succeeded` 显示分数/评语/出处；`failed/dead` 显示原因和“已停止处理，请联系教师”，不提供前端重试按钮。
- 60 秒仍未终态时停止轮询并显示手动刷新按钮；401 回登录页，403/404/503 显示可读文案。

## Configuration

| 变量 | 示例 | 说明 |
| --- | --- | --- |
| `RABBITMQ_URL` | `amqp://campusclaw:...@rabbitmq:5672/` | broker 连接 |
| `RABBITMQ_DEFAULT_USER` | `campusclaw` | broker 初始账号，仅容器使用 |
| `RABBITMQ_DEFAULT_PASS` | 空 | broker 初始口令，只在本机 `.env` |
| `QUEUE_GRADE` | `grade.tasks` | 主队列 |
| `QUEUE_DEAD` | `grade.dead` | 死信队列 |
| `GRADE_MAX_ATTEMPTS` | `5` | 重试上限 |
| `GRADE_RETRY_BASE_SECONDS` | `1` | 退避基数 |
| `GRADE_RETRY_MAX_SECONDS` | `16` | 退避上限 |
| `GRADE_JITTER_MS` | `250` | 抖动上限 |
| `GRADE_VISIBILITY_TIMEOUT_SECONDS` | `60` | 消息可见性/在途超时 |
| `GRADE_MODEL_TIMEOUT_SECONDS` | `30` | 单次模型调用超时 |
| `GRADE_LOCAL_DELAY_MS` | `0` | 本地验收设 2000，固定每次批改 2 秒；生产为 0 |
| `TASK_POLL_FIRST_MS` | `1000` | 前 10 秒轮询间隔 |
| `TASK_POLL_LATER_MS` | `2000` | 之后轮询间隔 |
| `TASK_POLL_MAX_SECONDS` | `60` | 前端停止轮询上限 |

- RabbitMQ、worker 不映射宿主端口；只有 web 映射。
- `CHAT_URL=local` 时 worker 使用本地确定性评分（按关键词覆盖和长度给 0–100 分并生成固定评语），不需要密钥；外部网关返回 JSON，解析失败按瞬时失败处理。

## Migration Plan

1. 在现有 `db.Migrate` 中追加 `CREATE TABLE IF NOT EXISTS` 的 `submissions`、`grade_tasks`、`outbox_messages`、`grade_results`；`assignments` 用 `ensureColumn` 查 `information_schema.COLUMNS`，缺列时幂等 `ALTER TABLE` 补 `published`、`created_by`、`created_at`，重复启动不重复。
2. 种子按 `class_id` 分别判断，给 A/B 各一份 `published=1` 的作业，带 `created_by`；本 change 不开放作业编辑接口，种子只用于提交/批改和跨班 404 验收。
3. 材料库 change 落地版本化迁移后，把这组 DDL 折叠为 `0003_async_grading.sql`，不修改已执行版本。
4. 先启动 RabbitMQ 和表，再改提交接口，最后启动 worker；顺序不可颠倒。
5. 本地模式跑三条判据；外部网关模式再跑一次失败分类和死信。
6. 全部通过后打 `async-202` 标签，归档本 change。

## Risks / Trade-offs

- RabbitMQ 持久化依赖磁盘和 `durable` 声明；节点磁盘满会导致 publish 失败，outbox 会保留 pending 并重试。
- 至少一次会多调用模型；幂等键和唯一约束兜底，但重复调用的成本由业务承担。
- outbox 每秒扫描会增加数据库读；用 `SKIP LOCKED` 和索引限制批量，单实例足够。
- worker 崩溃后未 ACK 的消息由 broker 重投；若 `visibility timeout` 太短会提前重投，设为 60 秒并配合心跳。
- 本地确定性评分只用于演示和验收，不代表真实模型质量；外部网关模式下必须校验 JSON 输出。
- 轮询有最多 2 秒延迟；本课接受，SSE 留后续。

## Open Questions

没有留给实现阶段的行为选择。实现若发现规约冲突，先改本 change 的 delta，再改代码。
