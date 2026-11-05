# 角色二评审记录：规约与工程规范

- 评审人：韩雅慧（角色二：开发系统）
- 日期：2026-11-06
- 手段：按 `docs/阶段一-交付说明.md` 第 5 节和 `docs/standards/08-review.md` 检查表，读三份 change 的 proposal/design/specs/tasks，以及 `docs/standards/02-backend.md`、`04-testing.md`、`06-ai.md`。
- 范围：只评「能不能按规约实现、边界清不清」；不勾选 `tasks.md`，不打 `async-202`，不写 SEC 红绿（那是角色三的 `reports/review-01.md` / `reports/security-precheck.md`）。
- 时序说明：async-grading 的代码已经按 `tasks.md` 落地，本记录是补书面评审；material-library 尚未开工，本记录作为后续实现前的结论。

判定只用：通过 / 有保留通过 / 不通过 / 不适用。

## 1. 检查表

| 看什么 | foundation | async-grading | material-library | 02 后端 | 04 测试 | 06 AI |
| --- | --- | --- | --- | --- | --- | --- |
| 边界与不做 | 通过 | 通过 | 通过 | 通过 | 通过 | 通过 |
| 失败路径（非法/无权限/不存在/依赖不可达） | 通过 | 通过 | 通过 | 通过 | 通过 | 通过 |
| 权限与同形 404 | 通过 | 通过 | 通过 | 通过 | 不适用 | 通过 |
| 数据模型与事务 | 通过 | 有保留通过 | 通过 | 有保留通过 | 不适用 | 不适用 |
| 文案与接口形状 | 通过 | 有保留通过 | 通过 | 通过 | 不适用 | 通过 |
| 规模是否可实现 | 通过 | 通过 | 有保留通过 | 通过 | 通过 | 通过 |
| 证据与门禁 | 通过 | 有保留通过 | 不适用（未实现） | 通过 | 有保留通过 | 通过 |

总评：三份规约都可以作为实现依据，没有「写了做不到」的条款。async-grading 允许继续验收；material-library 允许读，但开工前要处理规模问题。没有整份不通过。

## 2. foundation（已归档）

**查了什么**：`openspec/changes/archive/2026-10-28-establish-platform-foundation/` 的四份文件。

**判据**：一条 Compose 能起；`/live` 与 `/health` 分离；不做材料库新功能；legacy SQL 有书面例外。

**结果：通过。**

- 范围清楚：只加固骨架，登录/材料/检索/问答行为不改。
- 放弃方案合理：不用空仓库、不把 `/health` 继续当存活、不在骨架阶段迁完 SQL。
- 实现侧已有 `v0.1.0-skeleton` 和 `make grade` 骨架项，本评审不代替角色三复跑。

## 3. async-grading（当前实现目标）

**查了什么**：`openspec/changes/2026-11-05-add-async-grading/` 四份文件，对照 `docs/lesson-08/self-check.md` 10 行。

**判据**：提交与批改可拆；202 不含分数；outbox 可实现；失败四类都有场景；不做完整作业模块和 SEC 自查本身。

**结果：有保留通过（可实现，三处措辞要记住，不改 Scenario）。**

1. **课件「提交返回 202」已被规约拆开，这是对的。** `POST .../submissions` 返回 200/201，`POST .../grade` 才返回 202。`spec.md` 的 Purpose 仍写「提交只返回 202」，与 Requirement 正文不一致。实现按 Requirement 和 `tasks.md` 2.1/2.2，不按 Purpose 那一句。角色一可在后续改 Purpose，实现者不得为了通过去改 Scenario。
2. **`GET /api/assignments` 是前端必需，Interfaces 表原先没列。** design 的 Frontend 写了「列出本班已发布作业」，但接口表只有 submissions/grade/tasks。实现已补只读列表；权限与班级隔离沿用会话班级。建议角色一补进接口表，不当新功能。
3. **proposal「提交/任务/outbox 同事务」容易读成「POST submissions 就写 task」。** `tasks.md` 2.2 写明是 grade 请求在同一事务写 submission 状态、grade_task、outbox。实现按 2.2：提交正文先落库，批改再开事务。这与「有批改必有任务」一致，不是「有正文必有任务」。
4. **门禁例外已有书面出处。** `08-review` 把 Playwright 写成合并必跑；`04-testing` 和 `AGENTS.md` 写明材料库实现后再补。第 8 课用 `scripts/async_test.py` + `verify.py` 覆盖三条判据和 `/assignments` 页面可加载，不把缺 Playwright 当成实现失败。
5. **不做项清楚，且与实现一致：** 无作业 CRUD、无教师手工评分、无 SSE、无 `async-202`（待角色三）、无 SEC 报告（待角色三）。

