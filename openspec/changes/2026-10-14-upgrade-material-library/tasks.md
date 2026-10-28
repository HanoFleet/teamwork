# 2026-10-14-upgrade-material-library — 任务清单

> **执行顺序**：按编号。第 0 组是基线，必须先完成；没有可启动的基线和通过的现有验收，不写业务代码。
> **勾选规则**：只有角色二完成实现、角色三按该条 `verify` 复现通过后，才能勾选。角色一不得用“代码已写”替代验收证据。
> **分支与提交**：分支 `change/2026-10-14-upgrade-material-library`；提交信息格式 `<type>(material-library): <task-id> <一句话>`，例如 `feat(material-library): 2.4 上传写入 v1 并异步索引`。
> **规约校验**：`npx -y @fission-ai/openspec@1.15.0 validate 2026-10-14-upgrade-material-library --strict`。
> **实现约束**：没有写进本 change delta 的行为不实现；规约含糊时先改 delta，再改代码。

## 0. 基线（骨架优先）

- [ ] **0.1 确认现有骨架可启动** — 涉及：`archive/campusclaw-baseline.zip`、`archive/README.md`。从干净克隆解压归档（或 `git checkout v2.0.0-baseline`），按包内 README 复制 `.env` 并填好变量，执行 `docker compose up --build -d`；记录 commit、`/health` 响应和 `python3 scripts/verify.py` 的基线结果。verify: `curl -fsS http://localhost:8080/health` 返回 200；`python3 scripts/verify.py` 通过。
- [ ] **0.2 建立规约校验入口** — 涉及：`openspec/changes/2026-10-14-upgrade-material-library/`。在干净环境执行 `npx -y @fission-ai/openspec@1.15.0 validate 2026-10-14-upgrade-material-library --strict`。verify: 退出码 0，输出 `Change '2026-10-14-upgrade-material-library' is valid`。
- [ ] **0.3 创建变更分支并保护基线** — 涉及：Git。从 `main` 建 `change/2026-10-14-upgrade-material-library`；不在 `main` 上直接改。verify: `git branch --show-current` 输出分支名；`git log --oneline -1` 是基线 commit。
- [ ] **0.4 跑工程规范自查** — 涉及：`docs/standards/`、`AGENTS.md`、`.cursor/rules/`。执行 `python3 scripts/standards_check.py`，确认八类规范文件、规则入口和检查列齐备。verify: 退出码 0；输出八类规范名称和检查项数量。

## 1. 迁移与配置底座

