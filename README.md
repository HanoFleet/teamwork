# CampusClaw 2.0 · 小组项目仓库

CampusClaw 把教研材料按班级放进可登录的知识库。教师上传材料，本班学生只读；正文切成切片后，本班可以用关键字、向量或混合检索，命中能回到原文；没有依据时不生成回答。本仓库是第 7 课小组项目的主仓库，基线来自 CampusClaw 迭代 1/2。

## 小组与角色

| 姓名 | 学号 | 角色 | 阶段一交付 |
| --- | --- | --- | --- |
| 李斯坦 | 2601210362 | 角色一：制定规约 | 本 change 的四份文件、八类工程规范、四步核对 |
| 韩雅慧 | 2601210643 | 角色二：开发系统 | 评审规约与规范；后续按 `tasks.md` 实现 |
| 禹霖 | 2601210536 | 角色三：项目验收 | 评审规约与规范；后续扩展 `verify.py` 并逐条验收 |

## 项目启动四步

第 7 课要求一次完成四步，每一步的产物是下一步的输入。本仓库的对应关系：

| 步骤 | 交付物 | 仓库位置 | 完成现象 | 当前状态 |
| --- | --- | --- | --- | --- |
| 1 建仓库 | 仓库、README、忽略规则、协作约定 | 仓库根目录、`.gitignore`、`AGENTS.md` | 克隆后按 README 跑通；主干随时可启动 | 已完成；`verify.py` 基线通过 |
| 2 定规约 | 一份变更的四份文件 | `openspec/changes/upgrade-material-library/` | `--strict` 通过；另起会话可照做 | 格式与结构已完成；另起会话评审待三人执行 |
| 3 立规范 | 规则文件与按需调用的技能 | `docs/standards/`、`.cursor/rules/`、`AGENTS.md` | 改一次代码产物的分层命名符合规范；换会话结果一致 | 八类规范已落文件；`standards_check.py` 通过；换会话一致性待评审 |
| 4 落骨架 | 可启动最小实现、健康检查、版本标签 | `docker-compose.yml`、`backend/`、`frontend/` | 克隆 → 填配置 → 一条命令 → `/health` 成功 | 基线已具备；本 change 的 0 组先复核，1.7/1.8 补日志与 `/ready` |

三类偏差的自查：没有“先写代码后补规约”；规范已落成文件，不是留在会话里；本 change 按材料库增量交付，不是一次生成整套业务。

详细证据和待办见 [`docs/项目启动-四步核对.md`](docs/项目启动-四步核对.md)。

## 当前阶段：阶段一 · 制定规约与立规范

本轮**只交付规约和规范，不实现功能**。变更名：`upgrade-material-library`。

入口：`openspec/changes/upgrade-material-library/`

| 文件 | 回答的问题 | 评审标准 |
| --- | --- | --- |
| [`proposal.md`](openspec/changes/upgrade-material-library/proposal.md) | 为什么做、做到哪、不做什么、放弃过哪些方案 | 不读代码也能判定本次改动的必要性；至少有 3 条“不做”和 1 条被放弃的候选方案 |
| [`design.md`](openspec/changes/upgrade-material-library/design.md) | 选型、分层、关键取舍、接口、数据模型、状态机 | 每条取舍都写明“选了什么、放弃了什么、代价由谁承担” |
| [`specs/`](openspec/changes/upgrade-material-library/specs/) | 四条能力、28 条需求、143 个场景 | 每个场景是“前置条件 / 操作 / 可观测结果”，每条需求至少一个场景 |
| [`tasks.md`](openspec/changes/upgrade-material-library/tasks.md) | 按什么顺序实现、每条怎么验 | 骨架任务排最前；每条都有 `涉及` 和 `verify` |

四份文件的具体阅读顺序建议：先看 `proposal.md` 的“本次做到哪 / 本次不做 / 放弃的候选方案”，再看 `design.md` 的“关键取舍”，然后按能力读 `specs/`，最后用 `tasks.md` 判断实现顺序。

