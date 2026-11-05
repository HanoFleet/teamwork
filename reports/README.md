# reports/ 证据目录

这里放**实际执行过**的命令输出、报告和截图，不放“应该可以”的结论。

## 当前状态

第 8 课的异步批改和 SEC 自查尚未执行。目录中暂时只有本说明，没有伪造的通过记录。角色三按 [`docs/lesson-08/self-check.md`](../docs/lesson-08/self-check.md) 执行后，再在本目录生成以下文件：

| 文件 | 内容 |
| --- | --- |
| `async-grading.md` | 判据一 P95、判据二停 worker、观测值与复跑命令 |
| `risk-concurrency.md` | 重复提交/重复投递只出一份结果 |
| `risk-transaction.md` | 提交/任务/outbox 同事务、停消费者恢复、无孤儿任务 |
| `risk-authz.md` | SEC-02 跨班一条，命令可原样复跑 |
| `security-precheck.md` | SEC-01～SEC-07 三段式记录与红/绿判定 |
| `security-baseline.md` | 密钥扫描、依赖审计基线 |
| `review-01.md` | 交叉评审“手段/查了什么/判据/结果” |

## 目录规则

- `teacher-*/` 是 `make grade` 自动生成的隔离验收报告，已在 `.gitignore` 中忽略；需要提交时单独挑选，不整目录提交。
- `*.tmp` 是临时输出，不提交。
- 每份报告写清：执行时间、执行人、命令、实际输出、判定；失败就写失败。
- 至少保留 1 条红项，后续课次从红改到绿并保留前后证据。
- 报告里不得出现 `.env` 明文、Cookie、令牌、数据库 DSN、上传正文或绝对路径。
