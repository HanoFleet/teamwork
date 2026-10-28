# 05 部署运维规范

| 项目 | 内容 |
| --- | --- |
| 规范编号 | `05-ops` |
| 掌管范围 | 制品、运行环境、构建、健康检查、日志、发布与回滚、数据变更顺序、备份恢复 |
| 落地方式 | 镜像、健康检查、日志字段、端口等常驻约束写入 `.cursor/rules/campusclaw-standards.mdc`；“按规范发一次版本”写成技能 |
| 违反时 | 不得发布；先改 Compose/Dockerfile/文档，再重新验证 |

## 这一页管什么

管一次发布从构建到回滚的完整路径：镜像是否可复现、环境是否只换配置、健康检查是否分层、日志是否能排障、回滚是否演练过、数据变更是否向后兼容。

不管：资源访问控制归 `03-security.md`；接口契约归 `02-backend.md`，本页只引用。

## 项目事实

> 旧实现已打包到 `archive/campusclaw-baseline.zip`；实现阶段从归档恢复对应目录。本文中的 `backend/`、`frontend/`、Compose 路径指恢复后的目标结构。

- Compose 服务：`web`（Nginx）、`api`（Go）、`db`（MySQL 8）、`qdrant`；只有 `web` 映射宿主端口 `WEB_PORT`（默认 8080）。
- 卷：`db_data`、`uploads`、`qdrant_data`；`docker compose down` 不带 `-v` 保留数据。
- `api` 镜像分两阶段：`golang:1.25-alpine` 构建，`alpine:3.21` 运行；运行镜像包含 `ca-certificates` 和 `poppler-utils`。
- 健康检查：`/live` 是存活检查，不查依赖；`/health` 是就绪检查，查 MySQL、Qdrant、嵌入配置；`/ready` 是 `/health` 的别名。
- 日志：stdout 单行 JSON，字段 `ts/level/msg/request_id`，请求日志加 `method/path/status/duration_ms`。
- 配置：全部来自 `.env`；`.env.example` 只保留键名/占位；密钥不入库。
- 数据迁移：`schema_migrations` 按版本执行，先加后删，保持旧版本可读。

## 规范条目

| 条目 | 项目事实 | 为什么 | 怎么检查 |
| --- | --- | --- | --- |
| 可复现构建 | `go.mod`/`go.sum`、`package-lock.json` 入库；Dockerfile 多阶段；运行镜像只放二进制和运行时依赖 | 同一提交构建出不同产物，回滚和排障都不可信 | 同一提交连续构建两次，镜像摘要或运行产物应一致 |
| 镜像标签 | 镜像用提交号或版本号打标签，不用 `latest` 作为唯一标识；`v2.0.0-baseline` 标记改造前基线，`v0.1.0-skeleton` 标记本次骨架 | 只有 `latest` 无法回退到确定版本 | `docker images` 能看到提交号/版本标签；README 记录对应关系 |
| 同镜像跨环境 | 开发、测试、演示共用同一镜像，只替换 `.env`；密钥与环境变体分开存放 | 换环境重新构建会引入未验证差异 | 用同一镜像换一份 `.env` 启动，功能一致 |
| 健康检查分层 | `/live` 200 只证明进程活着，不查 MySQL/Qdrant；`/health` 和 `/ready` 依赖正常 200，任一失败 503 并给 `checks` | 把存活和就绪混在一起会让“进程活着”和“能服务”混淆 | 停 db：`/live` 200、`/health` 503 `db=false`；停 Qdrant：`/health` 503 `qdrant=false` |
| 结构化日志 | stdout 单行 JSON；`ts` RFC3339 UTC；`request_id` 来自 `X-Request-ID` 或生成；不写口令、令牌、Cookie、正文、绝对路径、DSN | 多行日志和缺 request_id 无法串联一次请求 | `docker compose logs api` 每行可被 `jq` 解析；同一请求的响应头和日志 id 一致 |
| 优雅停机 | SIGTERM 后停止接新连接，等待在途请求最多 10 秒，再退出；迁移和索引写入不在中途强杀 | 直接 kill 会切断请求并留下半写状态 | 慢请求期间 `docker compose stop api`，请求完成且退出码 0 |
| 发布顺序 | 构建镜像打提交号 → 先加后删迁移 → 滚动/重建 api → `/ready` 通过 → 记录版本与验证结论 | 先删列/先切流量会导致旧版本不可用 | 按顺序演练一次；每步有命令和结果 |
| 回滚 | 保留上一版本镜像标签；回滚只切回上一标签，不反向执行迁移；步骤写进 README 并演练 | 没演练的回滚在故障时不可用 | 执行一次回滚，记录耗时；回滚后 `/ready` 通过 |
| 数据变更顺序 | 迁移先加列/表，代码同时兼容新旧；删除列/表放到下一个版本；`0001` 基线不改 | 先删后加会让旧实例和回滚失败 | 旧库升级后旧接口仍可用；回滚版本能读新结构 |
| 备份与恢复 | 备份 MySQL、`uploads` 卷、Qdrant 卷；保留期 7 天；每学期演练一次恢复 | 只备份数据库会丢失文件和向量 | 在临时目录恢复一次，材料详情、文件和检索都可用 |
| 端口与网络 | 只有 `web` 有 `ports`；`db`、`qdrant`、模型网关不映射宿主；api 只在 Compose 网络内 | 暴露数据库/Qdrant 等于绕过所有授权 | `docker compose config` 检查 `ports`；宿主连接 3306/6333 失败 |
| 版本标签与记录 | 骨架基线、每次发布打标签；`docs/verification.md` 记录版本、命令、结果、负责人 | 没有标签和记录无法复现“当时验的是什么” | `git tag` 有基线标签；验证记录含提交号 |

## 本课最小集合

1. 一键启动：`cp .env.example .env` → 填值 → `docker compose up --build -d --wait` → `/live` 200、`/health` 200。
2. 分层健康检查：`/live` 不查依赖；`/health`/`/ready` 查 MySQL、Qdrant、嵌入配置。
3. 单行 JSON 日志 + request ID。
4. 镜像/提交号标签和回滚路径。
5. 端口最小暴露：只有 `web`。
6. 备份清单：MySQL、`uploads`、Qdrant。

## 违反时怎么处理

- `/health` 只报存活：改为 `/live` 只报存活，`/health` 报依赖；这是本项目的明确语义。
- 日志多行或没有 request_id：补日志中间件，补单测。
- Compose 暴露 db/qdrant 端口：删除 `ports`，重新跑 `docker compose config`。
- 没有回滚标签或步骤：阻断发布，补标签和演练记录。
- 例外（例如本地 HTTP 下 Cookie 不加 `Secure`）：写进本规范，注明只在本地生效。