- [ ] **1.1 实现迁移执行器** — 涉及：`backend/internal/db/migrate.go`（新增）。启动时按版本号排序读取 `migrations/*.sql`，计算 SHA-256，已记录版本跳过，校验和不一致返回错误；在监听端口前执行。verify: `go test ./internal/db/...`；人为改坏 `0002` 后启动，进程非零退出且日志含 checksum。
- [ ] **1.2 固化迁移 0001** — 涉及：`backend/internal/db/migrations/0001_baseline.sql`（新增）、`db.go`。把现有 `CREATE TABLE IF NOT EXISTS` 原样搬入；替换 `db.Migrate` 为迁移执行器；保留 `Seed`。verify: 空库启动后 `schema_migrations` 有 `0001`；三个预置账号和两份预置材料存在。
- [ ] **1.3 增加迁移 0002** — 涉及：`0002_material_library.sql`（新增）。按 `design.md` 第 5 节增加 `materials` 列（含 `updated_at`）、`material_versions`、`knowledge_entries.version/page_table`、`knowledge_chunks.generation/start_page/end_page`、`tags`、`material_tags`、`material_reads`、`favorites`、`login_failures` 及索引。verify: `SHOW CREATE TABLE` 与 `DESCRIBE` 含全部字段；重复启动不重复执行。
- [ ] **1.4 回填旧数据** — 涉及：`0002` 或 `0003_backfill.sql`、`db.Seed`。为已有材料插入 v1 版本，`body` 取现有 `knowledge_entries.body`，`file_type` 按 `original_ext` 映射；旧切片置 `generation=0`，材料置 `pending`。verify: 旧库升级后每份材料恰有一条 v1；旧切片仍在且 `generation=0`；材料状态为 pending。
- [ ] **1.5 配置 `EMBEDDING_DIM`** — 涉及：`backend/internal/config/config.go`、`.env.example`、`docker-compose.yml`、`backend/internal/embed/embed.go`、`backend/internal/qdrant/client.go`。必填、1 至 4096；本地嵌入输出该维度；Qdrant 集合名 `campusclaw_<dim>`。verify: 缺变量启动失败；`EMBEDDING_DIM=768` 时集合名和向量长度都是 768；`go test ./internal/embed/...` 通过。
- [ ] **1.6 登录失败计数落库和可信 IP** — 涉及：`backend/internal/auth/limiter.go`、`backend/internal/httpapi/auth.go`、`backend/internal/httpapi/server.go`、`frontend/nginx.conf`。删除内存计数，读写 `login_failures`；Nginx 覆盖 `X-Real-IP`；Go 只在直接对端属于可信私网时采用，否则用连接地址；成功后清计数，锁定到期后重置。verify: 重启 api 后仍锁定；伪造 `X-Forwarded-For` 5 次后正确口令仍 401；`login_failures` 只有真实 IP 一行。
- [ ] **1.7 结构化日志与请求 ID** — 涉及：`backend/internal/httpapi/server.go`、`cmd/server/main.go`、新增 `internal/logging/`。stdout 单行 JSON；字段 `ts/level/msg/request_id`，请求日志加 `method/path/status/duration_ms`，可用时加 `class_id/user_id`；`X-Request-ID` 合法则沿用，否则生成 UUIDv4 并回写；过滤口令、令牌、Cookie、正文、路径和 DSN。verify: 请求带/不带 `X-Request-ID` 各一次，响应头和日志的 id 一致；日志可被 `jq` 解析；库停时日志 `status=503` 且不含 DSN。
- [ ] **1.8 存活/就绪检查与优雅停机** — 涉及：`backend/internal/httpapi/server.go`、`cmd/server/main.go`、`backend/internal/config/config.go`。`/health` 返回 `{status,version,time}` 且不访问依赖；`/ready` 检查 MySQL ping、Qdrant 可达、`EMBEDDING_DIM` 有效，失败 503 并给 `checks`；SIGTERM 后停止接新连接，最多等 10 秒。verify: 停 db 时 `/health` 200、`/ready` 503 `db=false`；停 Qdrant 时 `qdrant=false`；SIGTERM 时在途请求完成且进程 0 退出。

## 2. 文件抽取与上传

