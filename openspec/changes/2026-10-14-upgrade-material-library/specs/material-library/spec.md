# material-library Specification

## Purpose

规定教师和学生围绕材料库的新增行为：批量上传、索引进度、回收站、标签、版本、原文定位、阅读进度和收藏。所有场景都必须能通过 API、数据库、Go 测试或 Playwright 复现。

## ADDED Requirements

### Requirement: 批量上传与索引进度

教师 MUST 能通过 `POST /api/materials/batch` 以 `multipart/form-data` 提交 1 至 20 个文件，字段 `files` 可重复；可附带 `client_ids`（JSON 字符串数组，缺省时用 1 基序号）。单文件上限 `MAX_UPLOAD_BYTES`，总上限 20 MiB；0 个文件 400 `no_files`，超过 20 个 400 `too_many_files`，请求级失败无写入。每个文件独立校验和写入，一个失败不影响其他；全部失败仍返回 201，items 全部 `ok=false` 且无新增。响应 items 带 `client_id`、成功项 `id/title/version=1/index_status=pending`、失败项 `error`。索引状态为 `pending/indexing/ready/failed`，failed 带 `index_error`，前端每 2 秒轮询，教师可 reindex（202）。学生 403 且无残留。

#### Scenario: 一批文件独立完成

- **GIVEN** `teacher_a` 属于 A 班，准备 2 个合法 `.md` 和 1 个损坏的 PDF
- **WHEN** 调用 `POST /api/materials/batch`，字段 `files` 含这 3 个文件
- **THEN** 响应状态为 201，2 个 item 带 `id` 且 `index_status=pending`，1 个 item 为 `ok=false,error=invalid_file`
- **AND** `materials` 和 `material_versions` 各新增 2 行，上传目录新增 2 个文件
- **AND** 损坏 PDF 不留下文件或数据库行

#### Scenario: 索引状态按 2 秒轮询到 ready

- **GIVEN** 刚上传的材料 `index_status=pending`
- **WHEN** 前端每 2 秒请求一次 `GET /api/materials/{id}`
- **THEN** 首次响应为 `pending` 或 `indexing`，10 秒内出现 `ready`
- **AND** 列表和详情都显示「可检索」

#### Scenario: 索引失败与重试

- **GIVEN** `EMBEDDING_URL` 指向不可达地址
- **WHEN** 教师上传一份合法材料，随后恢复嵌入服务
- **THEN** 上传返回 201；随后 `index_status=failed`，`index_error` 非空
- **AND** 调用 `POST /api/materials/{id}/reindex` 返回 202，索引完成后状态变为 `ready`

#### Scenario: 单文件超限只失败该项

- **GIVEN** `teacher_a` 已登录，请求总大小不超过 20 MiB
- **WHEN** 批量提交一个合法文件和一份超过 `MAX_UPLOAD_BYTES` 的文件
- **THEN** 响应 201，超大文件 item 为 `ok=false,error=payload_too_large`
- **AND** 合法文件正常写入并进入索引，超大文件不留文件或数据库行

#### Scenario: 超过 20 个文件

- **GIVEN** `teacher_a` 已登录
- **WHEN** 批量提交 21 个文件
- **THEN** 响应状态为 400，`error=too_many_files`
- **AND** `materials`、`material_versions` 和上传目录均无新增

#### Scenario: 学生批量上传被拒绝

- **GIVEN** `student_a1` 已登录
- **WHEN** 调用 `POST /api/materials/batch`
- **THEN** 响应状态为 403，`error=forbidden`
- **AND** 没有文件落盘，没有数据库行

#### Scenario: 零文件被拒绝

- **GIVEN** `teacher_a` 已登录
- **WHEN** 调用 `POST /api/materials/batch`，字段 `files` 为空
- **THEN** 响应 400，`error=no_files`
- **AND** 材料表、版本表和上传目录都没有新增

#### Scenario: client_ids 数量不匹配

- **GIVEN** `teacher_a` 已登录
- **WHEN** 提交 2 个文件但 `client_ids` 只有 1 个
- **THEN** 响应 400，`error=invalid_request`
- **AND** 材料表、版本表和上传目录都没有新增