## 工程规范（八类）

课程要求“立规范”：前五类必修，后三类按项目性质选做。CampusClaw 是带 AI 和数据存储的项目，因此八类全部落成文件；产品规范同时承载前端约定，AI、数据、评审三类分别对应模型调用、MySQL/Qdrant/上传卷和三人协作。每条规范都带项目事实和“怎么检查”，能自动检查的写进脚本，其余写进评审表。

| 规范 | 类型 | 文件 | 检查方式 |
| --- | --- | --- | --- |
| 产品设计（含前端） | 必修 | [`docs/standards/01-product.md`](docs/standards/01-product.md) | 路由清单、四态文案、术语表、键盘与断点走查 |
| 后端开发 | 必修 | [`docs/standards/02-backend.md`](docs/standards/02-backend.md) | 分层落点、错误码表、幂等声明、分页边界、迁移回滚 |
| 安全开发 | 必修 | [`docs/standards/03-security.md`](docs/standards/03-security.md) | 未登记路由、越权重放、密钥 grep、移除授权看测试是否变红 |
| 测试 | 必修 | [`docs/standards/04-testing.md`](docs/standards/04-testing.md) | 三层用例、场景追溯、数据隔离、断言变异、一键命令 |
| 部署运维 | 必修 | [`docs/standards/05-ops.md`](docs/standards/05-ops.md) | `docker compose config`、`/health`+`/ready`、日志 `jq`、回滚演练 |
| AI 应用 | 选用 | [`docs/standards/06-ai.md`](docs/standards/06-ai.md) | 无依据拒答、提示词版本、超时降级、10–20 条评测集 |
| 数据 | 选用 | [`docs/standards/07-data.md`](docs/standards/07-data.md) + [`docs/data-dictionary.md`](docs/data-dictionary.md) | 命名审计、迁移只增、敏感分级、删除副本演练 |
| 评审与完成定义 | 选用 | [`docs/standards/08-review.md`](docs/standards/08-review.md) | DoD 五项、门禁全绿、证据归档、提交信息三字段 |

常驻入口：`.cursor/rules/campusclaw-standards.mdc`（`alwaysApply: true`）和 `AGENTS.md`。安全与评审两类按课程要求直接写进 `AGENTS.md`，其余规范以 `docs/standards/` 为唯一全文来源，规则文件只保留红线和阅读入口，避免两处内容漂移。

### 本轮边界（摘要）

**做：**

- 可演进的数据库迁移；PDF、DOCX、PPTX 上传；后台索引与状态；先建后换的重建。
- 材料版本历史、编辑冲突、文件替换、回收站、标签、排序分页、阅读进度、收藏。
- 原文码点定位、页码/幻灯片号、旧引用提示。
- 前端壳层拆分、全局搜索、统一反馈；登录限流、嵌入维度、Cookie、CSP、结构化日志、`/health` 与 `/ready` 分离等底座修复。

**不做：**

- 会话历史、追问、SSE、班级助手、AI 技能（模块二）。
- 课程单元、作业、练习、错题、公告、通知、学情统计（模块三）。
- 邀请码注册、CSV 批量导入、口令重置、超级管理员、AI 批改作业。
- 外部队列、Redis、对象存储、UI 框架、富文本编辑器。

完整清单见 `proposal.md` 的 “Out of Scope”。

### 怎么校验

官方格式校验（需要 Node.js）：

```bash
npx -y @fission-ai/openspec@1.15.0 validate upgrade-material-library --strict
```

仓库自带的结构自查和规范自查：

```bash
python3 scripts/spec_check.py
python3 scripts/standards_check.py
```

三条命令的预期结果都是退出码 0。`spec_check.py` 检查四份文件是否齐备、每个场景是否有 `GIVEN/WHEN/THEN`、每个需求是否至少有一个场景、失败路径是否覆盖四类、能力与场景对应表是否覆盖四个能力、tasks 是否以骨架任务开头且每条带 `verify`。`standards_check.py` 检查八类规范文件、`AGENTS.md` 与 `.cursor/rules/` 入口、每类规范的“怎么检查”列、数据字典和四步核对文件。

