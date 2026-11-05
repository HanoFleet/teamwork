# 数据字典

本文件是字段含义、约束、敏感级别和删除规则的唯一来源。结构变更必须同一提交更新本文件；`docs/standards/07-data.md` 只写规则，不重复字段定义。

## 约定

- 表名小写复数，字段 snake_case，时间统一 UTC `DATETIME`。
- 主键统一 `BIGINT AUTO_INCREMENT`；外键列加索引。
- 敏感级别：公开 / 内部 / 敏感 / 个人信息。
- 删除规则：软删除只改标记；彻底删除按 `07-data.md` 的副本清单执行。

## 当前 change 的数据影响

`2026-10-28-establish-platform-foundation` 不改数据库结构，只增加 `APP_VERSION`、`SHUTDOWN_TIMEOUT_SECONDS` 等运行配置。材料库的表结构变更（`material_versions`、`tags`、`material_reads` 等）属于 `2026-10-14-upgrade-material-library`，实现时按本字典一起更新。第 8 课 `2026-11-05-add-async-grading` 新增 `submissions`、`grade_tasks`、`outbox_messages`、`grade_results`，并扩展 `assignments`；由 `db.Migrate` 用 `CREATE TABLE IF NOT EXISTS` 与 `ensureColumn` 幂等执行，不改已有建表语句的语义。

## 迁移与认证

### `schema_migrations`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `version` | BIGINT | PK | 迁移版本号，从 1 递增 | 公开 |
| `name` | VARCHAR(128) | NOT NULL | 迁移文件名 | 公开 |
| `checksum` | CHAR(64) | NOT NULL | 文件 SHA-256，防止已执行脚本被改 | 公开 |
| `applied_at` | DATETIME | NOT NULL | 执行时间 | 内部 |

删除规则：不删除；只在重置数据库时随库清空。

### `classes`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `id` | BIGINT | PK | 班级 id | 内部 |
| `name` | VARCHAR(64) | NOT NULL, UNIQUE | 班级名（A/B） | 内部 |

删除规则：有用户或材料时禁止删除。

### `users`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `id` | BIGINT | PK | 用户 id | 内部 |
| `username` | VARCHAR(64) | NOT NULL, UNIQUE | 登录名 | 个人信息 |
| `password_hash` | VARCHAR(255) | NOT NULL | bcrypt 哈希 | 敏感 |
| `role` | ENUM('teacher','student') | NOT NULL | 角色 | 内部 |
| `class_id` | BIGINT | NOT NULL, FK classes | 归属班级 | 内部 |
| `display_name` | VARCHAR(64) | NULL | 显示名（本 change 可空） | 个人信息 |
| `must_change_password` | BOOLEAN | NOT NULL DEFAULT 0 | 首次登录强制改口令（后续模块） | 内部 |
| `last_login_at` | DATETIME | NULL | 最近登录时间（后续模块） | 个人信息 |

删除规则：不物理删除；停用后续模块实现。

### `sessions`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `id` | CHAR(64) | PK | 会话 id | 敏感 |
| `user_id` | BIGINT | NOT NULL, FK users | 用户 | 内部 |
| `expires_at` | DATETIME | NOT NULL | 过期时间 | 内部 |
| `created_at` | DATETIME | NOT NULL | 创建时间 | 内部 |

删除规则：登出、过期、改口令时删除。

### `login_failures`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `username` | VARCHAR(64) | PK 组成 | 尝试登录的用户名 | 个人信息 |
| `ip` | VARCHAR(45) | PK 组成 | 可信客户端 IP（IPv4/IPv6） | 个人信息 |
| `fail_count` | INT | NOT NULL DEFAULT 0 | 连续失败次数 | 内部 |
| `locked_until` | DATETIME | NULL | 锁定截止时间 | 内部 |
| `updated_at` | DATETIME | NOT NULL | 更新时间 | 内部 |

删除规则：成功登录清除；锁定到期后可重置；超过 24 小时的行由清理任务删除。

## 材料与版本