#### Scenario: 全部文件失败仍返回 201

- **GIVEN** `teacher_a` 已登录
- **WHEN** 批量提交两个都损坏的 PDF，`client_ids=["a","b"]`
- **THEN** 响应 201，两个 item 的 `client_id` 分别为 `a`/`b`，`ok=false`
- **AND** 材料表、版本表和上传目录都没有新增

### Requirement: 删除、撤销与回收站

本班教师 MUST 能软删除材料：DELETE 返回 204 并写 `deleted_at`；删除后学生所有读路径（列表、详情、文件、检索、问答、收藏、最近、快捷搜索）立即不可见，教师只在回收站看到。回收站可恢复：restore 接受 `{base_version}`，返回 200，清空 `deleted_at`；版本不是当前版本返回 409 `version_conflict`；未删除或已恢复材料返回 409 `not_deleted`。删除不取消在途索引，但不得重新可见；恢复返回删除前 `index_status`：ready 保持，pending/indexing 继续排队，failed 保持并需手动 reindex。purge 只在回收站：返回 204，清理文件、版本、知识条目正文、切片、向量、标签关联、阅读进度和收藏；取消排队/在途索引，worker 发现行不存在时丢弃新 generation，不写切片/向量；未删除材料 purge 返回 409 `not_deleted`；彻底删除后按 id 404；跨班/不存在同形 404；学生写接口 403。

#### Scenario: 删除立即隐藏

- **GIVEN** `teacher_a` 和 `student_a1` 同属 A 班，材料 id=1 对两人可见
- **WHEN** `teacher_a` 调用 `DELETE /api/materials/1`
- **THEN** 响应 204，`materials.deleted_at` 非空
- **AND** `student_a1` 的列表、详情、文件、`keyword` 检索和 `ask` 都不再出现 id=1
- **AND** `teacher_a` 的 `GET /api/trash` 含 id=1
- **AND** 再次 DELETE 返回 204，`deleted_at` 不变

#### Scenario: 十秒内撤销

- **GIVEN** 教师刚删除 id=1，页面显示撤销提示
- **WHEN** 在 10 秒内点击撤销
- **THEN** `POST /api/materials/1/restore` 返回 200，列表、检索和详情恢复
- **AND** `material_versions` 行数不变，`deleted_at` 为空
- **AND** 10 秒后提示消失，但回收站仍可恢复

#### Scenario: 恢复保留版本

- **GIVEN** id=1 有 3 个版本、2 个标签、1 条阅读进度
- **WHEN** 教师从回收站恢复
- **THEN** 3 个版本、2 个标签和该学生的阅读进度都仍存在
- **AND** `current_version` 不变，索引状态保持恢复前的值

#### Scenario: 彻底删除清理关联数据

- **GIVEN** 回收站中的 id=1 有文件、3 个版本、切片和向量
- **WHEN** 教师调用 `DELETE /api/materials/1/purge`
- **THEN** 响应 204；文件、`materials`、`material_versions`、`knowledge_chunks` 和 Qdrant 点都不存在
- **AND** 教师和学生按 id 访问都是 404

#### Scenario: 索引中彻底删除不复活

- **GIVEN** 材料 id=1 正在 `indexing`
- **WHEN** 教师先删除再 purge
- **THEN** 在途 worker 丢弃本次新 generation，不写切片或向量
- **AND** 教师和学生按 id 访问都是 404

#### Scenario: 未删除材料不能彻底删除

- **GIVEN** 材料 id=1 未删除，仍有文件、版本和切片
- **WHEN** 教师调用 `DELETE /api/materials/1/purge`
- **THEN** 响应 409，`error=not_deleted`
- **AND** 文件、版本、切片和向量都不变，`deleted_at` 仍为空

#### Scenario: 学生删除被拒绝

- **GIVEN** `student_a1` 已登录
- **WHEN** 调用 `DELETE /api/materials/1`
- **THEN** 响应 403，`error=forbidden`
- **AND** `deleted_at` 仍为空，列表和检索不变

#### Scenario: 跨班删除同形 404

