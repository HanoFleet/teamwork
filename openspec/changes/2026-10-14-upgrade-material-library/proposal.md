# 变更提案：2026-10-14-upgrade-material-library

| 项目 | 内容 |
| --- | --- |
| 变更名 | `2026-10-14-upgrade-material-library` |
| 阶段 | 阶段一：制定规约（只写规约，不实现） |
| 负责人 | 李斯坦（角色一：制定规约） |
| 评审 | 韩雅慧（角色二：开发系统）、禹霖（角色三：项目验收） |
| 基线 | 迭代 1/2：登录、班级隔离、txt/md 上传、三种检索、可追溯问答 |
| 规约入口 | `openspec/changes/2026-10-14-upgrade-material-library/specs/` |
| 归档状态 | 活动（未实现、未验收、未归档） |

## Why

当前 CampusClaw 已经能登录、按班级隔离、上传 txt/md、做关键字/向量/混合检索，并在没有依据时不生成回答。但材料库还停留在“能检索的材料列表”，教师日常要用的几件事都做不了：

- `backend/internal/materials/` 只允许 `.txt` 和 `.md`，教师手里的 PDF、Word、PPT 无法入库。
- `backend/internal/httpapi/materials.go` 在上传请求里同步调用 `retrieval.IndexMaterial`，文件一大，请求就长时间不返回；页面上看不到“什么时候能搜到”。
- `backend/internal/retrieval/index.go` 重建索引时先删旧切片再写新切片，重建期间这份材料检索不到。
- `knowledge_chunks.start_offset/end_offset` 相对预处理后的文本，引用无法稳定回到原文；PDF/PPT 也没有页码或幻灯片号。
- 材料上传后不能编辑、替换或恢复历史版本；改一个错字只能删除重传，旧引用随之失效。
- 删除是硬删除，没有回收站；材料没有标签、排序和分页；学生没有阅读进度和收藏。
- `backend/internal/db/db.go` 用 `CREATE TABLE IF NOT EXISTS` 建表，无法演进；`backend/internal/httpapi/server.go` 信任 `X-Forwarded-For` 第一段；`backend/internal/embed/embed.go` 把向量维度写死为 256；`frontend/src/api.ts` 把令牌存进 `localStorage`；`frontend/src/App.tsx` 是 629 行单体。

这些事实不需要读代码也能核对：它们分别对应现有接口的行为、README 的“范围”段和归档规约的条款。本 change 只修材料库和它依赖的底座。

## What Changes

1. **建立可演进的数据库迁移**：新增 `schema_migrations`，把现有建表固化为 `0001_baseline.sql`，后续变更按编号追加；已有数据库不清空即可升级。
2. **支持常见教学文件**：新增 `.pdf`、`.docx`、`.pptx` 的扩展名白名单、文件头/压缩包校验、文字抽取、页码/幻灯片边界；扫描件、加密、损坏文件当场拒绝且无残留。
3. **把索引改成后台任务**：上传请求只做校验、抽取和事务写入，提交后把材料加入队列并立即返回 201；材料暴露 `pending/indexing/ready/failed` 和失败原因，前端每 2 秒轮询，失败可重试。
4. **重建索引改为先建后换**：`knowledge_chunks` 增加 `generation`；新 generation 全部 ready 后才切换，重建期间旧索引照常可用，失败只清理新 generation。
5. **把引用固定到原文**：切片起止位置改为当前版本原文的 Unicode 码点下标，PDF/PPT 记录页码或幻灯片号；引用保存材料 id、版本号、原文区间和当时摘录，旧版本引用显示“原文已更新”。
6. **增加材料版本历史**：编辑、替换、恢复都追加新版本，旧版本不可改写；保存带 `base_version`，冲突返回 409 和最新内容；支持列出、读取、比较和恢复任意版本。
7. **增加材料库日常操作**：批量上传（最多 20 个文件）、删除/撤销/回收站/彻底删除、标签、重命名、排序、分页、阅读进度、收藏和最近阅读。
8. **拆分前端并统一反馈**：把 `App.tsx` 拆为 `pages/` 与 `components/`，路由进入 URL，提供桌面左栏/窄屏底栏、全局搜索、骨架屏、空状态、503 重试和草稿保留；移除 localStorage 令牌、伪造 `class_id: 999` 和客户端 `system` 消息。
9. **修复已知底座问题**：登录失败计数落 MySQL 并只信可信代理 IP；`EMBEDDING_DIM` 配置化且 Qdrant 集合名带维度；CSP、附件下载头和上传归档资源限制；结构化日志与请求 ID、`/health` 存活与 `/ready` 就绪分离、优雅停机。

