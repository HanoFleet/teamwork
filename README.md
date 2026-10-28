# CampusClaw 2.0 · 小组项目仓库

CampusClaw 把教研材料按班级放进可登录的知识库。教师上传材料，本班学生只读；正文切成切片后，本班可以用关键字、向量或混合检索，命中能回到原文；没有依据时不生成回答。本仓库是第 7 课小组项目的主仓库，基线来自 CampusClaw 迭代 1/2。

## 小组与角色

| 姓名 | 学号 | 角色 | 阶段一交付 |
| --- | --- | --- | --- |
| 李斯坦 | 2601210362 | 角色一：制定规约 | 本 change 的 proposal、design、specs、tasks |
| 韩雅慧 | 2601210643 | 角色二：开发系统 | 评审规约；后续按 `tasks.md` 实现 |
| 禹霖 | 2601210536 | 角色三：项目验收 | 评审规约；后续扩展 `verify.py` 并逐条验收 |

## 当前阶段：阶段一 · 制定规约

本轮**只交付规约，不实现功能**。变更名：`upgrade-material-library`。

入口：`openspec/changes/upgrade-material-library/`

| 文件 | 回答的问题 | 评审标准 |
| --- | --- | --- |
| [`proposal.md`](openspec/changes/upgrade-material-library/proposal.md) | 为什么做、做到哪、不做什么、放弃过哪些方案 | 不读代码也能判定本次改动的必要性；至少有 3 条“不做”和 1 条被放弃的候选方案 |
| [`design.md`](openspec/changes/upgrade-material-library/design.md) | 选型、分层、关键取舍、接口、数据模型、状态机 | 每条取舍都写明“选了什么、放弃了什么、代价由谁承担” |
| [`specs/`](openspec/changes/upgrade-material-library/specs/) | 四条能力、26 条需求、136 个场景 | 每个场景是“前置条件 / 操作 / 可观测结果”，每条需求至少一个场景 |
| [`tasks.md`](openspec/changes/upgrade-material-library/tasks.md) | 按什么顺序实现、每条怎么验 | 骨架任务排最前；每条都有 `涉及` 和 `verify` |

四份文件的具体阅读顺序建议：先看 `proposal.md` 的“本次做到哪 / 本次不做 / 放弃的候选方案”，再看 `design.md` 的“关键取舍”，然后按能力读 `specs/`，最后用 `tasks.md` 判断实现顺序。

### 本轮边界（摘要）

**做：**

- 可演进的数据库迁移；PDF、DOCX、PPTX 上传；后台索引与状态；先建后换的重建。
- 材料版本历史、编辑冲突、文件替换、回收站、标签、排序分页、阅读进度、收藏。
- 原文码点定位、页码/幻灯片号、旧引用提示。
- 前端壳层拆分、全局搜索、统一反馈；登录限流、嵌入维度、Cookie、CSP 等底座修复。

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

仓库自带的结构自查：

```bash
python3 scripts/spec_check.py
```

两条命令的预期结果都是退出码 0。自查脚本检查四份文件是否齐备、每个场景是否有 `GIVEN/WHEN/THEN`、每个需求是否至少有一个场景、失败路径是否覆盖四类、能力与场景对应表是否覆盖四个能力、tasks 是否以骨架任务开头且每条带 `verify`。

### 怎么评审（另起会话测试）

课程对“定规约”的实质检查不是格式，而是：**另起一个不带历史上下文的会话，只给仓库路径和变更名，执行者能按任务清单实现，且问不出规约没回答的问题。**

建议按下面步骤做一次：

1. 新开一个会话，只输入：仓库路径 + `upgrade-material-library`。
2. 要求它先读 `proposal.md`、`design.md`、`specs/`、`tasks.md`，然后列出它认为含糊或缺失的行为问题。
3. 如果它能直接按 `tasks.md` 编号实现，且问题只涉及代码细节而不是业务行为，规约就算通过；如果它问“这个接口返回什么”“跨班返回 403 还是 404”“失败后旧数据还在不在”，说明对应场景还缺判定。

### 能力与场景对应

| Capability | 类型 | 需求数 | 场景数 |
| --- | --- | ---: | ---: |
| `platform-foundation` | 新增 | 5 | 20 |
| `material-library` | 新增 | 9 | 42 |
| `auth-upload` | 修改 | 7 | 44 |
| `knowledge-retrieval` | 修改 | 5 | 30 |
| **合计** |  | **26** | **136** |

每个需求的详细场景见 `specs/<capability>/spec.md`；失败路径、放弃方案和验收证据见 `proposal.md`。

## 仓库结构

```text
.
├── AGENTS.md                         项目规则（规约先行、权限在服务端、密钥不入库）
├── README.md                         本文件
├── ITERATION.md                      迭代 1 的设计说明
├── docker-compose.yml                web / api / db / qdrant
├── .env.example                      环境变量模板，不含真实密钥
├── backend/                          Go api：auth、materials、retrieval、httpapi
├── frontend/                         React + Vite + Nginx
├── scripts/
│   ├── verify.py                     现有验收脚本
│   └── spec_check.py                 阶段一规约结构自查
├── docs/
│   ├── CampusClaw-2.0-规划.md        2.0 三个模块的总体规划
│   ├── verification.md               现有验收记录
│   ├── 阶段一-交付说明.md            本阶段交付物、校验记录和评审指引
│   └── 个人贡献记录.md               三人分工与提交对应关系
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
