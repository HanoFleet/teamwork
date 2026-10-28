# CampusClaw 2.0 · 小组项目仓库

> **本次提交重点：阶段一“制定规约”。** 第一眼入口是 [`SPEC.md`](SPEC.md)；完整规约在 `openspec/changes/2026-10-14-upgrade-material-library/`。改造前的可运行实现已打包成 [`archive/campusclaw-baseline.zip`](archive/campusclaw-baseline.zip)，根目录不再散落业务代码。

CampusClaw 把教研材料按班级放进可登录的知识库。教师上传材料，本班学生只读；正文切成切片后，本班可以用关键字、向量或混合检索，命中能回到原文；没有依据时不生成回答。本仓库是第 7 课小组项目的主仓库。

## 小组与角色

| 姓名 | 学号 | 角色 | 阶段一交付 |
| --- | --- | --- | --- |
| 李斯坦 | 2601210362 | 角色一：制定规约 | 本 change 的四份文件、八类工程规范、四步核对、旧实现归档 |
| 韩雅慧 | 2601210643 | 角色二：开发系统 | 评审规约与规范；后续按 `tasks.md` 实现 |
| 禹霖 | 2601210536 | 角色三：项目验收 | 评审规约与规范；后续扩展验收脚本并逐条验收 |

## 提交重点

这次按老师要求只制定规约，所以仓库根目录只保留：

- `SPEC.md`：一页看懂规约的入口。
- `openspec/`：完整规约、长期规约和历史 change。
- `docs/standards/`：八类工程规范。
- `docs/` 下的交付说明、四步核对、数据字典和贡献记录。
- `archive/campusclaw-baseline.zip`：改造前的可运行实现，打包成一个文件。

旧实现仍然可运行、可回溯：解压 ZIP 后按包内 README 启动；Git 标签 `v2.0.0-baseline` 指向原始基线提交 `4fd4232`。

## 项目启动四步

第 7 课要求一次完成四步，每一步的产物是下一步的输入。本次提交的重点是第 2、3 步；第 1 步已完成，第 4 步的骨架以归档 + 标签保留。

| 步骤 | 交付物 | 仓库位置 | 完成现象 | 当前状态 |
| --- | --- | --- | --- | --- |
| 1 建仓库 | 仓库、README、忽略规则、协作约定 | 仓库根目录、`.gitignore`、`AGENTS.md` | 仓库可访问，协作约定清楚 | 已完成；旧实现另有归档和标签 |
| 2 定规约 | 一份变更的四份文件 | `openspec/changes/2026-10-14-upgrade-material-library/` | `--strict` 通过；另起会话可照做 | 格式与结构已完成；另起会话评审待三人执行 |
| 3 立规范 | 规则文件与按需调用的技能 | `docs/standards/`、`.cursor/rules/`、`.cursor/skills/`、`AGENTS.md` | 改一次代码产物的分层命名符合规范；换会话结果一致 | 八类规范已落文件；`standards_check.py` 通过；换会话一致性待评审 |
| 4 落骨架 | 可启动最小实现、健康检查、版本标签 | `archive/campusclaw-baseline.zip`、`v2.0.0-baseline` | 解压 → 填配置 → 一条命令 → `/health` 成功 | 基线已归档；本 change 的 1.7/1.8 补日志与 `/ready`，2.x 收口分层 |

三类偏差的自查：没有“先写代码后补规约”；规范已落成文件，不是留在会话里；本 change 按材料库增量交付，不是一次生成整套业务。

详细证据和待办见 [`docs/项目启动-四步核对.md`](docs/项目启动-四步核对.md)。

## 规约入口

变更名：`2026-10-14-upgrade-material-library`。入口：`openspec/changes/2026-10-14-upgrade-material-library/`。

| 文件 | 回答的问题 | 评审标准 |
| --- | --- | --- |
| [`proposal.md`](openspec/changes/2026-10-14-upgrade-material-library/proposal.md) | 为什么做、做到哪、不做什么、放弃过哪些方案 | 不读代码也能判定必要性；至少 3 条“不做”和 1 条被放弃的候选方案 |
| [`design.md`](openspec/changes/2026-10-14-upgrade-material-library/design.md) | 选型、分层、关键取舍、接口、数据模型、状态机 | 每条取舍都写明“选了什么、放弃了什么、代价由谁承担” |
| [`specs/`](openspec/changes/2026-10-14-upgrade-material-library/specs/) | 四条能力、28 条需求、143 个场景 | 每个场景是“前置条件 / 操作 / 可观测结果”，每条需求至少一个场景 |
| [`tasks.md`](openspec/changes/2026-10-14-upgrade-material-library/tasks.md) | 按什么顺序实现、每条怎么验 | 骨架任务排最前；每条都有 `涉及` 和 `verify` |

