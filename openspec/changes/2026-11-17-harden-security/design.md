# 设计：2026-11-17-harden-security

## Context

第 8 课已有登录会话、角色/班级隔离、异步批改和请求日志；安全报告确认 SEC-03/04/07 为红，SEC-08 未做。第 9 课要求在不扩大产品范围的前提下，给配置写入、技能调用、CSRF 和审计建立最小但真实的链路，并把红项复测变绿。

现有代码的关键事实：

- `sessions` 只有 id/user_id/expires_at/created_at，没有 CSRF token（`backend/internal/db/db.go:80-87`）。
- `requireUser` 是唯一统一的登录检查点（`backend/internal/httpapi/server.go:156-171`），但角色检查分散在各 handler。
- `assistants`/`skills` 只有 `id,name` 占位表（`db.go:131-138`），无写路由。
- 请求日志只有 `request_id/method/path/status/duration_ms`；worker 日志有 task/submission/student/status/attempts/duration（`logging.go:74-94`、`worker.go:78-84`）。
- 前端 `api.ts` 还把 Bearer token 放 localStorage；网页应只依赖 HttpOnly Cookie。

## Goals / Non-Goals

**Goals:**

- Cookie 写请求有一次性 CSRF token 和同源校验；Bearer 脚本不受影响。
- 教师可写技能/助手配置；学生 403；助手按班级隔离。
- 技能运行走受控入口，`grade` 复用现有入队与归属检查，不开放分数写入。
- 审计日志七列可查，拒绝和 CSRF 失败也留痕。
- SQLi/XSS/CSRF 反例、资产门禁红绿、SEC-08 实验和回归证据齐全。

**Non-Goals:**

- 不做完整设置页、技能市场、助手编排、外部工具调用。
- 不实现多实例共享限流、生产 HTTPS/Secure Cookie、版本化迁移框架。
- 不改变现有 401/403/404 语义，除新增 CSRF 403 和审计查询 403。

## Decisions

### D1 会话级 CSRF token，而不是只靠 SameSite

- **选了什么**：登录生成 64 位 hex token，存 `sessions.csrf_token`；登录响应和 `/api/me` 返回；Cookie 认证的 POST/PUT/PATCH/DELETE 必须带 `X-CSRF-Token` 且与 session 匹配；Bearer 请求免 token；Origin/Referer 存在且 host 不匹配时 403。
- **放弃了什么**：只靠 `SameSite=Lax`、双提交 Cookie、把 token 放 localStorage。
- **代价由谁承担**：前端和所有脚本写请求要带 token；旧 session 需要重新登录。收益是任务清单要求的“缺少一次性令牌被拒”可机器验证。

### D2 最小配置 API，而不是只返回假 403

- **选了什么**：`assistants` 增加 `class_id/system_prompt/enabled/updated_at`；`skills` 增加 `skill_key/description/enabled/updated_at`；教师可 `GET/PATCH /api/skills`、`GET/PATCH /api/assistants`。助手按 class_id 隔离，技能是全局目录。
- **放弃了什么**：只做占位 403、完整设置页、独立 prompt_versions 表。
- **代价由谁承担**：多两张表的列和两条 API；收益是 SEC-03 有真实写入口、数据库前后核验和审计对象。

### D3 技能运行只包装现有入队服务

- **选了什么**：`POST /api/skills/{key}/run`；当前只启用 `grade`，body 只接受 `submission_id`；内部调用 `grading.Service.EnqueueGrade(actor, id)`；学生只能操作自己的提交，跨班/他人 404；不接受 `score`/`feedback`。
- **放弃了什么**：通用技能执行框架、模型工具调用、直接写 `grade_results` 的 HTTP 接口。
- **代价由谁承担**：技能种类少，不能演示复杂工具链；收益是不会为了测试开放后门，SEC-04 的授权边界可验证。

### D4 审计落库，而不是只写 stdout

