# 项目规则

没有写进 OpenSpec 的行为，就不实现。

## 当前阶段

- 阶段一是**制定规约**，活动 change 是 `openspec/changes/upgrade-material-library/`。本阶段只改 `openspec/`、`docs/` 和 `scripts/spec_check.py`，不改 `backend/`、`frontend/` 的业务代码。
- 规约入口：`proposal.md`（动因与边界）、`design.md`（取舍与接口）、`specs/*/spec.md`（可判定场景）、`tasks.md`（实现顺序与验收）。
- 规约校验：`npx -y @fission-ai/openspec@1.15.0 validate upgrade-material-library --strict`；结构自查：`python3 scripts/spec_check.py`。两条都必须退出码 0。
- 阶段一不归档 change。只有角色三完成 `tasks.md` 的 7.1 至 7.5，并留下 `docs/verification.md` 记录后，才允许合并 delta 并归档。

## 规约与实现

- 开工前先读 `openspec/specs/` 与仍在活动中的 `openspec/changes/<change>/`。归档之后，长期事实来源是 `openspec/specs/`。
- 规约含糊或没写「不做」时，先改 change 里的 delta（`proposal.md`、`design.md`、`specs/<capability>/spec.md`），再改代码。不要直接改已经归档的主力规约来迁就一次实现。
- 场景必须写成“前置条件 / 操作 / 可观测结果”：`GIVEN` 写角色、数据归属和已有数据，`WHEN` 写谁对哪个接口或页面做了什么，`THEN` 写返回值、数据变化和日志。只有 `THEN` 能被机器判定，形容词一律无效。
- 数值写具体：条数、长度、超时、阈值、分页、重试次数都写成数字，不写“较多”“较快”“视情况”。
- 每条能力至少一组场景，其中至少覆盖参数非法、无权限、资源不存在、依赖不可达四类失败路径中的一类；整个 change 必须四类都有。
- 一个 task 做完并跑过该条 verify，再勾选 `tasks.md`；不能用“代码已写”代替验收证据。

## 权限与安全

- 访问控制放在 Go 服务端。前端不显示按钮，不算隔离或授权。
- 跨班、同班他人私有、已删除和不存在 id 一律同形 404；日志可以区分，响应不可以。
- 班级只来自服务端会话；请求里的 `class_id`、`user_id`、`role` 一律不采信。
- 密钥、`.env`、上传文件和数据库文件不进 Git。仓库里只保留 `.env.example`。
- 网页只依赖 HttpOnly Cookie；Bearer 令牌只给 curl 和验收脚本。
- Qdrant、嵌入/对话网关和数据库不映射宿主端口；`/health` 不查数据库。

## 协作

- 分支：`change/<change-name>`；提交信息格式 `<type>(<capability>): <task-id> <一句话>`。
- 角色一制定规约，角色二实现，角色三验收且不写功能代码。角色一不在未经评审的情况下替角色二改实现。
- 评审顺序：先确认边界和失败路径，再确认接口和数据模型，最后确认任务顺序和验收命令。
- 实现时才发现的行为选择，补进 `design.md` 或对应的 delta，再改代码。
