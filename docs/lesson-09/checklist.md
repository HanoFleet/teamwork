# 第 9 课任务清单对照

| 第 9 课章节 | 实现/证据 | 状态 |
| --- | --- | --- |
| 一、开工前基线 | 第 8 课 `reports/security-precheck.md`；升 Go 前的 `docs/verification.md` | 升到 Go 1.26.11 之后还没有重跑 `make check` |
| 二、修授权 SEC-01～04 | `backend/internal/httpapi/{server,config,skill}.go`、`internal/catalog/`；`reports/security-fix-log.md` | 代码仍在；升 Go 后没有重跑接口复测 |
| 三、注入反例 | `apitest/cases/api/*/case.json`、`scripts/security_cases.py`、`scripts/security_test.py` | `make check` 只检查三段式文件和静态 XSS；在线请求在 `verify.py`，本机还没跑 |
| 四、资产处置 SEC-05～06 | `scripts/govuln_check.py`、`reports/govuln-disposition.md`、`reports/security-baseline.md` | 已在 Go 1.26.11 上跑过 govulncheck，输出 0 |
| 五、日志与 SEC-08 | `scripts/security_test.py` 的时间窗查询；`reports/sec08-experiment.md` | 时间窗查询已写进测试，还没有对 Compose 跑过；SEC-08 第四步仍是升 Go 前的记录 |
| 六、回归与归档 | `async-202`、两个 change 的归档 | 归档是升 Go 之前的；`make check`、`make grade`、`verify.py` 还没有用新工具链重跑 |
| 七、核查清单 | `reports/security-fix-log.md`、`reports/review-02.md`、`review-03.md` | 脚本/AI 自审完成；人工复评待角色三 |

## 未完成/待人工

- 角色三人工独立复评和签字仍需执行；`review-02/03` 明确是 AI/脚本记录，不冒充人工。
- 角色二已提交 Go 依赖清零（`cfe7e74`、`1a7e58f`）、注入反例文件（`b4659ee`）、列表页源码（`fc77004`）和审计时间窗测试（`090ca01`）。
- `fc77004` 的页面源码来自 Vite 上的真实列表页，标题由材料接口返回，不是先上传再打开。上传路径写在同一个 Playwright 用例里，本机没有 Compose，所以没跑。
- `090ca01` 和三条注入反例的在线请求都要等 `python3 scripts/verify.py`。本机 Docker 未启动，这次没有跑。
- 角色三人工独立复评仍然没做。
