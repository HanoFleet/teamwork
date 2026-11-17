# 变更提案：2026-11-17-harden-security

| 项目 | 内容 |
| --- | --- |
| 变更名 | `2026-11-17-harden-security` |
| 阶段 | 第 9 课：从红到绿 |
| 负责人 | 李斯坦（角色一：制定规约） |
| 评审 | 韩雅慧（角色二：开发系统）、禹霖（角色三：项目验收） |
| 基线 | `53951aa` + 第 8 课安全自查（SEC-03/04/07 红） |
| 状态 | 规约与实现同步交付，验收证据待复跑 |

## Why

第 8 课安全自查留下三项红：SEC-03 没有技能/提示词/助手配置写入口，SEC-04 没有技能执行链可验证绕过鉴权，SEC-07 没有可回查的技能审计日志。SEC-08 也未准备实验素材。第 9 课要求把红项修绿，同时补 SQL 注入、XSS、CSRF 三条反例、资产门禁红绿证据、回归和归档证据。

现有代码的授权检查分散在各 handler；技能/助手只有占位表；写请求只有 `SameSite=Lax`，没有 CSRF token；审计只有请求日志和 worker 任务日志，缺少操作人、对象、技能标识和用量。本 change 只做最小可验证的安全链路，不扩完整设置页和外部工具调用。

## What Changes

1. **CSRF 与同源校验**：登录和 `/api/me` 发放会话级一次性 token；Cookie 写请求必须带 `X-CSRF-Token`，Bearer 免 token；跨源 Origin/Referer 返回 403。
2. **教师配置 API**：新增技能与助手的查询/更新接口；学生写 403，助手按班级隔离，跨班 404；技能为全局目录。
3. **受控技能执行**：新增 `POST /api/skills/{key}/run`；`grade` 技能复用现有批改入队和归属校验，不允许直接写分数；跨班/他人 404 且库中无残留。
4. **七列审计日志**：新增 `audit_logs`；记录操作人、时间、操作类型、对象、结果、技能标识、用量/耗时；拒绝和 CSRF 失败也记录；教师可查，学生 403。
5. **注入反例与门禁**：新增 SQL 注入、XSS、CSRF 用例；`security_gate.py` 让 `make check-security` 在密钥命中或前端高危时非零退出；保存红绿证据。
6. **SEC-08 实验**：准备恶意讲义和 3 条诱导提问，记录四步实验；第四步工具/写入层必须拒绝并留审计。
7. **第 8 课收口**：补 Playwright `/assignments` 用例和 CI 的完整 `verify.py` job；证据齐后勾选 async tasks、打 `async-202`、归档。

## Out of Scope（本次不做）

- 不做完整设置页、技能市场、助手编排 UI；配置 API 只服务安全测试和最小管理。
- 不接真实外部模型工具调用；SEC-08 使用本地确定性问答，记录实际现象。
- 不做多实例共享限流、生产 HTTPS、`Secure` Cookie、版本化 schema_migrations。
- 不把 XSS/注入测试扩展成全站渗透测试；只覆盖课程要求的三条反例。
- 不修改已有 401/403/404 语义，除新增 CSRF 403 和审计查询 403。

## Alternatives Considered（放弃的候选方案）

| 候选方案 | 为什么放弃 |
| --- | --- |
| 只做 Origin/Referer，不做 CSRF token | 实现更小，但任务清单明确要求“缺少一次性令牌被拒”，无法给出绿证据。 |
| 用 localStorage 保存 CSRF token | 仍可被 XSS 读取；token 放内存，刷新后由 `/api/me` 重新发放。 |
| 直接开放通用 `/api/grade-results` 写入接口来测绕过 | 会制造真实后门；技能执行只包装现有入队服务，不开放分数写入。 |
| 为 SEC-03 只返回占位 403 | 没有真实配置写入和数据库前后核验，属于伪造绿项。 |
| 审计只写 stdout | 无法按技能标识、操作人和时间窗稳定回查；必须落库并保留查询接口。 |
| 用假密钥截图当门禁红项 | 必须让扫描器真实失败；用临时 git 仓库的假密钥跑 `secret_scan.py`，再跑绿项。 |

## Capabilities

### New Capabilities

- `security-hardening`：CSRF/同源、教师配置权限、受控技能执行、七列审计日志、注入反例、安全门禁和 SEC-08 实验。

### Modified Capabilities

- 无行为删除；认证、批改和材料接口保持现有契约，只增加 CSRF 校验、审计和新路由。

## Capability–Scenario Map（能力与场景对应）

| Capability | 类型 | Requirement 数 | Scenario 数 | 主要失败路径 | 验收证据 |
| --- | --- | ---: | ---: | --- | --- |
| `security-hardening` | 新增 | 6 | 29 | CSRF 403、学生配置 403、跨班 404、非法参数 400、审计库 503 | `reports/security-fix-log.md`、`reports/gate-red-green.md`、`reports/sec08-experiment.md`、`scripts/security_test.py`、`make grade`、CI |

## Failure Path Coverage（失败路径覆盖）

- **参数非法**：登录/配置/技能请求 body 非法、审计查询 limit 非法返回 400，且不写业务数据。
- **无权限**：学生调用教师配置写接口 403；学生查询审计 403；CSRF token 缺失/错误 403；Bearer 认证免 token。
- **资源不存在**：跨班助手、他人提交、未知/禁用技能、不存在审计对象统一同形 404；不泄露归属。
- **依赖不可达**：审计表/数据库不可用时查询返回 503；安全门禁在密钥或高危依赖命中时退出非 0。

## Evidence

- `reports/security-fix-log.md`：SEC-03/04/07/08 修复前后对照。
- `reports/gate-red-green.md`：`security_gate.py --self-test` 红项和正常绿项的实际输出。
- `reports/sec08-experiment.md`：四步实验现象，第四步工具/写入层为绿。
- `reports/review-02.md`、`reports/review-03.md`：AI 自审/脚本复现记录。
- `apitest/cases/security/`：SQLi/XSS/CSRF 和配置/技能/审计用例说明。
- `docs/lesson-09/checklist.md`：七节任务到证据的映射。

## Success Criteria（完成现象）

- SEC-03/04/07 复测变绿；SEC-08 四步有实际记录。
- SQLi/XSS/CSRF 三件套实际执行通过；无 raw HTML、无跨班泄露。
- 学生配置写 403 且数据库不变；跨班助手/他人提交 404 且无 task/outbox/result。
- 审计日志按 `skill_key=grade` 能查到七列；学生查审计 403。
- `make check`、`make check-security`、`make grade`、`verify.py`、Playwright 和 CI 全通过。
- 第 8 课 `tasks.md` 有证据的条目勾选，`async-202` 标签和归档完成；没有证据的条目保持未勾选并写明原因。
