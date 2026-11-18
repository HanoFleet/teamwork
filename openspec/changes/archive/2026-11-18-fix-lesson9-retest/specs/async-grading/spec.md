## MODIFIED Requirements

### Requirement: 事务性发件箱与可靠补投

提交/批改请求 MUST 在同一个数据库事务中写 submission、grade_task 和 outbox_message；MUST NOT 在事务内调用 RabbitMQ 或模型。独立 dispatcher MUST 轮询 pending outbox，使用 `FOR UPDATE SKIP LOCKED` 取批次，发布并等 confirm，成功后标 `published`；失败 MUST 增加 `attempts`、写 `next_attempt_at`，下轮继续。broker 不可用时接口仍 MUST 返回 202，任务保持 pending，恢复后自动补投。dispatcher 的批次事务 MUST 使用 READ COMMITTED，避免 pending 锁定读取的间隙锁阻塞新 outbox 插入；MUST 保留批次行锁、确认、唯一约束和持久化设置。

#### Scenario: 事务失败没有孤儿任务
- **GIVEN** 提交请求在插入 outbox 时数据库报错
- **WHEN** 请求返回 503
- **THEN** submission、grade_task 和 outbox 都没有新增行
- **AND** 重试成功后只产生一组记录

#### Scenario: broker 不可用时恢复补投
- **GIVEN** RabbitMQ 已停止
- **WHEN** 学生请求批改，随后启动 RabbitMQ
- **THEN** 请求返回 202，任务为 pending，outbox 为 pending
- **AND** dispatcher 恢复后自动发布，worker 最终把任务变为 succeeded，无需重新提交

#### Scenario: 重复发布由幂等兜底
- **GIVEN** dispatcher 已发布消息但在标记 published 前崩溃
- **WHEN** dispatcher 重启并再次发布同一消息
- **THEN** 至少一次投递允许两条相同消息
- **AND** worker 只保留一份 grade_results，任务最终 succeeded

#### Scenario: 批次锁定不阻塞新入队
- **GIVEN** 隔离 MySQL、RabbitMQ 和 dispatcher 正常，保持原持久化设置
- **WHEN** 顺序提交20份新版本并各计时一次批改请求，关联 API 耗时及数据库锁等待
- **THEN** 全部响应202且不含分数，保存20个完整样本，单次超过100ms输出WARN及完整样本，P95必须严格小于500ms，按enqueue-latency-v2规则判定
- **AND** 新 outbox 插入不被 dispatcher 的 PRIMARY supremum 间隙锁阻塞
