# 任务清单：2026-10-28-establish-platform-foundation

> 只有跑过该条 `verify` 才能勾选。证据写入 `docs/framework/verification.md` 和 `reports/teacher-*/`。

## 1. 骨架

- [x] **1.1 恢复可运行基线** — 从 `v2.0.0-baseline` 恢复 `backend/`、`frontend/`、Compose 和 `scripts/verify.py`，确保根目录能构建。verify: `docker compose build` 成功；`docker compose up -d --wait` 四个服务 healthy。
- [x] **1.2 配置外置** — 增加 `APP_VERSION`、`SHUTDOWN_TIMEOUT_SECONDS` 必填校验；缺失或越界非零退出。verify: `go test ./internal/config/...`；删变量启动失败。
- [x] **1.3 存活/就绪** — `/live` 不查依赖；`/health` 和 `/ready` 检查 MySQL、Qdrant、嵌入；query 400、非 GET 405。verify: `go test ./internal/health/...`；停 db 后 live 200、health 503、业务 503，恢复后 200。
- [x] **1.4 JSON 日志与 request ID** — 单行 JSON、`X-Request-ID` 生成/沿用、无 query/body/机密。verify: `go test ./internal/logging/...`；`docker compose logs api` 每行可解析，含 request_id/path/status。
- [x] **1.5 优雅停机** — SIGTERM 停止接新连接，最多等配置秒数，日志 `shutdown_complete`。verify: `make grade` 的 S13；`docker compose stop api` 后日志含 `shutdown_complete`。
- [x] **1.6 分层与变异门禁** — `scripts/layer_check.py`、`scripts/mutation.py`；新增 httpapi 文件不得有 SQL，legacy 例外登记。verify: `python3 scripts/layer_check.py`；`python3 scripts/mutation.py` 注入 SQL 时失败、还原后通过。
- [x] **1.7 一键检查与隔离验收** — `make check` 串起规约/规范/strict/分层/密钥/变异/Go/前端；`make grade` 独立 Compose 14 项并生成报告。verify: `make check` 退出 0；`make grade` 14/14 通过。
- [x] **1.8 CI 与证据归档** — GitHub Actions 跑 `make check` 和 `make grade`；复制脱敏报告到 `docs/framework/`；更新四步核对和贡献记录。verify: 本地 `make check`/`make grade` 通过；`docs/framework/verification.md` 含能力—Scenario—证据表；CI 工作流已推送；[run 40647071837](https://github.com/HanoFleet/teamwork/actions/runs/40647071837) 的 check/grade 均成功。
- [x] **1.9 归档与标签** — 全文 strict 通过后，把 delta 合并到 `openspec/specs/platform-foundation/spec.md`，归档本 change，打 `v0.1.0-skeleton`。verify: `npx -y @fission-ai/openspec@1.15.0 validate --all --strict`；`git tag -l 'v0.1.0-skeleton'`。

## 完成定义

- 7 条需求、19 个场景全部有对应证据。
- `make check`、`make grade`、`python3 scripts/verify.py` 全绿。
- 报告不含秘密；只有 web 映射宿主端口。
- `openspec validate --all --strict` 通过；标签和归档存在。