以上每一条都能单独演示或被测试；第 1、2、3、9 条是第 4 至 8 条的前置。

## Out of Scope（本次不做）

- **不做会话历史、追问、SSE 流式回答、班级助手和新的 AI 技能**。它们属于模块二，本 change 只保留现有 `/api/ask` 的非流式行为。
- **不做课程单元、作业、练习、错题、公告、通知和学情统计**。它们属于模块三，本 change 只在导航里显示禁用占位。
- **不做邀请码注册、CSV 批量导入和口令重置**。账号仍然只有预置的三个，注册属于模块三。
- **不做超级管理员，不做 AI 批改作业，不用 JWT 替代既有会话**。超级管理员会让跨班 404 失去证明力；批改和鉴权不在本轮范围。
- **不引入外部队列、Redis、对象存储或新的全文搜索服务**。单实例 Compose 下，进程内队列加数据库状态足够；新增依赖会扩大部署和验收面。
- **不引入 UI 框架或富文本编辑器**。前端只新增 `diff` 一个运行时依赖，编辑用文本框加实时预览，差异在前端计算。
- **不直接修改已归档的 `openspec/specs/`**。所有行为变化写成本 change 的 delta，验收通过后才合并并归档。
- **不实现学习路径、作业、练习、通知、班级管理页面**。导航项必须显示为禁用，直接输入 URL 不注册路由。

## Alternatives Considered（放弃的候选方案）

| 候选方案 | 为什么放弃 |
| --- | --- |
| 继续用 `CREATE TABLE IF NOT EXISTS` 加手工 `ALTER` 升级 | 无法在干净环境复现，也无法判断某个库升到了哪一版；已有数据升级只能靠人记。编号迁移能记录版本和校验和，失败可定位。代价是首次要把现有 DDL 固化成 `0001`，由开发者承担。 |
| 把文件抽取也放到后台队列 | 扫描件、加密、损坏文件会先返回成功，教师很久以后才知道失败；“上传要么全有要么全无”也很难保证。抽取放在请求内，索引放后台，代价是上传请求仍受 PDF 抽取的 10 秒上限约束。 |
| 重建索引继续先删后建 | 重建期间材料检索不到，违反“旧索引在新索引完成前可用”。先建后换需要多一列 `generation` 和一次切换事务，代价由开发者承担，收益是重建期间检索不中断。 |
| 版本历史用覆盖式或只保留当前版本 | 旧引用无法解释，恢复和审计都不可能。追加式版本会让存储随编辑增长，彻底删除前不自动清理，代价是磁盘占用，收益是可追溯。 |
| 引入 Redis 或外部消息队列做索引队列 | 单实例 Compose 下多一个依赖、多一组健康检查和故障模式；进程内队列加 `materials.index_status` 已能通过重启补排满足验收。代价是只支持单实例，与现有 README 的单实例约束一致。 |
| 继续用 localStorage 保存 Bearer 令牌 | 任意 XSS 都能读走令牌；现有服务端已经签发 HttpOnly Cookie。网页改用 Cookie，Bearer 只留给 curl 和验收脚本，代价是前端请求必须带 `credentials: "include"`。 |
| 引入 UI 框架或现成 Markdown 编辑器 | 会显著增加包体、主题适配和验收面；本阶段只需要文本框、预览和差异视图。代价是交互不如成熟编辑器丰富，收益是依赖少、可控。 |

## Capabilities

### New Capabilities

- `platform-foundation`：版本化迁移、页面壳层、全局搜索与统一反馈、索引与嵌入配置。
- `material-library`：批量上传与进度、回收站、标签与分页、编辑与版本历史、文件替换、原文定位、阅读进度与收藏、统一错误形状。

### Modified Capabilities

- `auth-upload`：登录限流持久化与可信 IP、角色写权限、班级隔离范围、多格式上传与异步索引、材料读取、Compose 与 Web 安全。
- `knowledge-retrieval`：异步索引与状态、当前 generation 检索、原文码点与版本化引用、重建先建后换。

## Capability–Scenario Map（能力与场景对应）

| Capability | 类型 | Requirement 数 | Scenario 数 | 主要失败路径 | 验收证据 |
| --- | --- | ---: | ---: | --- | --- |
| `platform-foundation` | 新增 | 7 | 27 | 迁移失败启动失败、缺少 `EMBEDDING_DIM`、401/503、`/ready` 失败 | Go 单测、`verify.py`、Playwright、`docker compose config` |
| `material-library` | 新增 | 9 | 42 | 400/403/404/409/413、用户伪造字段 | `verify.py`、Go 单测、Playwright、数据库查询 |
| `auth-upload` | 修改 | 7 | 44 | 400/401/403/404/413/503、重启后锁定 | `verify.py`、curl、数据库查询 |
| `knowledge-retrieval` | 修改 | 5 | 30 | 400/403/404/503、重建失败保留旧索引 | `verify.py`、Go 单测、Qdrant 查询 |
| **合计** |  | **28** | **143** |  |  |

