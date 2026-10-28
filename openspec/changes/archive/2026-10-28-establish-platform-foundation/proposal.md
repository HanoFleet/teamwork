# 变更提案：2026-10-28-establish-platform-foundation

| 项目 | 内容 |
| --- | --- |
| 变更名 | `2026-10-28-establish-platform-foundation` |
| 阶段 | 第 7 课项目启动：可运行骨架 |
| 负责人 | 李斯坦（角色一：制定规约） |
| 评审 | 韩雅慧（角色二：开发系统）、禹霖（角色三：项目验收） |
| 基线 | `v2.0.0-baseline`（提交 `4fd4232`） |
| 后续 change | `2026-10-14-upgrade-material-library`（材料库，未实现） |

## Why

CampusClaw 已经有一个可运行的迭代 1/2 应用，但它的工程骨架还缺第 7 课要求的最小面：没有 `/live` 与依赖就绪分离，没有单行 JSON 请求日志和 request ID，没有优雅停机，配置版本和停机预算没有外置，也没有一条命令的 `check`/`grade` 门禁。材料库的规约已经写得足够细，但如果框架本身不可运行、不可验收，规约就没有承载物。

本 change 只加固骨架，不改业务：保留现有登录、材料、检索和问答接口，新增存活/就绪、日志、停机、配置和门禁，让后续材料库 change 有一个可复现的基线。

## What Changes

1. 从 `v2.0.0-baseline` 恢复 `backend/`、`frontend/`、Compose 和验收脚本到根目录，确保仓库本身就是可运行工程。
2. 增加 `/live` 存活、`/health` 就绪（含 `db`、`qdrant`、`embedding` 检查）和 `/ready` 别名；`/health` 依赖不可达返回 503。
3. 增加单行 JSON 请求日志和 `X-Request-ID`：合法 ID 原样回写，非法/缺失时生成；日志含时间、级别、方法、路径、状态、耗时，不写 query、body、口令、令牌或 DSN。
4. 增加优雅停机：收到 SIGTERM 后停止接受新连接，在 `SHUTDOWN_TIMEOUT_SECONDS` 内排空在途请求，再关闭数据库。
5. 外置 `APP_VERSION` 和 `SHUTDOWN_TIMEOUT_SECONDS`；缺必填项启动失败，不取默认值。
6. 增加 `make check`（规约、规范、strict、分层、密钥、变异、Go 测试、前端构建）和 `make grade`（独立 Compose 项目、13 项验收、HTML/JSON 报告）。
7. 增加 CI、证据记录和骨架标签，归档本 change；材料库 change 保持活动，留给下一阶段。

## Out of Scope

- 不实现材料库的新功能：PDF/DOCX/PPTX 上传、后台索引、版本历史、回收站、标签、阅读进度、收藏、原文定位。
- 不修改登录、角色、班级隔离、材料上传、检索和问答的业务行为。
- 不引入 JWT 替代、超级管理员、AI 批改作业、外部队列、Redis 或对象存储。
- 不重构 `httpapi/auth.go`、`materials.go`、`server.go` 中已有的 SQL；它们是迭代 1/2 的 legacy 例外，材料库 change 再迁移。
- 不做浏览器端 UI 重构；本 change 只验证现有前端能构建、Compose 能启动。

## Alternatives Considered

| 候选方案 | 为什么放弃 |
| --- | --- |
| 新建一个空的 skeleton 仓库 | 会丢掉 CampusClaw 已有业务、历史规约和贡献记录；课程要的是同一个项目上的增量，不是另起项目。 |
| 继续只交规约、不恢复代码 | 老师明确看“框架”；只有 `design.md` 和归档 ZIP 无法证明一条命令能启动、`/health` 能响应。 |
| 把 `/health` 保持为存活、另加 `/ready` | 现有契约是 `/health` 不查库；但课程样例要求 `/health` 返回依赖状态。最终选择 `/live` 存活、`/health` 就绪、`/ready` 别名，并同步修改 `verify.py`，用课程语义覆盖旧契约。 |
| 把现有 `httpapi` SQL 全部迁到 repository 再交付 | 工作量大、风险高，会把骨架变更变成业务重构；本 change 登记 legacy 例外，只要求新增 `httpapi` 文件不写 SQL，材料库 change 再迁移。 |
| 用宿主机 Go 直接编译 | 课程标准启动方式是 Docker Compose；本机没有 Go。多阶段 Docker 构建更可复现，Go 镜像只在构建阶段使用。 |
| 手工截图表单验收 | 不可复现；改用 `make check` + 独立 Compose 的 `make grade`，报告落 `reports/teacher-*`。 |

## Capabilities

### New Capabilities

- `platform-foundation`：可复现启动、配置外置、存活/就绪、JSON 日志与请求 ID、优雅停机、分层门禁和验收证据。

### Modified Capabilities

无。现有业务接口保持不变；`/health` 的语义在 `auth-upload` 的部署条款中被本 change 修改，归档时合并。

## Evidence

- `make check` 退出码 0：规约、规范、OpenSpec strict、分层、密钥、变异、Go 测试/vet、前端构建。
- `make grade` 退出码 0：独立 Compose 项目 13 项检查，报告 `reports/teacher-*/report.html` 和 `report.json`。
- `python3 scripts/verify.py` 退出码 0：迭代 1/2 的登录、班级隔离、上传、检索、问答和停库场景全部通过。
- 证据记录：`docs/framework/verification.md`；标签 `v0.1.0-skeleton`。

## Open Questions

没有留给实现阶段的行为选择。实现若发现规约冲突，先修改本 change 的 delta，再改代码。
