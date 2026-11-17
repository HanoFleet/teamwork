# 任务清单：2026-11-17-harden-security

> 角色一维护；角色二实现，角色三复跑。任务默认未勾选；只有对应 verify 通过后才勾选。第 8 课的收口任务单独列在 8 组。

## 0. 基线与规约

- [x] **0.1 钉住第 8 课基线** — 涉及：`reports/security-precheck.md`、`reports/security-baseline.md`、`reports/review-01.md`。复跑 SEC-03/04/07，确认红项和缺口类别；记录 `make check` 当前绿基线。verify: 报告含复测时间、命令、实际红绿；`make check` 退出 0。
- [x] **0.2 登记 change** — 涉及：`scripts/spec_check.py`、`openspec/changes/2026-11-17-harden-security/`。把新 change 登记到 `CHANGE_RULES`，能力 `security-hardening`，需求/场景数与 proposal 表一致。verify: `python3 scripts/spec_check.py` 与 `openspec validate 2026-11-17-harden-security --strict` 通过。
- [x] **0.3 更新数据字典与安全规范** — 涉及：`docs/data-dictionary.md`、`docs/standards/03-security.md`、`06-ai.md`、`07-data.md`。补 `audit_logs`、`sessions.csrf_token`、`assistants`/`skills` 扩展、审计保留与敏感级别。verify: `scripts/standards_check.py` 通过；表字段和代码一致。

## 1. 数据库与种子

- [x] **1.1 sessions.csrf_token** — 涉及：`backend/internal/db/db.go`。新库 CREATE 含 `csrf_token`，旧库用 `ensureColumn` 补 `CHAR(64) NULL`；登录写入，旧 session 为空。verify: 新库/旧库各启动一次；`SHOW COLUMNS` 有列；旧 session 写请求 403。
- [x] **1.2 audit_logs 表** — 涉及：`db.go`、`docs/data-dictionary.md`。建表含七列、class_id、request_id、索引和保留规则；重复启动无副作用。verify: `SHOW CREATE TABLE audit_logs` 含索引；插入/查询一行成功。
- [x] **1.3 assistants/skills 扩展** — 涉及：`db.go`。assistants 补 class_id/system_prompt/enabled/updated_at；skills 补 skill_key/description/enabled/updated_at；补 `ensureIndex`。verify: 新库/旧库列存在；`skills.skill_key` 唯一索引存在；旧占位行不被误改。
- [x] **1.4 A/B 助手与技能种子** — 涉及：`db.go`。按班级幂等 seed A/B 助手，按 key seed `grade`、`ask`；不复制旧占位行。verify: 重复启动后 A/B 各一行、两个 skill key 各一行；`GET /api/assistants` 只看到本班。

## 2. CSRF 与前端传输

- [x] **2.1 登录/me 发放 token** — 涉及：`httpapi/auth.go`、`server.go`、`auth` 包。登录生成 32 字节随机 token 并写 session；登录响应和 `/api/me` 返回 `csrf_token`；Cookie 保持 HttpOnly/SameSite=Lax。verify: 登录响应含 64 hex；两次 `/api/me` 返回同一 token。
- [x] **2.2 requireUser 校验 CSRF/Origin** — 涉及：`httpapi/server.go`。Cookie 认证的 PUT/PATCH/POST/DELETE 校验 `X-CSRF-Token`；Bearer 免 token；Origin/Referer 跨源 403；失败写审计。verify: Go 单测 + curl 四类场景：无 token、错 token、跨源、Bearer。
- [x] **2.3 前端移除 localStorage token** — 涉及：`frontend/src/api.ts`、`App.tsx`。网页只用 Cookie；token 存内存；`api()` 自动加 `X-CSRF-Token`；上传 XHR 加 header；401 清理内存 token。verify: `grep` 无 `localStorage` token；`npm run build` 通过。
- [x] **2.4 登录/刷新 token 恢复** — 涉及：`api.ts`、`App.tsx`、`Assignments.tsx`。登录响应和 `getMe()` 都更新 token；刷新后写请求仍带 token。verify: 浏览器刷新 `/assignments` 后提交成功；无 token 的请求 403。

## 3. 配置 API