### 怎么评审（另起会话测试）

课程对“定规约”的实质检查不是格式，而是：**另起一个不带历史上下文的会话，只给仓库路径和变更名，执行者能按任务清单实现，且问不出规约没回答的问题。**

建议按下面步骤做一次：

1. 新开一个会话，只输入：仓库路径 + `upgrade-material-library`。
2. 要求它先读 `proposal.md`、`design.md`、`specs/`、`tasks.md`，然后列出它认为含糊或缺失的行为问题。
3. 如果它能直接按 `tasks.md` 编号实现，且问题只涉及代码细节而不是业务行为，规约就算通过；如果它问“这个接口返回什么”“跨班返回 403 还是 404”“失败后旧数据还在不在”，说明对应场景还缺判定。

**立规范的另起会话测试**：新开会话，只给仓库路径，要求它“按 `docs/standards/02-backend.md` 加一个材料标签接口”。检查目录是否落在 `httpapi/library/db` 的规定层、命名是否是 `/api/materials/{id}` + PATCH、错误是否只用错误码清单里的 code、是否声明幂等。换一个会话再做一次，两次结果应一致；不一致说明规范还停留在某次会话里。

### 能力与场景对应

| Capability | 类型 | 需求数 | 场景数 |
| --- | --- | ---: | ---: |
| `platform-foundation` | 新增 | 7 | 27 |
| `material-library` | 新增 | 9 | 42 |
| `auth-upload` | 修改 | 7 | 44 |
| `knowledge-retrieval` | 修改 | 5 | 30 |
| **合计** |  | **28** | **143** |

每个需求的详细场景见 `specs/<capability>/spec.md`；失败路径、放弃方案和验收证据见 `proposal.md`。

## 仓库结构

```text
.
├── AGENTS.md                         项目规则（规约先行、权限在服务端、密钥不入库）
├── README.md                         本文件
├── ITERATION.md                      迭代 1 的设计说明
├── docker-compose.yml                web / api / db / qdrant
├── .env.example                      环境变量模板，不含真实密钥
├── .cursor/
│   ├── rules/campusclaw-standards.mdc 常驻工程规范入口
│   └── skills/campusclaw-engineering/SKILL.md 加页面/加接口/补测试/发版本四类动作
├── backend/                          Go api：auth、materials、retrieval、httpapi
├── frontend/                         React + Vite + Nginx
├── scripts/
│   ├── verify.py                     现有验收脚本
│   ├── spec_check.py                 阶段一规约结构自查
│   └── standards_check.py            八类工程规范自查
├── docs/
│   ├── CampusClaw-2.0-规划.md        2.0 三个模块的总体规划
│   ├── verification.md               现有验收记录
│   ├── 阶段一-交付说明.md            本阶段交付物、校验记录和评审指引
│   ├── 项目启动-四步核对.md          四步交付物、完成现象和待办
│   ├── 个人贡献记录.md               三人分工与提交对应关系
│   ├── data-dictionary.md            字段、约束、敏感级别和删除规则
│   └── standards/
│       ├── 01-product.md             产品设计（含前端）
│       ├── 02-backend.md             后端开发
│       ├── 03-security.md            安全开发
│       ├── 04-testing.md             测试
│       ├── 05-ops.md                 部署运维
│       ├── 06-ai.md                  AI 应用
│       ├── 07-data.md                数据
│       └── 08-review.md              评审与完成定义
└── openspec/
    ├── config.yaml                   OpenSpec 项目上下文
    ├── specs/                        已归档的长期规约（事实来源）
    └── changes/
        ├── archive/                  已归档的历史 change
        └── upgrade-material-library/ 本阶段的活动 change
```

## 运行基线（阶段一不要求改动）