### `materials`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `id` | BIGINT | PK | 材料 id | 内部 |
| `class_id` | BIGINT | NOT NULL, FK classes, INDEX | 归属班级 | 内部 |
| `uploader_id` | BIGINT | NOT NULL, FK users | 上传者 | 内部 |
| `title` | VARCHAR(255) | NOT NULL | 显示标题 | 公开（本班） |
| `storage_name` | VARCHAR(80) | NOT NULL | 服务端生成的文件名 | 敏感 |
| `original_ext` | VARCHAR(8) | NOT NULL | 原扩展名 | 内部 |
| `file_type` | ENUM('txt','md','pdf','docx','pptx') | NOT NULL | 文件类型 | 内部 |
| `byte_size` | BIGINT | NOT NULL | 文件大小 | 内部 |
| `page_count` | INT | NOT NULL DEFAULT 0 | PDF 页数/PPT 幻灯片数 | 内部 |
| `current_version` | INT | NOT NULL DEFAULT 1 | 当前版本号 | 内部 |
| `index_status` | ENUM('pending','indexing','ready','failed') | NOT NULL DEFAULT 'pending' | 索引状态 | 内部 |
| `index_error` | VARCHAR(512) | NULL | 失败原因（脱敏） | 内部 |
| `current_generation` | INT | NOT NULL DEFAULT 0 | 当前检索 generation | 内部 |
| `updated_at` | DATETIME | NOT NULL | 最近一次元数据/状态变更时间 | 内部 |
| `deleted_at` | DATETIME | NULL | 软删除时间 | 内部 |
| `created_at` | DATETIME | NOT NULL | 创建时间 | 内部 |
| `seed_key` | VARCHAR(64) | NULL, UNIQUE | 预置材料幂等键 | 内部 |

删除规则：软删除设置 `deleted_at`；彻底删除按副本清单清理。

### `material_versions`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `id` | BIGINT | PK | 版本行 id | 内部 |
| `material_id` | BIGINT | NOT NULL, FK materials | 材料 | 内部 |
| `version` | INT | NOT NULL | 版本号，从 1 递增 | 内部 |
| `kind` | ENUM('upload','edit','replace','restore','seed') | NOT NULL | 版本来源 | 内部 |
| `body` | MEDIUMTEXT | NULL | txt/md 正文 | 敏感 |
| `storage_name` | VARCHAR(80) | NULL | 二进制文件存储名 | 敏感 |
| `original_filename` | VARCHAR(255) | NULL | 原文件名 | 个人信息（可能含姓名） |
| `byte_size` | BIGINT | NOT NULL | 版本大小 | 内部 |
| `editor_id` | BIGINT | NOT NULL, FK users | 编辑人 | 内部 |
| `change_note` | VARCHAR(200) | NULL | 修改说明 | 内部 |
| `created_at` | DATETIME | NOT NULL | 创建时间 | 内部 |

约束：`UNIQUE(material_id, version)`；只增不改。删除规则：随材料彻底删除。

### `knowledge_entries`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `id` | BIGINT | PK | 知识条目 id | 内部 |
| `material_id` | BIGINT | NOT NULL, UNIQUE, FK materials | 材料 | 内部 |
| `class_id` | BIGINT | NOT NULL, FK classes | 班级 | 内部 |
| `body` | MEDIUMTEXT | NOT NULL | 当前版本原文或抽取文本 | 敏感 |
| `version` | INT | NOT NULL DEFAULT 1 | 对应材料版本 | 内部 |
| `page_table` | JSON | NULL | 页/幻灯片起止码点表 | 内部 |
| `created_at` | DATETIME | NOT NULL | 创建时间 | 内部 |

删除规则：随材料彻底删除。

### `knowledge_chunks`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `id` | BIGINT | PK | 切片 id，同时是 Qdrant 点 id | 内部 |
| `class_id` | BIGINT | NOT NULL, FK classes, INDEX | 班级 | 内部 |
| `material_id` | BIGINT | NOT NULL, FK materials, INDEX | 材料 | 内部 |
| `knowledge_entry_id` | BIGINT | NOT NULL, FK knowledge_entries | 知识条目 | 内部 |
| `chunk_index` | INT | NOT NULL | 切片序号 | 内部 |
| `chunk_text` | MEDIUMTEXT | NOT NULL | 切片正文 | 敏感 |
| `start_offset` | INT | NOT NULL | 原文码点起点（含） | 内部 |
| `end_offset` | INT | NOT NULL | 原文码点终点（不含） | 内部 |
| `start_page` | INT | NULL | 起始页/幻灯片 | 内部 |
| `end_page` | INT | NULL | 结束页/幻灯片 | 内部 |
| `generation` | INT | NOT NULL DEFAULT 0 | 索引 generation | 内部 |
| `index_status` | ENUM('pending','ready','failed') | NOT NULL | 切片状态 | 内部 |
| `strategy` | VARCHAR(32) | NOT NULL | 切分策略 | 内部 |
| `created_at` | DATETIME | NOT NULL | 创建时间 | 内部 |

