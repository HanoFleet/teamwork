# 08 评审与完成定义规范

| 项目 | 内容 |
| --- | --- |
| 规范编号 | `08-review` |
| 掌管范围 | 完成定义、门禁、变更规模、评审检查表、责任与时限、例外、证据归档 |
| 落地方式 | 常驻约束写入 `AGENTS.md` 和 `.cursor/rules/campusclaw-standards.mdc`；归档流程写成技能 |
| 违反时 | 不评审、不合并、不打标签；例外必须书面化 |

## 这一页管什么

管“什么算完成、合并前必须跑什么、一次变更能有多大、谁在什么时间内评审、证据放在哪”。技术判定归各规范页，本页只管流程与判定。

## 项目事实

- 当前 change：`2026-10-14-upgrade-material-library`，阶段一只交付规约和规范，不实现业务代码。
- 规约门禁：`npx -y @fission-ai/openspec@1.15.0 validate 2026-10-14-upgrade-material-library --strict`。
- 结构门禁：`python3 scripts/spec_check.py`、`python3 scripts/standards_check.py`。
- 实现门禁：`go test ./...`、`python3 scripts/verify.py`、`npx playwright test`、`docker compose config`。
- 证据目录：`docs/verification.md`、`docs/阶段一-交付说明.md`、`docs/项目启动-四步核对.md`。
- 角色：李斯坦制定规约与规范；韩雅慧实现；禹霖验收且不写功能代码。

## 规范条目

| 条目 | 项目事实 | 为什么 | 怎么检查 |
| --- | --- | --- | --- |
| 完成定义（DoD） | 一次变更完成必须同时满足：① 对应 Scenario 全部满足；② 用例通过；③ 门禁通过；④ 文档同步；⑤ 验证记录归档。五项写在本文件，逐条勾选 | 只凭“代码写完了”会把未验证的变更当成完成 | 打开 `tasks.md` 和 `docs/verification.md`，五项缺一即未完成 |
| 门禁命令 | 合并前必跑：规约校验、两个结构自查、`go test ./...`、`python3 scripts/verify.py`、`npx playwright test`、`docker compose config`；任何一项非零退出即阻断 | 放水一次，后面所有“通过”都不可信 | CI 或本地记录命令和退出码；不得跳过钩子或改低阈值 |
| 变更规模 | 一次变更不超过一个 capability 或一组任务；本 change 是项目启动的第一个 change，包含底座和材料库 4 个 capability，作为已登记例外；后续新功能必须一个 capability 一个 change | 超大变更无法评审，也无法定位故障 | 新 change 超过 1 个 capability 或 30 条需求时，先拆分 |
| 评审检查表 | 人工看：边界、失败路径、权限、数据变化、文案、证据；工具看：格式、错误码、密钥、依赖、测试结果 | 只靠工具会漏业务判定，只靠人会漏格式和密钥 | 每次评审填表，逐项写“通过/不通过/不适用” |
| 责任人 | 作者负责当天修复失败用例和评审意见；评审人 24 小时内给出结论；验收人只认可复现证据 | 没有时限的评审会无限拖延 | 记录提交时间、评审时间、修复时间 |
| 例外 | 例外写入本规范或对应 change 的 `design.md`，写明原因、影响、替代检查和失效时间；口头豁免无效 | 例外留在会话里，下次没人知道 | 搜 `例外` 关键字；无书面记录即违规 |
| 证据归档 | 每次变更把变更说明、验证记录、评审结论放进 `docs/`，按 change 名可检索；截图/trace 放 `docs/` 或链接 | 没有证据无法复盘，也无法证明个人贡献 | 打开 `docs/` 能按 change 名找到三类材料 |
| 提交信息 | 格式 `<type>(<capability>): <task-id> <一句话>`；正文四字段：`Change:`、`Task:`、`Spec:`、`Verify:`；`Spec:` 写依据的 capability/Requirement | 提交历史是个人贡献和回溯的依据 | `git log` 抽查；缺字段或 `Spec:` 对应不到规约即不合规 |
| 标签 | 骨架基线打 `v2.0.0-baseline`；每次发布打版本标签；标签指向通过门禁的提交 | 没有标签无法回滚到确定版本 | `git tag` 对照发布记录 |
| 复盘 | 每次验收失败记录：现象、根因、修复、预防；同类问题第二次出现时更新规范 | 不复盘会重复踩同一个坑 | 看 `docs/verification.md` 是否有失败记录和预防措施 |

## 提交信息示例

```text
feat(material-library): 2.4 上传写入 v1 并异步入队

Change: 2026-10-14-upgrade-material-library
Task: 2.4
Spec: material-library/批量上传与索引进度
Verify: go test ./internal/httpapi/... && python3 scripts/verify.py
```

## 本课最小集合

1. DoD 五项写在根目录说明或本文件。
2. 门禁命令和退出码写进 README。
3. 一次变更走完“提变更 → 实现 → 自检 → 评审 → 归档 → 打标签”。
4. 例外书面化并实际走一次。
5. 证据归档到 `docs/`，按 change 名可查。

## 违反时怎么处理

- 门禁不通过仍合并：回退合并，补跑门禁并记录。
- 变更超出规模上限：拆成多个 change，保留原 change 作为父任务。
- 评审没有检查表或结论：视为未评审，重新评审。
- 例外只在聊天里说：补写到规范或 `design.md`，否则不生效。
- 证据缺失：验收不通过，不允许归档或打标签。