- [ ] **2.1 建立 `extract` 包与文件头校验** — 涉及：`backend/internal/extract/`（新增）。扩展名白名单 `.txt/.md/.pdf/.docx/.pptx`；PDF 必须 `%PDF-`；DOCX/PPTX 必须是合法 ZIP，条目不超过 2000、解压后不超过 100 MiB；txt/md 必须 UTF-8。verify: `go test ./internal/extract/...` 覆盖合法样本、伪造 PDF、非法 ZIP、超大条目、非 UTF-8。
- [ ] **2.2 实现 PDF 抽取** — 涉及：`extract/pdf.go`。调用 `pdftotext`，超时 10 秒、正文不超过 2,000,000 字符；记录每页起止码点；扫描件、加密、损坏返回可读错误。verify: 3 页样本的 `page_table` 有 3 项；扫描件返回 `scanned_pdf`；超时返回 `extract_timeout`。
- [ ] **2.3 实现 DOCX/PPTX 抽取** — 涉及：`extract/docx.go`、`extract/pptx.go`。用 `archive/zip` 和 `encoding/xml` 读取；DOCX 标题样式转 Markdown 标题；PPTX 记录每张幻灯片起止码点。verify: DOCX 样本的标题以 `#` 开头；PPTX 样本 `page_table` 用 `slide` 键；损坏文件返回 `invalid_archive`。
- [ ] **2.4 上传写入 v1 并异步入队** — 涉及：`backend/internal/httpapi/materials.go`、`backend/internal/library/`。上传请求完成校验、抽取、文件写入，并在事务中写 `materials`、`material_versions` v1、`knowledge_entries`；提交后入队并立即返回 201 `{id,title,version:1,index_status:"pending"}`；失败清理文件和事务。verify: 上传响应在 1 秒内返回（PDF 抽取时间除外）；库里有一份材料和 v1；嵌入关闭时材料行、版本和文件保留，状态最终 failed 并可重试。
- [ ] **2.5 实现批量上传** — 涉及：`httpapi/materials.go`、`httpapi/server.go`。新增 `POST /api/materials/batch`，字段 `files`；1 至 20 个文件，总大小不超过 20 MiB；逐文件校验和写入，一个失败不影响其他；响应 `items[]` 带 `client_id/ok/id/title/version/index_status/error`。verify: 2 个合法 + 1 个损坏 PDF 返回 201，2 个成功、1 个 `invalid_file`；21 个文件返回 400 `too_many_files`。
- [ ] **2.6 统一上传错误与无残留断言** — 涉及：`httpapi/materials.go`、`library/`。把 400/403/413/503 映射为固定 `error` code；超限返回 413；扫描件、伪造头、加密/损坏 Office、事务失败都不留文件或行。verify: `verify.py` 的上传失败场景逐条通过；数据库行数和上传目录文件数在失败前后相同。

## 3. 后台索引与原文定位

- [ ] **3.1 实现索引队列与状态机** — 涉及：`backend/internal/indexer/`（新增）、`httpapi/materials.go`、`retrieval/index.go`。进程内队列；上传/编辑/替换/恢复/reindex 置 `pending`；worker 置 `indexing`；成功 `ready`，失败 `failed` + `index_error`；启动时 `pending/indexing` 重新排队；同一材料只允许一个 worker。verify: 上传后状态先 pending/indexing，最终 ready；断开嵌入后 failed；恢复服务后 reindex 返回 202 并 ready；重启后 pending 材料继续索引。
- [ ] **3.2 实现 generation 先建后换** — 涉及：`retrieval/index.go`、`library/`。新切片写新 generation；全部 ready 后在事务里切换 `materials.current_generation`、删除旧切片、最后删旧向量；失败只清理新 generation。verify: 重建期间旧 generation 检索可用；成功后旧切片/向量不存在；注入失败后旧 generation 仍 ready。
- [ ] **3.3 实现原文码点映射和页码** — 涉及：`backend/internal/chunk/`、`extract/`、`retrieval/index.go`。预处理保留到原文的映射；切片 `start/end` 落原文码点；PDF/PPT 计算 `start_page/end_page`。verify: 含 emoji 的单测切出的文本与原文一致；PDF 命中的 page 与 `page_table` 一致。
- [ ] **3.4 引用带版本、区间和页码** — 涉及：`retrieval/service.go`、`httpapi/search.go`、`httpapi/ask.go`。命中增加 `version`、`start`、`end`、`page/slide`、`excerpt`；引用不使用 `chunk_id` 作为长期标识。verify: `verify.py` 检查字段；材料编辑后旧引用仍返回旧 excerpt 和 version；新引用使用当前 version。
- [ ] **3.5 检索只读当前 generation** — 涉及：`retrieval/service.go`、`retrieval/index.go`。关键字 SQL 和 Qdrant 过滤都带 `class_id` 和 `current_generation`，只读 `ready` 切片；`vector` 阈值 0.35，`hybrid` RRF k=60。verify: 旧 generation 不进入结果；pending/failed 切片不参与；Qdrant 停止时 keyword 200、vector/hybrid 503。

## 4. 材料库业务

