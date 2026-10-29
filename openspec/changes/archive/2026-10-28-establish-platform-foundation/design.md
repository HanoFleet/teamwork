# 设计：2026-10-28-establish-platform-foundation

## Context

基线来自 `v2.0.0-baseline`：Go 标准库后端、React 前端、MySQL 8、Qdrant、Nginx、Docker Compose。已有 `/api/login`、`/api/materials`、`/api/search`、`/api/ask` 等业务接口，`/health` 原本只表示进程存活。`httpapi/auth.go`、`materials.go` 和 `server.go` 里有迭代 1/2 遗留的 SQL；本 change 不重写这些业务，只把新增的框架能力放到独立包中。

## Goals / Non-Goals

**Goals:**

- 克隆后填 `.env`，一条 Compose 命令启动，`/live`、`/health`、`/ready` 可判定。
- 配置缺失/越界启动失败；日志可串联、可脱敏；SIGTERM 可排空。
- `make check` 和 `make grade` 可复现，报告可归档。
- 现有业务接口和迭代 1/2 的验收脚本继续通过。

**Non-Goals:**

见 `proposal.md`。不实现材料库新功能，不全面重构 legacy SQL。

## Decisions

### D1 恢复基线而不是新建空项目

- **选了什么**：从 `v2.0.0-baseline` 恢复 `backend/`、`frontend/`、Compose 和 `verify.py`，在根目录形成可运行工程。
- **放弃了什么**：新建一个干净的 skeleton 项目。
- **代价由谁承担**：需要保留 legacy `httpapi` SQL 例外；收益是业务、规约、历史和贡献记录不丢。

### D2 `/live` 存活、`/health` 就绪、`/ready` 别名

- **选了什么**：`/live` 只表示进程活着；`/health` 检查 MySQL ping、Qdrant 可达和嵌入配置，返回 `{status,version,time,checks}`；`/ready` 与 `/health` 同源。`/health` 和 `/ready` 拒绝 query 参数（400），非 GET 返回 405。
- **放弃了什么**：保留旧语义“`/health` 不查库、另加 `/ready`”。
- **代价由谁承担**：`verify.py` 和 README 要同步改成 `/live` 存活；收益是符合课程样例“`/health` 返回依赖状态”的语义。

### D3 JSON 日志与 request ID

- **选了什么**：`internal/logging` 统一 `slog` JSON handler；中间件读取/生成 `X-Request-ID`（8–64 个 `[A-Za-z0-9_-]`），回写响应头，记录 `ts`、`level`、`msg`、`request_id`、`method`、`path`、`status`、`duration_ms`；不记录 query、body、Authorization、Cookie、口令或 DSN。
- **放弃了什么**：继续用 `log.Printf` 纯文本；把请求体写进日志。
- **代价由谁承担**：日志解析依赖 JSON 格式，开发者要按字段查；收益是请求可串联且不泄露。

### D4 优雅停机

- **选了什么**：`internal/lifecycle` 在 SIGTERM 后停止接受新连接，调用 `http.Server.Shutdown`，最多等 `SHUTDOWN_TIMEOUT_SECONDS`（1–30，默认 10），超时强制关闭；退出前关闭数据库。
- **放弃了什么**：直接 `ListenAndServe` + 进程被杀；无限等待在途请求。
- **代价由谁承担**：停机多一个配置项和等待窗口；收益是不会切断在途请求，也不会挂死。

### D5 配置外置与启动失败

- **选了什么**：新增 `APP_VERSION`、`SHUTDOWN_TIMEOUT_SECONDS` 为必填；沿用现有 `SESSION_SECRET`、DB、上传、种子口令等必填项；缺失或越界直接非零退出，不取默认密钥。
- **放弃了什么**：给版本和停机时间默认值，方便本地启动。
- **代价由谁承担**：`.env.example` 和 Compose 必须同步；收益是环境可判定、不会静默用错配置。

### D6 分层与 legacy 例外

