# 第一阶段实施任务

> 所有任务初始保持未勾选。只有角色二完成实现、角色三运行对应 verify 并确认通过后，才能勾选；角色一不得用“代码已写”替代验收证据。

## 1. OpenSpec 与数据库底座

- [ ] 1.1 运行 `openspec validate upgrade-material-library --strict`，修复 change 结构、Requirement 和 Scenario 格式问题 — verify: 命令退出码为 0
- [ ] 1.2 将现有建表语句固化为迁移版本 1，新增 `schema_migrations`，按版本顺序执行且幂等 — verify: 空库和已有库启动后版本记录完整，已有用户/材料/文件仍在
- [ ] 1.3 添加材料版本、标签、阅读、收藏、删除和索引状态所需表/列/索引 — verify: `SHOW CREATE TABLE` 与 `DESCRIBE` 包含本 change 数据模型；重复启动不重复迁移

## 2. 文件抽取与安全上传

- [ ] 2.1 实现 txt/md/pdf/docx/pptx 扩展名白名单和文件头校验 — verify: 合法样本 201；伪造 PDF、非法 ZIP、`.exe` 和双扩展名均 400 且无残留
- [ ] 2.2 实现 PDF、DOCX、PPTX 的受限抽取、标题转换、页码/幻灯片边界和损坏/加密/扫描件错误 — verify: Go 抽取单测覆盖正常样本和失败样本；verify 检查正文、页码和错误文案
- [ ] 2.3 保持文件、`materials`、`knowledge_entries` 同步事务；抽取或事务失败清理全部已写文件 — verify: 人为注入失败后数据库行数和上传目录文件数均不变
- [ ] 2.4 扩展材料列表接口的标签、排序、分页、重命名和 index status — verify: curl 结果分页元数据、筛选、排序稳定且忽略请求 `class_id`

## 3. 后台索引与原文定位

- [ ] 3.1 实现 `pending/indexing/ready/failed` 队列、失败原因、重试和重启补排 — verify: 上传立即返回；轮询最终 ready；断开嵌入后 failed 可重试，重启后 pending/indexing 重新排队
- [ ] 3.2 为 `knowledge_chunks` 增加 generation，按先建后换重建索引 — verify: reindex 返回 202；期间旧索引可检索；成功后旧切片/向量才删除；失败只清理新 generation
- [ ] 3.3 实现预处理到原文码点的偏移映射和 PDF/PPT 页边界 — verify: 含 emoji/中文的 Go 单测 start/end 与前端高亮一致；命中含页码/幻灯片号
- [ ] 3.4 更新检索/问答出处为 material id、version、原文区间和摘录 — verify: 重建后引用仍可打开；材料版本变化显示“原文已更新”且保留旧摘录；既有跨班/无依据 verify 全通过

## 4. 编辑、替换与版本历史

- [ ] 4.1 实现 `PUT /api/materials/{id}/content` 的追加版本、修改说明和后台索引 — verify: 旧正文和新正文均可列出；ready 后检索新正文
- [ ] 4.2 实现文件替换，复用抽取和全有或全无约束 — verify: PDF/DOCX/PPTX 替换生成新版本，损坏替换 400 且旧文件/正文不变
- [ ] 4.3 实现 base version 乐观并发冲突 409 — verify: 两个窗口基于同一版本保存，后者获得 409 与最新内容且不覆盖先保存版本
- [ ] 4.4 实现版本列表、任意两版差异和恢复 — verify: 恢复版本本身生成新版本，历史行不改写，恢复后重新索引

## 5. 删除、回收站、阅读与收藏

- [ ] 5.1 实现软删除、回收站、撤销和教师彻底删除 — verify: 删除后学生列表/详情/文件/检索/问答立即不可见；恢复保留历史；彻底删除清理文件、版本、切片和向量
- [ ] 5.2 实现标签更新、重命名、权限和 404 同形规则 — verify: 学生写接口 403；其他班 id、同班其他学生私有 id、不存在 id 三次响应完全相同
- [ ] 5.3 实现学生阅读进度、已读/未读、最近阅读和滚动停止 2 秒上报 — verify: 重新打开恢复位置；其他学生不继承；请求次数符合节流规则
- [ ] 5.4 实现收藏/取消收藏和我的收藏 — verify: 收藏列表变化正确；跨班、他人和不存在 id 同形 404

## 6. 安全修复与部署

- [ ] 6.1 将登录失败计数迁入 MySQL，修复可信 IP 和伪造 `X-Forwarded-For` 绕过 — verify: 重启 API 和换伪造头都不能绕过锁定，错误与正确锁定响应同形
- [ ] 6.2 将嵌入维度配置化，Qdrant 集合名包含 `EMBEDDING_DIM` — verify: 不同维度本地模式能建立匹配集合；维度错误不会静默写入
- [ ] 6.3 清除网页 localStorage 令牌、`class_id:999` 和伪造 system 消息，保留 Bearer 脚本兼容 — verify: 前端源码静态检查通过；页面请求只依赖 HttpOnly Cookie
- [ ] 6.4 增加 CSP、上传附件下载头和压缩包资源限制；保持 Compose 只有 web 端口、`/health` 不查库 — verify: `docker compose config`、安全响应头和停库场景通过

## 7. 前端页面框架

- [ ] 7.1 将 `App.tsx` 拆为 pages/components，建立 `/`、`/materials`、`/materials/:id`、编辑、版本、注册、设置等路由 — verify: Playwright 桌面和手机宽度可直接刷新深层路由
- [ ] 7.2 实现左侧导航、窄屏底栏、北大红主色、浅色/深色主题和键盘可操作性 — verify: Playwright 与手动清单覆盖桌面、手机、深色、纯键盘
- [ ] 7.3 实现批量拖拽上传队列、索引状态、失败原因、重试和材料详情大纲/高亮 — verify: Playwright 上传 PDF 主路径和引用定位截图/结果可复现
- [ ] 7.4 实现编辑器、实时预览、版本差异视图、冲突提示、删除/回收站、阅读/收藏 UI — verify: Playwright 主路径“编辑 → 原文已更新 → 恢复旧版本”在桌面和手机各通过一次
- [ ] 7.5 实现全局 Ctrl/⌘+K 搜索、skeleton、空状态、错误重试和草稿恢复 — verify: 键盘操作可打开材料/操作；401/503 后草稿不丢

## 8. 验收与归档流程

- [ ] 8.1 扩展 `scripts/verify.py`，保留现有全部检查并加入迁移、多格式、异步索引、先建后换、版本、回收站、私有数据和安全修复场景 — verify: 角色三从干净 Compose 环境运行，失败项有实际响应证据
- [ ] 8.2 增加 Go 单元测试：抽取、映射、迁移、队列、版本冲突、重建、权限和本地模式 — verify: `go test ./...`
- [ ] 8.3 增加 Playwright 桌面/手机三条主路径和手动检查清单 — verify: 每条路径保存可复现结果或截图，不接受口头完成声明
- [ ] 8.4 全部验收通过后，将本 change delta 合并到 `openspec/specs/` 并归档；验收失败不得归档 — verify: `openspec validate --strict`、主规约含 material-library/platform-foundation，归档目录保留提案、设计和任务证据
