# 设计：upgrade-material-library

## Context

当前后端是同一条链路：浏览器 → Nginx（web）→ Go（api）→ MySQL（db）与 Qdrant（qdrant）。`backend/internal/db/db.go` 用一组 `CREATE TABLE IF NOT EXISTS` 建表；`backend/internal/httpapi/materials.go` 在上传请求里同步调用 `retrieval.IndexMaterial`；`backend/internal/retrieval/index.go` 重建时先删旧切片再写新切片；`knowledge_chunks.start_offset/end_offset` 相对预处理后的文本；前端 629 行的 `frontend/src/App.tsx` 同时承担路由、列表、上传、检索和主题。本 change 不重做认证和问答协议，只扩展材料库和它依赖的底座。

## Goals / Non-Goals

**Goals:**

- 常见教学文件可以安全抽取并快速返回上传结果，索引状态可观察、可重试。
- 材料可重命名、打标签、删除/恢复、编辑/替换，并保留可比较、可恢复的追加式版本历史。
- 检索和引用能定位到当前或历史版本的原文区间；重建期间旧索引继续可用。
- 学生拥有私有阅读进度和收藏；教师拥有回收站和材料管理能力。
- 数据库、前端壳层和安全修复可以被现有 `verify.py`、Go 测试和 Playwright 复现。

**Non-Goals:**

见 `proposal.md` 的“本次不做”。会话问答、班级教学、邀请码注册和超级管理员都不在本 change。

## 1. 选型

| 领域 | 选择 | 理由 | 放弃的候选 |
| --- | --- | --- | --- |
| 数据库升级 | `schema_migrations` 加编号 SQL | 可复现、可记录版本和校验和，旧库无需清空 | 继续 `CREATE TABLE IF NOT EXISTS` 加手工 `ALTER` |
| 文件抽取 | 请求内同步抽取，PDF 用 `pdftotext`，Office 用 `archive/zip` + `encoding/xml` | 失败能当场告诉教师，符合“上传要么全有要么全无” | 抽取也放后台；引入 LibreOffice 或第三方解析库 |
| 索引执行 | 进程内队列 + MySQL 状态 | 单实例 Compose 足够，重启可补排，不引入 Redis | Redis、RabbitMQ、外部队列服务 |
| 重建策略 | 新 generation 先建后换 | 重建期间旧索引可用，失败不影响旧数据 | 先删后建；停机重建 |
| 原文坐标 | Unicode 码点下标 | 与 Go `[]rune` 和前端 `Array.from` 一致，emoji 不错位 | UTF-8 字节偏移；UTF-16 偏移 |
| 版本历史 | `material_versions` 追加写入 | 旧引用、恢复和审计都可解释 | 覆盖式更新；只存当前版本 |
| 并发控制 | `base_version` 乐观锁 | 不需要长事务和锁表，冲突时给教师看差异 | 悲观行锁；最后写入者覆盖 |
| 前端框架 | React + Vite，保留现有依赖，只加 `diff` | 不扩大包体和主题适配面 | 引入 UI 框架、富文本编辑器 |
| 会话 | 网页用 HttpOnly Cookie，Bearer 只给脚本 | 防 XSS 读取；现有 `POST /api/login` 已返回令牌 | 继续用 localStorage 存 Bearer |

## 2. 分层与依赖方向

```text
backend/internal/
  db/
    migrate.go              迁移执行器：排序、校验和、记录、启动失败
    migrations/
      0001_baseline.sql     等价现有 CREATE TABLE IF NOT EXISTS
      0002_material_library.sql
  extract/                  txt/md/pdf/docx/pptx 抽取与文件头校验
  indexer/                  进程内队列、状态机、重启补排
  library/                  版本、回收站、标签、阅读、收藏
  httpapi/                  参数校验、权限映射、响应形状
  retrieval/                切片、三种检索、RRF、出处
  materials/                扩展名、标题、文本校验（保留）
  auth/                     会话、JWT、限流（限流改由 db 支撑）
```

依赖方向：

