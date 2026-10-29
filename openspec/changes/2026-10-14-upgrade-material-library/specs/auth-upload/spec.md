# auth-upload Specification

## Purpose

规定迭代 1 的登录、角色、班级隔离、材料上传入库和 Compose 发布行为。本 change 修改登录限流、角色写权限、班级隔离范围、上传格式与异步索引、材料读取、部署和 Web 安全条款；未列出的既有条款继续有效。

## MODIFIED Requirements

### Requirement: 用户登录

系统 MUST 允许教师与学生使用账号和密码登录，并签发服务端会话。未登录访问受保护接口时 MUST 返回 401，响应体 MUST NOT 含有材料标题、正文或磁盘路径。账号不存在、口令错误和登录限流 MUST 返回相同的状态码与响应体。登录成功 MUST 作废该用户此前的会话并换发新的会话标识。登出 MUST 删除服务端会话行，使旧 Cookie 失效。登录失败次数 MUST 以 `(username, trusted_ip)` 为键持久化在 MySQL 的 `login_failures` 表，API 重启 MUST NOT 清零。`trusted_ip` MUST 只取 Nginx 覆盖写入的 `X-Real-IP`，且仅当直接对端属于可信私网网段（`10.0.0.0/8`、`172.16.0.0/12`、`192.168.0.0/16`、`127.0.0.0/8`）时采用；否则 MUST 使用连接地址。`X-Forwarded-For` 的任何一段 MUST NOT 作为计数键。达到 `LOGIN_FAIL_THRESHOLD`（`.env.example` 示例 5；缺失或非法启动失败）后锁定 `LOGIN_LOCK_MINUTES`（`.env.example` 示例 15；缺失或非法启动失败）分钟；锁定期内即使口令正确 MUST 仍返回同形 401。锁定到期后 MUST 清除该键的失败计数。

#### Scenario: 教师与学生登录成功

- **GIVEN** 数据库已按 README 完成种子初始化
- **WHEN** 使用 `teacher_a` 或 `student_a1` 的正确口令调用 `POST /api/login`
- **THEN** 响应状态为 200，并设置 `HttpOnly`、`SameSite=Lax` 的会话 Cookie
- **AND** 随后 `GET /api/me` 返回的 `role` 与 `class_name` 与该账号的预置身份一致

#### Scenario: 错误密码与不存在账号同形

- **GIVEN** `teacher_a` 存在，`no_such_user` 不存在
- **WHEN** 分别使用不存在的用户名、以及存在用户的错误口令调用 `POST /api/login`
- **THEN** 两次响应的状态码都是 401，响应体相同
- **AND** 都不包含「用户不存在」或「密码错误」这类可区分文案

#### Scenario: 未登录访问受保护接口

- **GIVEN** 客户端没有会话 Cookie，也没有 Bearer 令牌
- **WHEN** 调用 `GET /api/materials`
- **THEN** 响应状态为 401，`error=unauthorized`
- **AND** 响应体不含任一预置材料的标题或正文

#### Scenario: 登出后旧 Cookie 失效

- **GIVEN** 用户已登录并持有有效 Cookie
- **WHEN** 调用 `POST /api/logout`，再用登出前的 Cookie 调用 `GET /api/me`
- **THEN** 第二次响应状态为 401
- **AND** 服务端不再保留该会话行

#### Scenario: 限流响应与口令错误同形

- **GIVEN** 同一用户名和真实来源 IP 的失败次数达到 `LOGIN_FAIL_THRESHOLD`
- **WHEN** 再使用正确口令调用 `POST /api/login`
- **THEN** 响应仍为 401，响应体与口令错误时相同
- **AND** 不签发会话 Cookie

#### Scenario: 重启后仍锁定

- **GIVEN** `teacher_a` 连续失败 5 次，`login_failures` 中 `locked_until` 未过期
- **WHEN** 重启 api 后用正确口令登录
- **THEN** 响应仍为 401，响应体与错误口令相同
- **AND** `login_failures` 中该键仍存在，`fail_count` 没有清零

#### Scenario: 伪造代理头不能换身份

- **GIVEN** 攻击者从同一真实 IP 发起登录请求
- **WHEN** 每次失败都更换 `X-Forwarded-For` 的第一段，连续失败 5 次
- **THEN** 第 6 次使用正确口令仍返回 401
- **AND** `login_failures` 中只按真实 IP 累计，不出现伪造 IP 的行