阅读顺序：先看 [`SPEC.md`](SPEC.md) 的“一分钟看懂 / 核心边界”，再读 `proposal.md` 的“本次做到哪 / 本次不做 / 放弃的候选方案”，然后看 `design.md` 的“关键取舍”，按能力读 `specs/`，最后用 `tasks.md` 判断实现顺序。

## 工程规范（八类）

课程要求“立规范”：前五类必修，后三类按项目性质选做。CampusClaw 是带 AI 和数据存储的项目，因此八类全部落成文件；产品规范同时承载前端约定，AI、数据、评审三类分别对应模型调用、MySQL/Qdrant/上传卷和三人协作。每条规范都带项目事实和“怎么检查”。

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

常驻入口：`.cursor/rules/campusclaw-standards.mdc`（`alwaysApply: true`）和 `AGENTS.md`。按动作执行的步骤在 `.cursor/skills/campusclaw-engineering/SKILL.md`。安全与评审两类按课程要求直接写进 `AGENTS.md`，其余规范以 `docs/standards/` 为唯一全文来源。

## 本轮边界（摘要）

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

## 怎么校验

```bash
npx -y @fission-ai/openspec@1.15.0 validate 2026-10-14-upgrade-material-library --strict
python3 scripts/spec_check.py
python3 scripts/standards_check.py
```

三条命令的预期结果都是退出码 0。`spec_check.py` 检查四份文件是否齐备、每个场景是否有 `GIVEN/WHEN/THEN`、每个需求是否至少有一个场景、失败路径是否覆盖四类、能力与场景对应表是否覆盖四个能力、tasks 是否以骨架任务开头且每条带 `verify`。`standards_check.py` 检查八类规范文件、`AGENTS.md` 与 `.cursor/` 入口、每类规范的“怎么检查”列、数据字典和四步核对文件。

## 怎么评审（另起会话测试）

**定规约**：新开会话，只给仓库路径 + `2026-10-14-upgrade-material-library`，要求它先读四份文件，再列出含糊或缺失的行为问题。它能按 `tasks.md` 编号实现且问不出业务行为问题，就算通过。

**立规范**：新开会话，只给仓库路径，要求它“按 `docs/standards/02-backend.md` 加一个材料标签接口”。检查目录是否落在 `httpapi/library/db` 的规定层、命名是否是 `/api/materials/{id}` + PATCH、错误是否只用错误码清单里的 code、是否声明幂等。换一个会话再做一次，两次结果应一致。

## 能力与场景对应

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
├── SPEC.md                           本次提交的一页入口
├── README.md                         本文件
├── AGENTS.md                         项目规则（规约先行、权限在服务端、密钥不入库）
├── .gitignore                        忽略规则
├── .env.example                      环境变量模板，只写键名和占位
├── LICENSE                           许可证说明（未选择）
├── .cursor/
│   ├── rules/campusclaw-standards.mdc 常驻工程规范入口
│   ├── skills/campusclaw-engineering/SKILL.md 加页面/加接口/补测试/发版本
│   └── commands/opsx-*.md            OpenSpec 命令
├── archive/
│   ├── README.md                     旧实现归档说明和重新生成命令
│   ├── campusclaw-baseline.zip        旧实现（backend、frontend、Compose、verify.py）
│   └── campusclaw-baseline.sha256     归档包校验和
├── scripts/
│   ├── start-baseline.sh             解压归档、启动 Compose、等待 /health
│   ├── spec_check.py                 规约结构自查
│   └── standards_check.py            八类工程规范自查
├── docs/
│   ├── CampusClaw-2.0-规划.md        2.0 三个模块的总体规划
│   ├── 阶段一-交付说明.md            本阶段交付物、校验记录和评审指引
│   ├── 项目启动-四步核对.md          四步交付物、完成现象和待办
│   ├── 个人贡献记录.md               三人分工与提交对应关系
│   ├── data-dictionary.md            字段、约束、敏感级别和删除规则
│   ├── verification.md               旧实现验收记录（已归档说明）
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
        └── 2026-10-14-upgrade-material-library/ 本阶段的活动 change