- **GIVEN** `teacher_b` 属于 B 班，A 班材料 id=1
- **WHEN** 调用 `DELETE /api/materials/1`
- **THEN** 响应 404，响应体与删除不存在的 id 相同
- **AND** A 班材料的 `deleted_at` 仍为空

#### Scenario: 未删除或重复恢复被拒绝

- **GIVEN** 材料 id=1 未删除；另一份材料 id=2 已删除并已恢复
- **WHEN** 教师分别对 id=1 和 id=2 调用 restore，`base_version` 都等于当前版本
- **THEN** 两个响应都是 409，`error=not_deleted`
- **AND** 两份材料的 `deleted_at` 仍为空，版本行不变

#### Scenario: 删除中的索引不重新可见

- **GIVEN** 材料 id=1 正在 `indexing`，学生可见
- **WHEN** 教师删除 id=1，后台索引随后完成
- **THEN** 学生列表、详情、文件和检索始终看不到 id=1
- **AND** 教师回收站能看到 id=1；恢复后 `ready` 保持 ready、`pending`/`indexing` 继续排队、`failed` 保持 failed 需手动 reindex

### Requirement: 标签、重命名、排序和分页

本班教师 MUST 能通过 `PATCH /api/materials/{id}` 重命名材料并设置标签。请求体 `{title?, tags?}`；省略字段不变，`tags` 整体替换，`[]` 清空。`title` 1–255 字符，空或超长 400 `invalid_request`；标签 1–32 字符、每材料最多 10 个、同名复用，非法 400 `invalid_tag`。`GET /api/materials` 支持 `q/tag/sort/page/page_size`（默认 20，最大 100）；`q` 对标题和正文做大小写不敏感子串匹配，`sort` 只允许白名单值，默认 `created_desc`，非法 `sort` 或分页返回 400 `invalid_pagination`；响应含 `items/page/page_size/total`，同值按 `id DESC` 兜底；请求 `class_id` 忽略。学生只读，PATCH 403；非法分页 400 `invalid_pagination`，不修改数据。

#### Scenario: 标签筛选、排序与分页

- **GIVEN** A 班有 25 份未删除材料，其中 12 份标签为「第一章」；B 班有 5 份
- **WHEN** `teacher_a` 请求 `GET /api/materials?tag=第一章&sort=title_asc&page=2&page_size=10&class_id=<B班id>`
- **THEN** 响应 200，`total=12`，`items` 为 2 条，全部属于 A 班且标签为「第一章」
- **AND** 按标题升序排列，同标题按 id 降序；不含 B 班标题

#### Scenario: 非法分页

- **GIVEN** 已登录用户
- **WHEN** 请求 `page_size=101` 或 `page=0`
- **THEN** 响应 400，`error=invalid_pagination`
- **AND** 响应不含材料数据

#### Scenario: 重命名与标签

- **GIVEN** `teacher_a` 已登录，本班材料 id=1
- **WHEN** PATCH `{"title":"第一章讲义","tags":["第一章","实验"]}`
- **THEN** 响应 200，详情中的标题和标签更新
- **AND** 本班同名标签只保留一行
- **AND** 重命名不生成新版本，不触发重新索引

#### Scenario: 学生修改被拒绝

- **GIVEN** `student_a1` 已登录
- **WHEN** PATCH `/api/materials/1` 提交新标题或标签
- **THEN** 响应 403，标题和标签不变
- **AND** `material_versions` 不新增

#### Scenario: 跨班修改同形 404

- **GIVEN** `teacher_b` 属于 B 班，A 班材料 id=1
- **WHEN** PATCH `/api/materials/1`
- **THEN** 响应 404，响应体与 PATCH 不存在的 id 相同
- **AND** A 班材料的标题和标签不变

#### Scenario: 标签边界

- **GIVEN** `teacher_a` 已登录
- **WHEN** 提交长度为 33 的标签，或给一份材料提交 11 个标签
- **THEN** 响应 400，`error=invalid_tag`
- **AND** 标签表和关联表都不新增

#### Scenario: 部分更新与清空标签