- [x] **3.1 catalog 包** — 涉及：`backend/internal/catalog/`（新增）。实现 skills/assistants 查询与更新；SQL 只在 catalog；按 class_id 过滤助手；按 skill_key 查技能。verify: Go 单测覆盖查询、更新、跨班 404；`scripts/layer_check.py` 通过。
- [x] **3.2 配置路由** — 涉及：`httpapi/config.go`（新增）、`server.go`。新增 `GET/PATCH /api/skills`、`GET/PATCH /api/assistants`；教师写、学生 403；非法 body 400。verify: curl 教师/学生/匿名三身份；数据前后对比。
- [x] **3.3 班级隔离与请求字段忽略** — 涉及：`catalog`、`httpapi/config.go`。助手按会话班级加载；body 里的 class_id/role/user_id 不采信；跨班 404 与不存在同形。verify: A 教师改 B 助手 404；body 带 class_id=B 仍只改 A 班。
- [x] **3.4 配置写审计** — 涉及：`httpapi/config.go`、`internal/audit/`。成功写 `config.update` success；403/404 写 denied；对象为 `skill:<key>` 或 `assistant:<id>`。verify: 审计表行字段完整；无正文/提示词/密钥。

## 4. 技能运行

- [x] **4.1 技能路由** — 涉及：`httpapi/skill.go`（新增）、`server.go`。新增 `POST /api/skills/{key}/run`；只允许启用技能；未知/禁用 404。verify: 未知 key、禁用 grade、启用 grade 三种响应。
- [x] **4.2 复用 EnqueueGrade** — 涉及：`grading/service.go`、`httpapi/skill.go`。`grade` 只接受 submission_id，复用 `EnqueueGrade`；学生只能本人；他人/跨班 404；不接受 score/feedback。verify: 本人 202；他人 404 且 task/outbox/result 不增；body 带 score 仍按正文评分。
- [x] **4.3 教师/跨班拒绝** — 涉及：`httpapi/skill.go`、`grading/service.go`。教师运行 404；跨班学生 404；不泄露提交是否存在。verify: 两类请求响应 body 与不存在 id 相同；库无残留。
- [x] **4.4 技能运行审计** — 涉及：`httpapi/skill.go`、`internal/audit/`。成功写 `skill.run` accepted/success；失败写 denied；记录 skill_key=grade、submission 对象、耗时、usage 元数据。verify: 教师按 skill_key 查到行；行内无正文/密钥。

## 5. 审计日志与查询

- [x] **5.1 audit Store** — 涉及：`backend/internal/audit/`（新增）。`Insert` 截断/转义字符串，`usage_json` 只允许模型/token 元数据；`List` 按 class_id、skill_key、operator、时间窗、limit 查询。verify: Go 单测覆盖截断、非法 usage、过滤和 limit。
- [x] **5.2 审计查询路由** — 涉及：`httpapi/audit.go`（新增）、`server.go`。`GET /api/audit-logs` 教师可查本班；学生 403；limit 1–100；时间格式非法 400；DB 不可用 503。verify: 教师/学生/匿名/非法参数四类测试。
- [x] **5.3 拒绝与 CSRF 审计** — 涉及：`httpapi/server.go`、`config.go`、`skill.go`。CSRF 失败、配置 403/404、技能 404 都写 denied；匿名 401 不写。verify: 每种拒绝后审计行存在；401 前后审计计数不变。
- [x] **5.4 审计查询字段** — 涉及：`httpapi/audit.go`、`audit` 包。响应含七列 + request_id；不返回 body/prompt/secret；按时间倒序。verify: 响应字段断言；敏感字符串扫描为 0。

## 6. 注入反例与门禁

- [x] **6.1 SQLi 反例** — 涉及：`scripts/security_test.py`、`apitest/cases/security/`。测试登录/材料查询/搜索的 `' OR '1'='1`、`%`、`_`；断言无 B 班标题、无 500、无 SQL 报错。verify: 用例通过；跨班/同班对照结果正确。
- [x] **6.2 XSS 反例** — 涉及：`scripts/security_test.py`、`frontend/src/App.tsx`、`apitest/cases/security/`。上传 `<script>` 标题/正文；断言 JSON 转义、前端无 raw HTML。verify: 用例通过；源码扫描无 `rehype-raw`/`dangerouslySetInnerHTML`。
- [x] **6.3 CSRF 反例** — 涉及：`scripts/security_test.py`。同源无 token 403、恶意 Origin 403、正确 token 成功；Cookie 标志仍 HttpOnly/SameSite=Lax。verify: 三组断言通过；数据不变。
- [x] **6.4 security_test 接入 verify/acceptance** — 涉及：`scripts/verify.py`、`scripts/acceptance.py`、`scripts/check.sh`。`verify.py` 调用 security_test；acceptance 加 A16–A19；check.sh 编译 security_test。verify: `make check`、`make grade`、`verify.py` 全通过。
- [x] **6.5 security_gate 红绿** — 涉及：`scripts/security_gate.py`、`Makefile`、`.github/workflows/check.yml`。secret scan + npm audit；命中/高危非 0；`--self-test` 用临时 git 仓库假密钥制造红项。verify: 红项退出 1，正常退出 0；`reports/gate-red-green.md` 含两次输出。
- [x] **6.6 静态安全回归** — 涉及：`scripts/check.sh`、`scripts/layer_check.py`。check.sh 增加前端 token/raw HTML 静态检查和 security_test 编译；新增 httpapi 仍无 SQL。verify: 故意注入违规字符串时检查失败，恢复后通过。

