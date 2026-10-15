## Why

当前 CampusClaw 已能完成登录、班级隔离、txt/md 上传和本班可追溯检索，但材料库仍不适合日常教学：常见的 PDF、Word、PPT 无法上传；上传会同步建立索引；失败和进度不可见；材料不能编辑、替换或恢复历史版本；删除没有回收站；引用不能稳定定位到原文；学生没有阅读进度和收藏。数据库仍用不可演进的 `CREATE TABLE IF NOT EXISTS`，前端把所有页面和材料逻辑放在一个 `App.tsx` 中，并存在限流、向量维度和浏览器令牌等已知问题。

## What Changes

- 引入带 `schema_migrations` 的编号迁移机制，第一版迁移与现有表结构等价，已有数据库不清空即可升级。
- 新增 PDF、DOCX、PPTX 抽取和文件头/压缩包校验；抽取在上传请求中完成，索引放入后台队列。
- 为材料增加索引状态、失败原因、标签、软删除、版本历史、原文定位、阅读进度和收藏。
- 增加批量上传、状态轮询、失败重试、回收站、在线编辑、文件替换、版本比较和恢复。
- 重建索引改为 generation 先建后换；旧索引在新索引完成前继续可检索，引用使用材料版本和原文区间。
- 将 `App.tsx` 拆为页面和通用组件，建立左侧导航/窄屏底栏、全局搜索、骨架屏、空状态、重试反馈和材料详情编辑体验。
- 修复限流持久化、可信客户端 IP、嵌入维度配置、前端令牌保存、伪造 `class_id`/`system` 消息等现有问题。

## Capabilities

### New Capabilities

- `material-library`：多格式材料、异步索引、回收站、标签、版本、引用定位、阅读进度与收藏。
- `platform-foundation`：数据库迁移、页面壳层、统一反馈和基础安全修复。

### Modified Capabilities

- `auth-upload`：扩展文件类型和抽取安全校验；上传事务仍原子，但索引异步；网页只使用 HttpOnly Cookie。
- `knowledge-retrieval`：索引后台化，重建先建后换，切片偏移指向原文，出处绑定材料版本。

## Scope and Interfaces

本 change 包含：

- `GET /api/materials` 的标签筛选、排序、分页和索引状态。
- `POST /api/materials` 的 PDF/DOCX/PPTX、批量上传和异步索引状态。
- `POST /api/materials/{id}/reindex` 返回 202，并支持失败后重试。
- `PATCH`、`DELETE /api/materials/{id}`、`POST /api/materials/{id}/restore`、`GET /api/trash`。
- `PUT /api/materials/{id}/content`、`POST /api/materials/{id}/file`。
- `GET /api/materials/{id}/versions`、`POST /api/materials/{id}/versions/{v}/restore`。
- `PUT /api/materials/{id}/progress`、`PUT`/`DELETE /api/materials/{id}/favorite`。

所有新接口都继承会话班级、角色权限、同形 404、CSRF/Origin 和上传原子性约束。

## Non-goals

- 不实现会话历史、追问、SSE 流式回答、班级助手或新的 AI 技能；旧 `/api/ask` 保持兼容。
- 不实现课程单元、作业、练习、错题、公告、通知和学情统计。
- 不做超级管理员，不让 AI 给作业打分，不引入 JWT 替代既有会话，不引入 LangChain/LlamaIndex/Dify。
- 不把 Qdrant、嵌入网关、对话网关或数据库映射到宿主端口，不把密钥发送到浏览器。
- 不直接修改已归档的 `openspec/specs/`；实现完成并验收后才由流程将 delta 合并并归档。

## Compatibility and Evidence

现有 `scripts/verify.py` 的检查必须全部保留并扩展。新增行为以 Go 单元测试、curl 响应、数据库查询、Playwright 桌面/手机路径和手动检查清单验收。未写入本 change 的行为不得实现。
