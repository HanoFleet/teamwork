## Context

当前后端沿用 `db.Migrate` 中的一组 `CREATE TABLE IF NOT EXISTS`，上传同步调用 `retrieval.IndexMaterial`，切片偏移相对预处理文本，重建会先删除旧索引。前端的 629 行 `App.tsx` 同时承担路由、材料列表、上传、检索和主题状态。第一阶段在同一条浏览器 → Nginx → Go → MySQL/Qdrant 链路上扩展材料库，不重做认证或问答协议。

## Goals / Non-Goals

**Goals:**

- 常见教学文件可以安全抽取并快速返回上传结果，索引状态可观察、可重试。
- 材料可重命名、打标签、删除/恢复、编辑/替换，并保留可比较、可恢复的追加式版本历史。
- 检索和引用能定位到当前或历史版本的原文区间；重建期间旧索引继续可用。
- 学生拥有私有阅读进度和收藏；教师拥有回收站和材料管理能力。
- 数据库、前端壳层和安全修复可被现有 verify、Go 测试和 Playwright 复现。

**Non-Goals:**

见 `proposal.md`。后续 change 负责会话问答和班级教学。

## Decisions

### Decision 1: 编号迁移而不是启动时拼接 DDL

新增 `schema_migrations(version, applied_at)`。迁移文件按数字顺序执行，成功后记录版本；已记录版本跳过。第一版脚本等价当前所有表，之后只追加迁移。迁移失败返回启动错误，不清空已有数据。MySQL DDL 非事务性，因此每个脚本保持小而可重复，并在 verify 中检查半途重启后的补齐结果。

### Decision 2: 抽取同步，索引异步

上传请求只负责大小/扩展名/文件头校验、抽取文字和页码表、写文件及 `materials`/`knowledge_entries` 事务。PDF 通过带超时和输出上限的 `pdftotext`，DOCX/PPTX 通过 `archive/zip` 与 XML 读取；压缩包限制文件数、单文件大小和总展开大小。扫描件、加密、损坏或无可复制文字立即返回 400，不能产生数据库行或文件。事务提交后将 material id 放入进程内队列，立即返回 201；索引状态由 `pending`、`indexing`、`ready`、`failed` 表示，失败原因可见且可重试。

### Decision 3: 重建采用 generation 先建后换

`knowledge_chunks` 增加 `generation`，材料保存当前 generation。新 generation 的切片和向量全部成功后，在事务中将其标为可见并删除旧切片，随后删除旧向量；失败时只清理新 generation。检索只读当前 generation，因此重建期间旧索引继续可用。启动时重新排队 `pending`/`indexing` 材料。

### Decision 4: 原文坐标和版本化出处

预处理可以去 URL、折叠空白，但必须保存预处理字符到原文码点的映射。切片 `start/end` 一律是当前版本原文码点下标；PDF/PPT 保存页码或幻灯片号。消息或检索引用保存 `material_id`、`version`、原文区间和当时摘录，不把易变的 chunk id 当作长期引用。材料版本变化后，旧引用显示“原文已更新”并保留旧摘录。

### Decision 5: 追加式版本和乐观并发

每次编辑、替换或恢复都在 `material_versions` 追加一行，不改写历史。保存请求必须携带开始编辑时的 `base_version`；不是最新版本时返回 409 和最新内容，前端显示差异。恢复旧版本本身生成新版本并触发后台索引。只有教师可修改本班材料；学生和其他班按既有 403/404 规则处理。

### Decision 6: 软删除与私有进度

删除立即设置 `deleted_at`，列表、检索、问答和学生详情都排除已删除材料。教师可在回收站撤销或彻底删除；撤销生成新的可见状态，但不重写版本历史。阅读进度和收藏按用户与材料唯一约束保存，按 id 访问时核对会话班级和用户归属；跨班、同班其他学生、不存在 id 的响应完全相同。

### Decision 7: 前端壳层与安全边界

拆分 `App.tsx` 为 `pages/` 和 `components/`，路由状态进入 URL。壳层提供首页、材料、问答导航；学习路径、作业、练习、通知和班级管理在本阶段只能显示为禁用占位，不提供业务接口或搜索数据。窄屏使用底部标签栏。Ctrl/⌘+K 只搜索材料、材料操作和已有常用操作。统一 skeleton、空状态、503 重试和草稿恢复。网页端只依赖 HttpOnly Cookie，Bearer 只为 curl/验收脚本保留；删除 `localStorage` 令牌、伪造 `class_id:999` 和客户端 `system` 消息。

### Decision 8: 配置化嵌入维度和可信 IP