- **GIVEN** 材料 id=1 的标题为「旧标题」，标签为 `["第一章","实验"]`
- **WHEN** PATCH 只提交 `{"tags":["第一章"]}`，再提交 `{"tags":[]}`
- **THEN** 第一次后标题仍为「旧标题」，标签只剩「第一章」
- **AND** 第二次后标签为空，标题不变
- **AND** 两次都不生成新版本，不触发重新索引

### Requirement: 在线编辑正文

本班教师 MUST 能编辑 `.txt` 和 `.md` 正文：`PUT /api/materials/{id}/content`，请求体为 `{body, change_note, base_version}`；`body` 上限 `MAX_UPLOAD_BYTES`，`change_note` 上限 200 字符。每次保存 MUST 在 `material_versions` 追加一行并把 `current_version` 加 1，MUST NOT 改写旧版本；随后 MUST 排队后台索引。`base_version` 不等于当前版本时 MUST 返回 409 `version_conflict`，响应含 `current_version` 和最新 `body`，MUST NOT 写入新版本。非 `.txt` 或 `.md` 材料调用本接口 MUST 返回 400 `not_editable`。学生调用 MUST 返回 403；跨班或不存在 id MUST 返回同形 404。

#### Scenario: 编辑生成新版本并重建索引

- **GIVEN** `teacher_a` 已登录，材料 id=1 的 `current_version=1`，正文含「旧内容」
- **WHEN** `PUT /api/materials/1/content` 提交 `{body:"新内容", change_note:"改错字", base_version:1}`
- **THEN** 响应 200，`current_version=2`
- **AND** `material_versions` 有 v1、v2，v1 正文仍含「旧内容」
- **AND** `index_status=pending`；ready 后 `keyword` 检索「新内容」命中，检索「旧内容」不命中

#### Scenario: 并发编辑冲突

- **GIVEN** 两个浏览器窗口都以 `base_version=1` 打开同一份材料
- **WHEN** 窗口 A 保存成功，窗口 B 随后保存
- **THEN** 窗口 B 得到 409，响应含 `error=version_conflict`、`current_version=2` 和最新正文
- **AND** v2 内容仍是 A 的正文，没有被覆盖
- **AND** B 以 `base_version=2` 重新提交后成功生成 v3

#### Scenario: 学生编辑被拒绝

- **GIVEN** `student_a1` 已登录
- **WHEN** 调用 `PUT /api/materials/1/content` 或 `POST /api/materials/1/file`
- **THEN** 响应 403，`error=forbidden`
- **AND** `material_versions` 行数不变，`current_version` 不变

#### Scenario: 跨班编辑同形 404

- **GIVEN** `teacher_b` 属于 B 班，A 班材料 id=1
- **WHEN** `PUT /api/materials/1/content`
- **THEN** 响应 404，响应体与不存在的 id 相同
- **AND** A 班版本表不变

#### Scenario: 非文本格式不可直接编辑

- **GIVEN** 材料 id=1 的 `file_type=pdf`
- **WHEN** `PUT /api/materials/1/content`
- **THEN** 响应 400，`error=not_editable`
- **AND** `current_version` 和版本表不变

### Requirement: 版本历史与恢复

教师 MUST 能通过 `GET /api/materials/{id}/versions` 列出全部版本、`GET .../versions/{v}` 读取任一版本、`GET .../versions/{v}/file` 下载二进制版本、在前端比较任意两版，并通过 `POST .../versions/{v}/restore` 恢复任一版本。版本行只追加，不得被后续编辑、替换或恢复改写。恢复请求 `{base_version}`；不是当前版本返回 409 `version_conflict`，成功生成新版本并把 `current_version` 加 1，随后排队索引。版本文件下载只支持 PDF/DOCX/PPTX，用 `Content-Disposition: attachment`；`.txt/.md` 调用 MUST 返回 400 `not_replaceable`，正文用 `GET .../versions/{v}`；跨班、非法版本或不存在版本同形 404。学生访问版本列表/详情/文件 MUST 返回 403，写接口同样 403。

#### Scenario: 恢复不改写历史

- **GIVEN** 材料已有 v1、v2、v3
- **WHEN** 教师以 `base_version=3` 恢复 v1
- **THEN** 响应 200，新增 v4，正文等于 v1
- **AND** v1、v2、v3 的内容不变
- **AND** `index_status=pending`，ready 后可检索 v1 的内容