- [ ] **4.1 软删除、回收站、恢复和彻底删除** — 涉及：`backend/internal/library/trash.go`（新增）、`httpapi/materials.go`。`DELETE` 写 `deleted_at`；列表/详情/文件/检索/问答排除已删除；教师 `GET /api/trash`；restore 清空 `deleted_at`；purge 只接受已删除材料，删除文件、版本、切片、向量和标签关联，未删除返回 409。verify: 删除后学生五条读路径都不可见；恢复保留版本；purge 后按 id 404，未删除 purge 返回 409；学生写接口 403。
- [ ] **4.2 标签、重命名、排序和分页** — 涉及：`library/library.go`、`httpapi/materials.go`。`PATCH` 标题 1 至 255、标签 1 至 32、每材料最多 10 个、同名复用；列表支持 `q/tag/sort/page/page_size`，默认 20、最大 100，响应含 `total`，同值按 id 降序。verify: 25 份材料、标签筛选、第 2 页和标题排序结果稳定；`page_size=101` 返回 400；学生 PATCH 403。
- [ ] **4.3 在线编辑、409 冲突和版本历史** — 涉及：`library/versions.go`、`httpapi/materials.go`。`PUT content` 带 `body/change_note/base_version`；事务内比对 `current_version`，不一致 409 带最新正文；每次成功追加版本并置 pending；版本列表、单版本读取、恢复接口。verify: v1 保存成功生成 v2；两个窗口并发时后者 409；恢复 v1 生成 v4 且 v1-v3 不变；非文本格式 400。
- [ ] **4.4 文件替换** — 涉及：`library/versions.go`、`httpapi/materials.go`。`POST file` 复用抽取和校验；只接受与当前 `file_type` 相同的 PDF/DOCX/PPTX；成功追加版本、置 pending；失败保留旧文件/正文/版本；文本格式返回 400；`base_version` 冲突 409。verify: 合法 PDF 替换生成 v2 且旧文件仍可读；损坏 PDF 返回 400 且 v1 不变；`.md` 和类型不一致都返回 400；学生 403。
- [ ] **4.5 大纲和引用定位数据** — 涉及：`library/outline.go`、`httpapi/materials.go`。详情返回 Markdown ATX 标题的 `level/text/offset`；引用进入详情时按 `version/start/end` 定位；旧版本显示“原文已更新”和旧 excerpt；越界只显示摘录。verify: 大纲 3 项 level 正确；emoji 前后的引用高亮正确；旧版本和越界场景不 500。
- [ ] **4.6 阅读进度、收藏和最近阅读** — 涉及：`library/reading.go`、`httpapi/materials.go`。`PUT/GET progress`、`PUT/DELETE favorite`、`GET favorites`、`GET recent`；`user_id` 只来自会话；`(user_id, material_id)` 唯一；前端滚动停止 2 秒后上报。verify: 重新打开回到 1200；两个学生互不覆盖；重复收藏不重复；伪造 `user_id` 被忽略；跨班/他人/不存在同形 404。
- [ ] **4.7 统一 404 和 403** — 涉及：`httpapi/` 所有新 handler。按 id 先整行读出再校验班级和归属；跨班、同班他人私有、已删除、非法 id 返回相同 404；学生写接口 403；日志可区分，响应不可区分。verify: `verify.py` 对每类新资源比较状态、头和 body；进度和收藏的伪造 `user_id` 不生效；非法 id `abc/-1/0` 都是 404。

## 5. 前端壳层与材料库页面