标准启动方式只有 Docker Compose。本机直接跑 Go 二进制不算交付。

```bash
cp .env.example .env
# 填写 SESSION_SECRET、MYSQL_ROOT_PASSWORD、DB_PASSWORD 和三个 SEED_*_PASSWORD
# 检索相关项可先保持 .env.example 里的 local / Qdrant 地址
# SESSION_SECRET 至少 16 个字符，每个口令至少 8 个字符
docker compose up --build -d
docker compose ps
```

首次启动 MySQL 可能要几十秒。在这之前打开页面可能短暂看到 502，等 api 连上数据库后即可登录。

- 登录页：`http://localhost:8080/`（端口由 `.env` 的 `WEB_PORT` 决定）
- 存活检查：`http://localhost:8080/health`，不需要登录，不查询数据库
- 就绪检查：`http://localhost:8080/ready`，不需要登录，返回 MySQL、Qdrant 和嵌入配置状态（本 change 的 1.8 实现）

数据库端口不映射到宿主机。要查表时进入容器：

```bash
docker compose exec db mysql -u"$DB_USER" -p"$DB_PASSWORD" campusclaw
```

`docker compose down` 之后再 `up`（不要加 `-v`）会保留数据库、已上传文件和 Qdrant 向量。`-v` 会清空卷，只在想重置时使用。

预置账号：

| 用户名 | 角色 | 班级 | 口令 |
| --- | --- | --- | --- |
| `teacher_a` | 教师 | A | `.env` 里的 `SEED_TEACHER_PASSWORD` |
| `student_a1` | 学生 | A | `SEED_STUDENT_A_PASSWORD` |
| `student_b1` | 学生 | B | `SEED_STUDENT_B_PASSWORD` |

预置材料标题是「A班-函数单调性讲义」和「B班-牛顿定律笔记」。A 班检索「牛顿定律」应得到空 `hits`。现有接口是 `POST /api/search` 和 `POST /api/ask`。

现有验收：

```bash
python3 scripts/verify.py
```

脚本会按 README 的场景请求本机 Compose，并把不含口令的结果写到 `docs/verification.md`。

### 现有底线（本 change 不破坏）

1. 班级只来自服务端会话，请求里的 `class_id` 一律忽略。
2. 跨班、已删除、同班他人私有和不存在 id 都返回同形 404。
3. 没有依据就不生成；所有 AI 输出带出处。
4. Qdrant 和模型网关不映射宿主，密钥只在服务端。
5. 只用 Docker Compose 启动，只有 web 映射端口；`/health` 不查数据库。
6. 上传要么全部写入，要么什么都不留。
7. 不做超级管理员，不让 AI 给作业打分。

## 协作约定

- **规约先行**：没有写进 OpenSpec delta 的行为不实现。规约含糊或没写“不做”时，先改 delta，再改代码。
- **角色边界**：角色一负责提案、设计、规约和任务清单；角色二只实现规约行为；角色三写验收、逐条判定，不写功能代码。
- **分支与提交**：功能开发在 `change/<change-name>` 分支进行；提交信息写 `<type>(<capability>): <task-id> <一句话>`，例如 `feat(material-library): 2.4 上传写入 v1 并异步索引`。
- **勾选规则**：一个 task 做完并跑过该条 `verify`，才勾选 `tasks.md`；不能用“代码已写”代替验收证据。
- **评审**：每个 change 先由三人评审规约，确认无歧义后再进入实现；实现中发现冲突，先改 delta。
- **密钥**：`.env`、上传文件和数据库文件不进 Git；仓库只保留 `.env.example`。
- **归档**：全部验收通过后才把 delta 合并到 `openspec/specs/` 并归档 change；归档后 `openspec/specs/` 是长期事实来源。

## 链接

- 团队仓库：https://github.com/HanoFleet/teamwork
- 课程案例：https://devops.hello1023.com/课件/第7课-课件-小组项目启动/pages/case.html
