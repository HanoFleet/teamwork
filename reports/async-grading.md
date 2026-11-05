# 异步批改三条判据

- 执行时间：2026-11-06（UTC 2026-11-05 17:12）
- 执行人：韩雅慧（角色二，开发）
- 分支：`change/2026-11-05-add-async-grading`
- 环境：本机 Compose，`GRADE_LOCAL_DELAY_MS=2000`，`CHAT_URL=local`
- 命令：`python3 scripts/verify.py`（内含 `scripts/async_test.py`）
- 完整输出：`docs/verification.md`

角色三应按同一命令独立复跑后再签字。本文件记录角色二实现后的第一次实际结果，不是验收通过声明。

## 判据一：请求时间不随批改时间增长

- 操作：worker 保持运行（本地批改固定 2 秒），连续提交 20 份不同内容并各请求一次 `POST /api/submissions/{id}/grade`，记录 HTTP `time_total`。
- 实际：20 次均返回 202，body 仅含 `task_id` / `status:"pending"` / `status_url`，不含 `score`/`feedback`。
- P95：8.0ms（阈值 500ms）。
- 结论：通过。提交链路没有等待模型。

## 判据二：停 worker 不丢任务

- 操作：`docker compose stop worker` → 学生提交并请求批改 → 查 `grade_tasks.status` → `docker compose start worker` → 轮询 `GET /api/tasks/{task_id}`。
- 实际：停 worker 后接口仍 202，任务为 `pending`；启动 worker 后无需重新提交，任务变为 `succeeded`。
- 结论：通过。

## 观测值（本次运行）

| 项 | 值 |
| --- | --- |
| 202 响应 P95 | 8.0ms |
| 本地批改时延 | 2000ms（worker 日志 `duration_ms≈2014`） |
| 队列 | `grade.tasks` 及 `grade.retry.1s`…`16s`、`grade.dead` 均为 durable |
| 宿主端口 | 仅 web |

复跑：

```bash
docker compose up --build -d --wait
python3 scripts/verify.py
```
