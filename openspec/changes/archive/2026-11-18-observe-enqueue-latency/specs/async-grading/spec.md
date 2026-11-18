## ADDED Requirements

### Requirement: 入队延迟观察与P95门禁
第9课异步批改复测 MUST 使用enqueue-latency-v2。MUST 恰好20次新提交全部202且无score/feedback。nearest-rank P95取第19小值，MUST 严格小于500ms。大于100ms MUST 输出WARN及序号、request_id、完整耗时并保存警告列表，MUST NOT仅因100ms警告失败。MUST 保留全部历史证据和原失败判定，新评估独立存储。既有功能、权限、并发、事务、幂等、恢复与状态流转继续适用。

#### Scenario: 观察边界
- **GIVEN** 本班学生20条有效202样本均为100ms
- **WHEN** 测试负责人运行检查入口
- **THEN** 退出0，warnings为0，P95=100ms

#### Scenario: 单次慢样本警告
- **GIVEN** 本班学生20条202样本，19条为64.5362ms、1条为122.06220000007306ms
- **WHEN** 测试负责人运行检查入口
- **THEN** 退出0，P95=64.5362ms，1条WARN含序号、request_id及122.06220000007306ms

#### Scenario: P95边界阻断
- **GIVEN** 本班学生20条202样本，18条为100ms、2条为500ms
- **WHEN** 测试负责人运行检查入口
- **THEN** P95=500ms，退出1，2条WARN

#### Scenario: 非法样本拒绝
- **GIVEN** 输入19或21条，或负数、非数值、NaN、Infinity耗时，或畸形JSON
- **WHEN** 测试负责人检查输入
- **THEN** 退出1，输出ERROR，原输入字节不变；原API非法参数400验收继续适用

#### Scenario: 无权限样本拒绝
- **GIVEN** 学生请求产生403样本
- **WHEN** 测试负责人检查包含该样本的20条记录
- **THEN** 退出1，保留403，原配置不变与审计denied验收继续适用

#### Scenario: 不存在或跨班样本拒绝
- **GIVEN** 学生请求不存在或跨班资源产生404样本
- **WHEN** 测试负责人检查包含该样本的20条记录
- **THEN** 退出1，保留404，同形响应与task和outbox无新增验收继续适用

#### Scenario: 依赖故障拒绝
- **GIVEN** MySQL不可达产生503样本
- **WHEN** 测试负责人检查包含该样本的20条记录
- **THEN** 退出1，保留503，原事务回滚与live=200验收继续适用

#### Scenario: 历史证据只读重评
- **GIVEN** 原20条样本含122.06220000007306ms且历史passed=false
- **WHEN** 测试负责人以新规则离线评估并指定新输出路径
- **THEN** 原文件SHA256一致，新文件含enqueue-latency-v2及WARN，现存输出路径拒绝覆盖并退出1

### Requirement: 发布证据与现行索引
第9课发布 MUST 保留原始证据和历史manifest字节，MUST 以独立现行索引声明基线提交、变更文件、删除项与排除项。两个既有docs证据目录 MUST 通过Git存储和重新检出后SHA256一致。浏览器.last-run.json MUST 被忽略，历史索引对它的引用 MUST 由显式别名解析到内容相同的冻结证据副本。历史tests/manifest.json MUST 标注对应2d2900b基线与第9课round-02未提交快照，MUST NOT作为现行路径哈希判据。现行README MUST描述单次100ms仅WARN及20条202、P95严格小于500ms的硬条件。

#### Scenario: 证据跨Git往返保持原字节
- **GIVEN** 负责人持有两个既有docs目录及原SHA256记录
- **WHEN** 在独立临时仓库暂存、写tree并重新检出拟发布文件
- **THEN** 全部选定证据的工作树、Git blob及检出SHA256一致，原工作树暂存区不变

#### Scenario: 临时运行文件排除与历史别名
- **GIVEN** 原gate manifest含browser-results/.last-run.json
- **WHEN** 按现行发布清单验证
- **THEN** 原路径被Git忽略且未纳入发布，显式别名副本SHA256等于原manifest记录，原manifest字节不变

#### Scenario: 当前索引与历史快照分离
- **GIVEN** 历史tests/manifest.json有8个路径已在v2阶段修改
- **WHEN** 验证现行发布索引和历史版本说明
- **THEN** 旧manifest SHA256不变，8项旧值保留，现行索引全部引用可解析且校验当前Git发布字节

#### Scenario: 篡改或非法发布引用拒绝
- **GIVEN** 临时检出副本中的索引文件缺失、越界或内容被修改
- **WHEN** 运行发布验证入口
- **THEN** 退出1并输出ERROR，原始证据不被修改
