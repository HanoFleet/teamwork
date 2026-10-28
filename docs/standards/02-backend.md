# 02 后端开发规范

| 项目 | 内容 |
| --- | --- |
| 规范编号 | `02-backend` |
| 掌管范围 | 分层与依赖方向、接口命名与版本、统一响应与错误码、幂等与并发、分页、迁移、配置 |
| 落地方式 | 常驻约束写入 `.cursor/rules/campusclaw-standards.mdc`；“按规范加一个接口”写成技能 |
| 违反时 | 新接口不得合并；先改规范或写例外，再改代码 |

## 这一页管什么

管 Go 服务端的结构与对外契约：代码放在哪一层、接口怎么命名、错误怎么返回、写接口是否幂等、分页怎么稳定、迁移怎么演进、配置从哪里来。

不管：页面与文案归 `01-product.md`；权限判定归 `03-security.md`；镜像、健康检查和日志字段归 `05-ops.md`。

## 项目事实

> 旧实现已打包到 `archive/campusclaw-baseline.zip`；实现阶段从归档恢复对应目录。本文中的 `backend/`、`frontend/`、Compose 路径指恢复后的目标结构。

- 目录：`backend/internal/httpapi/` 是接口层；`library/`、`indexer/`、`retrieval/` 是业务层；`db/` 是数据访问层；`extract/`、`qdrant/`、`embed/`、`chat/` 是适配层。
- 现有偏差：`httpapi/materials.go` 和 `httpapi/auth.go` 里有 SQL；本 change 把材料读写逐步移到 `library/`，新增代码不得再在 handler 里写 SQL。
- 现有接口都在 `/api/` 下，没有 `/v1` 前缀。把 `/api` 视为 v1 命名空间；新增接口继续用 `/api/...`，不为了“版本化”重命名已有路径。出现破坏性变更时另开 `/api/v2/...`，旧路径保留一个版本周期。
- 现有成功响应是资源相关 JSON（`{materials:[]}`、`{hits:[]}`、`{answer,citations}`），错误响应是 `{"error":"<code>"}`。本 change 保留成功形状，错误体增加 `request_id` 放在响应头 `X-Request-ID`，不改已有字段名。
- 配置全部来自环境变量；缺失即启动失败，不取默认密钥。`EMBEDDING_DIM` 必填，`SHUTDOWN_TIMEOUT` 固定 10 秒。
- 数据库是 MySQL 8；迁移脚本在 `backend/internal/db/migrations/`，`schema_migrations` 记录版本和校验和。

## 规范条目

