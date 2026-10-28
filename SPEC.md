# CampusClaw 2.0 规约

> **本次提交重点：阶段一“制定规约”。** 入口就是本文件；完整规约在 `openspec/changes/upgrade-material-library/`。改造前的可运行实现已打包到 [`archive/campusclaw-baseline.zip`](archive/campusclaw-baseline.zip)，根目录不再散落业务代码。

| 项目 | 内容 |
| --- | --- |
| 变更名 | `upgrade-material-library` |
| 阶段 | 阶段一：制定规约（另附八类工程规范） |
| 负责人 | 李斯坦（角色一：制定规约） |
| 评审 | 韩雅慧（角色二：开发系统）、禹霖（角色三：项目验收） |
| 状态 | 活动；未实现、未验收、未归档 |
| 基线 | 标签 `v2.0.0-baseline`（提交 `4fd4232`），实现已归档 |
| 提交标签 | `v2.0.0-stage1-spec` |

## 一分钟看懂

CampusClaw 2.0 要把“能检索的材料列表”扩展成教师和学生日常可用的材料库：

- 教师能上传 PDF、Word、PPT，看到索引进度，编辑/替换材料并保留版本，删除后能从回收站恢复。
- 学生能按原文定位引用，继续上次阅读位置，收藏材料。
- 检索和引用始终能回到原文；重建索引期间旧索引仍可用；没有依据时不生成回答。

本轮只做**材料库和它依赖的底座**。会话追问、班级助手、课程单元、作业、练习、通知、学情统计、邀请码注册都不在本变更内。

## 四份文件

| 文件 | 回答的问题 | 直接打开 |
| --- | --- | --- |
| 动因 | 为什么做、做到哪、不做什么、放弃过哪些候选方案 | [`proposal.md`](openspec/changes/upgrade-material-library/proposal.md) |
| 设计 | 选型、分层、关键取舍、接口、数据模型、状态机 | [`design.md`](openspec/changes/upgrade-material-library/design.md) |
| 需求规约 | 4 个 capability、28 条需求、143 个场景 | [`specs/`](openspec/changes/upgrade-material-library/specs/) |
| 任务清单 | 48 条可勾选任务，骨架任务排最前，每条带 `verify` | [`tasks.md`](openspec/changes/upgrade-material-library/tasks.md) |

## 能力与规模

| Capability | 类型 | 需求 | 场景 | 负责什么 |
| --- | --- | ---: | ---: | --- |
| `platform-foundation` | 新增 | 7 | 27 | 迁移、页面壳层、全局搜索、嵌入配置、结构化日志、`/ready` 与优雅停机 |
| `material-library` | 新增 | 9 | 42 | 批量上传、回收站、标签分页、编辑/版本/替换、原文定位、进度收藏、统一 404 |
| `auth-upload` | 修改 | 7 | 44 | 登录限流、角色写权限、班级隔离、多格式上传、读取下载、Compose、Web 安全 |
| `knowledge-retrieval` | 修改 | 5 | 30 | 异步索引、当前 generation 检索、原文码点引用、先建后换重建 |
| **合计** |  | **28** | **143** |  |

## 核心边界

**做：**

- 数据库版本迁移；PDF/DOCX/PPTX 上传与抽取；后台索引状态与重试；先建后换重建。
- 材料版本、编辑冲突、文件替换、回收站、标签、排序分页、阅读进度、收藏。
- 原文码点定位、页码/幻灯片号、旧引用“原文已更新”。
- 前端壳层拆分、全局搜索、统一反馈；登录限流、嵌入维度、Cookie、CSP、日志、`/ready`。

**不做：**

- 会话历史、追问、SSE、班级助手、AI 技能（模块二）。
- 课程单元、作业、练习、错题、公告、通知、学情（模块三）。
- 邀请码注册、CSV 导入、口令重置、超级管理员、AI 批改作业。
- 外部队列、Redis、对象存储、UI 框架、富文本编辑器。

完整“不做”清单见 [`proposal.md`](openspec/changes/upgrade-material-library/proposal.md) 的 Out of Scope。

## 关键判据

- **跨班 404**：跨班、同班他人私有、已删除、非法 id 和不存在的 id 返回同形 404；状态、头、body 逐字节一致。
- **没有依据不生成**：本班没有切片时返回固定文案，不调用对话网关。
- **索引状态**：`pending → indexing → ready/failed`；failed 带 `index_error`，可重试；重建期间旧 generation 仍可检索。
- **版本冲突**：保存带 `base_version`，不是最新返回 409 和最新正文，不覆盖他人修改。
- **原文坐标**：`start/end` 是当前版本正文的 Unicode 码点，`start` 含、`end` 不含；PDF/PPT 带页码/幻灯片号。
- **上传原子性**：文件、材料、版本、知识库要么全部写入，要么都不留；扫描件/加密/损坏当场 400。
- **部署底线**：只有 web 映射宿主端口；`/health` 只报存活，`/ready` 报依赖状态。

## 怎么校验

```bash
npx -y @fission-ai/openspec@1.15.0 validate upgrade-material-library --strict
python3 scripts/spec_check.py
python3 scripts/standards_check.py
```

三条命令的预期结果都是退出码 0。`spec_check.py` 检查四份文件、场景三段式、失败路径、能力—场景对应表和任务清单；`standards_check.py` 检查八类工程规范、常驻规则、工程技能、数据字典和四步核对。

## 评审顺序

1. 读本文件的“一分钟看懂”和“核心边界”，确认范围和方向。
2. 读 `proposal.md` 的“本次做到哪 / 本次不做 / 放弃的候选方案”。
3. 读 `design.md` 的 8 条取舍，确认每条都有“选了什么 / 放弃了什么 / 代价由谁承担”。
4. 按 capability 读 `specs/`，重点看失败路径和同形 404。
5. 用 `tasks.md` 判断实现顺序；另起一个不带上下文的会话，只给仓库路径和变更名，看它能否照做。
6. 规范是否常驻：另起会话按 `docs/standards/02-backend.md` 加一个材料标签接口，核对分层、命名、错误码和幂等声明。

## 工程规范

八类规范在 [`docs/standards/`](docs/standards/)：产品/前端、后端、安全、测试、部署、AI、数据、评审。常驻入口是 [`AGENTS.md`](AGENTS.md) 和 [`.cursor/rules/campusclaw-standards.mdc`](.cursor/rules/campusclaw-standards.mdc)；按动作执行的步骤在 [`.cursor/skills/campusclaw-engineering/SKILL.md`](.cursor/skills/campusclaw-engineering/SKILL.md)。字段定义在 [`docs/data-dictionary.md`](docs/data-dictionary.md)。

## 旧实现

- 归档包：[`archive/campusclaw-baseline.zip`](archive/campusclaw-baseline.zip)，说明见 [`archive/README.md`](archive/README.md)。
- 基线标签：`v2.0.0-baseline`（`4fd4232`）。
- 本阶段标签：`v2.0.0-stage1-spec`。
- 解压后可按包内 README 运行；不把旧代码放在根目录，是为了让本次提交的第一眼就是规约。

## 后续

阶段一不实现功能。实现、验收和归档按 [`tasks.md`](openspec/changes/upgrade-material-library/tasks.md) 第 0 至 7 组推进；全部验收通过后才把 delta 合并到 `openspec/specs/` 并归档。