#### Scenario: 版本列表与差异

- **GIVEN** 材料已有 v1、v2、v3
- **WHEN** 调用 `GET /api/materials/1/versions`，并在前端选择 v1 与 v3
- **THEN** 响应 200，返回 3 条元数据（版本号、类型、编辑人、修改说明、时间）
- **AND** 前端差异视图列出新增和删除行，不修改任何版本
- **AND** PDF/DOCX/PPTX 的版本比较只显示元数据和文件下载，不做文本 diff

#### Scenario: 读取旧版本文件

- **GIVEN** PDF 材料 id=1 有 v1、v2 两个版本
- **WHEN** 教师请求 `GET /api/materials/1/versions/1/file`
- **THEN** 响应 200，`Content-Disposition` 以 `attachment` 开头，内容是 v1 文件
- **AND** 请求不存在的 v3 返回 404；对 `.md` 版本调用该接口返回 400 `not_replaceable`

#### Scenario: 学生不能读版本

- **GIVEN** `student_a1` 已登录，本班材料 id=1 有版本
- **WHEN** 请求版本列表、版本详情或版本文件
- **THEN** 每个响应都是 403，`error=forbidden`
- **AND** 不返回版本正文、文件或修改说明

### Requirement: 文件替换

本班教师 MUST 能替换 PDF、DOCX、PPTX 材料文件：`POST /api/materials/{id}/file`，字段为 `file`、`change_note`、`base_version`。抽取和校验规则 MUST 与上传相同；替换文件 MUST 与当前 `file_type` 相同，不同时 MUST 返回 400 `type_mismatch`。成功后 MUST 追加新版本、把 `current_version` 加 1，并排队后台索引。`base_version` 不是当前版本时 MUST 返回 409 `version_conflict`。对 `.txt` 或 `.md` 调用 MUST 返回 400 `not_replaceable`，文本材料 MUST 走 `PUT content`。替换失败 MUST 保留旧文件、旧正文和旧版本，MUST NOT 新增版本。学生调用 MUST 返回 403；跨班或不存在 id MUST 返回同形 404。

#### Scenario: 替换成功生成新版本

- **GIVEN** 材料 id=1 为 PDF，`current_version=1`，v1 文件可下载
- **WHEN** `POST /api/materials/1/file` 上传一份合法 PDF，`base_version=1`
- **THEN** 响应 200，`current_version=2`，`material_versions` 新增 v2
- **AND** v1 文件仍可读取，`index_status=pending`
- **AND** ready 后检索命中新 PDF 的正文

#### Scenario: 替换失败保留旧数据

- **GIVEN** 材料 id=1 为 PDF，v1 可用
- **WHEN** `POST /api/materials/1/file` 上传一个损坏 PDF，`base_version=1`
- **THEN** 响应 400，`error=invalid_file`
- **AND** 旧文件、`knowledge_entries.body` 和 v1 都保留
- **AND** 不新增 v2，`current_version` 仍为 1

#### Scenario: 文本格式不走文件替换

- **GIVEN** 材料 id=1 为 `.md`，`current_version=1`
- **WHEN** `POST /api/materials/1/file` 上传一个 `.md` 文件，`base_version=1`
- **THEN** 响应 400，`error=not_replaceable`
- **AND** `current_version` 和版本表不变，响应提示改用 `PUT /api/materials/1/content`

#### Scenario: 替换文件类型必须一致

- **GIVEN** 材料 id=1 为 PDF，`current_version=1`
- **WHEN** `POST /api/materials/1/file` 上传一个 `.docx` 文件，`base_version=1`
- **THEN** 响应 400，`error=type_mismatch`
- **AND** 旧文件、旧正文、v1 和 `current_version` 都不变


### Requirement: 原文大纲与引用定位

