# auth-upload Specification

## Purpose

本 change 只修改既有部署和健康检查条款：`/live` 表示进程存活，`/health` 表示依赖就绪；其余登录、角色、班级隔离、上传和读取条款继续有效。

## MODIFIED Requirements

### Requirement: Docker Compose 部署与健康检查

标准启动方式 MUST 是 Docker Compose 的 web、api、db、qdrant 四个服务。只有 web MUST 映射宿主端口。数据库和 Qdrant 端口 MUST NOT 映射到宿主。`GET /live` MUST 不要求登录，且 MUST NOT 访问 MySQL、Qdrant、嵌入或对话网关。`GET /health` MUST 不要求登录，检查 MySQL ping、Qdrant 可达和嵌入配置；全部通过返回 200 `{status:"ready"}`，任一失败返回 503 `{status:"not_ready"}`。数据库不可用时，业务接口 MUST 返回 503，而不是 401。`docker compose down` 之后再 `up`（不带 `-v`）MUST 保留已上传的数据。

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