- **选了什么**：新增 `health`、`logging`、`lifecycle` 三个包；新增 `httpapi` 文件不得出现 SQL。`auth.go`、`materials.go`、`server.go` 中已有 SQL 登记为 legacy 例外，`scripts/layer_check.py` 只对非例外文件失败；`scripts/mutation.py` 注入 SQL 证明门禁会红。
- **放弃了什么**：本 change 把 legacy SQL 全部迁到 repository。
- **代价由谁承担**：例外写进本文件和 `docs/standards/02-backend.md`；材料库 change 负责迁移；收益是本次不把骨架变更扩大成业务重构。

### D7 一门禁一验收

- **选了什么**：`make check` 串起规约/规范/strict/分层/密钥/变异/Go 测试/vet/前端构建；`make grade` 用独立 Compose 项目、随机端口和随机口令跑 14 项运行验收，失败即非零并生成 HTML/JSON 报告。
- **放弃了什么**：只靠手工 curl 和截图；在正式环境上跑验收。
- **代价由谁承担**：验收需要 Docker、Python 和本地镜像；收益是可复现、可归档、不会污染正式数据。

## Interfaces

| 方法与路径 | 权限 | 成功 | 失败 |
| --- | --- | --- | --- |
| `GET /live` | 公开 | 200 `{status:"ok",version,time}` | 400（带 query） |
| `GET /health` | 公开 | 200 `{status:"ready",version,time,checks}` | 400（带 query）；503（依赖不可用） |
| `GET /ready` | 公开 | 同 `/health` | 同 `/health` |
| `POST /health` | 公开 | — | 405 |
| 现有 `/api/*` | 保持原状 | 保持原状 | 保持原状 |

## Configuration

| 变量 | 必填 | 校验 | 用途 |
| --- | --- | --- | --- |
| `APP_VERSION` | 是 | 非空 | `/live`、`/health` 返回版本 |
| `SHUTDOWN_TIMEOUT_SECONDS` | 是 | 1–30 | SIGTERM 排空上限 |
| `SESSION_SECRET` | 是 | 至少 16 字符 | 会话签名 |
| `MAX_UPLOAD_BYTES` | 是 | 1–16777216 | 单文件上限 |
| `LOGIN_FAIL_THRESHOLD` / `LOGIN_LOCK_MINUTES` | 是 | 正整数 | 登录锁定 |
| `SEED_*_PASSWORD` | 是 | 至少 8 字符 | 种子账号 |
| 现有 DB/Qdrant/嵌入/对话配置 | 是 | 非空 | 依赖连接 |

固定上限：`/health` 探测 2 秒；Compose 只映射 web；api 容器 `stop_grace_period: 12s`。

## Risks / Trade-offs

- 现有 `httpapi` SQL 未迁移，分层检查只覆盖新增文件；例外已登记，材料库 change 负责清理。
- 旧 `verify.py` 依赖 `/health` 存活语义，已改为 `/live` 存活、`/health` 就绪；如果外部脚本仍用旧语义，需要同步。
- Qdrant 不可达时 `/health` 503，但 `keyword` 检索仍可用；这是有意的：就绪检查反映完整能力，业务降级由检索层处理。
- 前端升级 Vite 8 / react-router 7 后构建通过，但未做浏览器端全量回归；本 change 只保证构建和现有页面可加载。
- `make grade` 需要 Docker 和 Python；课程教师环境只有 Docker Compose 时，可用 `make acceptance` 的等价命令，报告仍生成。

## Migration Plan

1. 从 `v2.0.0-baseline` 恢复代码，不修改数据库结构。
2. 增加配置、健康、日志、停机包，修改 `main.go` 和 `server.go`。
3. 更新 Compose/Nginx/`.env.example`，让 api 健康检查用 `/live`。
4. 更新 `verify.py` 的存活/就绪断言。
5. 跑 `make check`、`make grade`、`python3 scripts/verify.py`。
6. 归档本 change，合并 spec 到 `openspec/specs/platform-foundation/spec.md`，打 `v0.1.0-skeleton`。

## Open Questions

没有留给实现阶段的行为选择。实现若发现规约冲突，先修改本 change 的 delta，再改代码。
