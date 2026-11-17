# CampusClaw 2.0 · 小组项目仓库

> **当前提交重点：第 7 课骨架 + 第 8 课异步批改（已归档）+ 第 9 课安全加固（已归档）。** 第一眼入口是 [`SPEC.md`](SPEC.md)。Compose 六服务可启动；第 8 课异步判据、第 9 课 CSRF/配置权限/审计/SQLi-XSS-CSRF 反例和 SEC-08 实验均已通过本地、隔离验收和 CI。证据见 [`reports/`](reports/)。材料库是后续 change。

CampusClaw 把教研材料按班级放进可登录的知识库。教师上传材料，本班学生只读；正文切成切片后，本班可以用关键字、向量或混合检索，命中能回到原文；没有依据时不生成回答。

## 小组与角色

| 姓名 | 学号 | 角色 | 阶段一交付 |
| --- | --- | --- | --- |
| 李斯坦 | 2601210362 | 角色一：制定规约 | 规约、八类规范、可运行骨架、验收证据 |
| 韩雅慧 | 2601210643 | 角色二：开发系统 | 第 8 课异步批改、第 9 课安全加固实现；后续材料库 |
| 禹霖 | 2601210536 | 角色三：项目验收 | 第 8 课安全报告、第 9 课复评；逐条验收并写 `docs/verification.md` |

## 当前状态

- 已归档 change：`2026-10-28-establish-platform-foundation`（7 需求/19 场景）、`2026-11-05-add-async-grading`（10/32/30）、`2026-11-17-harden-security`（6/29/40）。
- 活动 change：`openspec/changes/2026-10-14-upgrade-material-library/`（26 条需求、151 个场景、46 条任务），后续材料库，尚未实现。
- 长期规约：`openspec/specs/` 下的 `platform-foundation`、`auth-upload`、`knowledge-retrieval`、`async-grading`、`security-hardening`。
- 第 8 课自查映射：[`docs/lesson-08/self-check.md`](docs/lesson-08/self-check.md)；第 9 课逐节对照：[`docs/lesson-09/checklist.md`](docs/lesson-09/checklist.md)。安全报告在 [`reports/security-fix-log.md`](reports/security-fix-log.md)、[`reports/gate-red-green.md`](reports/gate-red-green.md)、[`reports/sec08-experiment.md`](reports/sec08-experiment.md)。
- 标签：`v2.0.0-baseline`、`v0.1.0-skeleton`、`v2.0.0-stage1-spec`、`async-202`（第 8 课验收）。

## 项目启动四步

| 步骤 | 交付物 | 当前状态 |
| --- | --- | --- |
| 1 建仓库 | README、`.gitignore`、LICENSE、`.env.example`、协作约定 | 已完成 |
| 2 定规约 | foundation、async-grading、security-hardening 四份文件（已归档）+ material-library 四份文件（活动） | 已完成 |
| 3 立规范 | 八类规范、常驻规则、技能、`make check` 门禁 | 已完成 |
| 4 落骨架 | Compose 一条命令、`/live`/`/health`、JSON 日志、优雅停机、`v0.1.0-skeleton` | 已完成 |

## 快速启动

```bash
cp .env.example .env
# 填写 SESSION_SECRET、MYSQL_ROOT_PASSWORD、DB_PASSWORD 和三个 SEED_*_PASSWORD
# APP_VERSION 默认 v2.0.0-skeleton，SHUTDOWN_TIMEOUT_SECONDS 默认 10
docker compose up --build -d --wait
curl -fsS http://localhost:8080/live
curl -fsS http://localhost:8080/health
```

- 登录页：`http://localhost:8080/`
- `/live`：存活，不查依赖。
- `/health`：就绪，检查 MySQL、Qdrant、嵌入配置；依赖不可用返回 503。
- `/ready`：`/health` 的别名。
- 只有 web 映射宿主端口；db、qdrant、api、rabbitmq、worker 不对外。
- 作业页：`http://localhost:8080/assignments`（学生提交后轮询批改状态）。
- `.env` 还需填写 `RABBITMQ_DEFAULT_PASS` 和 `RABBITMQ_URL`（与 broker 口令一致）。

## 门禁