`EMBEDDING_DIM` 是服务端配置，Qdrant 集合名包含维度，避免模型更换后写入失败。Nginx 传 `X-Real-IP`；Go 仅在请求来自可信 web 代理时采用该值，否则使用连接地址。登录失败计数进入 MySQL，重启不能绕过锁定。响应增加 CSP，上传文件只按附件下载。

## Interfaces

| 方法与路径 | 权限 | 成功 | 主要失败 |
| --- | --- | --- | --- |
| `POST /api/materials` | 教师、本班 | 201，含 material id、版本和 index status | 400 文件/抽取错误；413 超限；403 学生；事务失败无残留 |
| `GET /api/materials` | 已登录 | 200，分页、标签、排序、索引状态 | 401/503 |
| `PATCH /api/materials/{id}` | 本班教师 | 200，重命名/标签更新 | 403/404 |
| `DELETE /api/materials/{id}` | 本班教师 | 204，进入回收站 | 403/404 |
| `POST /api/materials/{id}/restore` | 本班教师 | 200，恢复材料 | 403/404 |
| `GET /api/trash` | 本班教师 | 200，回收站列表 | 403 |
| `PUT /api/materials/{id}/content` | 本班教师 | 200，新版本并排队索引 | 409 冲突；403/404 |
| `POST /api/materials/{id}/file` | 本班教师 | 200，新版本并排队索引 | 400/403/404 |
| `GET /api/materials/{id}/versions` | 本班教师 | 200，版本元数据 | 403/404 |
| `POST /api/materials/{id}/versions/{v}/restore` | 本班教师 | 200，新恢复版本 | 403/404 |
| `PUT /api/materials/{id}/progress` | 当前学生 | 204 | 404（跨班/他人/不存在同形） |
| `PUT/DELETE /api/materials/{id}/favorite` | 当前学生 | 204 | 404（同上） |
| `POST /api/materials/{id}/reindex` | 本班教师 | 202，状态 pending | 403/404 |

## Data Model

- `schema_migrations(version, applied_at)`。
- `materials` 增加 `file_type`、`page_count`、`current_version`、`index_status`、`index_error`、`deleted_at`、`current_generation`。
- `material_versions(id, material_id, version, kind, body_or_storage, editor_id, change_note, created_at)`，`(material_id, version)` 唯一。
- `knowledge_entries` 指向当前版本的原文或抽取文本；页码表和原文映射随版本保存。
- `knowledge_chunks` 增加 `generation`、原文 `start_offset/end_offset`、可选 `start_page/end_page`，查询只读当前 generation 的 ready 切片。
- `tags(id, class_id, name)`、`material_tags(material_id, tag_id)`。
- `material_reads(user_id, material_id, version, position, completed, updated_at)` 与 `favorites(user_id, material_id, created_at)`，均以用户/材料建立唯一约束，并通过 `materials.class_id` 校验班级归属。
- `login_failures` 记录用户名、可信 IP、失败次数、锁定截止时间。

所有新增业务表通过材料或其他归属表校验班级；直接承载跨班数据的表带 `class_id`，私有的 `material_reads` 与 `favorites` 不重复存 `class_id`，而是通过 `material_id -> materials.class_id` 在服务端校验，并按 `user_id` 过滤。除全局技能表外，班级归属列或关联表均建立索引。

## Configuration and Deployment

新增 `EMBEDDING_DIM`，以及已有 Qdrant/网关配置的校验；`.env.example` 只放空值或占位。API 镜像安装 `poppler-utils`。Compose 仍为 web、api、db、qdrant，只有 web 映射宿主端口。Qdrant 和网关只在服务端网络可达。`/health` 不访问数据库；数据库不可用时业务接口返回 503。

## Risks / Trade-offs

- 抽取依赖系统 `pdftotext`，必须设置超时和输出上限，避免恶意 PDF 拖垮 API。
- MySQL DDL 非事务性，迁移脚本需要幂等并在启动时逐个记录。
- 原文码点映射和多页抽取比现有文本切分复杂，但能保证 emoji、页码和旧引用可解释。
- 进程内队列在单实例 Compose 下足够；重启通过状态补排，暂不引入外部队列。
- 软删除保留历史和文件会占用空间，彻底删除作为教师显式操作，不提供自动清理。

## Migration Plan

1. 将当前建表 DDL 固化为迁移版本 1，创建 `schema_migrations` 并记录成功版本。
2. 后续迁移依次添加新列、新表、索引和约束；启动时不删除旧数据。
3. 将旧 `knowledge_chunks` 迁入 generation 0；已有材料标记为 pending 并后台重建。
4. 迁移完成后才启用新材料接口；失败仍保留旧材料和旧索引。
5. 角色三扩展 `verify.py` 和 Playwright，全部通过后才把 delta 合并到主规约并归档。

## Open Questions

没有留给实现阶段的行为选择。实现若发现规约冲突，必须先修改本 change 的 delta，再修改代码。