每个 Requirement 至少有一个 Scenario；没有 Scenario 的 Requirement 不允许出现。四个能力的具体条款见 `specs/<capability>/spec.md`，任务与场景的对应关系见 `tasks.md` 每条的 `verify`。

## Failure Path Coverage（失败路径覆盖）

| 类别 | 本 change 的代表场景 | 期望可观测结果 |
| --- | --- | --- |
| 输入非法 | 非法扩展名、伪造 PDF 头、加密/损坏 Office、非法分页、非法标签、非文本格式编辑、空查询 | 400/413；无文件、无数据库行、无版本 |
| 无权限 | 学生上传/批量上传/编辑/删除/重建、客户端声明 `role=teacher` | 403；相关表和目录计数不变 |
| 资源不存在或不可见 | 跨班 id、已删除材料、非法 id、永不存在的 id；同班他人的进度/收藏 | 同形 404：状态、头、body 逐字节相同；他人私有数据不可通过任何 id 读取 |
| 外部依赖不可达 | Qdrant 停止、数据库停止、嵌入失败、迁移失败 | `keyword` 仍可用；`vector`/`hybrid` 503；`/health` 不查库、`/ready` 返回依赖状态；材料 `failed` 可重试；迁移失败启动退出 |
| 并发冲突 | 两个窗口基于同一 `base_version` 保存 | 后者 409，含 `current_version` 和最新正文，旧内容不被覆盖 |
| 边界值 | 20/21 个文件、`page_size` 100/101、800/80 切分、0.35 阈值、`k=60`、2 秒轮询/节流 | 边界内成功，越界返回 400/413 或按规则过滤 |

## Compatibility and Existing Contracts

本 change 保留以下既有底线，任何新接口都不得破坏：

1. 班级只来自服务端会话，请求里的 `class_id` 一律忽略。
2. 跨班、已删除和不存在 id 都返回同形 404；响应不泄露资源是否存在；同班他人的进度和收藏不可通过任何 id 或查询参数读取。
3. 没有依据就不生成；`/api/ask` 的非流式协议和 `citations` 顺序保持不变。
4. Qdrant、嵌入网关、对话网关和数据库不映射宿主端口；密钥只在服务端环境变量。
5. 只用 Docker Compose 启动，只有 web 映射端口；`/health` 不查数据库，依赖状态由 `/ready` 提供。
6. 上传的文件、`materials`、`material_versions`、`knowledge_entries` 要么全部写入，要么全部不写。
7. 不做超级管理员，不让 AI 给作业打分。
8. 网页只依赖 HttpOnly Cookie；Bearer 令牌只为 curl 和验收脚本保留。

与后续 change 的关系：模块二（会话、追问、SSE、助手、技能）和模块三（邀请码、单元、作业、练习、通知、学情）不在本 change 内。本 change 只提供它们依赖的材料、索引、版本和页面壳层；后续 change 必须另行写 delta，不得直接把本 change 的规约当作已实现功能。

## Success Criteria（完成现象）

- `npx -y @fission-ai/openspec@1.15.0 validate 2026-10-14-upgrade-material-library --strict` 退出码为 0，无 error、无 warning。
- `python3 scripts/spec_check.py` 和 `python3 scripts/standards_check.py` 退出码为 0：前者检查四份文件、场景三段式、失败路径和任务清单；后者检查八类工程规范、规则入口和检查列。
- 四份文件齐备：`proposal.md`、`design.md`、`specs/*/spec.md`、`tasks.md`。
- 每条 Requirement 至少一组 Scenario；没有无归属的 Scenario；能力与场景对应表可逐行核对。
- 数值判据具体：20 个文件、2 秒、800/80 字、0.35、`k=60`、100 条分页、409/413/503 等均可直接转成测试断言。
- 另起一次不带历史上下文的会话，只给仓库路径和变更名，执行者能按 `tasks.md` 的编号顺序实现，且问不出规约未回答的行为问题。
- 本 change 未留下“待定”“视情况”“较高/较低”这类不可判定的表述；实现中发现冲突，必须先在 delta 里改，再改代码。

## Open Questions

没有留给实现阶段的业务选择。实现若发现规约冲突或缺口，先修改本 change 的 delta，再修改代码；不得用实现细节反向解释规约。