约束：全文索引 `FULLTEXT(chunk_text) WITH PARSER ngram`；索引 `(material_id, generation, index_status)`。删除规则：重建时删旧 generation；彻底删除随材料清理。

## 标签、阅读与收藏

### `tags`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `id` | BIGINT | PK | 标签 id | 内部 |
| `class_id` | BIGINT | NOT NULL, FK classes | 班级 | 内部 |
| `name` | VARCHAR(32) | NOT NULL | 标签名 | 公开（本班） |

约束：`UNIQUE(class_id, name)`。删除规则：材料彻底删除后，无关联的标签可保留。

### `material_tags`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `material_id` | BIGINT | PK 组成, FK materials | 材料 | 内部 |
| `tag_id` | BIGINT | PK 组成, FK tags | 标签 | 内部 |

删除规则：随材料彻底删除。

### `material_reads`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `user_id` | BIGINT | PK 组成, FK users | 用户 | 个人信息 |
| `material_id` | BIGINT | PK 组成, FK materials | 材料 | 内部 |
| `version` | INT | NOT NULL | 阅读时版本 | 内部 |
| `position` | INT | NOT NULL | 原文码点位置 | 个人信息 |
| `completed` | BOOLEAN | NOT NULL | 是否读完 | 个人信息 |
| `updated_at` | DATETIME | NOT NULL | 更新时间 | 个人信息 |

约束：`PRIMARY KEY(user_id, material_id)`。删除规则：随材料彻底删除；用户停用后续模块处理。

### `favorites`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `user_id` | BIGINT | PK 组成, FK users | 用户 | 个人信息 |
| `material_id` | BIGINT | PK 组成, FK materials | 材料 | 内部 |
| `created_at` | DATETIME | NOT NULL | 收藏时间 | 个人信息 |

约束：`PRIMARY KEY(user_id, material_id)`。删除规则：随材料彻底删除。

## 异步批改（第 8 课）

### `assignments`（扩展）

复用现有占位表，第 8 课补充以下列；本 change 只要求能创建一份已发布作业，不做编辑和截止。

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `published` | BOOLEAN | NOT NULL DEFAULT 0 | 是否已发布，只有已发布作业可提交 | 内部 |
| `created_by` | BIGINT | NULL, FK users | 创建教师 | 内部 |
| `created_at` | DATETIME | NULL | 创建时间 | 内部 |

迁移：已有数据库通过 `information_schema.COLUMNS` 检查后幂等 `ALTER TABLE` 补列，不能只改 `CREATE TABLE IF NOT EXISTS`；种子按 `class_id` 给 A/B 各一份 `published=1` 的作业。

删除规则：本 change 不提供删除接口；已有提交时不得物理删除。

### `submissions`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `id` | BIGINT | PK | 提交 id | 内部 |
| `assignment_id` | BIGINT | NOT NULL, FK assignments, INDEX | 作业 | 内部 |
| `student_id` | BIGINT | NOT NULL, FK users | 提交学生 | 个人信息 |
| `class_id` | BIGINT | NOT NULL, FK classes | 会话班级 | 内部 |
| `body` | MEDIUMTEXT | NOT NULL | 提交正文 | 敏感 |
| `version` | INT | NOT NULL DEFAULT 1 | 内容版本，从 1 递增 | 内部 |
| `status` | ENUM('submitted','grading','graded') | NOT NULL DEFAULT 'submitted' | 提交状态 | 内部 |
| `created_at` | DATETIME | NOT NULL | 创建时间 | 内部 |
| `updated_at` | DATETIME | NOT NULL | 更新时间 | 内部 |

约束：`UNIQUE(assignment_id, student_id, version)`，`INDEX(class_id, student_id)`。`submissions` 按版本追加：每个版本一行，`id` 就是返回给前端的 `submission_id`；内容变化插入新行并返回新 id，旧行、旧任务和旧结果都保留。状态流转：创建为 `submitted`，worker 开始为 `grading`，成功为 `graded`；瞬时失败回 `submitted`，永久失败/dead 也回 `submitted`，失败原因只记在 `grade_tasks`。删除规则：保留；不提供删除接口。