材料详情 `GET /api/materials/{id}` MUST 返回 `outline`：Markdown ATX 标题（`#` 至 `######`）的 `level`、`text` 和原文码点 `offset`，按出现顺序排列。检索和问答引用 MUST 携带 `material_id`、`version`、`start`、`end`、`excerpt`，PDF 或 PPT 另带 `page` 或 `slide`；`start` 含、`end` 不含，单位是当前版本正文的 Unicode 码点。前端 MUST 按码点切片并滚动到对应位置高亮，MUST NOT 用切片 id 猜测位置。引用版本小于 `current_version` 时 MUST 显示「原文已更新」和引用当时的 `excerpt`，并提供打开当前版本的入口；范围超出当前正文时 MUST 只显示摘录，MUST NOT 报 500。前端 MUST 显示「切片 n · 第 p 页」或「切片 n · 第 s 张」。

#### Scenario: 大纲与跳转

- **GIVEN** 材料正文含 `# 第一章`、`## 1.1 函数`、`### 例题`
- **WHEN** 调用材料详情并点击大纲中的「1.1 函数」
- **THEN** `outline` 含 3 项，level 分别为 1、2、3，offset 指向标题起始码点
- **AND** 页面滚动到该标题；刷新后仍能通过大纲再次定位

#### Scenario: 引用按码点高亮

- **GIVEN** 正文为「😀😀单调递增」，引用为 `start=2,end=6`
- **WHEN** 从检索命中打开详情
- **THEN** 高亮「单调递增」四个字符，不因 emoji 的 UTF-16 长度而偏移
- **AND** 页面显示切片序号；若为 PDF 则显示页码

#### Scenario: 旧版本引用提示

- **GIVEN** 引用基于 v1，材料当前为 v2
- **WHEN** 打开该引用
- **THEN** 显示「原文已更新」和 v1 的 `excerpt`
- **AND** 提供「打开当前版本」入口，不把 v1 的偏移直接套到 v2 上高亮

#### Scenario: 越界范围

- **GIVEN** 引用为 `start=100,end=200`，当前正文只有 50 个码点
- **WHEN** 打开详情
- **THEN** 页面正常渲染并显示摘录，不高亮，不出现 500
- **AND** 不修改材料或版本数据

### Requirement: 阅读进度与收藏

学生 MUST 能通过 `PUT /api/materials/{id}/progress` 记录 `{version,position,completed}`；`version` 必须等于 `current_version`，否则 409 `version_conflict`；`position` 为 0 至正文码点长度，越界 400 `invalid_position`；`completed` 原样保存。`GET .../progress` 读取自己的进度；无记录返回默认值，记录版本落后时返回截断到当前长度的 stale 记录，下一次 PUT 覆盖。服务端只从会话取 `user_id`，按 `(user_id,material_id)` 唯一保存；前端滚动停止 2 秒后最多上报一次。学生可通过 `PUT`/`DELETE /api/materials/{id}/favorite` 收藏，并通过 `GET /api/favorites` 查看。教师只看自己的记录；跨班、他人私有或不存在 id 同形 404。

#### Scenario: 阅读位置恢复

- **GIVEN** `student_a1` 打开材料 id=1，正文有 2000 个码点
- **WHEN** 滚动到 position=1200，停止 2 秒后前端上报，然后关闭并重新打开
- **THEN** `PUT` 返回 204，`material_reads` 只有一行 `(student_a1, 1)`
- **AND** 重新打开时滚动到约 1200；2 秒内多次滚动只产生 1 次请求

#### Scenario: 用户之间不共享进度

- **GIVEN** `student_a1` 和 `student_a2` 同属 A 班
- **WHEN** `student_a1` 在 id=1 记录 position=1200
- **THEN** `student_a2` 打开 id=1 时 position 为 0 或自己的记录
- **AND** `student_a2` 的 PUT 不覆盖 `student_a1` 的行

#### Scenario: 收藏与取消

- **GIVEN** `student_a1` 已登录
- **WHEN** `PUT` favorite，然后 `GET /api/favorites`，再 `DELETE` favorite
- **THEN** 第一次返回 204，收藏列表含 id=1，DELETE 后列表为空
- **AND** 重复 PUT 仍返回 204，不产生重复行

#### Scenario: 客户端伪造 user_id 被忽略

