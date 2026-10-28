# 07 数据规范

| 项目 | 内容 |
| --- | --- |
| 规范编号 | `07-data` |
| 掌管范围 | 命名与类型、主外键、审计字段、迁移纪律、数据字典、敏感分级、留存删除、跨存储一致性、测试数据 |
| 落地方式 | 常驻约束写入 `.cursor/rules/campusclaw-standards.mdc`；数据字典单独放在 `docs/data-dictionary.md` |
| 违反时 | 建表/改表不得合并；先改数据字典和迁移，再写代码 |

## 这一页管什么

管数据结构、生命周期和分级：表怎么命名、字段怎么审计、迁移怎么演进、哪些数据敏感、删除时哪些副本要清、MySQL/Qdrant/上传卷怎么保持一致。

不管：查询语句归 `02-backend.md`；备份与恢复归 `05-ops.md`。

## 项目事实

- 数据库：MySQL 8，库名 `campusclaw`，字符集 `utf8mb4`，时间统一 UTC `DATETIME`。
- 现有表：`classes`、`users`、`sessions`、`materials`、`knowledge_entries`、`knowledge_chunks`、`handouts`、`assignments`、`assistants`、`skills`。
- 本 change 新增：`schema_migrations`、`login_failures`、`material_versions`、`tags`、`material_tags`、`material_reads`、`favorites`；并给 `materials`、`knowledge_entries`、`knowledge_chunks` 加列。
- 跨存储：切片正文在 MySQL `knowledge_chunks`，向量在 Qdrant，原文件在 `uploads` 卷；三者的关联键是 `material_id`、`chunk_id`。
- 敏感数据：`users.password_hash`、`sessions.id`、`login_failures`、学生 `material_reads.position`、`favorites`、材料正文和原文件。
- 数据字典：`docs/data-dictionary.md` 是字段含义的唯一来源；本文件只写规则。

## 规范条目

| 条目 | 项目事实 | 为什么 | 怎么检查 |
| --- | --- | --- | --- |
| 命名与类型 | 表名小写复数、snake_case；字段 snake_case；时间用 `*_at`；状态用 ENUM 并列出取值；布尔用 `is_*` 或 `completed` | 同一概念多种命名会让查询和迁移出错 | 与 `docs/data-dictionary.md` 比对；出现两种风格即缺陷 |
| 主键与外键 | 主键统一 `BIGINT AUTO_INCREMENT`；外键写明并加索引；跨资源引用带归属字段（如 `class_id`）或能一次取到归属 | 没有外键和索引会在删除和查询时留下孤儿数据 | 抽查每张表能否一次取到 `class_id`；删除材料后无孤儿版本/切片 |
| 审计字段 | 业务表必须有 `created_at`；可变的加 `updated_at`；版本表记录 `editor_id`；版本行只增不改 | 没有审计字段无法解释“谁什么时候改了什么” | 抽查建表语句；缺少即补迁移 |
| 迁移纪律 | 迁移文件只增不改；每版记录 SHA-256；先加后删；每个版本写回滚动作；空库和旧库各跑一次 | 改历史迁移会让不同环境结构不一致 | 修改已执行文件应因 checksum 失败；按说明回滚成功 |
| 数据字典 | `docs/data-dictionary.md` 记录每张表、字段、类型、约束、敏感级别、留存/删除规则；结构变更同一提交更新 | 字段含义散落在代码和文档里，评审无法判断 | 变更说明与字典对照；缺字段说明即缺陷 |
| 敏感分级 | 四级：公开（材料标题）、内部（班级名）、敏感（正文、路径）、个人信息（用户名、进度、收藏）。敏感字段清单和脱敏规则集中在一处 | 分级不清会导致日志和导出泄露 | 抽查日志/响应/导出，含敏感原值即失败 |
| 留存与删除 | 材料软删除后保留版本和文件，彻底删除时清空；会话过期后删除；`login_failures` 保留 24 小时；备份保留 7 天 | 只删业务表会留下向量、文件和备份副本 | 执行一次删除演练，逐项核对副本清单 |
| 跨存储一致性 | 上传：先写文件，再事务写 MySQL，提交后入队；删除：先软删除 MySQL，彻底删除时按“向量 → 切片 → 版本 → 文件 → 标签关联”清理；失败记录补偿 | 中途失败会留下孤儿向量或文件 | 人为制造 Qdrant 失败，检查材料状态和残留；重试可清理 |
| 测试数据 | 只用预置账号和测试上传材料；生产数据不进测试；需要样本时脱敏后导出 | 未脱敏测试数据是事故 | 抽查测试库和 `uploads`；出现真实姓名/学号即事故 |

## 删除副本清单

彻底删除一份材料时，必须逐项核对：

| 副本 | 位置 | 清理方式 |
| --- | --- | --- |
| 业务行 | `materials` | 删除 |
| 版本 | `material_versions` | 删除 |
| 切片 | `knowledge_chunks` | 删除 |
| 向量 | Qdrant `campusclaw_<dim>` | 按 `chunk_id` 删除点 |
| 原文件 | `uploads/` | 删除存储文件 |
| 标签关联 | `material_tags` | 删除关联，孤立标签可保留 |
| 阅读进度/收藏 | `material_reads`、`favorites` | 删除 |
| 缓存 | 前端/会话中的材料摘要 | 下一次请求自然失效，不长期缓存正文 |
| 备份 | MySQL/上传卷/Qdrant 备份 | 按 7 天保留期自然过期；不承诺即时清除 |

## 本课最小集合

1. 命名与审计字段：新表全部符合，业务表有 `created_at`；本 change 给 `materials` 补 `updated_at`。
2. 迁移只增且可回滚：`0001` 基线不改，`0002` 有回滚说明。
3. 数据字典：`docs/data-dictionary.md` 覆盖所有新表和新列。
4. 敏感分级清单：至少列出 `password_hash`、`sessions`、`login_failures`、`material_reads`、`favorites`、正文、上传路径。
5. 留存期：会话、失败计数、备份的保留时间。
6. 删除演练：按副本清单执行一次“建 → 删 → 核对”。

**现有例外**：`classes`、`users` 等迭代 1/2 的表没有完整 `created_at/updated_at`；本 change 只补 `materials.updated_at`，其余在后续迁移补齐。这个例外登记在此，不用“以后再说”代替。

## 违反时怎么处理

- 新表没有 `created_at` 或数据字典条目：不合并。
- 修改已执行迁移：停止合并，补新迁移或恢复原文件。
- 删除只清了 MySQL、没清 Qdrant/文件：视为缺陷，补清理和重试。
- 日志/导出出现敏感原值：阻断合并，补脱敏并清理已产生记录。
- 例外（例如备份不即时删除）：写进本规范，说明保留期和责任人。
