# platform-foundation Specification

## Purpose

规定本 change 所有能力共用的底座：可升级数据库、页面壳层、全局搜索与统一反馈、索引与嵌入配置。它不实现材料库业务，也不引入后续教学业务。

## ADDED Requirements

### Requirement: 版本化数据库迁移

服务启动时 MUST 按版本号升序执行 `backend/internal/db/migrations/` 中打包的 SQL 脚本。每个脚本 MUST 在 `schema_migrations(version, name, checksum, applied_at)` 中记录版本、文件名和 SHA-256；已记录版本 MUST 跳过，已有版本的文件校验和不一致时 MUST 启动失败。迁移 MUST 在监听端口前完成；失败时进程 MUST 以非零状态退出，MUST NOT 清空、重建或覆盖已有表。`0001_baseline.sql` MUST 等价当前 `db.Migrate` 的全部 `CREATE TABLE IF NOT EXISTS` 语句，使迭代 1/2 的数据库无需清空即可升级。

#### Scenario: 空库完成全部迁移

- **GIVEN** 一个空的 MySQL 8.0 数据库，`.env` 已按 `.env.example` 填好
- **WHEN** 启动 api 进程
- **THEN** `GET /health` 返回 200
- **AND** `schema_migrations` 含从 `0001` 到当前最新版本的连续记录
- **AND** `classes`、`users`、`sessions`、`materials`、`knowledge_entries`、`knowledge_chunks` 都存在

#### Scenario: 旧库升级保留数据

- **GIVEN** 一个迭代 1/2 的数据库，含 1 个教师、2 个学生、1 份材料和已 ready 的切片
- **WHEN** 使用本 change 的 api 启动
- **THEN** 上述用户、材料和切片行数不变，正文和文件仍可读取
- **AND** `materials` 的新增列取默认值，`material_versions`、`tags`、`material_reads`、`favorites` 等新表存在
- **AND** 预置账号和预置材料没有重复插入

#### Scenario: 迁移失败时启动失败

- **GIVEN** `migrations/` 中新增一个语法错误的版本 N+1，且版本 1 至 N 已成功执行
- **WHEN** 启动 api
- **THEN** 进程以非零状态退出，不监听端口
- **AND** 错误日志包含失败版本号 N+1
- **AND** `schema_migrations` 仍只有 1 至 N，已有业务行数不变

#### Scenario: 校验和不一致拒绝启动

- **GIVEN** 版本 `0002` 已执行，之后有人修改了 `0002_*.sql` 的内容
- **WHEN** 启动 api
- **THEN** 进程以非零状态退出，日志指出 `0002` 校验和不一致
- **AND** 不执行 `0002` 之后的版本，不修改已有数据

#### Scenario: 重启不重复迁移

- **GIVEN** 数据库已完成全部迁移
- **WHEN** 连续启动 api 两次
- **THEN** 每个版本的 `applied_at` 不变，`schema_migrations` 行数不增加
- **AND** 种子用户和材料不重复，教师后来上传的材料仍在

### Requirement: 页面壳层与响应式导航

前端 MUST 把 `frontend/src/App.tsx` 拆为 `pages/` 与 `components/`，路由状态 MUST 进入 URL。桌面宽度大于等于 768px 时 MUST 显示左侧导航，可用项为：首页 `/`、材料 `/materials`、问答 `/ask`、设置 `/settings`，教师额外显示回收站 `/trash`。窄屏小于 768px 时 MUST 显示底部标签栏，最多 4 项：首页、材料、问答、设置。直接打开 `/materials/{id}`、`/materials/{id}/edit`、`/materials/{id}/versions`、`/trash`、`/settings` MUST 返回 SPA 入口并在登录后渲染；未登录访问 MUST 回到登录页，且页面 MUST NOT 出现材料标题。北大红主色、浅色/深色主题和纯键盘操作 MUST 保留。

#### Scenario: 桌面导航

- **GIVEN** `teacher_a` 已登录，浏览器视口为 1440×900
- **WHEN** 打开 `/`
- **THEN** 左侧导航出现，首页、材料、问答、设置、回收站可点击
- **AND** 学习路径、作业、练习、通知、班级管理带有 `aria-disabled="true"`
- **AND** 按 Tab 可依次到达全部可用项，按 Enter 可打开

#### Scenario: 窄屏底栏

- **GIVEN** `student_a1` 已登录，浏览器视口为 390×844
- **WHEN** 打开 `/materials`
- **THEN** 底部标签栏显示首页、材料、问答、设置四项
- **AND** 不显示回收站和班级管理
- **AND** 内容区可滚动到最后一个材料，不被底栏遮挡

#### Scenario: 深层路由刷新

- **GIVEN** `teacher_a` 已登录，本班存在材料 id=1
- **WHEN** 直接打开 `/materials/1/versions` 并刷新页面
- **THEN** 响应为 200 的 SPA 入口，页面渲染版本页，不出现 404
- **AND** 未登录会话打开同一 URL 时进入登录页，DOM 不含材料标题

#### Scenario: 主题与键盘操作

- **GIVEN** 已登录用户
- **WHEN** 切换到深色主题，并只用键盘打开材料详情
- **THEN** `document.documentElement.dataset.theme` 为 `dark`，键盘焦点可见
- **AND** 刷新后主题保持；主题偏好可以存在 localStorage，但其中 MUST NOT 含会话令牌

### Requirement: 禁用占位与教师专属路由

学习路径、作业、练习、通知、班级管理 MUST 显示为禁用项，MUST NOT 注册路由，MUST NOT 请求后端；禁用项 MUST 带 `aria-disabled="true"`，键盘可以到达但不能激活。教师专属路由 `/trash` 对学生 MUST 显示无权限提示，MUST NOT 请求回收站数据。

