---
name: campusclaw-engineering
description: 按 CampusClaw 2.0 工程规范执行四类固定动作：加一个页面、加一个后端接口、补一组测试、发一次版本。仅在对应动作被调用时使用。
---

# CampusClaw 工程技能

规则约束在 `AGENTS.md`、`.cursor/rules/campusclaw-standards.mdc` 和 `docs/standards/`；本技能只规定执行步骤。每次使用前先读对应规范，不凭记忆。

## 1. 按规范加一个页面

**输入**：页面名、路由、服务角色（教师/学生/两者）、数据来源接口。

**步骤**：

1. 在 `docs/standards/01-product.md` 的页面清单里登记路由、角色和入口；同一功能不新增第二个入口。
2. 在 `frontend/src/pages/` 建页面，在 `frontend/src/components/` 复用按钮、输入、卡片、提示条、骨架屏、空状态。
3. 四态齐全：加载 skeleton、正常、空（含下一步）、错误（401/403/404/409/413/503 的可读文案）。
4. 颜色、间距、字号只用 `styles.css` 变量；桌面 ≥768px 左栏，窄屏 <768px 底栏。
5. 键盘可到达、焦点可见、表单有 label；窄屏 390×844 和桌面 1440×900 各走一次。
6. 更新 README 页面清单或 change 的 `proposal.md`。

**产出**：页面文件、路由、四态截图或 Playwright 断言、规范更新。

## 2. 按规范加一个后端接口

**输入**：资源名、方法、角色、请求字段、成功/失败状态码、是否幂等。

**步骤**：

1. 在 `docs/standards/02-backend.md` 的接口命名表和错误码表里登记；错误码只能从清单取。
2. 路由放 `backend/internal/httpapi/`，参数解析和权限调用在接口层；业务规则和事务放 `library/`、`indexer/` 或 `retrieval/`；SQL 放 `db/` 或对应数据访问层。
3. 按 id 先取整行，再校验班级和归属；跨班、他人私有、已删除、非法 id 和不存在 id 同形 404。
4. 写接口声明幂等；唯一约束放数据库；分页参数 `page/page_size` 白名单、`id` 兜底。
5. 在对应 capability 的 `spec.md` 增加 Requirement 和 Scenario（GIVEN/WHEN/THEN），再写代码。
6. 补 Go 单元测试和 `verify.py` 场景；改坏被测逻辑确认用例会变红。

**产出**：handler、业务方法、迁移（如需）、规约 delta、测试、`verify.py` 结果。

## 3. 按规范补一组测试

**输入**：capability、Requirement、Scenario 列表。

**步骤**：

1. 用例清单逐条对应 Scenario；正常/失败/边界分组。
2. 单元测覆盖业务规则；`verify.py` 覆盖每条能力的接口路径；Playwright 只覆盖主路径。
3. 每条用例自建数据、自清理；随机顺序运行结果一致；外部依赖用替身或本地模式。
4. 断言不只查状态码，还要查数据变化；对被测逻辑做一次等价破坏，确认用例变红。
5. 更新 `docs/verification.md`：命令、退出码、结果、负责人。

**产出**：测试文件、`make check` / `make grade` / `verify.py` 输出、验证记录。

## 4. 按规范发一次版本

**输入**：版本号或提交号、变更清单、回滚目标。

**步骤**：

1. 跑门禁：`make check`、`make grade`、`python3 scripts/verify.py`；材料库实现后再加 Playwright。
2. 迁移先加后删；旧版本仍可读；回滚不反向执行迁移。
3. 构建镜像并用提交号/版本号打标签；同一镜像换 `.env` 部署。
4. 启动后先看 `/ready`，通过后才接流量；记录版本、命令、结果和负责人。
5. 演练一次回滚到上一标签，记录耗时；失败时只走回滚路径。

**产出**：镜像标签、验证记录、回滚记录、`docs/verification.md` 更新。

## 失败时

- 规范与代码冲突：改代码；确需保留旧写法，把例外写进对应规范和 `design.md`。
- 门禁失败：不合并、不打标签；修完重跑全部门禁。
- 规约没写的行为：先改 delta，再改代码。
