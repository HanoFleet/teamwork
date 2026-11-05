# 任务清单：2026-11-05-add-async-grading

> 执行顺序：先有可启动的 RabbitMQ、worker 和表，再改提交接口，最后补消费者、重试、查询和证据。任务默认未勾选；只有对应 `verify` 通过后才勾选。角色一负责本文件，角色二实现，角色三验收。

## 0. 基线与依赖

- [ ] **0.1 确认 foundation 可启动** — 涉及：`docker-compose.yml`、`Makefile`、`scripts/verify.py`。从当前 `main` 复制 `.env`，执行 `docker compose up --build -d --wait`，记录 `/live`、`/health` 和 `verify.py` 基线。verify: `/live` 200、`/health` 200、`python3 scripts/verify.py` 通过。
- [ ] **0.2 确认材料库规约边界** — 涉及：`openspec/changes/2026-10-14-upgrade-material-library/`。本 change 不依赖材料库已实现；表结构由本 change 的任务创建。verify: `openspec validate 2026-11-05-add-async-grading --strict` 通过。
- [ ] **0.3 建立报告目录** — 涉及：`reports/`、`.gitignore`。确认 `reports/teacher-*` 忽略，`reports/async-grading.md`、`reports/risk-concurrency.md`、`reports/risk-transaction.md` 可提交。verify: `git check-ignore` 结果符合预期。

## 1. 队列、任务表与部署

- [ ] **1.1 Compose 增加 RabbitMQ 和 worker** — 涉及：`docker-compose.yml`、`.env.example`、`deploy/`。增加 rabbitmq（durable、无宿主端口）和 worker（无宿主端口、依赖 rabbitmq/db）；只有 web 映射端口。verify: `docker compose config` 只有 web 有 `ports`；`docker compose up -d --wait` 六个服务启动。
- [ ] **1.2 建立队列拓扑** — 涉及：`backend/internal/queue/`（新增）。声明 exchange `grade`、主队列 `grade.tasks`、重试队列 `grade.retry.1s`…`16s`、死信 `grade.dead`，全部 durable；publisher confirm、manual ack、prefetch 1。verify: RabbitMQ 管理接口或 `rabbitmqctl list_queues` 显示队列；重启 broker 后队列仍在。
- [ ] **1.3 建表与迁移** — 涉及：`backend/internal/db/`。创建 `submissions`（按版本追加，`UNIQUE(assignment_id,student_id,version)`）、`grade_tasks`、`outbox_messages`、`grade_results`；`assignments` 用 `ensureColumn` 查 `information_schema.COLUMNS`，缺列时幂等 `ALTER TABLE` 补 `published`、`created_by`、`created_at`。verify: `SHOW CREATE TABLE` 含唯一约束；旧库升级后列存在；重复启动不重复建表/迁移。
- [ ] **1.4 任务与 outbox 状态字段** — 涉及：`grade_tasks`、`outbox_messages`。任务含 submission_version/status/attempts/max_attempts/error/next_run_at/started_at/finished_at；outbox 含 status/attempts/next_attempt_at/published_at，payload 含 task_id/submission_id/submission_version。verify: 插入和查询字段完整；索引 `(status,next_run_at)` 存在。

## 2. 提交与 202 契约

- [ ] **2.1 提交接口** — 涉及：`backend/internal/httpapi/`、`backend/internal/grading/`、`backend/internal/db/`。`POST /api/assignments/{id}/submissions` 仅本班学生本人；去除首尾空白后内容 1–20,000 字符；内容不变复用当前 submission 行，内容变化插入新行、`version+1`、返回新的 `submission_id`；教师 403，跨班/他人同形 404。种子按 class_id 给 A/B 各一份已发布作业，仅用于提交/批改和跨班 404，不开放作业 CRUD。verify: curl 正常/教师/他人/跨班；两次编辑产生两行和两个 submission_id；A/B 种子各一份且重复启动不重复。
- [ ] **2.2 批改入口与 202** — 涉及：`httpapi/`、`grading/`。`POST /api/submissions/{id}/grade` 首次在同一事务写 submission 状态、grade_task（含 submission_version）、outbox（payload 含版本），返回 202 `{task_id,status:"pending",status_url}`；同一版本已有结果时返回 200、同一 task_id 和已有 result，不新建任务。verify: 202 响应字段；`grade_tasks`/`outbox_messages` 各一行且版本正确；响应无 score/feedback；重复请求 200 且不新增。
- [ ] **2.3 重复批改复用 task** — 涉及：`grading/`。同一 submission/version 的幂等键唯一；重复请求返回同一 `task_id`，不新增 task/outbox。verify: 连发两次，`COUNT(*)` 不变，task_id 相同。
- [ ] **2.4 无同步模型调用** — 涉及：`httpapi/`、`cmd/server`。提交/批改请求内 MUST NOT 调用模型；代码搜索不到评分调用分支。verify: 请求耗时与模型耗时无关；日志无模型调用记录。

## 3. Outbox 与 worker

- [ ] **3.1 事务性 outbox** — 涉及：`grading/`、`queue/`。提交事务提交后才允许 dispatcher 发布；事务内无 RabbitMQ/模型调用。verify: 注入 outbox 插入失败，三张表无新增；重试只一组记录。
- [ ] **3.2 dispatcher 补投** — 涉及：`cmd/server` 或 `internal/outbox/`。每秒扫描 pending，`FOR UPDATE SKIP LOCKED`，publish 等 confirm，成功标 published，失败写 attempts/next_attempt_at。verify: 停 RabbitMQ 提交后 outbox pending；恢复后自动发布。
- [ ] **3.3 worker 消费与 ACK** — 涉及：`cmd/worker`（新增）、`internal/worker/`。取消息、按 `submission_id + submission_version` 读版本正文、调模型、写该版本结果、DB 提交后 ACK；终态直接 ACK；崩溃未 ACK 时被重投。verify: 停 worker 任务 pending，启动后 succeeded；kill 后重投仍只有一份结果；编辑后旧任务仍读旧正文。
- [ ] **3.4 独立启停/扩容** — 涉及：`docker-compose.yml`、`cmd/worker`。worker 可单独 `stop/start`，不接宿主请求。verify: 判据二复现；`docker compose ps` worker 无宿主端口。