- `httpapi` 只依赖 `library`、`indexer`、`retrieval`、`db` 的接口，不直接写 SQL 之外的业务规则。
- `indexer` 依赖 `extract`、`retrieval`、`db`；`retrieval` 不反向依赖 `indexer`。
- `extract` 不依赖数据库和 HTTP，只接收字节流并返回文本、页码表和错误。
- `db` 只负责连接、迁移和种子，不依赖上层业务包。
- 所有访问控制放在 `httpapi` 和 `library` 的服务端校验；前端隐藏按钮不构成授权。

## 3. 关键取舍

### 取舍 1：编号迁移，而不是启动时拼接 DDL

- **选了什么**：`0001_baseline.sql` 固化现有表结构，后续每个版本一个文件；`schema_migrations` 记录版本、文件名、SHA-256 和 `applied_at`。
- **放弃了什么**：继续在 `db.Migrate` 里追加 `CREATE TABLE IF NOT EXISTS` 和临时 `ALTER`。
- **代价由谁承担**：开发者首次要把现有 DDL 整理成基线，并在 CI/验收里多跑一次“空库 + 旧库”升级；收益是任何环境都能复现升级路径。

### 取舍 2：抽取同步、索引异步

- **选了什么**：上传请求完成大小、扩展名、文件头、ZIP 安全校验、文字抽取、页码表，以及文件、`materials`、`material_versions`、`knowledge_entries` 的事务写入；提交后把 material id 放进队列，立即返回 201；worker 每批 32 条调用嵌入。
- **放弃了什么**：把抽取也放进后台，上传立即返回成功。
- **代价由谁承担**：上传请求仍受 PDF 抽取 10 秒上限约束，大 PDF 的请求会慢；收益是扫描件、加密、损坏文件当场失败且无残留，教师不会等到很久以后才发现。

### 取舍 3：先建后换，而不是先删后建

- **选了什么**：`knowledge_chunks` 增加 `generation`；新 generation 全部 ready 后，在一个事务里切换 `materials.current_generation` 并删除旧切片，最后删除旧向量。
- **放弃了什么**：重建时先删旧切片和旧向量，再写新切片。
- **代价由谁承担**：开发者和验收要覆盖“重建期间检索仍可用”“失败只清理新 generation”；收益是重建不打断学生检索，也不会因为中途失败把材料变成不可用。

### 取舍 4：原文码点坐标，而不是预处理文本或字节偏移

- **选了什么**：`start_offset/end_offset` 一律是当前版本正文的 Unicode 码点下标，`start` 含、`end` 不含；预处理只用于切分，通过映射把切片边界折回原文。
- **放弃了什么**：沿用相对预处理文本的偏移；使用 UTF-8 字节或 UTF-16 偏移。
- **代价由谁承担**：切片和页码逻辑要维护映射，开发者多写单测；收益是 emoji、中文和 PDF 页码都能稳定高亮，旧引用也能解释。

### 取舍 5：追加式版本和乐观并发

- **选了什么**：每次编辑、替换、恢复都追加 `material_versions` 一行；保存和恢复携带 `base_version`，不是最新时返回 409 和最新内容。
- **放弃了什么**：最后写入者覆盖；悲观行锁；只保留当前版本。
- **代价由谁承担**：存储随版本增长，教师偶尔要处理冲突；收益是历史可比较、可恢复，旧引用不会因为一次编辑而失去依据。

### 取舍 6：软删除和回收站

- **选了什么**：`DELETE` 写 `deleted_at`，学生列表、详情、文件、检索和问答立即排除；教师通过回收站恢复或彻底删除；恢复保留版本、标签、进度和收藏；只有已删除材料允许彻底删除。
- **放弃了什么**：硬删除；定时自动清理；单独的回收站表。
- **代价由谁承担**：数据库和上传卷会保留已删除材料，直到教师彻底删除；收益是误删可恢复，删除语义在所有读路径一致。

### 取舍 7：前端壳层拆分，但不引入 UI 框架

- **选了什么**：`App.tsx` 拆为 `pages/` 和 `components/`，路由进入 URL，桌面左栏/窄屏底栏，全局搜索只搜已实现资源，统一 skeleton/空状态/503 重试/草稿保留；运行时只新增 `diff`。
- **放弃了什么**：引入 UI 框架、富文本编辑器、独立状态管理库。
- **代价由谁承担**：开发者要自己写可访问的导航、对话框和差异视图；收益是依赖少、主题和验收面可控。