## 7. SEC-08 实验

- [x] **7.1 素材** — 涉及：`docs/lesson-09/sec08/`。准备 1 份含“忽略以上指令”的恶意讲义和 3 条诱导提问（提示词原文、改评分、绕权限）。verify: 素材存在；不含真实密钥或个人信息。
- [x] **7.2 四步实验脚本** — 涉及：`scripts/sec08_experiment.py`。登录、上传/选择恶意材料、跑三条提问、跑技能越权写入；记录实际输出，不修改生产数据。verify: 四步都有输出；第四步写入被 404/403 拒绝，审计有 denied。
- [x] **7.3 SEC-08 报告** — 涉及：`reports/sec08-experiment.md`。记录执行时间、身份、命令、实际现象、判定；第四步为绿，前三步如实记录。verify: 报告可按路径打开；不复制真实提示词/密钥。

## 8. 回归、第 8 课收口与归档

- [x] **8.1 全量回归** — 涉及：`make check`、`make check-security`、`make grade`、`verify.py`、Playwright。三组全跑；安全修复不误伤材料、问答、异步判据。verify: 全部退出 0；报告含命令和结果。
- [x] **8.2 修复证据** — 涉及：`reports/security-fix-log.md`、`reports/security-precheck.md`、`reports/security-baseline.md`。SEC-03/04/07/08 修复前后对照；更新基线命令，删除不存在的 `week8_security.py` 说明。verify: 每个红项有修复后实际值；基线与当前仓库命令一致。
- [x] **8.3 复评记录** — 涉及：`reports/review-02.md`、`reports/review-03.md`。至少两份来自 AI 自审/脚本输出，写清手段/查了什么/判据/结果；不冒充人工签字。verify: 记录可检索；引用实际命令和输出。
- [x] **8.4 Playwright 第 8 课 5.2** — 涉及：`frontend/e2e/`（含 `playwright.config.ts`、`package.json`）。从 `/assignments` 提交并轮询到 succeeded；失败/dead 显示原因。verify: 本地 Compose 下 Playwright 通过；截图/报告归档。
- [x] **8.5 CI full verify** — 涉及：`.github/workflows/check.yml`、`scripts/ci_env.py`。新增 verify job：生成隔离 env，起 Compose，跑 verify.py（三条判据）和 Playwright，失败也清理。verify: CI run 成功；日志可查。
- [x] **8.6 第 8 课任务勾选** — 涉及：`openspec/changes/2026-11-05-add-async-grading/tasks.md`。30 条任务逐条对照证据；有 verify 的勾选，缺证据的保留并写原因；不把代码存在当验收。verify: 勾选数与证据表一致。
- [x] **8.7 async-202 与归档** — 涉及：Git tag、`openspec/changes/archive/`、`openspec/specs/async-grading/`。全部通过后打 `async-202`；归档 change 并同步长期 specs；更新 README/SPEC/AGENTS。verify: `git tag -l` 有 async-202；archive 目录可查；strict 通过。
- [x] **8.8 第 9 课归档判断** — 涉及：`reports/`、`openspec/changes/2026-11-17-harden-security/`。所有 Requirement 有实际证据后勾选本 change；未通过项保留红并阻塞归档。verify: 任务勾选、报告路径、CI 结果三者一致。

## 完成定义

- SEC-03/04/07 复测绿；SEC-08 四步有记录，第四步绿。
- SQLi/XSS/CSRF 用例实际执行；`make check`、`make check-security`、`make grade`、`verify.py`、Playwright、CI 全通过。
- 审计日志七列可按 skill_key 回查；学生配置/审计 403，跨班/他人 404 无残留。
- 第 8 课任务有证据的勾选，`async-202` 和归档完成；没有证据的保持未勾选并写明。
- 报告中的红绿来自实际命令，不伪造、不把“无接口”写成“已拒绝”。