#### Scenario: 锁定到期后可登录

- **GIVEN** `teacher_a` 的锁定时间已过
- **WHEN** 使用正确口令登录
- **THEN** 响应 200，签发新 Cookie
- **AND** 该 `(username, trusted_ip)` 的 `fail_count` 被清除

### Requirement: 角色权限

系统 MUST 只承认会话中的 `teacher` 与 `student` 两种角色。教师 MUST 可以上传、批量上传、重命名、打标签、编辑、替换、删除、恢复、彻底删除和重建索引本班材料。学生调用上述任一写接口 MUST 返回 403，且材料表、版本表、知识库表、标签表、切片表和上传目录都 MUST NOT 发生变化。学生 MUST 可以读取本班未删除材料、检索、问答、记录自己的进度和收藏。客户端自行声明的角色 MUST NOT 被采信。

#### Scenario: 学生上传被拒绝

- **GIVEN** `student_a1` 持有有效会话
- **WHEN** 调用 `POST /api/materials` 提交一份合法 `.md` 文件
- **THEN** 响应状态为 403，`error=forbidden`
- **AND** 材料表行数、版本表行数、知识库表行数和上传目录中的文件数与调用前相同

#### Scenario: 教师上传被允许

- **GIVEN** `teacher_a` 持有有效会话
- **WHEN** 上传一份非空 UTF-8 的 `.md` 或 `.txt`
- **THEN** 响应状态为 201，响应体含新材料的 id、标题、`version=1` 和 `index_status=pending`
- **AND** 本班列表随后能查到该标题

#### Scenario: 学生可以读取本班材料

- **GIVEN** `student_a1` 持有有效会话
- **WHEN** 请求本班材料列表、详情和原文件
- **THEN** 三个请求都成功
- **AND** 学生界面不提供上传入口；该限制不代替上面的 403

#### Scenario: 学生调用全部教师写接口被拒绝

- **GIVEN** `student_a1` 持有有效会话，本班材料 id=1
- **WHEN** 依次调用 batch、PATCH、DELETE、restore、purge、`PUT content`、`POST file` 和 reindex
- **THEN** 每个请求都返回 403 和 `{"error":"forbidden"}`
- **AND** 上述表和上传目录的计数与调用前相同

#### Scenario: 客户端声明角色无效

- **GIVEN** `student_a1` 持有有效会话
- **WHEN** 在请求体或 Header 中写入 `role=teacher`
- **THEN** 服务端仍按会话中的学生角色处理，写接口返回 403
- **AND** `GET /api/me` 返回的 `role` 仍是 `student`

### Requirement: 班级隔离

系统 MUST 把班级当作数据边界。列表查询 MUST 只使用会话中的 `class_id`。按 id 读取详情或文件时 MUST 先取出整行再核对班级。跨班访问与 id 不存在 MUST 都返回 404，且响应体相同，MUST NOT 含有对方标题、正文或存储路径。请求里的 `class_id` MUST 被忽略。本 change 新增的材料版本、标签、回收站、阅读进度、收藏和索引状态接口 MUST 遵守同一规则；列表的 `tag`、`sort`、`page` 参数 MUST NOT 改变班级过滤。

#### Scenario: 跨班按 id 访问材料被拒绝

- **GIVEN** A 班用户持有有效会话，B 班存在材料 id=99
- **WHEN** 请求 `GET /api/materials/99` 和 `GET /api/materials/99/file`
- **THEN** 两个响应都是 404
- **AND** 响应体与请求一个不存在的 id 时相同，且不含 B 班标题、正文和存储路径

#### Scenario: 列表不泄露其他班级

- **GIVEN** A 班和 B 班各有预置材料
- **WHEN** A 班用户调用 `GET /api/materials`，包括附带 `class_id` 指向 B 班的查询参数
- **THEN** 结果只含 A 班材料
- **AND** 不出现 B 班预置标题「B班-牛顿定律笔记」

#### Scenario: 上传时的班级字段不改变归属

- **GIVEN** A 班教师持有有效会话
- **WHEN** 上传文件时在表单中另外提交 `class_id` 为 B 班
- **THEN** 新材料、版本行和知识库行的 `class_id` 仍是该教师会话中的班级
- **AND** B 班列表不出现这条标题

