# platform-foundation Specification

## Purpose

规定第一阶段共享底座：可升级数据库、页面壳层、统一反馈和已知安全修复。它不引入后续教学业务。

## ADDED Requirements

### Requirement: 版本化数据库迁移

服务启动 MUST 按数字顺序执行打包的迁移脚本，并在 `schema_migrations` 记录成功版本。已执行版本不得重复执行；已有数据库升级不得清空用户、材料、文件、切片或向量。迁移失败 MUST 使启动失败并保留可诊断错误。

#### Scenario: 空库和旧库都能升级

- **WHEN** 使用空 MySQL 启动，或使用现有迭代 1/2 数据库启动
- **THEN** 所有迁移按顺序完成，`schema_migrations` 含版本记录
- **AND** 旧用户、材料和索引仍存在，新增列和表可用

#### Scenario: 重启不重复迁移

- **WHEN** API 重启两次
- **THEN** 已记录迁移不重复执行
- **AND** 种子和已有业务数据不复制、不覆盖

### Requirement: 页面壳层与响应式导航

前端 MUST 将页面和通用组件从单体 `App.tsx` 拆出。桌面导航 MUST 提供首页、材料、问答以及本阶段已有页面的入口；后续课程单元、作业、练习、通知和班级管理只能显示为明确的禁用占位，不得要求对应业务接口或搜索结果。窄屏 MUST 使用底部标签栏。必须保留北大红主色、浅色/深色主题和键盘可操作性。材料、编辑、版本、设置、注册等路由 MUST 可直接打开或刷新。

#### Scenario: 桌面和窄屏主导航

- **WHEN** 在桌面和手机宽度登录
- **THEN** 导航分别显示左侧栏和底部标签栏
- **AND** 本阶段已有的首页、材料、问答入口可用，后续课程单元、作业、练习、通知和班级管理入口明确显示为禁用占位
- **AND** 用户可以键盘到达材料、问答和设置页面

#### Scenario: 直接刷新深层路由

- **WHEN** 登录后直接打开 `/materials/{id}/versions` 或 `/settings`
- **THEN** 页面按服务端会话恢复并显示对应内容
- **AND** 未登录时回到登录页且不泄露材料标题

### Requirement: 全局搜索和统一反馈

Ctrl/⌘+K MUST 打开全局搜索，搜索本阶段已实现的材料、材料操作和常用操作；后续单元、作业、练习、通知数据未实现时不得出现在搜索结果中。后续教学入口可以作为禁用占位显示，但不得声称可搜索或打开。搜索支持上下键选择和 Enter 执行。页面加载 MUST 显示 skeleton；空列表 MUST 给出下一步建议；网络 503 或可重试错误 MUST 显示重试按钮。401 MUST 弹出重新登录并保留当前页面和未提交草稿。

#### Scenario: 键盘搜索

- **WHEN** 用户按 Ctrl/⌘+K 输入材料标题片段并按上下键、Enter
- **THEN** 搜索结果可选中并打开材料详情
- **AND** 结果不包含其他班级材料或教师专属操作

#### Scenario: 错误可重试且草稿不丢

- **WHEN** 服务器暂时返回 503，用户正在编辑材料或填写问题
- **THEN** 页面显示明确错误和重试按钮
- **AND** 重试或重新登录后草稿仍在，提交成功后才清理

### Requirement: 可信限流和嵌入配置

登录失败计数 MUST 存 MySQL，API 重启不得清除锁定。Go MUST 只信来自可信 web 代理的真实客户端 IP，不得使用可伪造的第一段 `X-Forwarded-For` 绕过限流。嵌入维度 MUST 来自 `EMBEDDING_DIM`，Qdrant 集合名 MUST 包含维度；维度不匹配不得静默写入错误集合。

#### Scenario: 重启不能绕过登录锁定

- **WHEN** 用户达到失败阈值后重启 API，再提交正确口令
- **THEN** 仍返回与错误口令同形的 401，直到锁定期结束

#### Scenario: 伪造代理头不能绕过

- **WHEN** 客户端变更 `X-Forwarded-For` 头重复提交失败口令
- **THEN** 失败计数仍按可信来源累计，正确口令不能因换头立即绕过锁定

#### Scenario: 维度跟随配置

- **WHEN** 使用不同 `EMBEDDING_DIM` 启动本地嵌入
- **THEN** Qdrant 集合按该维度创建或选择
- **AND** 检索向量长度与集合维度一致

### Requirement: 部署与客户端安全底线

Compose MUST 只映射 web 端口，Qdrant、MySQL 和模型网关不得映射宿主。密钥只能在服务端环境变量；前端源码和响应不得包含密钥、向量分量或伪造 `class_id`/`system` 消息。Markdown MUST 不执行原始 HTML，响应 MUST 设置 CSP。

#### Scenario: 宿主端口与源码检查

- **WHEN** 查看 Compose 配置和前端构建源码
- **THEN** 只有 web 有 `ports`
- **AND** 不存在前端 localStorage 令牌、`class_id: 999` 或伪造 system 消息
- **AND** `verify.py` 中的隔离测试仍可使用这些测试输入而不进入正式页面
