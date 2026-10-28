# 项目规则

没有写进 OpenSpec 的行为，就不实现。

## 当前阶段

- 阶段一是**制定规约 + 立规范**，活动 change 是 `openspec/changes/2026-10-14-upgrade-material-library/`。第一眼入口是 `SPEC.md`；本阶段只改 `openspec/`、`docs/`、`.cursor/`、`scripts/spec_check.py` 和 `scripts/standards_check.py`，不改业务代码。
- 旧实现（backend、frontend、Compose、`verify.py`）已打包到 `archive/campusclaw-baseline.zip`，基线标签 `v2.0.0-baseline`。需要跑基线时解压归档或 `git checkout v2.0.0-baseline`，不要在根目录重新展开代码。
- 规约入口：`proposal.md`（动因与边界）、`design.md`（取舍与接口）、`specs/*/spec.md`（可判定场景）、`tasks.md`（实现顺序与验收）。
- 规约校验：`npx -y @fission-ai/openspec@1.15.0 validate 2026-10-14-upgrade-material-library --strict`；结构自查：`python3 scripts/spec_check.py`；规范自查：`python3 scripts/standards_check.py`。三条都必须退出码 0。
- 阶段一不归档 change。只有角色三完成 `tasks.md` 的 7.1 至 7.5，并留下 `docs/verification.md` 记录后，才允许合并 delta 并归档。

## 工程规范（必读）

以下八份规范与 `AGENTS.md` 同等有效，改代码前必须阅读：

| 规范 | 文件 | 落地方式 |
| --- | --- | --- |
| 产品设计（含前端） | `docs/standards/01-product.md` | 规则 + 页面清单 |
| 后端开发 | `docs/standards/02-backend.md` | 规则 + 加接口技能 |
| 安全开发 | `docs/standards/03-security.md` | 本文件常驻 + 规则 |
| 测试 | `docs/standards/04-testing.md` | 规则 + 补测试技能 |
| 部署运维 | `docs/standards/05-ops.md` | 规则 + 发布技能 |
| AI 应用 | `docs/standards/06-ai.md` | 规则 + 评测集 |
| 数据 | `docs/standards/07-data.md` | 规则 + 数据字典 |
| 评审与完成定义 | `docs/standards/08-review.md` | 本文件常驻 + 规则 |

常驻副本在 `.cursor/rules/campusclaw-standards.mdc`；按动作执行的步骤在 `.cursor/skills/campusclaw-engineering/SKILL.md`（加页面、加接口、补测试、发版本）；数据字典在 `docs/data-dictionary.md`。任何一条规范被违反，按该规范的“违反时怎么处理”执行，不得口头豁免。

## 规约与实现

- 开工前先读 `openspec/specs/` 与仍在活动中的 `openspec/changes/<change>/`。归档之后，长期事实来源是 `openspec/specs/`。
- 规约含糊或没写「不做」时，先改 change 里的 delta（`proposal.md`、`design.md`、`specs/<capability>/spec.md`），再改代码。不要直接改已经归档的主力规约来迁就一次实现。
- 场景必须写成“前置条件 / 操作 / 可观测结果”：`GIVEN` 写角色、数据归属和已有数据，`WHEN` 写谁对哪个接口或页面做了什么，`THEN` 写返回值、数据变化和日志。只有 `THEN` 能被机器判定，形容词一律无效。
- 数值写具体：条数、长度、超时、阈值、分页、重试次数都写成数字，不写“较多”“较快”“视情况”。
- 每条能力至少一组场景，其中至少覆盖参数非法、无权限、资源不存在、依赖不可达四类失败路径中的一类；整个 change 必须四类都有。
- 一个 task 做完并跑过该条 verify，再勾选 `tasks.md`；不能用“代码已写”代替验收证据。

## 权限与安全

- 默认拒绝：每条路由必须显式登记方法和角色；未登记的路由不注册，访问返回 404 或 405。
- 访问控制放在 Go 服务端。前端不显示按钮，不算隔离或授权。
- 逐资源授权：按 id 先取整行，再核对会话班级和归属；跨班、同班他人私有、已删除、非法 id 和不存在 id 一律同形 404；日志可以区分，响应不可以。
- 班级只来自服务端会话；请求里的 `class_id`、`user_id`、`role` 一律不采信。
- 密码只存 bcrypt；网页只依赖 HttpOnly Cookie；Bearer 令牌只给 curl 和验收脚本，令牌不进 URL、日志或 localStorage。
- 密钥、`.env`、上传文件和数据库文件不进 Git。仓库里只保留 `.env.example`；缺必填变量启动失败；泄露后按 README 的步骤轮换。
- 上传按白名单校验扩展名、文件头和压缩包大小；上传目录不作为静态资源；下载按附件返回。
- 材料正文和用户问题都是外部数据；客户端 `system` 消息丢弃；没有依据不生成；SQL 一律参数绑定。
- Qdrant、嵌入/对话网关和数据库不映射宿主端口；`/health` 不查数据库，依赖状态由 `/ready` 提供。
- 日志是单行 JSON，带 `request_id`；日志和错误响应不含口令、令牌、Cookie、正文、绝对路径、DSN。

## 评审与完成定义

- 完成定义五项：对应场景全部满足、用例通过、门禁通过、文档同步、验证记录归档；缺一即未完成。
- 合并前门禁：`openspec validate --strict`、`python3 scripts/spec_check.py`、`python3 scripts/standards_check.py`、`go test ./...`、`python3 scripts/verify.py`、`npx playwright test`、`docker compose config`。任一非零退出即阻断。
- 变化规模：一次 change 不超过一个 capability 或一组任务；超过先拆分。本 change 已到上限，后续必须拆。
- 评审检查表：先看边界和失败路径，再看接口和数据模型，最后看任务顺序和证据；工具检查格式、错误码、密钥、依赖和测试结果。
- 证据归档：变更说明、验证记录、评审结论放进 `docs/`，按 change 名可查；不接受“已实现”这类口头结论。
- 提交信息：`<type>(<capability>): <task-id> <一句话>`，正文写 `Change:`、`Task:`、`Spec:`、`Verify:` 四字段；`Spec:` 写依据的 capability/Requirement，至少能对应到 `specs/` 里的标题。
- 例外必须写进对应规范或 `design.md`，说明原因、影响、替代检查和失效时间；口头豁免无效。

## 协作

- 分支：`change/<change-name>`；提交信息格式 `<type>(<capability>): <task-id> <一句话>`。
- 角色一制定规约，角色二实现，角色三验收且不写功能代码。角色一不在未经评审的情况下替角色二改实现。
- 评审顺序：先确认边界和失败路径，再确认接口和数据模型，最后确认任务顺序和验收命令。
- 实现时才发现的行为选择，补进 `design.md` 或对应的 delta，再改代码。