- [ ] **5.1 拆分 `App.tsx` 并建立路由** — 涉及：`frontend/src/App.tsx`、`frontend/src/pages/`、`frontend/src/components/`、`frontend/src/main.tsx`。拆出首页、材料、材料详情、编辑、版本、回收站、问答、设置；路由进入 URL；现有登录、主题、材料列表行为不变。verify: `npm run build` 通过；深链 `/materials/1/versions` 刷新可打开；未登录回登录页。
- [ ] **5.2 实现响应式导航和主题** — 涉及：`components/`、`styles.css`。把现有 800px 媒体查询改为 768px；桌面 ≥768px 左栏；窄屏 <768px 底栏；教师多回收站；学习路径/作业/练习/通知/班级管理禁用且不注册路由；保留北大红、深浅主题、键盘焦点。verify: Playwright 1440×900 和 390×844 各截图/断言一次；Tab 可达全部可用项。
- [ ] **5.3 材料列表、标签、分页和状态** — 涉及：`pages/Materials.tsx`、`components/`。列表显示标题、时间、标签、`index_status`、已读/未读；标签筛选、排序、分页；pending/indexing 每 2 秒刷新，failed 显示原因和重试。verify: Playwright 上传后状态从 pending 到 ready；分页和标签筛选结果与 API 一致。
- [ ] **5.4 批量上传队列** — 涉及：`pages/Materials.tsx`、`components/UploadQueue.tsx`。拖拽多文件；逐文件显示上传中/索引中/可检索/失败和原因；失败可重试；一个失败不影响其他。verify: Playwright 一次拖入 2 个合法 + 1 个损坏 PDF，三个状态分别正确。
- [ ] **5.5 材料详情、大纲和高亮** — 涉及：`pages/MaterialDetail.tsx`、`components/Outline.tsx`、`components/Highlight.tsx`。详情显示大纲、正文、标签、版本、索引状态；从引用进入按码点滚动和高亮；显示“切片 n · 第 p 页”；旧版本提示“原文已更新”。verify: Playwright 点击引用定位；emoji 前后高亮不偏移；刷新后大纲可再次跳转。
- [ ] **5.6 编辑器、预览、差异和冲突** — 涉及：`pages/MaterialEdit.tsx`、`pages/MaterialVersions.tsx`、`components/DiffView.tsx`。textarea 加实时预览；保存带 `base_version` 和修改说明；409 显示最新内容与差异，允许覆盖或放弃；版本页可比较任意两版并恢复。verify: Playwright 两个窗口并发保存，后者看到 409 和差异；恢复 v1 生成新版本且历史不变。
- [ ] **5.7 回收站和撤销** — 涉及：`pages/Trash.tsx`、`components/Toast.tsx`。删除后 10 秒内可撤销；回收站可恢复或彻底删除；学生不显示入口。verify: Playwright 删除后提示、撤销恢复；回收站恢复和彻底删除各一次。
- [ ] **5.8 阅读进度、收藏和最近阅读** — 涉及：`pages/Home.tsx`、`pages/MaterialDetail.tsx`、`components/`。滚动停止 2 秒上报；重新打开恢复位置；列表标记已读；首页显示最近阅读和收藏；收藏/取消收藏。verify: Playwright 打开材料滚动后关闭再开，位置恢复；收藏列表变化正确。
- [ ] **5.9 全局搜索与统一反馈** — 涉及：`components/CommandPalette.tsx`、`components/EmptyState.tsx`、`components/Skeleton.tsx`、`components/ErrorRetry.tsx`。Ctrl/⌘+K 搜索材料与操作，最多 20 条；上下键和 Enter；skeleton、空状态、503 重试；401 重新登录回原页；草稿写 `campusclaw.draft.*`。verify: Playwright 键盘搜索打开材料；503 后草稿保留；学生搜索结果不含教师操作。

## 6. 安全与客户端收口

