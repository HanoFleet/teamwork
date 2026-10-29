# platform-foundation Specification

## Purpose

规定 CampusClaw 2.0 第 7 课的可运行骨架：可复现启动、配置外置、存活/就绪、单行 JSON 日志与请求 ID、优雅停机、分层门禁和可归档的验收证据。它不实现材料库或教学业务，只给后续 change 一个可验证的基线。

## ADDED Requirements

### Requirement: 可复现启动与配置外置

仓库 MUST 能用 Docker Compose 的 web、api、db、qdrant 四个服务启动；只有 web MUST 映射宿主端口。`GET /live` MUST 在进程监听后 2 秒内返回 200。`.env.example` MUST 只写键名和占位值；`APP_VERSION`、`SHUTDOWN_TIMEOUT_SECONDS`、`SESSION_SECRET`、数据库口令、种子口令和现有检索配置 MUST 为必填，缺失或越界时 api MUST 非零退出且不监听端口，MUST NOT 使用默认密钥或默认版本。`SHUTDOWN_TIMEOUT_SECONDS` MUST 为 1 至 30 的整数。

#### Scenario: 干净克隆一条命令启动

- **GIVEN** 干净克隆的仓库、已按 `.env.example` 填好本机 `.env`、Docker Compose 可用
- **WHEN** 执行 `docker compose up --build -d --wait`
- **THEN** web、api、db healthy，qdrant 已启动，只有 web 发布宿主端口
- **AND** 2 秒内 `GET /live` 返回 200 `{status:"ok",version,time}`
- **AND** 响应版本等于 `.env` 的 `APP_VERSION`

#### Scenario: 缺失或越界配置启动失败

- **GIVEN** 其他配置有效
- **WHEN** 删除 `APP_VERSION`，或把 `SHUTDOWN_TIMEOUT_SECONDS` 设为 `0` 或 `31`，启动 api
- **THEN** 进程非零退出且不监听端口
- **AND** 日志只指出配置键，不输出原始秘密值

#### Scenario: 端口只暴露 web

- **GIVEN** Compose 配置已渲染
- **WHEN** 查看 `docker compose config`
- **THEN** `db`、`qdrant`、`api` 都没有 `ports`
- **AND** `web` 有且只有一个宿主端口映射

### Requirement: 存活与就绪检查

`GET /live` MUST 只表示进程存活，MUST NOT 访问 MySQL、Qdrant、嵌入或对话网关。`GET /health` MUST 是就绪检查，检查 MySQL ping、Qdrant 可达和嵌入配置；全部通过返回 200 `{status:"ready",version,time,checks:{db,qdrant,embedding}}`，任一失败返回 503 `{status:"not_ready",...}`，MUST NOT 含口令、DSN 或内部地址。`GET /ready` MUST 与 `/health` 同源。`/live`、`/health`、`/ready` MUST 拒绝 query 参数（400），非 GET 方法 MUST 返回 405。

#### Scenario: 依赖正常时就绪通过

- **GIVEN** MySQL、Qdrant 和嵌入配置都正常
- **WHEN** 请求 `/live`、`/health` 和 `/ready`
- **THEN** `/live` 返回 200 `{status:"ok"}`，`/health` 与 `/ready` 返回 200 `{status:"ready"}`
- **AND** `checks` 中 `db`、`qdrant`、`embedding` 都是 `true`

#### Scenario: MySQL 停止时只有就绪失败

- **GIVEN** api 已启动，MySQL 被停止
- **WHEN** 请求 `/live`、`/health` 和 `GET /api/materials`
- **THEN** `/live` 仍返回 200
- **AND** `/health` 返回 503，`checks.db=false`
- **AND** 业务接口返回 503，不返回 401
- **AND** MySQL 恢复后 `/health` 重新返回 200

#### Scenario: Qdrant 停止时就绪失败

- **GIVEN** MySQL 正常，Qdrant 被停止
- **WHEN** 请求 `/health`
- **THEN** 响应 503，`checks.qdrant=false`
- **AND** `/live` 仍返回 200，`keyword` 检索仍可用

#### Scenario: 查询参数和非 GET 被拒绝

- **GIVEN** api 正在运行
- **WHEN** 请求 `GET /health?x=1` 和 `POST /health`
- **THEN** 第一个返回 400 `invalid_request`，第二个返回 405
- **AND** 两个响应都不含依赖详情或数据

### Requirement: 最小公开面与默认拒绝

公开接口 MUST 只有 `GET /live`、`GET /health`、`GET /ready`；现有 `/api/*` 业务接口保持原状，本 change MUST NOT 新增业务能力。未登记的 API MUST 返回 404；未登录访问受保护业务接口 MUST 返回 401；附件路径 MUST NOT 作为静态资源暴露。

#### Scenario: 未登记 API 不存在

- **GIVEN** api 正在运行
- **WHEN** 请求 `GET /api/not-registered` 或 `GET /uploads/guessed.txt`
- **THEN** 两个响应都是 404
- **AND** 不返回材料、用户或前端 index

#### Scenario: 未登录业务接口仍是 401

- **GIVEN** 匿名客户端
- **WHEN** 请求 `GET /api/materials`
- **THEN** 响应 401 `unauthorized`
- **AND** 响应体不含材料标题或正文