| 条目 | 项目事实 | 为什么 | 怎么检查 |
| --- | --- | --- | --- |
| 分层与依赖方向 | 接口层只做参数解析、权限调用和错误映射；业务层持有事务和规则；数据访问层持有 SQL；适配层只封装外部服务。依赖方向 `httpapi → library/indexer/retrieval → db`，禁止反向 | 分层混乱会让权限和事务散落，无法定位缺陷 | 新增模块检查落点；`grep -R "SELECT\|INSERT\|UPDATE\|DELETE" backend/internal/httpapi` 应为空（现有遗留逐步清零） |
| 接口命名与版本 | 资源用小写复数：`/api/materials`、`/api/materials/{id}/versions`；读 GET，建 POST，改 PATCH/PUT，删 DELETE；路径不写动词。`/api` 是 v1，破坏性变更用 `/api/v2` | 同一资源多种命名会让调用方和测试不断猜 | 新接口对照命名表；出现 `/getMaterial`、`/deleteMaterial` 这类路径即缺陷 |
| 统一响应与错误码 | 成功返回资源 JSON；失败统一 `{"error":"<code>"}`，响应头 `X-Request-ID`；错误码只从下表取，新增先登记 | 错误码散落会让前端和验收无法按码判定 | 抽查 400/401/403/404/409/413/503 各一条；出现表外 code 即缺陷 |
| 错误码清单 | `invalid_request`、`invalid_file`、`invalid_archive`、`invalid_query`、`invalid_pagination`、`invalid_tag`、`not_editable`、`not_replaceable`、`type_mismatch`、`unauthorized`、`invalid_credentials`、`forbidden`、`not_found`、`version_conflict`、`not_deleted`、`payload_too_large`、`too_many_files`、`no_files`、`unavailable`、`embedding_dim_mismatch` | 错误码是验收和前端分支的唯一稳定标识 | 维护本表；新增错误码必须在同一提交登记 |
| 幂等声明 | `POST /api/materials` 不幂等（每次新材料）；`POST /api/materials/batch` 不幂等；`PUT /api/materials/{id}/content` 不幂等（每次新版本）；`POST .../file` 不幂等；`POST .../versions/{v}/restore` 不幂等（每次新版本）；`PUT .../progress`、`PUT/DELETE .../favorite`、`POST .../reindex` 幂等 | 重复请求产生重复副作用是最难排查的缺陷 | 对幂等接口连发两次，行数/状态不变；对非幂等接口连发两次，得到两个明确结果而不是半条数据 |
| 唯一约束 | 版本 `(material_id, version)`、标签 `(class_id, name)`、阅读 `(user_id, material_id)`、收藏 `(user_id, material_id)` 都在数据库加唯一键 | 应用层“先查后写”存在时间窗 | `SHOW CREATE TABLE` 检查唯一键；并发请求下不出现重复行 |
| 分页与排序 | `page` ≥1，`page_size` 1 至 100、默认 20；`sort` 只允许 `created_desc`、`created_asc`、`title_asc`、`title_desc`；同值用 `id DESC` 兜底；非法参数返回 400 | 排序不稳定会导致翻页重复或遗漏 | 构造同标题记录翻两页；非法 sort 返回 400，不退化为全量 |
| 事务边界 | 上传：抽取在事务外，文件、`materials`、`material_versions`、`knowledge_entries` 在一个事务内；索引在提交后异步入队。事务内禁止调用嵌入、Qdrant、对话网关或写大文件 | 事务内做外部调用会长时间持锁，失败无法回滚外部副作用 | 人为让事务内插入失败，检查文件被清理、外部服务未被调用 |
| 迁移纪律 | 迁移文件只增不改；每个版本记录 SHA-256；回滚动作写在同一版本的说明里；空库和旧库各跑一次 | 改历史迁移会让不同环境结构不一致 | 修改已执行的 `0002`，启动应因 checksum 失败；按说明执行回滚可回到上一版 |
| 配置外置 | 地址、密钥、开关只从环境变量读取；缺任何必填项启动失败，不取默认值；`.env.example` 只写键名或占位 | 默认值会让生产静默连到错误地址 | 删一个必填变量启动，应非零退出；源码中搜不到真实地址或密钥 |
| 错误与日志分离 | 响应给用户的是固定 code 和可读文案；日志给开发者的是 request_id、路径、状态和错误原因；日志不写正文、口令、令牌、DSN | 把堆栈或 SQL 返回给用户会泄露结构，日志缺上下文无法排障 | 触发 503 和 400，检查响应无堆栈、日志有 request_id 且无机密 |

## 接口风格示例

```text
GET    /api/materials?tag=第一章&sort=title_asc&page=2&page_size=10
POST   /api/materials/batch                  # files, 1..20
PATCH  /api/materials/{id}                   # title, tags
PUT    /api/materials/{id}/content           # body, change_note, base_version
POST   /api/materials/{id}/versions/{v}/restore
DELETE /api/materials/{id}/purge             # 仅已删除材料
GET    /ready                                # 无需登录，返回依赖状态
```

## 本课最小集合

1. 分层与依赖方向：新增 `extract/`、`indexer/`、`library/` 落在规定层，handler 不写 SQL。
2. 接口命名与版本：本 change 的 15 个新路径全部符合资源命名；不改已有路径。
3. 统一错误结构与错误码清单：本文件维护唯一清单。
4. 幂等声明：上表覆盖本 change 全部写接口。
5. 配置外置：`EMBEDDING_DIM` 缺失即启动失败。
6. 分页与排序：`page/page_size/sort` 白名单和 `id` 兜底。

## 违反时怎么处理

- 新接口在 handler 里写 SQL：退回，把查询移到 `library/` 或 `db/`。
- 出现表外错误码：先登记到本文件，再合并。
- 写接口没有幂等声明：视为未完成，补声明和重复请求用例。
- 迁移脚本被修改：停止合并，补新迁移或恢复原文件；不得用 `--force` 绕过 checksum。
- 例外（例如某个历史接口暂时无法改响应形状）：写进本文件的“项目事实/例外”，并在 `tasks.md` 留迁移任务，不做口头豁免。