#### Scenario: 标签与分页不改变班级

- **GIVEN** A 班和 B 班各有一份标签为「第一章」的材料
- **WHEN** A 班用户请求 `GET /api/materials?tag=第一章&page=1&page_size=20&class_id=<B班id>`
- **THEN** 响应 200，只返回 A 班材料
- **AND** 不出现 B 班标题，也不返回 403

#### Scenario: 新资源跨班同形 404

- **GIVEN** A 班教师持有有效会话，B 班存在材料 id=99
- **WHEN** 请求 id=99 的版本列表、restore、progress 和 favorite
- **THEN** 每个响应都是 404，响应体与不存在的 id 相同
- **AND** 服务端日志可以记录越权，但响应不泄露资源是否存在

### Requirement: 材料上传与知识库入库

教师上传成功时，系统 MUST 在校验通过后把原文件写入上传目录，并在同一数据库事务中插入 `materials`、`material_versions`（version=1）和 `knowledge_entries`（当前版本正文）。扩展名 MUST 使用白名单 `.txt`、`.md`、`.pdf`、`.docx`、`.pptx`，匹配前 MUST 对扩展名做小写归一（`.PDF` 视为 `.pdf`）。`.txt` 和 `.md` MUST 是 UTF-8；PDF MUST 以 `%PDF-` 开头；DOCX 和 PPTX MUST 是合法 ZIP，条目数不超过 2000，解压后不超过 100 MiB。PDF 文字抽取 MUST 在请求内完成，超时 10 秒、正文不超过 2,000,000 字符；DOCX 和 PPTX MUST 用 ZIP 加 XML 读取，标题样式 MUST 转为 Markdown 标题，页或幻灯片边界 MUST 记录到 `knowledge_entries.page_table`。扫描件、加密、损坏或无可复制文字 MUST 返回 400，并给出可读原因；MUST NOT 创建材料、版本、知识库、文件或切片。超过 `MAX_UPLOAD_BYTES` MUST 返回 413。事务提交后 MUST 将材料 id 放入后台索引队列并返回 201；事务失败 MUST NOT 留下材料行、版本行、知识库行或未关联文件。存储名 MUST 由服务端生成。

#### Scenario: 上传后知识库与列表可查

- **GIVEN** `teacher_a` 持有有效会话
- **WHEN** 上传一份含正文的合法 `.md`
- **THEN** 响应 201，含 `id`、`title`、`version=1` 和 `index_status=pending`
- **AND** 本班 `GET /api/materials` 出现新标题
- **AND** `GET /api/materials/{id}` 返回的正文与文件内容一致，且归属该教师的班级
- **AND** 响应不含磁盘绝对路径

#### Scenario: 非法扩展名不留残留

- **GIVEN** `teacher_a` 持有有效会话
- **WHEN** 上传扩展名为 `.exe` 的文件，或文件名为 `notes.md.exe`
- **THEN** 响应状态为 400，`error=invalid_file`
- **AND** 材料表、版本表、知识库表和上传目录都没有新增记录或文件

#### Scenario: 超限与非法内容不留残留

- **GIVEN** `teacher_a` 持有有效会话
- **WHEN** 上传超过 `MAX_UPLOAD_BYTES` 的文件，或上传非 UTF-8 内容
- **THEN** 超限响应为 413，非法内容响应为 400
- **AND** 四张表和上传目录都没有新增残留

#### Scenario: 本班学生可见且其他班不可见

- **GIVEN** A 班教师刚上传一份材料，切片尚未 ready
- **WHEN** 同班学生刷新列表，其他班用户按 id 访问该材料
- **THEN** 同班学生能在列表中看到该标题并下载原文件
- **AND** 其他班用户得到 404

#### Scenario: 上传成功后本班可检索正文

- **GIVEN** 教师上传成功且该材料 `index_status=ready`
- **WHEN** 本班用户用原文中的词做 `keyword` 检索
- **THEN** `hits` 含该材料
- **AND** 其他班用户用同一词检索时 `hits` 不含该材料

#### Scenario: 扫描件被当场拒绝

- **GIVEN** `teacher_a` 持有有效会话，准备一份只有图片、没有可复制文字的 PDF
- **WHEN** 调用 `POST /api/materials`
- **THEN** 响应 400，`error=scanned_pdf`，提示可能是扫描件
- **AND** 材料、版本、知识库、文件和切片都没有新增

