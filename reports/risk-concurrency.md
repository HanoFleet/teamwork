# 重复提交 / 重复投递

- 执行时间：2026-11-06
- 执行人：韩雅慧（角色二）
- 命令：`python3 scripts/verify.py` 中的幂等段
- 记录：`docs/verification.md` 行「PASS 重复批改复用同一 task_id」「PASS 重复请求和重复投递只有一份结果」

## 重复请求

对同一 `submission_id`/`version` 连续两次 `POST /api/submissions/{id}/grade`。

- 两次返回同一个 `task_id`。
- `grade_tasks` 该提交只有 1 行。
- `outbox_messages` 按幂等键 `grade:<submission_id>:<version>` 只有 1 行。

## 重复投递

在已有 outbox 行上再插入一条 payload 相同、幂等键不同的 pending 消息，让 dispatcher 再投递一次。

- `grade_results` 仍为 1 行。
- 分数保持首次写入，不因第二次执行改写。

## 结论

通过：至少一次投递 + 唯一约束，重复不会产生第二份结果。角色三需独立复跑。
