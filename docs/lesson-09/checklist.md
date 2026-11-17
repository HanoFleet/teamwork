# 第 9 课任务清单对照

| 第 9 课章节 | 实现/证据 | 状态 |
| --- | --- | --- |
| 一、开工前基线 | 第 8 课 `reports/security-precheck.md`；本轮 `docs/verification.md`；`make check` | 已复跑 |
| 二、修授权 SEC-01～04 | `backend/internal/httpapi/{server,config,skill}.go`、`internal/catalog/`；`reports/security-fix-log.md` | SEC-01/02 绿；SEC-03/04 复测绿 |
| 三、注入反例 | `scripts/security_test.py`、`apitest/cases/security/README.md`；SQLi/XSS/CSRF 均 PASS | 绿 |
| 四、资产处置 SEC-05～06 | `scripts/security_gate.py`、`reports/gate-red-green.md`、`reports/security-baseline.md` | 门禁红绿；npm 0；密钥 0 |
| 五、日志与 SEC-08 | `audit_logs`、`GET /api/audit-logs`、`docs/lesson-09/sec08/`、`reports/sec08-experiment.md` | 七列可查；第四步绿 |
| 六、回归与归档 | `make check`、`make grade`、`verify.py`、Playwright、`async-202`、async change 归档 | 已完成；async 与 harden change 均已归档 |
| 七、核查清单 | `reports/security-fix-log.md`、`reports/review-02.md`、`review-03.md` | 脚本/AI 自审完成；人工复评待角色三 |

## 未完成/待人工

- 角色三人工独立复评和签字仍需执行；`review-02/03` 明确是 AI/脚本记录，不冒充人工。
- `reports/security-baseline.md` 中 Go `govulncheck` 的 46 条通报仍需按包登记处置；本轮只把 npm 高危纳入阻断门禁。
