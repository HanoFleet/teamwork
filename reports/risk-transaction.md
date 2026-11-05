# 事务与 outbox

- 执行时间：2026-11-06
- 执行人：韩雅慧（角色二）
- 命令：`python3 scripts/verify.py`
- 记录：`docs/verification.md` 行「PASS outbox 插入失败时 task/outbox 无新增」「PASS 停 worker 提交仍 202，恢复后自动 succeeded」「PASS 停 RabbitMQ 仍 202/pending，恢复后自动 succeeded」

## 同事务

`POST /api/submissions/{id}/grade` 在同一事务中写 `grade_tasks`、`outbox_messages`，并更新对应 `submissions` 行（状态保持 `submitted` 直到 worker 开始），事务内不调用 RabbitMQ 或模型。

用 root 创建 `fail_outbox` 触发器，使 outbox 插入失败：

- 接口返回 503。
- `grade_tasks` 与 `outbox_messages` 行数不变。
- 去掉触发器后再次请求，只产生一组记录，并返回 202。

提交正文的 `submissions` 行在 `POST .../submissions` 时已经提交；批改事务回滚不会删除该版本行，也不会留下半截任务。

## 停消费者恢复

`docker compose stop worker` 后提交仍 202，任务 pending；启动 worker 后自动 succeeded，无需重新提交。

## 停 broker 恢复

`docker compose stop rabbitmq` 后批改仍 202，outbox 保持 `pending`；`docker compose start rabbitmq` 后 dispatcher 自动发布，任务变为 succeeded。

## 失败分类

- 正文含 `GRADE_PERMANENT_FAIL`：任务进入 `failed`，`grade_results` 无行。
- 正文含 `GRADE_TRANSIENT_FAIL`：任务回到 `pending` 且 `attempts=1`。

## 结论

通过：有批改必有任务（outbox 补投），失败无孤儿任务。角色三需独立复跑。