```

## 旧实现存档

`archive/campusclaw-baseline.zip` 包含改造前的 Go api、React 前端、Nginx、Compose、`scripts/verify.py`、基线 README/ITERATION 和验收记录。需要跑基线时：

```bash
cp .env.example .env
# 填写 SESSION_SECRET、MYSQL_ROOT_PASSWORD、DB_PASSWORD、SEED_*_PASSWORD
./scripts/start-baseline.sh
```

脚本会解压归档到 `.baseline/`、把根目录 `.env` 复制进基线、执行 `docker compose up --build -d`，并等待 `/health` 成功。手动方式：

```bash
unzip archive/campusclaw-baseline.zip
cd campusclaw-baseline
cp .env.example .env
# 填写密钥和口令
docker compose up --build -d
curl -fsS http://localhost:8080/health
python3 scripts/verify.py
```

ZIP 由 `git archive` 从标签 `v2.0.0-baseline`（`4fd4232`）生成；重新生成命令见 [`archive/README.md`](archive/README.md)。

### 现有底线（本 change 不破坏）

1. 班级只来自服务端会话，请求里的 `class_id` 一律忽略。
2. 跨班、已删除、同班他人私有和不存在 id 都返回同形 404。
3. 没有依据就不生成；所有 AI 输出带出处。
4. Qdrant 和模型网关不映射宿主，密钥只在服务端。
5. 只用 Docker Compose 启动，只有 web 映射端口；`/health` 不查数据库，依赖状态由 `/ready` 提供。
6. 上传要么全部写入，要么什么都不留。
7. 不做超级管理员，不让 AI 给作业打分。

## 协作约定

- **主干唯一**：`main` 是唯一主干。阶段一只有文档提交，直接在 `main` 上完成；开始写第一行功能代码后，`main` 设保护规则，直接推送应被拒绝，功能改动走 `change/<change-name>` 分支和评审。
- **每次改动一条变更**：命名 `YYYY-MM-DD-短横小写英文名`，当前活动变更是 `2026-10-14-upgrade-material-library`；验收通过后归档，归档后的规约并入 `openspec/specs/`，成为下一次改动的既有约定。
- **提交信息写依据**：提交信息写“改了什么、依据哪条规约”，格式为 `<type>(<capability>): <task-id> <一句话>`，正文含 `Change:`、`Task:`、`Spec:`、`Verify:`；不写 `update`/`fix` 这类无信息提交。
- **每人克隆跑通**：每位成员按 README 从零克隆、填配置、跑通 `/health`；未参与启动的成员也要独立成功，不需要口头补充。
- **分工不是各写各的**：角色一、二、三只是评审和交付责任，规约、规范、骨架由全组一起定、一起评审；评审对象是仓库里的文件，不是印象。
- **密钥边界**：根目录和归档包只放 `.env.example`，只写键名和占位；密钥、数据库口令、上传文件不进代码、镜像层、前端构建产物、日志与错误信息、问题单与截图。发现泄露立即轮换并重写历史。
- **归档**：全部验收通过后才把 delta 合并到 `openspec/specs/` 并归档 change；归档后 `openspec/specs/` 是长期事实来源。

## 第一次提交检查

| 检查项 | 现状 |
| --- | --- |
| README 有项目定位和从克隆到启动的步骤 | 有；`./scripts/start-baseline.sh` 一条命令启动归档基线 |
| `.gitignore` 过滤依赖、构建产物、本机配置/密钥、临时文件 | 有；含 `node_modules`、`dist`、`.env`、`.baseline` 等 |
| LICENSE 或“未选择”说明 | 有；见下面“许可证” |
| 协作约定写进 README | 有；主干唯一、变更命名、提交依据、每人跑通、密钥边界 |
| `.env.example` 只写键名和占位 | 有；根目录 `.env.example` |
| 变更目录按 `YYYY-MM-DD-英文名` 命名 | 有；`openspec/changes/2026-10-14-upgrade-material-library/` |
| 归档后的规约能在主干检索到 | 有；`openspec/specs/` 和 `openspec/changes/archive/` |
| 全部提交历史检索不到密钥 | 已用 `git grep` 检查；归档包只含 `.env.example` |
| 主干保护、直接推送被拒绝 | 需在 GitHub 仓库设置中开启；阶段一文档提交不涉及功能代码 |
| 每位成员独立克隆跑通 | 待组员按 README 各自执行一次 |

结论：**文件层面可以提交**；剩下两项是组内动作（每人克隆跑通）和仓库设置（主干保护），不影响把仓库地址交上去。

## 许可证

未选择许可证。课程作业保留所有权利；如需复用代码、规约或规范，请先联系作者。若后续要开源，再补 MIT 或 Apache-2.0 全文，并在此处更新。

## 链接

- 团队仓库：https://github.com/HanoFleet/teamwork
- 课程案例：https://devops.hello1023.com/课件/第7课-课件-小组项目启动/pages/case.html