#### Scenario: 学生打开教师专属路由

- **GIVEN** `student_a1` 已登录
- **WHEN** 直接打开 `/trash`
- **THEN** 页面显示「无权限」提示，不显示回收站列表
- **AND** 网络面板没有成功的 `GET /api/trash` 请求；若发出请求，返回 403

#### Scenario: 后续教学入口只是占位

- **GIVEN** `student_a1` 已登录，桌面视口
- **WHEN** 点击导航中的「作业」，或直接打开 `/assignments`
- **THEN** 「作业」入口带 `aria-disabled="true"`，不跳转，不发请求
- **AND** `/assignments` 不渲染业务页面，只显示「本阶段未开放」

### Requirement: 全局搜索与统一反馈

Ctrl/⌘+K MUST 打开全局搜索。搜索范围 MUST 限于当前用户可见的已实现资源：材料标题、教师材料操作（打开、编辑、版本、删除）、学生材料操作（打开、收藏）和常用操作（切换主题、退出登录）；不返回其他 action。查询少于 1 个字符时 MUST NOT 请求后端；结果 MUST 最多 20 条，按标题匹配优先、更新时间降序。上下键 MUST 移动选中项，Enter MUST 执行，Esc MUST 关闭。不得返回其他班级材料或教师专属操作给学生。页面加载 MUST 显示 skeleton；空列表 MUST 显示下一步建议；400、401、404、409、413、503 MUST 显示可读错误；503 MUST 提供重试按钮。401 MUST 弹出重新登录，成功后 MUST 回到原路由；材料编辑器和提问框草稿 MUST 保存在 `localStorage` 的 `campusclaw.draft.*`，提交成功或用户明确放弃后 MUST 删除。

#### Scenario: 键盘搜索材料

- **GIVEN** A 班教师有标题含「函数」的材料，B 班有「B班-牛顿定律笔记」
- **WHEN** 按 Ctrl/⌘+K，输入「函数」，按方向键下再按 Enter
- **THEN** 打开对应材料详情
- **AND** 结果列表不含「牛顿定律」
- **AND** 请求 `GET /api/quick-search?q=函数` 的响应最多 20 条

#### Scenario: 学生看不到教师操作

- **GIVEN** `student_a1` 已登录
- **WHEN** 打开全局搜索并输入「删除」
- **THEN** 结果不含删除、编辑、版本恢复等教师操作
- **AND** 只含学生可用的打开、收藏和材料搜索

#### Scenario: 空结果给出下一步

- **GIVEN** 本班没有标题含「zzz」的材料
- **WHEN** 搜索「zzz」
- **THEN** 显示「没有找到匹配项」和「试试材料页的标签筛选」
- **AND** 不显示错误状态或重试按钮

#### Scenario: 503 重试与草稿保留

- **GIVEN** 教师正在 `/materials/1/edit` 编辑正文，草稿已写入 `localStorage`
- **WHEN** 保存请求返回 503
- **THEN** 页面显示「服务暂时不可用」和重试按钮，编辑器内容不变
- **AND** 刷新页面后草稿仍在；保存成功后该草稿键被删除

#### Scenario: 401 重新登录回到原页

- **GIVEN** 会话过期，教师停留在 `/materials/1/versions`
- **WHEN** 页面收到 401
- **THEN** 弹出重新登录，登录成功后回到 `/materials/1/versions`
- **AND** 登录页和返回后的页面都不显示其他班材料

### Requirement: 索引与嵌入配置

`EMBEDDING_DIM` MUST 是必填环境变量，取值为 1 至 4096 的整数；缺失、非整数或越界 MUST 使 api 启动失败，MUST NOT 回退到 256。Qdrant 集合名 MUST 为 `campusclaw_<EMBEDDING_DIM>`。本地嵌入 MUST 输出该维度；外部嵌入返回的向量长度不等于该值时，材料 MUST 标记为 `failed`，`index_error` 为 `embedding_dim_mismatch`，MUST NOT 写入任何 ready 切片。`MAX_UPLOAD_BYTES` MUST 保持 1 至 16777216 的整数校验。固定上限 MUST 为：单次批量 20 个文件、请求总大小 20 MiB、PDF 抽取 10 秒、抽取正文 2,000,000 字符、压缩包 2000 个条目、解压后 100 MiB、列表默认 20 条且最多 100 条。

#### Scenario: 维度跟随配置

- **GIVEN** `EMBEDDING_DIM=768`，嵌入使用本地实现
- **WHEN** 上传并索引一份材料
- **THEN** Qdrant 集合名为 `campusclaw_768`，写入向量长度为 768
- **AND** 检索返回 200

#### Scenario: 缺少维度拒绝启动

- **GIVEN** `.env` 未设置 `EMBEDDING_DIM`
- **WHEN** 启动 api
- **THEN** 进程以非零状态退出，日志包含 `EMBEDDING_DIM`
- **AND** 不监听端口，不写 Qdrant

#### Scenario: 维度不匹配不静默写入

- **GIVEN** Qdrant 已有 `campusclaw_256`，配置为 `EMBEDDING_DIM=768`，外部嵌入返回 256 维向量
- **WHEN** 教师上传材料
- **THEN** 材料 `index_status=failed`，`index_error=embedding_dim_mismatch`
- **AND** `knowledge_chunks` 没有该材料的 ready 行，`campusclaw_768` 中没有该材料向量

#### Scenario: 批量与分页上限

- **GIVEN** 教师一次选择 21 个文件
- **WHEN** 调用批量上传
- **THEN** 返回 400 `too_many_files`
- **AND** 材料表、版本表和上传目录都不新增
- **AND** 20 个文件的同一请求被接受