#### Scenario: 伪造文件头被拒绝

- **GIVEN** 一个扩展名为 `.pdf` 但内容不是以 `%PDF-` 开头的文件
- **WHEN** 教师上传该文件
- **THEN** 响应 400，`error=invalid_file`
- **AND** 上传目录没有新文件

#### Scenario: 加密或损坏的 Office 文件被拒绝

- **GIVEN** 一个不是 ZIP 的 `.docx`，或解压后条目数超过 2000 的 `.pptx`
- **WHEN** 教师上传该文件
- **THEN** 不是 ZIP 的返回 400 `error=invalid_archive`；ZIP 可解压但 XML 损坏的返回 400 `error=invalid_file`
- **AND** 不执行 XML 解析，不留下文件和数据库行

#### Scenario: 事务失败不留残留

- **GIVEN** 上传流程已写完文件，但插入 `knowledge_entries` 时数据库返回错误
- **WHEN** 教师重试同一文件
- **THEN** 第一次响应 503，材料表、版本表和知识库表没有新行，上传目录没有遗留文件
- **AND** 重试成功后只产生一条材料和一条 v1 记录

#### Scenario: PDF 页码与 PPT 幻灯片号

- **GIVEN** 一份 3 页 PDF 和一份 4 张幻灯片的 PPTX
- **WHEN** 教师分别上传并等待索引 ready
- **THEN** `knowledge_entries.page_table` 记录每页或每张幻灯片的起止码点
- **AND** 检索命中带 `page` 或 `slide`，值与原文位置一致

### Requirement: 材料读取与下载

已登录用户 MUST 只能读取本班未删除材料。详情 MUST 返回标题、班级、时间、文件类型、当前版本、索引状态、标签、大纲和知识库正文。下载 MUST 走 `GET /api/materials/{id}/file`，并先校验会话与班级；响应 MUST 使用 `Content-Disposition: attachment` 和 `X-Content-Type-Options: nosniff`。上传目录 MUST NOT 作为静态资源暴露。已软删除材料对非回收站接口 MUST 返回同形 404。

#### Scenario: 直接猜测上传路径失败

- **GIVEN** 客户端知道上传目录中的存储文件名
- **WHEN** 请求 `/uploads/` 下的该文件名
- **THEN** 响应不是文件内容
- **AND** 状态码不是 200

#### Scenario: 详情不返回存储路径

- **GIVEN** 本班用户持有有效会话
- **WHEN** 请求材料详情
- **THEN** 响应含标题、正文、`file_type`、`current_version`、`index_status`、`tags` 和 `outline`
- **AND** 响应不含 `storage_name`、绝对路径或 `/uploads/` 路径

#### Scenario: 下载按附件返回

- **GIVEN** 本班用户请求一份 PDF 材料
- **WHEN** 调用 `GET /api/materials/{id}/file`
- **THEN** 响应 200，`Content-Disposition` 以 `attachment` 开头
- **AND** 响应头含 `X-Content-Type-Options: nosniff`

#### Scenario: 已删除材料对普通接口不可见

- **GIVEN** 材料 id=1 已软删除
- **WHEN** 学生请求列表、详情、文件和检索
- **THEN** 详情和文件返回 404，列表和检索不含该材料
- **AND** 响应体与不存在的 id 相同

### Requirement: Docker Compose 部署与健康检查

标准启动方式 MUST 是 Docker Compose 的 web、api、db、qdrant 四个服务。只有 web MUST 映射宿主端口。数据库和 Qdrant 端口 MUST NOT 映射到宿主。`GET /live` MUST 不要求登录，且 MUST NOT 访问 MySQL、Qdrant、嵌入或对话网关。`GET /health` MUST 不要求登录，检查 MySQL ping、Qdrant 可达和嵌入配置；全部通过返回 200，任一失败返回 503。数据库不可用时，业务接口 MUST 返回 503，而不是 401。`docker compose down` 之后再 `up`（不带 `-v`）MUST 保留已上传的数据。api 镜像 MUST 包含 `pdftotext`。

#### Scenario: Compose 启动后可访问