- [ ] **6.1 移除网页令牌和伪造字段** — 涉及：`frontend/src/api.ts`、`App.tsx`、`Ask.tsx`。删除 `localStorage` 令牌读写，请求带 `credentials: "include"`；删除 `class_id: 999` 和客户端 `system` 消息；保留 Bearer 仅给脚本。verify: 构建产物 grep 不到 `campusclaw_token`、`class_id: 999`；curl 仍可用 Bearer 调用 `/api/me`。
- [ ] **6.2 增加 CSP、附件下载头和安全响应头** — 涉及：`frontend/nginx.conf`、`httpapi/json.go`、`httpapi/materials.go`、`docker-compose.yml`。CSP 按 `design.md` 第 10 节；下载 `Content-Disposition: attachment`、`nosniff`；不暴露服务器版本。verify: `curl -I` 检查三个头；上传目录静态路径 404。
- [ ] **6.3 收口 Compose 和镜像** — 涉及：`docker-compose.yml`、`backend/Dockerfile`。api 镜像安装 `poppler-utils`；仍只有 web 端口；`/health` 不查库；Qdrant/MySQL 不映射宿主。verify: `docker compose config` 只有 web 的 `ports`；`docker compose exec api pdftotext -v` 成功；停 db 后 `/health` 200、业务 503。

## 7. 验收与归档

- [ ] **7.1 扩展 `scripts/verify.py`** — 涉及：`scripts/verify.py`、`docs/verification.md`。保留现有全部检查；新增迁移、多格式、批量、异步索引、先建后换、版本冲突、回收站、标签分页、进度收藏、统一 404、学生 403、依赖不可达。每类新资源测“跨班 id / 已删除或不可见 id / 不存在 id”，响应必须逐字节相同；进度和收藏另测伪造 `user_id` 被忽略。verify: 从干净 Compose 运行 `python3 scripts/verify.py` 全绿；结果写入 `docs/verification.md`。
- [ ] **7.2 Go 单元测试** — 涉及：`backend/internal/*_test.go`。覆盖抽取、文件头/ZIP 限制、码点映射、迁移、队列状态、generation 切换、409 冲突、大纲、分页、限流键、搜索过滤、日志字段、`/health` 与 `/ready`。verify: `go test ./...` 全绿；覆盖率报告存 `docs/`。
- [ ] **7.3 Playwright 端到端** — 涉及：`frontend/e2e/`（新增）。三条主路径在 1440×900 和 390×844 各跑一次：① 上传 PDF → 等 ready → 检索 → 点引用高亮；② 编辑 → 旧引用提示“原文已更新” → 恢复旧版本；③ 删除 → 撤销/回收站恢复 → 彻底删除。verify: `npx playwright test` 全绿；失败时保存截图和 trace。
- [ ] **7.4 手动检查清单** — 涉及：`docs/manual-checklist.md`（新增）。手机宽度、深色主题、只用键盘各走一遍登录、列表、详情、编辑、版本、回收站；记录日期、浏览器版本和结果。verify: 清单每项有实际结果，不接受“应该可以”。
- [ ] **7.5 汇总验收记录** — 涉及：`docs/verification.md`。写清每个 change 条目的场景、命令、实际结果、通过/失败、证据链接；失败项写退回原因。verify: 角色三签字；失败项全部关闭或明确延后。
- [ ] **7.6 合并 delta 并归档** — 涉及：`openspec/specs/`、`openspec/changes/archive/`。只有 7.1 至 7.5 全部通过后才把 delta 合并到主 specs，按日期归档 change；归档后 `openspec/specs/` 是长期事实来源。verify: `openspec validate --all --strict` 通过；归档目录含 proposal/design/specs/tasks 和验收记录。

## 完成定义（Definition of Done）

- 所有 checkbox 已勾选，且每条都有可复现的 `verify` 结果。
- `npx -y @fission-ai/openspec@1.15.0 validate 2026-10-14-upgrade-material-library --strict` 通过，无 error、无 warning。
- `python3 scripts/spec_check.py` 和 `python3 scripts/standards_check.py` 通过。
- `go test ./...`、`python3 scripts/verify.py`、`npx playwright test` 全绿。
- `docker compose config` 只有 web 暴露端口；`/health` 不查库；停 db 时业务接口 503。
- 仓库全部提交历史中检索不到密钥、`.env`、上传文件或数据库文件。
- 角色三在 `docs/verification.md` 留下验收记录；未通过项不得归档。