### 取舍 8：网页只依赖 Cookie，Bearer 只给脚本

- **选了什么**：网页端所有请求带 `credentials: "include"`，不再读写 `localStorage` 令牌；`POST /api/login` 仍返回 Bearer，供 curl 和 `verify.py` 使用。
- **放弃了什么**：继续把 Bearer 存进 `localStorage`；完全删除 Bearer。
- **代价由谁承担**：前端要处理 Cookie 的 401 和重新登录；收益是 XSS 不能直接读走令牌，同时保持脚本兼容。

## 4. 接口契约

所有接口默认要求登录，班级只来自会话。错误体统一为 `{"error":"<code>"}`；409 额外带 `current_version` 和 `body`。按 id 的资源先整行读出，再校验班级和归属。

| 方法与路径 | 权限 | 成功 | 主要失败 |
| --- | --- | --- | --- |
| `POST /api/materials` | 本班教师 | 201 `{id,title,version:1,index_status:"pending"}` | 400 文件/抽取；413 超限；403 学生；503 依赖 |
| `POST /api/materials/batch` | 本班教师 | 201 `{items:[{client_id,ok,id?,title?,version?,index_status?,error?}]}` | 400 `no_files`/`too_many_files`；413；403 |
| `GET /api/materials` | 已登录 | 200 `{items,page,page_size,total}` | 400 `invalid_pagination`；401；503 |
| `GET /api/materials/{id}` | 已登录 | 200 标题、正文、版本、状态、标签、大纲 | 404（跨班/删除/不存在同形） |
| `GET /api/materials/{id}/file` | 已登录 | 200 附件 | 404 |
| `PATCH /api/materials/{id}` | 本班教师 | 200 | 400 `invalid_tag`；403；404 |
| `DELETE /api/materials/{id}` | 本班教师 | 204，进入回收站 | 403；404 |
| `POST /api/materials/{id}/restore` | 本班教师 | 200 | 403；404 |
| `DELETE /api/materials/{id}/purge` | 本班教师 | 204 | 403；404；409 `not_deleted` |
| `GET /api/trash` | 本班教师 | 200 | 403 |
| `PUT /api/materials/{id}/content` | 本班教师 | 200 `{version,index_status}` | 400 `not_editable`；403；404；409；413 |
| `POST /api/materials/{id}/file` | 本班教师 | 200 `{version,index_status}` | 400/413；403；404；409 |
| `GET /api/materials/{id}/versions` | 本班教师 | 200 `{versions:[...]}` | 403；404 |
| `GET /api/materials/{id}/versions/{v}` | 本班教师 | 200 `{version,kind,body?,file_url?,change_note}` | 403；404 |
| `POST /api/materials/{id}/versions/{v}/restore` | 本班教师 | 200 `{version}` | 403；404；409 |
| `POST /api/materials/{id}/reindex` | 本班教师 | 202 `{index_status:"pending"}` | 403；404 |
| `PUT /api/materials/{id}/progress` | 本班学生/教师 | 204 | 400；404 |
| `GET /api/materials/{id}/progress` | 当前用户 | 200 `{version,position,completed}` | 404 |
| `PUT/DELETE /api/materials/{id}/favorite` | 当前用户 | 204 | 404 |
| `GET /api/favorites` | 当前用户 | 200 `{items}` | 401 |
| `GET /api/recent` | 当前用户 | 200 最近阅读最多 5 条 | 401 |
| `GET /api/quick-search?q=` | 已登录 | 200 最多 20 条 | 401；503 |
| `GET /health` | 公开 | 200 `{status,version,time}`，不查依赖 | 无 |
| `GET /ready` | 公开 | 200 `{status:"ready",checks}` | 503 `{status:"not_ready",checks}` |

现有 `POST /api/search`、`POST /api/ask`、`POST /api/materials/{id}/reindex` 的路径保持不变；`/api/search` 增加可选的 `scope`（材料 id 列表或标签），不改变默认行为。

## 5. 数据模型

### 迁移与认证

