# 异步批改三条判据

- 执行时间：2026-11-06（UTC 2026-11-05 17:33）
- 执行人：韩雅慧（角色二，开发）
- 分支：`change/2026-11-05-add-async-grading`
- 环境：本机 Compose，`GRADE_LOCAL_DELAY_MS=2000`，`CHAT_URL=local`
- 命令：`python3 scripts/verify.py`（内含 `scripts/async_test.py`）
- 完整输出：`docs/verification.md`

角色三应按同一命令独立复跑后再签字。本文件记录角色二实现后的实际结果，不是验收通过声明。

## 判据一：请求时间不随批改时间增长

- 操作：worker 保持运行（本地批改固定 2 秒），连续提交 20 份不同内容并各请求一次 `POST /api/submissions/{id}/grade`，记录 HTTP `time_total`。
- 实际：20 次均返回 202，body 仅含 `task_id` / `status:"pending"` / `status_url`，不含 `score`/`feedback`。
- 20 个耗时（ms，请求顺序）：10.2, 9.5, 11.8, 5.5, 6.4, 13.9, 7.4, 8.4, 5.8, 7.8, 6.5, 6.7, 7.5, 5.7, 6.1, 7.1, 5.6, 5.6, 5.4, 5.8
- P95：11.8ms（阈值 500ms）。
- 结论：通过。提交链路没有等待模型。

## 判据二：停 worker 不丢任务

- 操作：`docker compose stop worker` → 学生提交并请求批改 → 查 `grade_tasks.status` → `docker compose start worker` → 轮询 `GET /api/tasks/{task_id}`。
- 状态序列：停 worker 后接口 202、任务 `pending`；启动 worker 后变为 `succeeded`；再次 `POST /grade` 返回 200 且带已有 `result`。
- 结论：通过。无需重新提交。

## 观测值（本次运行）

| 项 | 值 |
| --- | --- |
| 202 响应 P95 | 11.8ms |
| 本地批改时延 | 2000ms |
| 队列 durable | `grade.tasks`、`grade.retry.1s`…`16s`、`grade.dead` 均为 true |
| 跑完后队列深度 | `grade.tasks=0`；`grade.dead=1`（永久失败用例）；`grade.retry.8s=1`（瞬时失败仍在退避） |
| 幂等样例 | `grade_results.score=12.00`，`grade_tasks.attempts=1` |
| 宿主端口 | 仅 web |

复跑：

```bash
docker compose up --build -d --wait
python3 scripts/verify.py
```
