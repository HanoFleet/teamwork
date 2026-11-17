# 第 9 课任务清单对照

| 第 9 课章节 | 实现/证据 | 状态 |
| --- | --- | --- |
| 一、开工前基线 | 第 8 课 `reports/security-precheck.md`；本轮 `docs/verification.md`；`make check` | 已复跑 |
| 二、修授权 SEC-01～04 | `backend/internal/httpapi/{server,config,skill}.go`、`internal/catalog/`；`reports/security-fix-log.md` | SEC-01/02 绿；SEC-03/04 复测绿 |
| 三、注入反例 | `apitest/cases/api/*/case.json`、`scripts/security_cases.py`、`scripts/security_test.py` | 文件和静态检查进 `make check`；在线请求进 `verify.py` |
| 四、资产处置 SEC-05～06 | `scripts/govuln_check.py`、`reports/govuln-disposition.md`、`reports/security-baseline.md` | 密钥 0；npm 高危 0；Go 1.26.11 上 govulncheck 0 |
| 五、日志与 SEC-08 | `audit_logs`、`GET /api/audit-logs?operator_id&from&to`、`reports/sec08-experiment.md` | 七列可查；学生 403 按时间窗回查；第四步绿 |
| 六、回归与归档 | `make check`、`make grade`、`verify.py`、Playwright、`async-202`、async change 归档 | 已完成；async 与 harden change 均已归档 |
| 七、核查清单 | `reports/security-fix-log.md`、`reports/review-02.md`、`review-03.md` | 脚本/AI 自审完成；人工复评待角色三 |

## 未完成/待人工

- 角色三人工独立复评和签字仍需执行；`review-02/03` 明确是 AI/脚本记录，不冒充人工。
- 角色二已补 Go 依赖清零（`cfe7e74`、`1a7e58f`）、注入反例落盘（`b4659ee`）、列表页源码（`fc77004`）和审计时间窗（`090ca01`）。人工复现不在这些提交里。
