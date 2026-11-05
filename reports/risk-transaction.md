# 事务与 outbox

- 执行时间：2026-11-06
- 执行人：韩雅慧（角色二）
- 命令：`python3 scripts/verify.py`
- 记录：`docs/verification.md` 行「PASS outbox 插入失败时 task/outbox 无新增」「PASS 停 worker 提交仍 202，恢复后自动 succeeded」

## 同事务

`POST /api/submissions/{id}/grade` 在同一事务中写 `grade_tasks` 和 `outbox_messages`，事务内不调用 RabbitMQ 或模型。

用 root 创建 `fail_outbox` 触发器，使 outbox 插入失败：

- 接口返回 503。
- `grade_tasks` 与 `outbox_messages` 行数不变。
- 去掉触发器后再次请求，只产生一组记录，并返回 202。

提交正文的 `submissions` 行在 `POST .../submissions` 时已经提交；批改事务回滚不会删除该版本行，也不会留下半截任务。

## 停消费者恢复

`docker compose stop worker` 后提交仍 202，任务 pending；启动 worker 后自动 succeeded，无需重新提交。

## 结论

通过：有提交必有任务（outbox 补投），失败无孤儿任务。角色三需独立复跑。