```bash
make check            # 规约、规范、strict、分层、密钥、变异、Go 测试/vet、前端构建、注入反例文件
make check-security   # security_gate：SEC-05 密钥 + SEC-06 npm/govulncheck，命中非 0
make grade            # 独立 Compose 项目 18 项（含 A15 异步、A16-A18 安全），生成 reports/teacher-*/ 报告
python3 scripts/verify.py   # 迭代 1/2、第 8 课三条判据、第 9 课安全回归
cd frontend/e2e && npx playwright test   # /assignments 提交并轮询
```

`.github/workflows/check.yml` 在每次 push 和 PR 上跑 `make check-security`、`make check`、`make grade` 和 `verify`（Compose + 三条异步判据 + 安全回归 + Playwright）；main 上 [run 44044051264](https://github.com/HanoFleet/teamwork/actions/runs/44044051264) 的 check/grade/verify 三个 job 均成功。

`make check` 的 `spec_check.py` 检查活动 change `material-library`；归档的 async-grading/security-hardening 由 `openspec validate --all --strict` 和长期 specs 检查。`make check-security` 是真实门禁：假密钥 self-test 退出 1，正常仓库退出 0；Go 依赖由 `govulncheck` v1.9.0 在 Go 1.26.11 上复扫，有通报则退出 1。SEC-01～SEC-04、SEC-07/SEC-08 由 `verify.py` 和 `reports/` 复测。注入反例文件在 `make check` 的 `security_cases.py` 里检查。

`make grade` 使用独立项目名、随机端口和随机口令，不修改正式数据；报告写入 `reports/teacher-*`，证据汇总在 [`docs/verification.md`](docs/verification.md) 与 [`docs/lesson-09/checklist.md`](docs/lesson-09/checklist.md)。

## 规约入口

### 当前：platform foundation（已归档）

| 文件 | 内容 |
| --- | --- |
| [`proposal.md`](openspec/changes/archive/2026-10-28-establish-platform-foundation/proposal.md) | 为什么加固骨架、范围、放弃方案 |
| [`design.md`](openspec/changes/archive/2026-10-28-establish-platform-foundation/design.md) | 分层、`/live`/`/health`、日志、停机、legacy 例外 |
| [`specs/`](openspec/changes/archive/2026-10-28-establish-platform-foundation/specs/) | 7 条需求、19 个场景 |
| [`tasks.md`](openspec/changes/archive/2026-10-28-establish-platform-foundation/tasks.md) | 9 条任务和验证证据 |

### 已归档：async grading（第 8 课）

| 文件 | 内容 |
| --- | --- |
| [`proposal.md`](openspec/changes/archive/2026-11-05-add-async-grading/proposal.md) | RabbitMQ、outbox、worker、202 + task_id、三条判据 |
| [`design.md`](openspec/changes/archive/2026-11-05-add-async-grading/design.md) | 队列拓扑、状态机、事务序列、幂等键、失败分类 |
| [`specs/async-grading/spec.md`](openspec/specs/async-grading/spec.md) | 10 条需求、32 个场景，已并入长期 spec |
| [`tasks.md`](openspec/changes/archive/2026-11-05-add-async-grading/tasks.md) | 30 条任务全部勾选，`async-202` |

### 已归档：security hardening（第 9 课）

| 文件 | 内容 |
| --- | --- |
| [`proposal.md`](openspec/changes/archive/2026-11-17-harden-security/proposal.md) | CSRF、配置权限、技能入口、审计、注入反例、门禁和 SEC-08 |
| [`design.md`](openspec/changes/archive/2026-11-17-harden-security/design.md) | 会话 token、审计表、catalog、技能包装、安全测试 |
| [`specs/security-hardening/spec.md`](openspec/specs/security-hardening/spec.md) | 6 条需求、29 个场景，已并入长期 spec |
| [`tasks.md`](openspec/changes/archive/2026-11-17-harden-security/tasks.md) | 40 条任务全部勾选 |

逐节对照见 [`docs/lesson-09/checklist.md`](docs/lesson-09/checklist.md)。

### 后续：material library（活动规约）

| 文件 | 内容 |
| --- | --- |
| [`proposal.md`](openspec/changes/2026-10-14-upgrade-material-library/proposal.md) | 材料库、多格式、版本、回收站、阅读进度 |
| [`design.md`](openspec/changes/2026-10-14-upgrade-material-library/design.md) | 迁移、抽取、先建后换、版本冲突、原文坐标 |
| [`specs/`](openspec/changes/2026-10-14-upgrade-material-library/specs/) | 26 条需求、151 个场景 |
| [`tasks.md`](openspec/changes/2026-10-14-upgrade-material-library/tasks.md) | 46 条任务，尚未勾选 |

## 接口与语义

| 方法与路径 | 说明 |
| --- | --- |
| `GET /live` | 存活；不访问依赖，200 `{status:"ok",version,time}` |
| `GET /health` | 就绪；检查 MySQL、Qdrant、嵌入，200 `ready` / 503 `not_ready` |
| `GET /ready` | `/health` 别名 |
| 现有 `/api/login`、`/api/materials`、`/api/search`、`/api/ask` | 保持迭代 1/2 行为；本阶段不改业务 |
| 第 8 课异步批改 | `GET /api/assignments`、`POST /api/assignments/{id}/submissions`、`POST /api/submissions/{id}/grade` 返回 202 + `task_id`、`GET /api/tasks/{task_id}` 只读查询 |
| 第 9 课安全配置 | `GET/PATCH /api/skills`、`GET/PATCH /api/assistants`、`POST /api/skills/{key}/run`、`GET /api/audit-logs`（教师） |

`/health` 和 `/ready` 拒绝 query 参数（400），非 GET 返回 405；未知 `/api/*` 返回 404；未登录业务接口返回 401。

## 工程规范（八类）

| 规范 | 文件 | 检查方式 |
| --- | --- | --- |
| 产品设计（含前端） | [`docs/standards/01-product.md`](docs/standards/01-product.md) | 路由清单、四态、术语、键盘与断点 |
| 后端开发 | [`docs/standards/02-backend.md`](docs/standards/02-backend.md) | 分层、错误码、幂等、分页、迁移 |
| 安全开发 | [`docs/standards/03-security.md`](docs/standards/03-security.md) | 默认拒绝、越权、密钥、输入输出 |
| 测试 | [`docs/standards/04-testing.md`](docs/standards/04-testing.md) | 三层用例、场景追溯、数据隔离、门禁 |
| 部署运维 | [`docs/standards/05-ops.md`](docs/standards/05-ops.md) | 镜像、`/live`/`/health`、日志、回滚 |
| AI 应用 | [`docs/standards/06-ai.md`](docs/standards/06-ai.md) | 无依据拒答、提示词版本、超时降级 |
| 数据 | [`docs/standards/07-data.md`](docs/standards/07-data.md) + [`docs/data-dictionary.md`](docs/data-dictionary.md) | 命名审计、迁移、敏感分级、删除副本 |
| 评审与完成定义 | [`docs/standards/08-review.md`](docs/standards/08-review.md) | DoD、门禁、证据、提交信息 |

常驻入口：`AGENTS.md` 和 `.cursor/rules/campusclaw-standards.mdc`；按动作执行的步骤在 `.cursor/skills/campusclaw-engineering/SKILL.md`。

## 仓库结构

```text
.
├── SPEC.md                     本次提交的一页入口
├── README.md                   本文件
├── AGENTS.md                   项目规则
├── Makefile                    up / check / check-security / grade
├── docker-compose.yml          web / api / db / qdrant / rabbitmq / worker（仅 web 映射宿主端口）
├── .env.example                环境变量模板，只写键名和占位
├── LICENSE                     未选择许可证说明
├── backend/                    Go api 与 worker：cmd/server、cmd/worker、
│                               httpapi、grading、queue、outbox、worker、
│                               retrieval、db、config、auth、health、logging、lifecycle
├── frontend/                   React 18 + Vite 8 + Nginx
├── deploy 相关                 各 Dockerfile 与 Nginx 配置
├── scripts/
│   ├── check.sh                完整门禁
│   ├── acceptance.py           隔离验收与报告
│   ├── grade.sh                验收入口
│   ├── layer_check.py          分层静态检查
│   ├── secret_scan.py          工作树和历史密钥扫描
│   ├── mutation.py             分层门禁变异验证
│   ├── spec_check.py           规约结构自查
│   ├── standards_check.py      八类规范自查
│   ├── verify.py               迭代 1/2、第 8 课判据、第 9 课安全回归
│   ├── async_test.py           第 8 课三条判据
│   ├── security_test.py        第 9 课 SQLi/XSS/CSRF/配置/审计
│   ├── security_gate.py        SEC-05/06 门禁与红绿自测
│   ├── security_static.py      前端 token/raw HTML 静态检查
│   ├── sec08_experiment.py     SEC-08 四步实验
│   └── ci_env.py               CI verify job 隔离环境
├── apitest/cases/async/        第 8 课三条判据用例说明
├── apitest/cases/security/     第 9 课安全反例说明
├── frontend/e2e/               Playwright /assignments 测试
├── reports/                    第 8/9 课实际证据与复评记录
├── docs/
│   ├── lesson-07/verification.md + teacher-report.html/json
│   ├── lesson-08/self-check.md  第 8 课 10 行自查映射
│   ├── lesson-08/security-inventory.md  受保护/写入接口清单
│   ├── lesson-09/checklist.md  第 9 课七节对照
│   ├── lesson-09/sec08/        SEC-08 素材
│   ├── standards/01-08
│   ├── data-dictionary.md
│   ├── 阶段一-交付说明.md
│   ├── 项目启动-四步核对.md
│   └── 个人贡献记录.md
├── openspec/
│   ├── specs/                  platform-foundation、auth-upload、knowledge-retrieval、
│   │                           async-grading、security-hardening
│   └── changes/
│       ├── archive/            foundation、async-grading、security-hardening
│       └── 2026-10-14-upgrade-material-library/  后续材料库
└── archive/
    ├── campusclaw-baseline.zip 基线历史快照
    └── README.md               归档说明
```

## 第一次提交检查

| 检查项 | 现状 |
| --- | --- |
| README 有项目定位和克隆到启动步骤 | 有；`docker compose up --build -d --wait` |
| `.gitignore` 过滤依赖、构建产物、密钥、临时文件 | 有；含 `node_modules`、`dist`、`.env`、`reports/teacher-*`、`.env.acceptance` |
| LICENSE 或“未选择”说明 | 有；见下面“许可证” |
| 协作约定写进 README | 有；主干唯一、变更命名、提交依据、每人跑通、密钥边界 |
| `.env.example` 只写键名和占位 | 有 |
| 变更目录按 `YYYY-MM-DD-英文名` 命名 | 有；foundation、material-library、async-grading 都带日期 |
| 归档后的规约能在主干检索到 | 有；`openspec/specs/` 和 `openspec/changes/archive/` |
| 第 8 课 10 行自查有规约映射 | 有；`docs/lesson-08/self-check.md`；角色二已实现，角色三验收待执行 |
| 全部提交历史检索不到密钥 | `make check` 的 `secret_scan.py` 已扫描工作树和历史 |
| 主干保护、直接推送被拒绝 | 需在 GitHub 仓库设置中开启；功能开发走 `change/<change-name>` |
| 每位成员独立克隆跑通 | 待组员按 README 各自执行一次 |

## 协作约定

- **主干唯一**：`main` 是唯一主干；功能开发在 `change/<change-name>` 分支，评审后合并。开始写功能代码后，`main` 设保护规则，直接推送应被拒绝。
- **每次改动一条变更**：命名 `YYYY-MM-DD-短横小写英文名`；验收通过后归档，归档规约并入 `openspec/specs/`。
- **提交信息写依据**：`<type>(<capability>): <task-id> <一句话>`，正文含 `Change:`、`Task:`、`Spec:`、`Verify:`。
- **每人克隆跑通**：每位成员按 README 从零启动并确认 `/live` 与 `/health`。
- **分工不是各写各的**：角色一、二、三只是评审和交付责任，规约、规范、骨架由全组一起定、一起评审。
- **密钥边界**：只放 `.env.example`；密钥不进代码、镜像、前端构建、日志、问题单和截图；泄露立即轮换并重写历史。
- **归档**：全部验收通过后才合并 delta 并归档；归档后 `openspec/specs/` 是长期事实来源。

## 许可证

未选择许可证。课程作业保留所有权利；如需复用代码、规约或规范，请先联系作者。详见 [`LICENSE`](LICENSE)。

## 链接

- 团队仓库：https://github.com/HanoFleet/teamwork
- 第 7 课案例：https://devops.hello1023.com/课件/第7课-课件-小组项目启动/pages/case.html
- 第 8 课任务清单：https://devops.hello1023.com/课程任务清单-第8课.html