- `schema_migrations(version BIGINT PRIMARY KEY, name VARCHAR(128) NOT NULL, checksum CHAR(64) NOT NULL, applied_at DATETIME NOT NULL)`。
- `login_failures(username VARCHAR(64), ip VARCHAR(45), fail_count INT NOT NULL, locked_until DATETIME NULL, updated_at DATETIME NOT NULL, PRIMARY KEY(username, ip), INDEX idx_login_failures_updated (updated_at))`。

### 材料与版本

- `materials` 增加：
  - `file_type ENUM('txt','md','pdf','docx','pptx') NOT NULL`
  - `page_count INT NOT NULL DEFAULT 0`
  - `current_version INT NOT NULL DEFAULT 1`
  - `index_status ENUM('pending','indexing','ready','failed') NOT NULL DEFAULT 'pending'`
  - `index_error VARCHAR(512) NULL`
  - `deleted_at DATETIME NULL`
  - `current_generation INT NOT NULL DEFAULT 0`
  - `updated_at DATETIME NOT NULL`
  - `INDEX idx_materials_class_deleted (class_id, deleted_at, created_at)`
  - `INDEX idx_materials_status (index_status)`
- `material_versions`：
  - `id BIGINT PRIMARY KEY AUTO_INCREMENT`
  - `material_id BIGINT NOT NULL`
  - `version INT NOT NULL`
  - `kind ENUM('upload','edit','replace','restore','seed') NOT NULL`
  - `body MEDIUMTEXT NULL`（txt/md）
  - `storage_name VARCHAR(80) NULL`（pdf/docx/pptx）
  - `original_filename VARCHAR(255) NULL`
  - `byte_size BIGINT NOT NULL`
  - `editor_id BIGINT NOT NULL`
  - `change_note VARCHAR(200) NULL`
  - `created_at DATETIME NOT NULL`
  - `UNIQUE KEY uq_versions_material_version (material_id, version)`
  - `INDEX idx_versions_material_created (material_id, created_at)`
- `knowledge_entries` 增加：
  - `version INT NOT NULL DEFAULT 1`
  - `page_table JSON NULL`，元素为 `{page, start, end}`（PPT 用 `slide`）
  - `body` 继续是当前版本的原文或抽取文本；预处理不改写它。
- `knowledge_chunks` 增加：
  - `generation INT NOT NULL DEFAULT 0`
  - `start_page INT NULL`、`end_page INT NULL`
  - `INDEX idx_chunks_generation (material_id, generation, index_status)`
  - `start_offset/end_offset` 改为当前版本原文的码点下标。

### 标签、阅读与收藏

- `tags(id BIGINT PK, class_id BIGINT NOT NULL, name VARCHAR(32) NOT NULL, UNIQUE(class_id, name))`。
- `material_tags(material_id BIGINT, tag_id BIGINT, PRIMARY KEY(material_id, tag_id), INDEX(tag_id))`。
- `material_reads(user_id BIGINT, material_id BIGINT, version INT NOT NULL, position INT NOT NULL, completed BOOLEAN NOT NULL, updated_at DATETIME NOT NULL, PRIMARY KEY(user_id, material_id), INDEX(user_id, updated_at))`。
- `favorites(user_id BIGINT, material_id BIGINT, created_at DATETIME NOT NULL, PRIMARY KEY(user_id, material_id), INDEX(user_id, created_at))`。

`material_reads` 和 `favorites` 不重复存 `class_id`，通过 `material_id -> materials.class_id` 在服务端校验，并按 `user_id` 过滤。除 `skills` 等全局表外，所有新表都有班级归属列或通过材料归属校验，并建立相应索引。

## 6. 索引状态机

```text
上传/保存/替换/恢复/reindex
            │
            ▼
        pending ──worker 取任务──▶ indexing
            ▲                        │
            │                        ├── 成功：新 generation ready，切换 current_generation，删旧切片/向量 ──▶ ready
            │                        └── 失败：只清理新 generation，旧 generation 保留 ──▶ failed
            │
            └── 教师重试 / api 重启补排（pending、indexing）
```

规则：

