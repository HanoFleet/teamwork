# CampusClaw 2.0 规约

> **当前提交重点：第 7 课可运行骨架 + 第 8 课异步批改规约。** 骨架已经落到根目录，`docker compose up -d --wait` 可启动；foundation 已归档，第 8 课异步批改（RabbitMQ、outbox、worker、任务状态、三条判据）只交付规约，材料库是后续 change。

| 项目 | 内容 |
| --- | --- |
| 已归档 change | `2026-10-28-establish-platform-foundation` |
| 当前活动 change | `2026-11-05-add-async-grading`（第 8 课规约，未实现） |
| 后续 change | `2026-10-14-upgrade-material-library`（活动，未实现） |
| 负责人 | 李斯坦（角色一：制定规约） |
| 评审 | 韩雅慧（角色二：开发系统）、禹霖（角色三：项目验收） |
| 骨架标签 | `v0.1.0-skeleton` |
| 基线标签 | `v2.0.0-baseline`（`4fd4232`） |

## 一分钟看懂

- 仓库本身就是可运行的 CampusClaw：Go 后端、React 前端、MySQL、Qdrant、Nginx、Compose。
- 当前骨架新增 `/live` 存活、`/health` 就绪、`/ready` 别名、单行 JSON 日志、request ID、优雅停机、配置外置。
- `make check` 是合并前门禁；`make grade` 是独立 Compose 验收，生成 HTML/JSON 报告。
- 第 8 课异步批改规约已补齐：提交返回 202 + `task_id`，任务持久化，outbox 投递，独立 worker 消费，失败退避/死信，重复只出一份结果；实现与证据待角色二、三。
- 材料库（PDF/Word/PPT、后台索引、版本、回收站、阅读进度）还没有实现，规约在后续 change。

## 已归档 change：platform foundation

| 文件 | 内容 |
| --- | --- |
| [`proposal.md`](openspec/changes/archive/2026-10-28-establish-platform-foundation/proposal.md) | 为什么加固骨架、范围、放弃方案 |
| [`design.md`](openspec/changes/archive/2026-10-28-establish-platform-foundation/design.md) | 分层、健康、日志、停机、legacy 例外 |
| [`specs/`](openspec/changes/archive/2026-10-28-establish-platform-foundation/specs/) | 7 条需求、19 个场景 |
| [`tasks.md`](openspec/changes/archive/2026-10-28-establish-platform-foundation/tasks.md) | 9 条任务与验证证据 |

范围：只做骨架，不做材料库新功能。现有登录、材料、检索、问答接口保持原状。

## 当前活动 change：async grading（第 8 课）

| 文件 | 内容 |
| --- | --- |
| [`proposal.md`](openspec/changes/2026-11-05-add-async-grading/proposal.md) | RabbitMQ、outbox、worker、202 + task_id、三条判据 |
| [`design.md`](openspec/changes/2026-11-05-add-async-grading/design.md) | 队列拓扑、状态机、事务序列、幂等键、失败分类 |
| [`specs/async-grading/spec.md`](openspec/changes/2026-11-05-add-async-grading/specs/async-grading/spec.md) | 10 条需求、31 个场景 |
| [`tasks.md`](openspec/changes/2026-11-05-add-async-grading/tasks.md) | 30 条任务，未勾选 |

范围：只做“提交 → 异步批改 → 查询结果”的最小链路。不做完整作业模块、教师手工评分、SSE/WebSocket、技能/提示词配置和 SEC 自查本身的实现。逐行自查见 [`docs/lesson-08/self-check.md`](docs/lesson-08/self-check.md)。

## 后续 change：material library

| 文件 | 内容 |
| --- | --- |
| [`proposal.md`](openspec/changes/2026-10-14-upgrade-material-library/proposal.md) | 材料库、多格式、版本、回收站、阅读进度 |
| [`design.md`](openspec/changes/2026-10-14-upgrade-material-library/design.md) | 迁移、抽取、先建后换、版本冲突、原文坐标 |
| [`specs/`](openspec/changes/2026-10-14-upgrade-material-library/specs/) | 26 条需求、151 个场景 |
| [`tasks.md`](openspec/changes/2026-10-14-upgrade-material-library/tasks.md) | 46 条任务，未勾选 |

它依赖已归档的 foundation 骨架；日志、`/live`/`/health`/`/ready` 和优雅停机不再重复定义。

## 核心边界

**做（本次骨架）：**

- 一条 Compose 命令启动；只有 web 映射宿主端口。
- `APP_VERSION`、`SHUTDOWN_TIMEOUT_SECONDS` 和现有必填配置缺失即启动失败。
- `/live` 存活；`/health`、`/ready` 检查 MySQL、Qdrant、嵌入配置。
- 单行 JSON 日志 + request ID；不记录 query、body、口令、令牌或 DSN。
- SIGTERM 排空在途请求，最多等配置秒数。
- `make check` 和 `make grade` 可复现；失败即非零。