结论：按这份规约开工是合理的；上述 1–3 是文档缺口，不是实现做不了。

## 4. material-library（后续，未实现）

**查了什么**：`openspec/changes/2026-10-14-upgrade-material-library/proposal.md` 的 Why / 不做 / 能力表。

**判据**：条款能否实现；是否和 async-grading 抢范围；是否超过 `08-review` 的变更规模。

**结果：有保留通过（先不实现）。**

- **边界清楚：** 不做模块三作业/练习/学情；不做外部队列做索引（进程内队列 + 库状态）。这与第 8 课 RabbitMQ 批改队列不冲突：一个管批改，一个管材料索引。
- **规模超 `08-review` 字面：** 4 个 capability、26 条需求、151 个场景、46 条任务。规范写「一次不超过一个 capability 或一组任务」「超过 1 个 capability 或 30 条需求先拆」。需求数未过 30，capability 数过了。开工前应由角色一书例外或拆 change；角色二不在本轮开始实现。
- **依赖顺序：** 依赖已归档 foundation；应等 async-grading 验收归档后再动，避免两个活动 change 同时改 `db.go` / 前端壳层。

## 5. 八类规范（重点 02 / 04 / 06）

按分工只深评后端、测试、AI；其余六类当作已读、本记录不逐条打表。

### 02 后端：有保留通过

- 分层可执行：新增 `httpapi` 不得写 SQL；第 8 课写入放 `grading/`、`outbox/`、`worker/`。已按此实现，`make check` 分层通过。
- 幂等声明覆盖 `POST /grade`；唯一约束清单与表结构一致。
- 同一保留：事务条目写「submission/grade_task/outbox 在一个事务」，实现落在 grade 请求，不落在 submit 请求。与第 3 节第 3 点相同，不另开缺陷。

### 04 测试：有保留通过

- 层次清楚：状态机/幂等用 Go 单测，三条判据用 `verify.py`。
- 与 `08-review` 冲突：合并前门禁写了 Playwright，本页又写「材料库实现时补」。第 8 课按本页和 `AGENTS.md`，不按 08 那句阻塞。
- 本页「正向用例超过 100ms 不通过」是材料库接口的项目值，不能套到批改执行时间；批改 P95 判据用的是 202 响应 < 500ms、本地批改 2 秒，两者不混用。

### 06 AI：通过

- 「能用规则完成的不用模型」：本地批改用关键词覆盖与篇幅，`CHAT_URL=local` 不打网关，符合调用边界。
- `/api/ask` 仍是先检索、无依据不生成；本 change 没有改问答契约。
- 10–20 条问答评测集属于材料库/问答，不是第 8 课必交；批改用固定本地规则 + 三条判据代替模型评测，可接受。
- SEC-03「没有技能/提示词写接口」按自查表应记红，由角色三执行，本评审不填造 403 绿。

## 6. 对后续工作的含义

| 事项 | 结论 |
| --- | --- |
| async-grading 实现 | 规约足够，保持现有实现；不因 Purpose 那句「提交返回 202」去改接口 |
| async-grading 归档 / 打标签 | 仍等角色三独立复现和 SEC |
| 改 OpenSpec Scenario | 不做。缺口记在本文件，交给角色一决定是否改 delta |
| 开始 material-library | 现在不要。先处理规模（拆 change 或书面例外），再按 `tasks.md` 开工 |

## 7. 复跑本评审

读本文件所引路径即可复核。本评审不产生新的运行命令；实现侧命令仍是：

```bash
make check
make check-security
make grade
python3 scripts/verify.py
```