### Requirement: 结构化日志与请求 ID

每次 HTTP 请求 MUST 生成或沿用 `X-Request-ID`：合法值 MUST 为 8 至 64 个 `[A-Za-z0-9_-]`，缺失或非法时 MUST 生成新 ID 并回写响应头。api MUST 向 stdout 输出单行 JSON，字段含 `ts`、`level`、`msg`、`request_id`、`method`、`path`、`status`、`duration_ms`；MUST NOT 记录 query string、请求体、Authorization、Cookie、口令、令牌或 DSN。日志写入失败 MUST NOT 改变业务响应。

#### Scenario: 缺失请求 ID 时生成并贯穿

- **GIVEN** 请求不带 `X-Request-ID`
- **WHEN** 调用 `GET /live`
- **THEN** 响应头含合法的 `X-Request-ID`
- **AND** 对应的 stdout JSON 日志 `request_id` 与响应头相同
- **AND** 日志含 `method`、`path`、`status`、`duration_ms`

#### Scenario: 合法请求 ID 原样回写

- **GIVEN** 请求头 `X-Request-ID: verify-lesson07`
- **WHEN** 调用 `GET /health`
- **THEN** 响应头和日志都保留 `verify-lesson07`
- **AND** 同一个请求带非法值（少于 8 字符或含空格）时，服务端生成新的合法 ID，不回显原值

#### Scenario: 日志不含敏感内容

- **GIVEN** 请求带 query 参数和 `Authorization` 头
- **WHEN** 调用 `GET /health?token=secret`
- **THEN** JSON 日志只有 `path=/health`，没有 query、Authorization、Cookie 或口令
- **AND** 响应体也不含这些内容

### Requirement: 优雅停机

api 收到 SIGTERM 后 MUST 停止接受新连接，等待在途请求最多 `SHUTDOWN_TIMEOUT_SECONDS` 秒，再关闭数据库并退出；超时后 MUST 强制关闭，MUST NOT 无限等待。正常停机 MUST 在日志中留下 `shutdown_complete`。

#### Scenario: 在途请求完成后再退出

- **GIVEN** 一个请求正在处理，预计在停机预算内完成
- **WHEN** api 收到 SIGTERM
- **THEN** 不再接受新连接，在途请求正常完成
- **AND** 日志出现 `shutdown_started` 和 `shutdown_complete`，进程以 0 退出

#### Scenario: 超出预算强制结束

- **GIVEN** 在途请求超过 `SHUTDOWN_TIMEOUT_SECONDS`
- **WHEN** api 收到 SIGTERM
- **THEN** 服务端在预算到期后强制关闭连接并退出
- **AND** 日志记录超时原因，不无限挂起

### Requirement: 分层与门禁

新增 `httpapi` 文件 MUST NOT 出现 SQL；现有 `auth.go`、`materials.go`、`server.go` 中的 SQL MUST 作为 legacy 例外登记。`make check` MUST 串起规约、规范、OpenSpec strict、分层、密钥、变异、Go 测试/vet 和前端构建，任一非零 MUST 阻断。变异脚本 MUST 能通过临时注入 SQL 让分层检查失败，并在还原后恢复通过。

#### Scenario: 正常门禁通过

- **GIVEN** 当前工作树
- **WHEN** 执行 `make check`
- **THEN** 规约、规范、strict、分层、密钥、变异、Go 测试/vet 和前端构建全部通过
- **AND** 退出码为 0

#### Scenario: 注入 SQL 时门禁变红

- **GIVEN** 正常门禁通过
- **WHEN** 临时在新增 `httpapi` 文件中写入 `SELECT * FROM users` 并运行分层检查
- **THEN** 检查失败并指出文件和行号
- **AND** 删除临时文件后检查恢复通过

### Requirement: 验收与证据

`make grade` MUST 用独立 Compose 项目、随机端口和随机口令运行当前骨架验收，至少覆盖启动、`/live`、`/health`、`/ready`、默认拒绝、日志、停库/恢复、端口边界和优雅停机；任何必测失败、缺证据或清理失败 MUST 退出非零。报告 MUST 写到 `reports/teacher-*/report.html` 和 `report.json`，不含口令或令牌。`python3 scripts/verify.py` MUST 继续通过；证据 MUST 归档到 `docs/lesson-07/verification.md`。

#### Scenario: 隔离验收通过并生成报告

- **GIVEN** Docker Compose 和 Python 可用
- **WHEN** 执行 `make grade`
- **THEN** 14 项检查全部通过，退出码 0
- **AND** 生成自包含 `report.html` 和 `report.json`，包含提交号、逐项判据和结果
- **AND** 报告不含 `.env` 中的秘密

#### Scenario: 失败或缺证据不能判通过

- **GIVEN** 一条必测检查被破坏，或测试阶段没有产生预期记录
- **WHEN** 执行验收
- **THEN** 报告该项失败或阻塞，总体退出非零
- **AND** 不把空结果或未运行项写成通过

#### Scenario: 验收隔离并清理

- **GIVEN** 正式 Compose 项目可能已在运行
- **WHEN** 执行 `make grade`
- **THEN** 使用独立项目名和端口，不停止或修改正式项目的容器、卷和数据
- **AND** 结束后只清理本次创建的容器、网络和卷，报告保留