- **GIVEN** `student_a1` 已登录
- **WHEN** `PUT` progress 请求体附带 `user_id: 999`
- **THEN** 只写入 `student_a1` 的行，999 没有记录
- **AND** 响应不返回其他用户数据

#### Scenario: 私有数据同形 404

- **GIVEN** A 班用户、B 班材料 id=99、A 班已删除材料 id=98、永不存在的 id=1000
- **WHEN** 分别请求这三个 id 的详情、progress 和 favorite
- **THEN** 所有请求的响应状态都是 404，响应体逐字节相同
- **AND** 响应不含标题、用户名、路径或资源是否存在的信息
- **AND** 请求体或查询参数附带 `user_id=<他人>` 不改变当前会话用户的结果

#### Scenario: 无进度与旧版本进度

- **GIVEN** `student_a1` 对 id=1 没有进度；id=2 有 version=1、position=500 的记录，当前版本已到 2、正文 300 个码点
- **WHEN** 学生 GET 两个材料的 progress
- **THEN** id=1 返回 200 `{version:2,position:0,completed:false,updated_at:null}`
- **AND** id=2 返回 200 `{version:1,position:300,completed:false,stale:true}`
- **AND** 下一次 PUT 覆盖旧记录

#### Scenario: 教师只看到自己的

- **GIVEN** `teacher_a` 和 `student_a1` 同属 A 班，`student_a1` 有阅读记录
- **WHEN** `teacher_a` 请求自己的 progress 和 favorites
- **THEN** 只返回 `teacher_a` 自己的记录，或空列表
- **AND** 不存在按学生 id 查询其进度的接口

#### Scenario: 版本和位置边界

- **GIVEN** 材料 id=1 的 `current_version=2`，正文 100 个码点
- **WHEN** 学生 PUT `{version:1,position:10,completed:false}`，再 PUT `{version:2,position:101,completed:false}`
- **THEN** 第一次返回 409 `version_conflict`
- **AND** 第二次返回 400 `invalid_position`
- **AND** `material_reads` 没有新增或更新

### Requirement: 统一错误形状与权限边界

本 change 新增的所有按 id 资源（版本、回收站、阅读进度、收藏、索引状态）MUST 先读出完整行，再校验会话班级和用户归属。跨班、不存在、非法 id，以及已删除材料对普通读接口，MUST 返回完全相同的 404：状态码、`Content-Type`、响应体 `{"error":"not_found"}` 逐字节一致；除 `X-Request-ID`、`Date` 等每请求变化的值外，响应头一致；教师回收站列表和 material restore 是显式例外；已删除材料的版本 restore 返回 404。同班他人的进度和收藏 MUST NOT 通过任何 id 或查询参数读取，接口只使用会话 `user_id`。先校验角色和路由，再按 id 取行：学生调用教师写接口 MUST 一律返回 403，即使 id 跨班或不存在；对教师，跨班、不存在、已删除和非法 id 同形 404。服务端日志 MAY 区分越权与不存在，但响应 MUST NOT 泄露资源是否存在。所有新接口 MUST 忽略请求中的 `class_id` 和 `user_id` 字段。

#### Scenario: 新资源统一 404

- **GIVEN** A 班教师、B 班材料 id=99、不存在的 id=1000
- **WHEN** 分别请求 id=99 的版本列表、restore、progress、favorite，以及 id=1000 的详情
- **THEN** 每个请求的响应状态、响应头和 body 都相同：404 加 `{"error":"not_found"}`
- **AND** 响应不出现「forbidden」「cross-class」等可区分文案

#### Scenario: 非法 id

- **GIVEN** 已登录用户
- **WHEN** 请求 `/api/materials/abc`、`/api/materials/-1` 和 `/api/materials/0`
- **THEN** 三次都是同形 404，不是 400 或 500
- **AND** 不执行任何数据库写入

#### Scenario: 学生调用教师写接口

- **GIVEN** `student_a1` 已登录
- **WHEN** 依次调用 PATCH、DELETE、restore、purge、`PUT content`、`POST file` 和 reindex
- **THEN** 每个请求都返回 403 和 `{"error":"forbidden"}`
- **AND** 材料、版本、切片和标签行数都不变
