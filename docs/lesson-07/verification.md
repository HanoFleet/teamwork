# Platform Foundation 验证记录

日期：2026-10-28。分支：`change/platform-foundation`。骨架提交：`635d465`。范围：第 7 课可运行骨架，不含材料库新功能。

## 结论

- `make check`：通过（规约、规范、OpenSpec strict、分层、密钥、变异、Go 测试/vet、前端构建）。
- `make grade`：独立 Compose 项目 14 项检查全部通过，报告见 [`teacher-report.html`](teacher-report.html) 和 [`teacher-report.json`](teacher-report.json)。
- `python3 scripts/verify.py`：迭代 1/2 的登录、班级隔离、上传、检索、问答、停库场景全部通过。
- `python3 scripts/acceptance.py --self-test`：退出码 1，报告 `status=failed`，证明失败不会被写成通过。

## 能力—Scenario—证据

| 能力 / Scenario | 证据 |
| --- | --- |
| F1 / S01 干净克隆一条命令启动 | `make grade` A01；`docker compose ps` web/api/db healthy，qdrant 已启动；`/live` 200 |
| F1 / S02 缺失或越界配置启动失败 | `go test ./internal/config/...` 覆盖缺失项；`APP_VERSION`、`SHUTDOWN_TIMEOUT_SECONDS` 为 `need()` 必填，越界返回错误 |
| F1 / S03 端口只暴露 web | `make grade` A12；`docker compose config --format json` 检查 db/qdrant/api 无 `ports` |
| F2 / S04 依赖正常时就绪通过 | `make grade` A02/A03；`/health` 与 `/ready` 200，`checks` 三项 true |
| F2 / S05 MySQL 停止时只有就绪失败 | `make grade` A10/A11；停 db 后 live 200、health 503（db=false）、材料接口 503，恢复后 200 |
| F2 / S06 Qdrant 停止时就绪失败 | `make grade` A13；停 qdrant 后 live 200、health 503（qdrant=false），恢复后 200 |
| F2 / S07 查询参数和非 GET 被拒绝 | `make grade` A05/A06；`GET /health?x=1` 400，`POST /health` 405 |
| F3 / S08 未登记 API 不存在 | `make grade` A04；`GET /api/nope` 404；附件路径由 Nginx 返回 404 |
| F3 / S09 未登录业务接口仍是 401 | `make grade` A07；`GET /api/materials` 401，无材料正文 |
| F4 / S10 缺失请求 ID 时生成并贯穿 | `go test ./internal/logging/...`；`make grade` A08 验证合法 ID 回写 |
| F4 / S11 合法请求 ID 原样回写 | `make grade` A08；响应头与日志均为 `verify-lesson07` |
| F4 / S12 日志不含敏感内容 | `make grade` A09；JSON 日志可解析，无 `SESSION_SECRET=`/`DB_PASSWORD=` |
| F5 / S13 在途请求完成后再退出 | `backend/internal/lifecycle/server_test.go` 的 `TestServeDrainsInflightRequest` |
| F5 / S14 超出预算强制结束 | `backend/internal/lifecycle/server_test.go` 的 `TestServeForceClosesAfterTimeout` |
| F6 / S15 正常门禁通过 | `make check`；`scripts/layer_check.py` 输出通过 |
| F6 / S16 注入 SQL 时门禁变红 | `scripts/mutation.py`：注入 `SELECT * FROM users` 时失败，还原后通过 |
| F7 / S17 隔离验收通过并生成报告 | `make grade` 14/14，`reports/teacher-*/report.html`、`report.json` |
| F7 / S18 失败或缺证据不能判通过 | `python3 scripts/acceptance.py --self-test` 退出 1，报告 `status=failed` |
| F7 / S19 验收隔离并清理 | `make grade` 使用 `campusclaw-acceptance` 独立项目、随机端口/口令，`down -v` 只清理自建资源；正式 Compose 不受影响 |

## CI

