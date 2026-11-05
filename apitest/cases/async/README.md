# 异步批改自动化用例

由 `python3 scripts/async_test.py`（经 `python3 scripts/verify.py`）执行，覆盖第 8 课三条判据：

| 文件意图 | 判据 | 入口 |
| --- | --- | --- |
| P95 不随批改耗时增长 | 20 次 `POST /grade` 返回 202，P95 < 500ms，body 无分数 | `scripts/async_test.py` |
| 停 worker 不丢任务 | `docker compose stop worker` 后仍 202/pending，start 后 succeeded；再次 grade 为 200 | 同上 |
| 重复只有一份结果 | 重复 `POST /grade` + 补投 outbox，`grade_results` 仍一行且分数不变 | 同上 |
| 停 broker 补投 | `docker compose stop rabbitmq` 后仍 202、outbox pending，start 后 succeeded | 同上 |
| 永久/瞬时失败 | `GRADE_PERMANENT_FAIL` → failed 无结果；`GRADE_TRANSIENT_FAIL` → pending 且 attempts>0 | 同上 |

`make check` 跑 Go 状态机单测和分层/密钥门禁；完整三条判据随 `python3 scripts/verify.py` 和 CI 的 compose 环境执行。