### `grade_tasks`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `id` | BIGINT | PK | 任务行 id | 内部 |
| `task_id` | CHAR(26) | NOT NULL, UNIQUE | 对外任务标识（ULID） | 内部 |
| `submission_id` | BIGINT | NOT NULL, FK submissions, INDEX | 提交版本行 | 内部 |
| `submission_version` | INT | NOT NULL | 任务对应的提交版本 | 内部 |
| `class_id` | BIGINT | NOT NULL, FK classes | 班级 | 内部 |
| `student_id` | BIGINT | NOT NULL, FK users | 学生 | 个人信息 |
| `status` | ENUM('pending','running','succeeded','failed','dead') | NOT NULL DEFAULT 'pending' | 任务状态 | 内部 |
| `attempts` | INT | NOT NULL DEFAULT 0 | 已执行次数 | 内部 |
| `max_attempts` | INT | NOT NULL DEFAULT 5 | 重试上限 | 内部 |
| `idempotency_key` | VARCHAR(128) | NOT NULL, UNIQUE | `grade:<submission_id>:<version>` | 内部 |
| `error` | VARCHAR(512) | NULL | 最后错误（脱敏） | 内部 |
| `next_run_at` | DATETIME | NULL | 下次可执行时间 | 内部 |
| `started_at` | DATETIME | NULL | 最近一次开始时间 | 内部 |
| `finished_at` | DATETIME | NULL | 终态时间 | 内部 |
| `created_at` | DATETIME | NOT NULL | 创建时间 | 内部 |
| `updated_at` | DATETIME | NOT NULL | 更新时间 | 内部 |

约束：`INDEX(status, next_run_at)`。删除规则：不自动删除；`dead` 任务保留用于排障，清理策略在实现时另行定义。

### `outbox_messages`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `id` | BIGINT | PK | 发件箱行 id | 内部 |
| `message_id` | CHAR(26) | NOT NULL, UNIQUE | 消息标识（ULID） | 内部 |
| `idempotency_key` | VARCHAR(128) | NOT NULL, UNIQUE | 与任务相同的幂等键 | 内部 |
| `topic` | VARCHAR(64) | NOT NULL | 目标队列/主题 | 内部 |
| `payload` | JSON | NOT NULL | 消息体（task_id/submission_id/submission_version） | 内部 |
| `status` | ENUM('pending','published') | NOT NULL DEFAULT 'pending' | 投递状态 | 内部 |
| `attempts` | INT | NOT NULL DEFAULT 0 | 发布尝试次数 | 内部 |
| `next_attempt_at` | DATETIME | NULL | 下次重试时间 | 内部 |
| `created_at` | DATETIME | NOT NULL | 创建时间 | 内部 |
| `published_at` | DATETIME | NULL | 确认发布时间 | 内部 |

约束：`INDEX(status, next_attempt_at)`。删除规则：`pending` 不得删除；只允许清理已发布且超过运维保留期的行。

### `grade_results`

| 字段 | 类型 | 约束 | 说明 | 敏感 |
| --- | --- | --- | --- | --- |
| `id` | BIGINT | PK | 结果行 id | 内部 |
| `submission_id` | BIGINT | NOT NULL, FK submissions, INDEX | 提交 | 内部 |
| `version` | INT | NOT NULL | 提交版本 | 内部 |
| `idempotency_key` | VARCHAR(128) | NOT NULL, UNIQUE | 幂等键 | 内部 |
| `score` | DECIMAL(5,2) | NOT NULL | 0–100 分 | 个人信息 |
| `feedback` | TEXT | NOT NULL | 评语 | 个人信息 |
| `task_id` | CHAR(26) | NOT NULL | 产出结果的任务 | 内部 |
| `graded_at` | DATETIME | NOT NULL | 完成时间 | 内部 |

约束：`UNIQUE(submission_id, version)`；结果写入使用 `INSERT IGNORE`/`ON DUPLICATE KEY UPDATE id=id`，重复投递保留首次分数/评语，不新增第二行。删除规则：随 submission 保留；不提供删除接口。

## 占位表（本 change 不提供业务接口）

`assignments` 已被第 8 课最小使用；`handouts`、`assistants`、`skills` 仍保持现有结构，后续模块使用前必须先补数据字典、迁移和规约。当前只允许占位数据，不新增业务字段。

## 变更记录

| 日期 | 变更 | 迁移 |
| --- | --- | --- |
| 2026-10-28 | 初版：现有表 + `2026-10-14-upgrade-material-library` 新增/修改 | `0001`、`0002` |
| 2026-11-05 | 第 8 课：新增 `submissions`、`grade_tasks`、`outbox_messages`、`grade_results`，扩展 `assignments` | `db.Migrate`（IF NOT EXISTS + ensureColumn） |
