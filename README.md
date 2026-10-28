# CampusClaw 2.0 · 小组项目仓库

> **本次提交重点：第 7 课可运行骨架 + 规约。** 第一眼入口是 [`SPEC.md`](SPEC.md)。当前骨架已从基线恢复并加固，`docker compose up -d --wait` 可启动；材料库是下一个 change。

CampusClaw 把教研材料按班级放进可登录的知识库。教师上传材料，本班学生只读；正文切成切片后，本班可以用关键字、向量或混合检索，命中能回到原文；没有依据时不生成回答。

## 小组与角色

| 姓名 | 学号 | 角色 | 阶段一交付 |
| --- | --- | --- | --- |
| 李斯坦 | 2601210362 | 角色一：制定规约 | 规约、八类规范、可运行骨架、验收证据 |
| 韩雅慧 | 2601210643 | 角色二：开发系统 | 评审；后续按 `tasks.md` 实现材料库 |
| 禹霖 | 2601210536 | 角色三：项目验收 | 评审；逐条验收并写 `docs/verification.md` |

## 当前状态

- 已归档 change：`openspec/changes/archive/2026-10-28-establish-platform-foundation/`（7 条需求、19 个场景）。
- 活动 change：`openspec/changes/2026-10-14-upgrade-material-library/`（26 条需求、136 个场景、46 条任务），尚未实现。
- 长期规约：`openspec/specs/` 下的 `platform-foundation`、`auth-upload`、`knowledge-retrieval`。
- 标签：`v2.0.0-baseline`（骨架基线）、`v0.1.0-skeleton`（本次骨架）、`v2.0.0-stage1-spec`（规约提交）。

## 项目启动四步

| 步骤 | 交付物 | 当前状态 |
| --- | --- | --- |
| 1 建仓库 | README、`.gitignore`、LICENSE、`.env.example`、协作约定 | 已完成 |
| 2 定规约 | foundation 四份文件（已归档）+ material-library 四份文件（活动） | 已完成 |
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
- 只有 web 映射宿主端口；db、qdrant、api 不对外。

## 门禁

```bash
make check     # 规约、规范、strict、分层、密钥、变异、Go 测试/vet、前端构建
make grade     # 独立 Compose 项目 14 项验收，生成 reports/teacher-*/ 报告

`.github/workflows/check.yml` 在每次 push 和 PR 上跑 `make check` 与 `make grade`。
python3 scripts/verify.py   # 迭代 1/2 的登录、隔离、上传、检索、问答
```

`make grade` 使用独立项目名、随机端口和随机口令，不修改正式数据；报告写入 `reports/teacher-*`，证据汇总在 [`docs/framework/verification.md`](docs/framework/verification.md)。

## 规约入口

### 当前：platform foundation（已归档）

| 文件 | 内容 |
| --- | --- |
| [`proposal.md`](openspec/changes/archive/2026-10-28-establish-platform-foundation/proposal.md) | 为什么加固骨架、范围、放弃方案 |
| [`design.md`](openspec/changes/archive/2026-10-28-establish-platform-foundation/design.md) | 分层、`/live`/`/health`、日志、停机、legacy 例外 |
| [`specs/`](openspec/changes/archive/2026-10-28-establish-platform-foundation/specs/) | 7 条需求、19 个场景 |
| [`tasks.md`](openspec/changes/archive/2026-10-28-establish-platform-foundation/tasks.md) | 9 条任务和验证证据 |

### 后续：material library（活动）

| 文件 | 内容 |
| --- | --- |
| [`proposal.md`](openspec/changes/2026-10-14-upgrade-material-library/proposal.md) | 材料库、多格式、版本、回收站、阅读进度 |
| [`design.md`](openspec/changes/2026-10-14-upgrade-material-library/design.md) | 迁移、抽取、先建后换、版本冲突、原文坐标 |
| [`specs/`](openspec/changes/2026-10-14-upgrade-material-library/specs/) | 26 条需求、136 个场景 |
| [`tasks.md`](openspec/changes/2026-10-14-upgrade-material-library/tasks.md) | 46 条任务，尚未勾选 |

## 接口与语义

| 方法与路径 | 说明 |
| --- | --- |
| `GET /live` | 存活；不访问依赖，200 `{status:"ok",version,time}` |
| `GET /health` | 就绪；检查 MySQL、Qdrant、嵌入，200 `ready` / 503 `not_ready` |
| `GET /ready` | `/health` 别名 |
| 现有 `/api/login`、`/api/materials`、`/api/search`、`/api/ask` | 保持迭代 1/2 行为；本阶段不改业务 |

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
├── Makefile                    up / check / grade
├── docker-compose.yml          web / api / db / qdrant
├── .env.example                环境变量模板，只写键名和占位
├── LICENSE                     未选择许可证说明
├── backend/                    Go api：cmd、httpapi、service、domain、
│                               repository、health、logging、lifecycle、config
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
│   └── verify.py               迭代 1/2 验收
├── docs/
│   ├── framework/verification.md + teacher-report.html/json
│   ├── standards/01-08
│   ├── data-dictionary.md
│   ├── 阶段一-交付说明.md
│   ├── 项目启动-四步核对.md
│   └── 个人贡献记录.md
├── openspec/
│   ├── specs/                  platform-foundation、auth-upload、knowledge-retrieval
│   └── changes/
│       ├── archive/            历史 change（含本次 foundation）
│       └── 2026-10-14-upgrade-material-library/  后续材料库
└── archive/
    ├── campusclaw-baseline.zip 基线历史快照
    └── README.md               归档说明
```

## 第一次提交检查

| 检查项 | 现状 |
| --- | --- |
| README 有项目定位和克隆到启动步骤 | 有；`docker compose up --build -d --wait` |
| `.gitignore` 过滤依赖、构建产物、密钥、临时文件 | 有；含 `node_modules`、`dist`、`.env`、`reports`、`.env.acceptance` |
| LICENSE 或“未选择”说明 | 有；见下面“许可证” |
| 协作约定写进 README | 有；主干唯一、变更命名、提交依据、每人跑通、密钥边界 |
| `.env.example` 只写键名和占位 | 有 |
| 变更目录按 `YYYY-MM-DD-英文名` 命名 | 有；foundation 和 material-library 都带日期 |
| 归档后的规约能在主干检索到 | 有；`openspec/specs/` 和 `openspec/changes/archive/` |
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
- 课程案例：https://devops.hello1023.com/课件/第7课-课件-小组项目启动/pages/case.html
