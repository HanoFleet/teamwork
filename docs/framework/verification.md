# Platform Foundation 验证记录

日期：2026-10-28。分支：`change/platform-foundation`。骨架提交：`fca2793`。范围：第 7 课可运行骨架，不含材料库新功能。

## 结论

- `make check`：通过（规约、规范、OpenSpec strict、分层、密钥、变异、Go 测试/vet、前端构建）。
- `make grade`：独立 Compose 项目 14 项检查全部通过，报告见 [`teacher-report.html`](teacher-report.html) 和 [`teacher-report.json`](teacher-report.json)。
- `python3 scripts/verify.py`：迭代 1/2 的登录、班级隔离、上传、检索、问答、停库场景全部通过。
- `python3 scripts/acceptance.py --self-test`：退出码 1，报告 `status=failed`，证明失败不会被写成通过。

## 能力—Scenario—证据

| 能力 / Scenario | 证据 |
| --- | --- |
| F1 / S01 干净克隆一条命令启动 | `make grade` A01；`docker compose ps` 四个服务 healthy；`/live` 200 |
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
- CI 工作流已准备；本次推送因 PAT 缺少 `workflow` 权限未包含 `.github/workflows/check.yml`，待权限修复或从 GitHub 网页添加；本地 `make check`/`make grade` 已通过。
- 前端依赖已升级到 Vite 8.3.5、react-router-dom 7.18.5，`npm audit` 为 0；未做完整浏览器回归，本 change 只保证构建和现有页面可加载。
- 单人/三人评审：角色二、角色三的独立复现仍按 `docs/项目启动-四步核对.md` 的待办执行，不冒充已完成。