- 2026-10-28，提交 `6298002`，GitHub Actions [run 40647071837](https://github.com/HanoFleet/teamwork/actions/runs/40647071837)：`check` 和 `grade` 两个 job 都成功。
- 工作流：`.github/workflows/check.yml`，在 push、PR 和手动触发时运行 `make check` 与 `make grade`。

## 门禁命令

```text
$ make check
规约与规范：通过
OpenSpec strict：4 passed, 0 failed
分层、密钥、变异：通过
Go 格式/测试/vet：通过
前端 npm ci + build：通过（0 vulnerabilities）
check 全部通过

$ make grade
{"status": "passed", "counts": {"passed": 14, "failed": 0, "total": 14}}

$ python3 scripts/verify.py
全部断言通过。
```

## 说明

- 现有 `httpapi/auth.go`、`materials.go`、`server.go` 中的 SQL 是迭代 1/2 legacy 例外，已在 `design.md` 和 `docs/standards/02-backend.md` 登记；`layer_check.py` 只对新增文件失败。
- `/health` 的语义从“进程存活”改为“依赖就绪”，`/live` 承担存活；`verify.py` 已同步。
- CI 工作流在 `.github/workflows/check.yml`，推送和 PR 都会运行 `make check` 与 `make grade`；运行记录见 GitHub Actions。
- 前端依赖已升级到 Vite 8.3.5、react-router-dom 7.18.5，`npm audit` 为 0；未做完整浏览器回归，本 change 只保证构建和现有页面可加载。
- 单人/三人评审：角色二、角色三的独立复现仍按 `docs/项目启动-四步核对.md` 的待办执行，不冒充已完成。


## Fresh-session 检查记录

2026-10-28，按课程要求用无历史上下文的只读会话，仅给仓库路径和变更名，检查 material-library 四份文件能否照做。共执行多轮：

- 第一轮发现 20 余处未定义行为，包括 restore 语义、PATCH 的 title/tags 语义、进度 version/position、reindex 请求体、批量 client_ids、同形 404 与响应头、旧版本文件、二进制版本比较等；已逐项补进 proposal/design/specs/tasks。
- 后续轮次继续发现索引中编辑、purge 取消、无进度默认值、文本版本文件、学生访问版本、client_ids 数量、custom 参数持久化、恢复 failed 状态等；已修复。
- 最后一轮指出的 2 项（custom 的 `max_len`/`overlap_ratio` 持久化、恢复 failed 后不自动重试）已写入 `design.md` 和 material spec。
- 未再发现会阻断正常实现的新业务歧义；建议组内再跑一次独立会话做最终复核，不把本记录当成第三方评审。

## 第7课任务清单对照

| 任务清单项 | 状态 | 说明 |
| --- | --- | --- |
| 仓库地址可访问、教师有权限 | 通过 | 公开仓库 https://github.com/HanoFleet/teamwork |
| 仓库名用课题短名 | 差异 | 当前名 `teamwork`，不是 `campusclaw-2.0` 这类短名；只有仓库主人能改名，GitHub 会保留旧 URL 重定向 |
| 首次提交仅 README/.gitignore/LICENSE | 历史差异 | 仓库来自迭代 1/2，历史不是从空仓库开始；没有重写历史。当前根目录的首次提交材料已齐备 |
| README 一句话定位 + 本地运行 | 通过 | `README.md`、`SPEC.md` |
| .gitignore 先于代码 | 当前状态通过 | `.env`、`node_modules`、`dist`、`reports`、`.env.acceptance` 等已忽略；历史无法追溯 |
| `.env.example` 只写键名 | 通过 | 根目录 `.env.example` |
| 变更命名 `YYYY-MM-DD-英文名` | 通过 | foundation 和 material-library 都带日期 |
| 提交信息写依据 | 通过 | 最新提交含 `Change:`、`Task:`、`Spec:`、`Verify:` |
| 每人 clone 跑通 | 待组内执行 | 命令见 README；三人独立复跑未完成 |
| 四份文件齐全 | 通过 | foundation 7 需求/19 场景/9 任务已归档；material-library 26 需求/151 场景/46 任务活动 |
| `--strict` 通过 | 通过 | `validate --all --strict` 4 passed |
| 每条能力至少一组 Scenario / 失败路径 ≥4 | 通过 | 400/403/404/503/409/413 均有 |
| 能力与 Scenario 两列表 | 通过 | 本文件与 `proposal.md` |
| 五类必修 + 三类选用规范 | 通过 | `docs/standards/01` 至 `08` |
| 规范放在 Harness 可读位置 | 通过 | `AGENTS.md`、`.cursor/rules/`、`.cursor/skills/` |
| 改代码验证规范生效 | 通过 | `scripts/mutation.py` 注入 SQL 失败、还原通过；`make check` |
| 另起会话结果一致 | 已执行多轮 | 无历史只读会话发现项已逐项修复；最后一轮 2 项已写入 design/spec；组内最终复核待做 |
| 分层无反向依赖 | 例外 | 新增包已分层；`httpapi/auth.go`、`materials.go`、`server.go` 的 legacy SQL 登记为例外，材料库 change 迁移 |
| 配置全外置、缺失即失败 | 通过 | `APP_VERSION`、`SHUTDOWN_TIMEOUT_SECONDS` 等必填 |
| `/health` 免认证并返回依赖状态 | 通过 | `/health` 就绪；`/live` 存活；`/ready` 别名 |
| 日志一行 JSON + 请求标识 | 通过 | `internal/logging` |
| 骨架标签存在 | 通过 | `v0.1.0-skeleton` → `635d465` |
| 验证记录归档 `docs/lesson-07/` | 通过 | 本文件、`teacher-report.html`、`teacher-report.json` |
| 组内另一人从零启动 | 待执行 | 需要组员各自 clone、填 `.env`、`docker compose up -d --wait` |
| 主干保护规则 | 待仓库主人 | 当前账号无 admin 权限；需要 owner 设置 PR + status checks |