- 上传、编辑、替换、恢复、reindex 都把材料置为 `pending`，并清除旧 `index_error`。
- worker 取任务后置为 `indexing`；同一材料同一时间只允许一个 worker。
- 成功：`knowledge_chunks` 的新 generation 全部 `ready`，在事务里更新 `materials.current_generation`，删除旧 generation 的切片，最后删除旧向量，材料置 `ready`。
- 失败：只删除新 generation 的切片和向量，旧 generation 仍为当前；材料置 `failed`，写 `index_error`。
- 启动时把所有 `pending` 和 `indexing` 的材料重新排队；`indexing` 先重置为 `pending`。
- `POST /api/materials/{id}/reindex` 在已 `pending` 或 `indexing` 时返回 202，幂等；不要重复入队两次。

## 7. 原文坐标与页码

- 所有 `start/end` 都是解码后正文的 Unicode 码点下标，`start` 含、`end` 不含。
- Go 端用 `[]rune` 切片；前端用 `Array.from(body)`，不用 `body.slice`，避免 UTF-16 代理对错位。
- 预处理可以去掉 URL、折叠空白，但必须记录“预处理字符 → 原文码点”的映射；切片边界以原文码点落库。
- PDF 抽取时记录每页的起止码点：`page_table=[{"page":1,"start":0,"end":1234}, ...]`；PPT 用 `slide`。
- 切片的 `start_page` 取包含 `start` 的页，`end_page` 取包含 `end-1` 的页。
- 引用保存 `material_id`、`version`、`start`、`end`、`excerpt`，PDF/PPT 另存 `page` 或 `slide`；不把 `chunk_id` 当长期引用。
- 若引用 `version < current_version`，前端显示“原文已更新”和旧 `excerpt`；若 `start/end` 超出当前正文，只显示摘录，不高亮。
- `generation=0` 的旧切片是 legacy：可以检索，但不保证 `start/end` 可高亮；重建到新 generation 后恢复正常。

## 8. 版本与并发

- 版本号从 1 开始，上传生成 v1；编辑、替换、恢复各生成 v(N+1)。
- `material_versions` 只追加，不更新、不删除；彻底删除材料时才级联删除。
- 保存请求必须带 `base_version`。事务内 `SELECT current_version ... FOR UPDATE`，不匹配返回 409，响应带 `current_version` 和最新 `body`。
- 恢复也带 `base_version`；恢复内容复制为新版本，旧版本行不变。
- 非 `.txt`/`.md` 调用 `PUT content` 返回 400 `not_editable`；替换文件走 `POST file`，抽取规则与上传相同。
- 重命名和标签不生成版本，不触发索引。

## 9. 配置

| 变量/常量 | 默认 | 校验 | 用途 |
| --- | --- | --- | --- |
| `MAX_UPLOAD_BYTES` | 1048576 | 1 至 16777216 | 单文件上限 |
| `MAX_BATCH_FILES` | 20 | 固定 | 单次批量文件数 |
| `MAX_BATCH_BYTES` | 20 MiB | 不小于单文件上限 | 单次请求总上限 |
| `PDFTOTEXT_TIMEOUT` | 10 秒 | 固定 | PDF 抽取超时 |
| `EXTRACT_MAX_CHARS` | 2,000,000 | 固定 | 抽取正文上限 |
| `MAX_ARCHIVE_ENTRIES` | 2000 | 固定 | docx/pptx 条目上限 |
| `MAX_ARCHIVE_UNCOMPRESSED_BYTES` | 100 MiB | 固定 | 解压后总大小 |
| `EMBEDDING_DIM` | 无默认 | 1 至 4096，必填 | 向量维度、Qdrant 集合名 |
| `INDEX_POLL_MS` | 2000 | 固定 | 前端轮询索引状态 |
| `READ_PROGRESS_THROTTLE_MS` | 2000 | 固定 | 阅读进度上报节流 |
| `PAGE_SIZE_DEFAULT` | 20 | 固定 | 列表默认条数 |
| `PAGE_SIZE_MAX` | 100 | 固定 | 列表最大条数 |
| `LOGIN_FAIL_THRESHOLD` | 5 | 正整数 | 登录失败阈值 |
| `LOGIN_LOCK_MINUTES` | 15 | 正整数 | 锁定时长 |
| `TRUSTED_PROXY_CIDRS` | `10/8,172.16/12,192.168/16,127/8` | 固定 | 可信代理网段 |
| `SHUTDOWN_TIMEOUT` | 10 秒 | 固定 | SIGTERM 后等待在途请求的上限 |