## 4. 状态机、失败分类与幂等

- [ ] **4.1 状态机** — 涉及：`grading/`、`worker/`。pending→running→succeeded；瞬时失败回 pending+attempts+next_run_at；永久失败 failed；达到上限 dead；终态不执行。verify: Go 单测覆盖五种状态和非法转移；数据库字段正确。
- [ ] **4.2 失败分类与退避** — 涉及：`worker/`、`grading/`。瞬时失败 429/5xx/超时重试，最多 5 次，1/2/4/8/16 秒+0–250ms 抖动；永久失败不重试；上限进 `grade.dead`。verify: 构造 429 和永久失败；attempts/间隔/死信符合；死信保留错误。
- [ ] **4.3 重复提交/投递幂等** — 涉及：`grading/`、`worker/`。幂等键 `grade:<submission_id>:<version>`；task/outbox/result 唯一约束；结果写入保留首次分数/评语。verify: 重复请求只一个 task；重复消息只一行 result，attempts 增加、score 不变。
- [ ] **4.4 权限与同形 404** — 涉及：`httpapi/`。提交/批改/查询只允许本人或本班教师；跨班、他人、不存在同形 404；教师以学生身份提交 403。verify: 三类 id 三次响应 body/状态/Content-Type 相同（忽略 X-Request-ID/Date）。

## 5. 查询与前端

- [ ] **5.1 任务查询接口** — 涉及：`httpapi/`、`grading/`。`GET /api/tasks/{task_id}` 只读，返回状态/attempts/result/error/时间；不触发任务。verify: pending/running/succeeded/failed/dead 五种响应；查询不改变 attempts。
- [ ] **5.2 前端轮询** — 涉及：`frontend/src/`。新增学生 `/assignments` 页面：列出本班已发布作业，提交后保存 `submission_id` 并请求批改；前 10 秒每 1 秒轮询，之后每 2 秒，终态停止，最多 60 秒；60 秒后停止并提示手动刷新；显示 pending/running/succeeded/failed/dead。verify: Playwright 从 `/assignments` 提交，用 mock/本地 2 秒批改看到 succeeded；停 worker 时显示 pending。
- [ ] **5.3 结果展示与错误** — 涉及：`frontend/src/`。succeeded 显示分数/评语/出处；failed/dead 显示原因和“已停止处理，请联系教师”的说明，不提供前端重试按钮；403/404/503 有可读文案。verify: 五种状态截图/断言。

## 6. 三条判据与证据

- [ ] **6.1 判据一：P95 不随批改增长** — 涉及：`scripts/`、`reports/async-grading.md`。本地模式设 `GRADE_LOCAL_DELAY_MS=2000`，连续提交 20 份不同内容，记录 `time_total`；P95 < 500ms，响应无分数。verify: 报告含命令、20 个数值、P95 和结论。
- [ ] **6.2 判据二：停 worker 不丢任务** — 涉及：`reports/async-grading.md`。停 worker 提交，查 pending；启动 worker，轮询到 succeeded。verify: 报告含 stop/start 命令、状态序列、耗时。
- [ ] **6.3 判据三：重复只有一份结果** — 涉及：`reports/risk-concurrency.md`、`reports/risk-transaction.md`。重复请求+重复投递；结果一行，attempts 增加，score 不变；记录事务/孤儿检查。verify: 报告含 SQL/接口输出和结论。
- [ ] **6.4 自动化** — 涉及：`apitest/cases/async/`、`make check`、`.github/workflows/check.yml`。三条判据转为用例，CI 运行。verify: `make check` 全绿；CI run 成功。
- [ ] **6.5 观测与标签** — 涉及：`reports/`、Git。记录队列长度、执行耗时、attempts、死信数量；打 `async-202` 标签。verify: `git tag -l`；报告含观测值。

## 7. 第 8 课安全自查（角色三）

- [ ] **7.1 SEC-01～SEC-07** — 涉及：`docs/lesson-08/security-inventory.md`、`reports/security-precheck.md`、`reports/risk-authz.md`、`reports/security-baseline.md`。按接口清单逐项写前置/操作/可观测结果/实际/红绿；至少保留 1 条红。verify: 角色三独立复现至少 2 条，判定一致。
- [ ] **7.2 密钥与依赖** — 涉及：`reports/security-baseline.md`。全历史密钥扫描 0 命中，或已轮换并清历史；`npm audit`/Go 扫描高危清零或书面处置。verify: 报告含命令和计数。
- [ ] **7.3 交叉评审记录** — 涉及：`reports/review-01.md`、`reports/security-precheck.md`。按七维度+三分法写评审结论，作为最终报告“审核记录”首份。verify: 记录可检索，结论有依据。

## 完成定义

- 三条判据可复现，报告在 `reports/`，用例在 `apitest/cases/async/` 并随 `make check`/CI 运行。
- 任务、outbox、结果三张表的唯一约束和状态机测试通过。
- 停 worker、停 broker、模型瞬时/永久失败、重复提交/投递都有实际结果。
- `git tag async-202` 存在；本 change 验收通过后才归档。
- 第 8 课 SEC-01～SEC-07 自查有实际记录，至少 1 条红，不伪造绿。