- **选了什么**：新增 `audit_logs`，字段覆盖操作人、时间、操作类型、对象、结果、技能标识、用量/耗时和 request_id；配置写入、技能运行、拒绝、CSRF 失败都写；教师 `GET /api/audit-logs` 可按 skill_key/operator/time 过滤，学生 403。
- **放弃了什么**：只靠 grep 容器日志、JSON 大字段存全部上下文。
- **代价由谁承担**：每次安全操作多一次插入；审计插入失败只记 ERROR、不阻塞主操作，但测试要求关键行存在。`usage_json` 只放模型/ token 元数据，不放正文、提示词或密钥。

### D5 安全测试复用现有 helper，而不是新建测试框架

- **选了什么**：新增 `scripts/security_test.py`，签名与 `async_test.py` 一致（`run(note, fail, call, login, mysql, compose, ENV)`）；由 `verify.py` 调用；`acceptance.py` 增加 A16–A19 让 CI `grade` 覆盖；`apitest/cases/security/README.md` 映射用例。
- **放弃了什么**：pytest/unittest 新框架、Playwright 覆盖所有安全用例。
- **代价由谁承担**：测试仍依赖 Compose；收益是与现有登录/MySQL/Compose helper 一致，少维护一套环境。

### D6 门禁红绿用临时仓库制造真实失败

- **选了什么**：`scripts/security_gate.py` 调 `secret_scan.py` 和 `npm audit --audit-level=high`；`--self-test` 在临时 git 仓库提交一个假 `SESSION_SECRET`，让扫描器真实退出 1，再在干净临时仓库退出 0；输出写 `reports/gate-red-green.md`。
- **放弃了什么**：用环境变量伪造失败、把真实密钥放进工作树。
- **代价由谁承担**：self-test 多几次临时 git 操作；收益是红/绿都是扫描器真实判定，不污染主仓库。

## Architecture

```text
browser ── cookie + X-CSRF-Token ──► nginx ──► api
                                             ├─ requireUser + CSRF/Origin
                                             ├─ catalog (skills/assistants)
                                             ├─ audit_logs
                                             ├─ grading.EnqueueGrade
                                             └─ GET /api/audit-logs (teacher)
                                                     │
                                                 RabbitMQ
                                                     │
                                                  worker
```

## Data Model

### `sessions`（扩展）

- `csrf_token CHAR(64) NULL`：登录时生成；旧 session 为空，需重新登录。

### `audit_logs`

- `id BIGINT PK AUTO_INCREMENT`
- `occurred_at DATETIME(6) NOT NULL`
- `operator_id BIGINT NULL`、`operator_username VARCHAR(64) NOT NULL`、`operator_role ENUM('teacher','student','system') NOT NULL`
- `class_id BIGINT NULL`
- `operation VARCHAR(64) NOT NULL`、`object_type VARCHAR(32) NOT NULL`、`object_id VARCHAR(64) NOT NULL`
- `result_status ENUM('success','failure','denied','accepted') NOT NULL`
- `skill_key VARCHAR(64) NULL`
- `duration_ms INT NULL`、`usage_json JSON NULL`
- `error_code VARCHAR(64) NULL`、`request_id VARCHAR(64) NULL`
- 索引：`(occurred_at)`、`(operator_id, occurred_at)`、`(skill_key, occurred_at)`、`(object_type, object_id)`
- 删除规则：保留，不提供删除接口；后续按运维保留期清理。

### `assistants`（扩展）

- 新增 `class_id BIGINT NULL`、`system_prompt TEXT NULL`、`enabled BOOLEAN NOT NULL DEFAULT 1`、`updated_at DATETIME NULL`
- `class_id` 为 NULL 的旧占位行不参与班级列表；种子按 A/B 各建一行。
- 索引 `(class_id)`。

### `skills`（扩展）

- 新增 `skill_key VARCHAR(64) NULL`、`description TEXT NULL`、`enabled BOOLEAN NOT NULL DEFAULT 1`、`updated_at DATETIME NULL`
- `UNIQUE(skill_key)`；旧占位行 key 为 NULL，不参与按 key 查询。
- 种子 `grade`（作业批改）、`ask`（问答）。

## Interfaces

