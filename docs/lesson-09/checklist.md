# 第 9 课任务清单对照

| 第 9 课章节 | 实现/证据 | 状态 |
| --- | --- | --- |
| 一、开工前基线 | 第 8 课 `reports/security-precheck.md`；升 Go 后的 `docs/verification.md` | 2026-11-17 在 Go 1.26.11 上 `make check` 通过，含 gofmt、`go test`、vet 和前端构建 |
| 二、修授权 SEC-01～04 | `backend/internal/httpapi/{server,config,skill}.go`、`internal/catalog/`；`reports/security-fix-log.md` | `python3 scripts/verify.py` 已复测 SEC-03/04/07，通过 |
| 三、注入反例 | `apitest/cases/api/*/case.json`、`scripts/security_cases.py`、`scripts/security_test.py`、`reports/xss-page-source.md` | `make check` 检查反例文件和静态 XSS。在线 SQLi/XSS/CSRF 已由 `verify.py` 跑过并通过。列表页是登录后上传再打开，源码含 `&lt;script&gt;alert(1).md` |
| 四、资产处置 SEC-05～06 | `scripts/govuln_check.py`、`reports/govuln-disposition.md`、`reports/security-baseline.md` | 已在 Go 1.26.11 上跑过 govulncheck，输出 0 |
| 五、日志与 SEC-08 | `scripts/security_test.py` 的时间窗查询；`docs/verification.md`；`reports/sec08-experiment.md` | 时间窗查询已在 Compose 上跑过，SEC-03 记录为「时间窗查到 denied」。SEC-08 实验记录仍是升 Go 之前的那一次，这次没有重做 |
| 六、回归与归档 | `async-202`、两个 change 的归档、`docs/verification.md` | 归档早于这次 Go 升级。升级后已重跑：`make check` 通过，`make grade` 18/18（`reports/teacher-20261117T154351Z`，该目录不入库），`verify.py` 全部断言通过 |
| 七、核查清单 | `reports/security-fix-log.md`、`reports/review-02.md`、`review-03.md` | 脚本/AI 自审完成；人工复评待角色三 |

## 未完成/待人工

- 角色三人工独立复评和签字仍需执行；`review-02/03` 明确是 AI/脚本记录，不冒充人工。
- 显示标题用 `path.Base`。文件名 `<script>alert(1)</script>.md` 会被截成 `script>.md`，所以页面源码用的是不含 `/` 的 `<script>alert(1).md`。
- SEC-08 第四步没有在这次工具链上重做。