- **GIVEN** 已从 `.env.example` 复制并填好变量
- **WHEN** 执行 `docker compose up --build -d`
- **THEN** 浏览器可以打开 web 端口上的登录页
- **AND** 未登录 `GET /live` 返回 200 且响应体表示进程存活
- **AND** `GET /health` 返回 200 `{status:"ready"}`

#### Scenario: 数据库端口不对外

- **GIVEN** Compose 配置已生效
- **WHEN** 查看 `docker compose config` 并在宿主上连接 MySQL 和 Qdrant 默认端口
- **THEN** db 和 qdrant 服务都没有 `ports` 映射
- **AND** api 容器环境中没有 MySQL 管理员口令

#### Scenario: 数据库停止时健康检查与业务接口分离

- **GIVEN** web 和 api 正在运行
- **WHEN** 停止 db 容器后访问 `/live`、`/health` 和 `GET /api/materials`
- **THEN** `/live` 仍返回 200
- **AND** `/health` 返回 503，`checks.db=false`
- **AND** 材料接口返回 503，而不是 401

#### Scenario: 重建容器后数据仍在

- **GIVEN** 教师已上传一份材料
- **WHEN** 执行 `docker compose down` 再 `docker compose up -d`，且不使用 `-v`
- **THEN** 同一账号再次登录后仍能在列表中看到该材料
- **AND** 材料的版本和阅读进度仍在

#### Scenario: api 镜像包含 PDF 抽取工具

- **GIVEN** Compose 已启动
- **WHEN** 执行 `docker compose exec api pdftotext -v`
- **THEN** 命令以 0 退出并输出版本信息
- **AND** 上传 PDF 的路径可以完成抽取

### Requirement: Web 行为与安全

前端 MUST 提供登录页和材料页。刷新后身份 MUST 以 `GET /api/me` 为准。收到 401 时 MUST 回到登录页。上传入口是否显示 MUST 只取决于 `/api/me` 的角色。材料正文 MUST 以 Markdown 渲染，且材料中的脚本 MUST NOT 被执行。网页端 MUST 只依赖 `HttpOnly` Cookie 维持会话，MUST NOT 把令牌写入 `localStorage` 或 `sessionStorage`。`POST /api/login` MAY 返回 Bearer 令牌供 curl 和验收脚本使用，但前端 MUST NOT 读取或保存该字段。正式页面 MUST NOT 包含演示用的 `class_id: 999` 或客户端伪造的 `system` 消息。响应 MUST 设置 CSP：`default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'`。

#### Scenario: 刷新后以服务端会话恢复身份

- **GIVEN** 已登录用户刷新材料页
- **WHEN** 页面加载
- **THEN** 页面调用 `GET /api/me`
- **AND** 不读取 localStorage 中的角色来决定上传入口

#### Scenario: 401 回到登录页

- **GIVEN** 会话已失效
- **WHEN** 材料页收到 401
- **THEN** 页面进入登录页
- **AND** 不继续展示材料标题

#### Scenario: Markdown 不执行脚本

- **GIVEN** 材料正文包含 `<script>alert(1)</script>`
- **WHEN** 打开材料详情
- **THEN** 详情区把它显示为文本
- **AND** 浏览器不执行该脚本

#### Scenario: 网页不保存令牌

- **GIVEN** 用户通过网页登录成功
- **WHEN** 检查浏览器 `localStorage` 和 `sessionStorage`
- **THEN** 不存在 `campusclaw_token` 或任何 Bearer 令牌
- **AND** 后续请求只依赖 Cookie

#### Scenario: 脚本仍可用 Bearer

- **GIVEN** 验收脚本调用 `POST /api/login`
- **WHEN** 响应返回 `token`
- **THEN** 脚本可以带 `Authorization: Bearer <token>` 调用 `GET /api/me`
- **AND** 网页端代码没有读取该字段

#### Scenario: 正式页面无伪造字段

- **GIVEN** 前端已构建
- **WHEN** 检查构建产物和源码
- **THEN** 不存在 `class_id: 999` 和客户端构造的 `system` 消息
- **AND** `verify.py` 仍可以使用这些测试输入，但它们不进入正式页面

#### Scenario: 安全响应头

- **GIVEN** web 服务已启动
- **WHEN** 请求任意页面
- **THEN** 响应含上面规定的 CSP 和 `X-Content-Type-Options: nosniff`
- **AND** 响应不含服务器版本或框架版本
