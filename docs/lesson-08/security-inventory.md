# 第 8 课安全自查接口清单

> 角色一整理，角色三执行；本文件只列清单和判定口径，**SEC 的“当前实际”均待角色三填写，不冒充已验收**。标“第 8 课”的接口已由角色二实现，红绿判定仍待角色三执行。

## 1. 受保护接口（不少于 5 个）

| # | 方法与路径 | 允许角色 | 未登录期望 | 跨班/他人期望 | 状态 |
| ---: | --- | --- | --- | --- | --- |
| 1 | `GET /api/me` | 已登录教师/学生 | 401 | 只返回会话本人 | 现有 |
| 2 | `GET /api/materials` | 已登录教师/学生 | 401 | 只返回会话班级 | 现有 |
| 3 | `POST /api/materials` | 本班教师 | 401 | 学生 403；跨班不改变归属 | 现有 |
| 4 | `GET /api/materials/{id}` | 本班教师/学生 | 401 | 跨班/不存在同形 404 | 现有 |
| 5 | `GET /api/materials/{id}/file` | 本班教师/学生 | 401 | 跨班/不存在同形 404 | 现有 |
| 6 | `POST /api/materials/{id}/reindex` | 本班教师 | 401 | 学生 403；跨班 404 | 现有 |
| 7 | `POST /api/search` | 已登录教师/学生 | 401 | 只检索会话班级，不返回其他班 | 现有 |
| 8 | `POST /api/ask` | 已登录教师/学生 | 401 | 只使用会话班级切片 | 现有 |
| 9 | `GET /api/assignments` | 已登录教师/学生 | 401 | 只返回会话班级已发布作业 | 第 8 课已实现，待验收 |
| 10 | `POST /api/assignments/{id}/submissions` | 本班学生本人 | 401 | 教师 403；其他学生/跨班 404 | 第 8 课已实现，待验收 |
| 11 | `POST /api/submissions/{id}/grade` | 提交本人 | 401 | 教师/其他学生/跨班 404 | 第 8 课已实现，待验收 |
| 12 | `GET /api/tasks/{task_id}` | 提交本人或本班教师 | 401 | 其他学生/跨班/不存在同形 404 | 第 8 课已实现，待验收 |

公开接口不列入保护清单：`GET /live`、`GET /health`、`GET /ready`、`POST /api/login`。

## 2. 写入类接口

| 方法与路径 | 写什么 | 允许角色 | 备注 |
| --- | --- | --- | --- |
| `POST /api/login` | 创建会话、失败计数 | 公开 | 登录限流与同形 401 |
| `POST /api/logout` | 删除会话 | 已登录 | 旧 Cookie 立即失效 |
| `POST /api/materials` | 材料、知识库、文件 | 本班教师 | 学生 403，失败无残留 |
| `POST /api/materials/{id}/reindex` | 切片、向量、索引状态 | 本班教师 | 学生 403 |
| `POST /api/assignments/{id}/submissions` | submission 版本行 | 本班学生本人 | 第 8 课已实现，待验收 |
| `POST /api/submissions/{id}/grade` | grade_task、outbox | 提交本人 | 第 8 课已实现，待验收；不直接写分数 |

本课不提供 `POST /api/tasks/{task_id}/retry`；失败/dead 只展示原因。技能、提示词、助手配置接口当前没有实现，所以 SEC-03 不能伪造 403 绿项；按“无接口可测/缺口”记红。

## 3. SEC-01～SEC-08 对照

| 检查项 | 目标接口/资产 | 期望 | 当前状态 |
| --- | --- | --- | --- |
| SEC-01 未登录访问受保护接口 | 上表 1～12 | 每个都是 401，响应不含正文/分数 | 待角色三执行 |
| SEC-02 跨班访问与跨班检索 | 材料 2～7；第 8 课 9～12 | 访问 404，检索空结果，任务/提交不泄露 | 待角色三执行 |
| SEC-03 学生修改技能与提示词 | 技能/提示词/助手写接口 | 学生 403 | 当前无接口；预期红 |
| SEC-04 技能工具绕过鉴权 | 直接调用批改写入（10～11） | 被拒绝，库中无 task/outbox | 待角色三执行 |
| SEC-05 密钥明文泄漏扫描 | 工作树、历史、前端产物、日志 | 0 命中，或已轮换并清历史 | 命令已备，报告待写 |
| SEC-06 依赖漏洞基线 | `frontend/package-lock.json`、Go 依赖 | 高危清零或书面处置 | 命令已备，报告待写 |
| SEC-07 审计日志可追溯 | 一次技能调用 | 能按技能标识回查操作人、结果、耗时、用量 | 当前无技能调用日志；任务日志有 `task_id` 但不等于技能日志，预期红 |
| SEC-08 恶意文档/提示词注入（选做） | 1 份含覆盖指令的讲义 + 3 条诱导提问 | 只准备素材，不试 | 未准备 |

**至少保留 1 条红项。** 不得把“没有接口”写成“已拒绝”，也不得把命令通过写成报告已完成。

## 4. 复跑命令

```bash
make check-security
# 或在 frontend 目录单独执行
npm audit --audit-level=high
```

接口类检查示例（变量由执行人填本机 `.env` 的值，不把口令写进报告）：

```bash
BASE=http://127.0.0.1:8080
curl -s -o /dev/null -w '%{http_code}\n' "$BASE/api/materials"
curl -s -o /dev/null -w '%{http_code}\n' -c /tmp/student_a1.cookie \
  -H 'Content-Type: application/json' \
  -d '{"username":"student_a1","password":"'"$SEED_STUDENT_A_PASSWORD"'"}' \
  "$BASE/api/login"
curl -s -o /dev/null -w '%{http_code}\n' -b /tmp/student_a1.cookie "$BASE/api/materials"
```

## 5. 报告落点

- `reports/security-precheck.md`：SEC-01～SEC-07 三段式记录与红/绿。
- `reports/risk-authz.md`：SEC-02 跨班一条，命令可原样复跑。
- `reports/security-baseline.md`：SEC-05/06 命令、计数、处置。
- `reports/review-01.md`：交叉评审“手段/查了什么/判据/结果”。

详细场景和任务映射见 [`self-check.md`](self-check.md)。