| 方法与路径 | 权限 | 成功 | 失败 |
| --- | --- | --- | --- |
| `GET /api/skills` | 已登录 | 200 `{skills:[...]}` | 401 |
| `PATCH /api/skills/{key}` | 教师 | 200 更新后的技能 | 400；403 学生；404 不存在 |
| `GET /api/assistants` | 已登录 | 200 本班助手 | 401 |
| `PATCH /api/assistants/{id}` | 本班教师 | 200 更新后的助手 | 400；403 学生；404 跨班/不存在 |
| `POST /api/skills/{key}/run` | 已登录 | `grade` 返回 202/200 任务 | 400；403；404 他人/跨班/禁用；503 |
| `GET /api/audit-logs` | 教师 | 200 `{logs:[...]}` | 400；403 学生；503 |
| `POST /api/login` | 公开 | 200 `{status,token,token_type,csrf_token}` | 400/401/403 跨源/503 |
| `GET /api/me` | 已登录 | 200 用户 + `csrf_token` | 401/503 |

- 现有 `/api/submissions/{id}/grade` 仍只入队；技能运行不写分数。
- 所有按 id 的资源先取整行再校验班级；跨班/他人/不存在同形 404。
- 审计查询不返回正文、提示词、密钥或模型原始输出。

## Security Flows

1. 登录：校验账号 → 生成 session id + csrf token → session 入库 → Set-Cookie（HttpOnly/SameSite=Lax）→ 返回 Bearer + csrf_token。
2. 写请求：`requireUser` 解析 Cookie/Bearer → Cookie 认证校验 Origin + `X-CSRF-Token` → 角色/归属检查 → 业务写入 → 审计行。
3. 技能运行：`skills/{key}` 查启用技能 → 仅 `grade` → `EnqueueGrade` → 审计 `skill.run`（object=submission:id, skill_key=grade）。
4. 拒绝：配置/技能越权写审计 `result_status=denied`；CSRF 失败写 `operation=csrf.check`；不写正文。
5. 查询：教师 `GET /api/audit-logs?skill_key=&operator_id=&from=&to=&limit=`，按 class_id 过滤；学生 403。

## Configuration

| 变量 | 示例 | 说明 |
| --- | --- | --- |
| `CSRF_TOKEN_BYTES` | `32` | token 熵；默认 32 字节，hex 64 字符 |
| `AUDIT_MAX_USAGE_BYTES` | `2048` | usage_json 截断上限；不写正文 |
| `AUDIT_QUERY_LIMIT` | `100` | 审计查询默认/最大条数 |
| `SECURITY_GATE_SELF_TEST` | `0` | 仅测试用；生产不设置 |

- 不新增宿主端口；CSRF token 不写 localStorage、不进 URL、不进日志。

## Migration Plan

1. `db.Migrate` 追加 `CREATE TABLE IF NOT EXISTS audit_logs`；`sessions` 用 `ensureColumn` 补 `csrf_token`；`assistants`/`skills` 补列。
2. 新增 `ensureIndex`（查 `information_schema.STATISTICS`）补 `assistants.class_id` 和 `skills.skill_key` 唯一索引；旧数据 key 为 NULL，不冲突。
3. 种子按班级补 A/B 助手，按 key 补 `grade`/`ask` 技能；旧占位行保留但不出现在班级列表。
4. 旧 session 无 token：GET 仍可读，写请求 403 直到重新登录；发版说明要求重新登录。
5. 先上数据库/后端，再上前端 CSRF；最后接测试和门禁。

## Risks / Trade-offs

- CSRF token 改所有写客户端；前端、verify.py、async_test.py、acceptance.py 必须同一提交更新，否则测试全红。
- 旧 session 没有 token；选择要求重新登录，避免自动补 token 带来的兼容分支。
- 审计插入失败采用 best-effort：主操作成功但记 ERROR；安全测试要求关键审计行存在。若后续合规要求 fail-closed，再另开 change。
- `skills` 是全局目录，助手按班级；这比完整 RBAC 简单，但足以验证 SEC-03/04 的边界。
- 不实现真实模型工具调用；SEC-08 第四步用 API/技能入口验证“写入层拒绝”，不伪造模型行为。
- 第 8 课归档依赖 Playwright 和 CI verify；若环境跑不起来，保持活动状态并报告阻塞。

## Open Questions

没有留给实现阶段的行为选择。若实现发现规约冲突，先改本 change 的 delta，再改代码。