**不做：**

- 材料库新功能（PDF/DOCX/PPTX、后台索引、版本、回收站、标签、阅读进度、收藏、原文定位）。
- 登录、角色、班级隔离、上传、检索、问答的行为修改。
- 全量重构 `httpapi/auth.go`、`materials.go`、`server.go` 的 legacy SQL；材料库 change 再迁移。
- 浏览器端全量 UI 重构；本 change 只保证构建和现有页面可加载。

**第 8 课规约做：**

- RabbitMQ durable exchange/queue、重试队列、死信队列；独立 worker；Compose 只有 web 对外。
- `submissions`、`grade_tasks`、`outbox_messages`、`grade_results`；提交、任务、outbox 同事务。
- `POST /api/submissions/{id}/grade` 返回 202 + `task_id`；`GET /api/tasks/{task_id}` 只读查询；前端轮询到终态。
- 至少一次投递 + 幂等键/唯一约束；瞬时失败 1/2/4/8/16 秒退避，永久失败直接 failed，5 次后 dead。
- 三条判据落 `reports/` 和 `apitest/cases/async/`，验收后打 `async-202`。

**第 8 课规约不做：**

- 完整模块三（作业编辑/截止/附件、练习、错题、公告、学情、课程单元）。
- 教师手工评分 UI、模型评分规则训练、SSE/WebSocket 推送。
- 端到端恰好一次；采用至少一次 + 幂等结果。
- SEC-01～SEC-08 安全自查本身；那是角色三按任务清单执行并写 `reports/security-precheck.md`。

## 关键判据

- **启动**：`docker compose up --build -d --wait` 后 web/api/db healthy、qdrant 已启动；`/live` 2 秒内 200。
- **就绪**：`/health` 返回 `{status:"ready",checks:{db,qdrant,embedding}}`；停 MySQL 后 503 且 `db=false`，停 Qdrant 后 503 且 `qdrant=false`。
- **默认拒绝**：未知 `/api/*` 404；未登录业务接口 401；`/health` 带 query 400；非 GET 405。
- **日志**：每行单行 JSON，含 `request_id`、`method`、`path`、`status`、`duration_ms`；无敏感内容。
- **停机**：SIGTERM 后在途请求完成，日志有 `shutdown_started` 和 `shutdown_complete`；超时强制关闭。
- **分层**：新增 `httpapi` 文件不得有 SQL；legacy 文件在 `02-backend.md` 和 `design.md` 登记。
- **验收**：`make grade` 14 项通过；`--self-test` 退出 1，失败不会被写成通过。

## 怎么校验

```bash
make check
make check-security
make grade
python3 scripts/verify.py
npx -y @fission-ai/openspec@1.15.0 validate --all --strict
```

预期：`make check` 退出 0（同时检查 material-library 与 async-grading）；`make check-security` 跑密钥扫描和前端依赖审计；`make grade` 报告 14/14 通过；`verify.py` 全部断言通过；OpenSpec strict 全部通过。证据见 [`docs/lesson-07/verification.md`](docs/lesson-07/verification.md)；第 8 课自查映射见 [`docs/lesson-08/self-check.md`](docs/lesson-08/self-check.md)。

## 评审顺序

1. 跑 `docker compose up --build -d --wait`，看 `/live`、`/health`、`/ready`。
2. 跑 `make check`、`make check-security` 和 `make grade`，看报告。
3. 读 foundation 的 `proposal.md` / `design.md` / `specs/` / `tasks.md`。
4. 读 async-grading 的 `proposal.md` / `design.md` / `specs/async-grading/spec.md` / `tasks.md`，对照 `docs/lesson-08/self-check.md` 的 10 行。
5. 读 material-library 的 `proposal.md`，确认它依赖已归档骨架和 async-grading 的边界。
6. 另起一个不带上下文的会话，只给仓库路径和 change 名，看能否照 `tasks.md` 实现。

## 工程规范

八类规范在 [`docs/standards/`](docs/standards/)；常驻入口是 [`AGENTS.md`](AGENTS.md) 和 [`.cursor/rules/campusclaw-standards.mdc`](.cursor/rules/campusclaw-standards.mdc)；按动作执行的步骤在 [`.cursor/skills/campusclaw-engineering/SKILL.md`](.cursor/skills/campusclaw-engineering/SKILL.md)。

## 旧实现

[`archive/campusclaw-baseline.zip`](archive/campusclaw-baseline.zip) 是基线历史快照；当前可运行代码已经在根目录的 `backend/`、`frontend/`。旧快照用于对比和回溯，不作为本次提交主体。