新增环境变量必须写进 `.env.example` 和 `docker-compose.yml`；缺失或越界时启动失败，不取默认值。固定常量写在代码里并在测试中引用，不通过请求参数覆盖。

## 10. 安全与可观测性

- 上传：扩展名白名单之外校验文件头；PDF 必须以 `%PDF-` 开头；DOCX/PPTX 必须是合法 ZIP，限制条目数和解压后大小；下载一律 `Content-Disposition: attachment` 和 `nosniff`。
- Markdown 继续不渲染原始 HTML；响应增加 CSP：`default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'`。
- 所有修改数据的请求核对 `Origin`；提问和生成练习按用户限流。
- 材料文字只作为依据交给模型；客户端传来的 `system` 消息继续丢弃。
- 登录限流键为 `(username, trusted_ip)`；Nginx 用 `proxy_set_header X-Real-IP $remote_addr` 覆盖，Go 只在直接对端属于可信私网时采用该值，`X-Forwarded-For` 不参与计数。
- 网页端不保存令牌；Bearer 只用于脚本，服务端仍校验会话行。
- 日志：stdout 单行 JSON，字段 `ts`、`level`、`msg`、`request_id`，HTTP 请求另含 `method`、`path`、`status`、`duration_ms`；可用时加 `class_id`、`user_id`。`request_id` 从 `X-Request-ID` 读取（8 至 64 个可见 ASCII），缺失时生成 UUIDv4，并回写响应头。日志不写口令、令牌、Cookie、正文、绝对路径或 DSN。
- 检查：`/health` 只表示进程存活，不访问依赖；`/ready` 检查 MySQL ping、Qdrant 可达和 `EMBEDDING_DIM` 有效，失败返回 503。课程样例把依赖状态放在 `/health`，本项目为保留既有“`/health` 不查库”的公开契约，把依赖状态放到 `/ready`；这是写入规范的例外，不做静默偏离。
- 停机：收到 SIGTERM 后停止接受新连接，等待在途请求最多 10 秒，再退出；迁移和索引写入不在中途强杀。

## 11. 迁移计划

1. 把 `db.Migrate` 的现有 DDL 固化为 `0001_baseline.sql`，创建 `schema_migrations`，在监听端口前执行并记录。
2. `0002_material_library.sql` 增加 `materials`、`knowledge_entries`、`knowledge_chunks` 的新列，创建 `material_versions`、`tags`、`material_tags`、`material_reads`、`favorites`、`login_failures`。
3. 为已有材料插入 v1 版本，`body` 取现有 `knowledge_entries.body`；`file_type` 按 `original_ext` 映射。
4. 旧切片保留 `generation=0`，材料置 `pending`，后台重建 generation 1；重建完成前旧索引仍可检索，引用只保证摘录、不保证高亮。
5. 迁移失败时启动退出，保留旧数据和旧索引；修复迁移后重启即可继续。
6. 全部验收通过后，才把 delta 合并到 `openspec/specs/` 并归档 change。

## 12. 风险与代价

- PDF 抽取依赖 `pdftotext`，必须设置 10 秒超时和 2,000,000 字符上限，避免恶意 PDF 拖垮 api。
- MySQL DDL 非事务性，迁移脚本必须小而幂等，并在启动时逐个记录；半途失败靠 `schema_migrations` 和校验和定位。
- 原文码点映射和多页抽取比现有文本切分复杂，需要覆盖 emoji、中文、页码和旧引用的 Go/前端测试。
- 进程内队列只支持单实例；api 重启会短暂中断索引，但状态可补排，符合现有单实例部署约束。
- 软删除保留文件和版本会占用空间；彻底删除是教师显式操作，不提供自动清理。
- 143 个场景的验收需要角色三按 `tasks.md` 的 `verify` 分批执行；这是本 change 的主要进度风险。

## 13. Open Questions

没有留给实现阶段的行为选择。实现若发现规约冲突，先修改本 change 的 delta，再修改代码；不得用实现细节反向解释规约。
