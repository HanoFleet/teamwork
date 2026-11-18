## ADDED Requirements

### Requirement: 复测整改证据
整改 MUST 保留前端依赖审计前后JSON、锁文件重装结果、20次完整性能样本及测试源码档案；高危或严重非0 MUST 阻断验收。

#### Scenario: 替代工具链保持页面与开发入口
- **GIVEN** 原 React/TSX/CSS 源码与客户端深链接，后端在 127.0.0.1:8080
- **WHEN** 使用无原高危依赖链的工具运行 build、dev 和 preview
- **THEN** build 生成包含 JS/CSS 引用的 dist/index.html，生产与开发深链接可打开，dev/preview 的 /api 与 /health 转发至后端，作业提交和 XSS 回归通过
- **AND** 开发变更整页刷新，Fast Refresh 组件状态保留不在替代工具链范围内

#### Scenario: 兼容依赖安装与回归
- **GIVEN** 测试负责人在包含第9课修复的独立工作树，有锁文件与官方npm源
- **WHEN** 用修订锁文件运行npm ci、audit、前端build和作业页回归
- **THEN** 退出码均为0，high=0、critical=0，历史5条依赖链处置可追溯

#### Scenario: 性能观察与P95阻断
- **GIVEN** student_a1及本班已发布作业，隔离Compose健康
- **WHEN** 顺序创建20份提交并逐次计时POST批改入队
- **THEN** 保存20个202耗时、P95和超过100ms的次数，单次超过100ms输出WARN及完整样本，P95必须严格小于500ms，按enqueue-latency-v2规则判定

#### Scenario: 依赖不可达
- **GIVEN** npm仓库或镜像仓库不可达
- **WHEN** 安装或构建超时
- **THEN** 保存退出码和脱敏错误，标为阻塞，不登记为通过

#### Scenario: 非法配置不落库
- **GIVEN** 教师会话、本班技能存在
- **WHEN** 原回归提交非法配置body
- **THEN** HTTP 400，业务数据不变

#### Scenario: 学生写配置拒绝
- **GIVEN** 学生会话、有效CSRF、本班技能存在
- **WHEN** 原SEC-03提交配置修改
- **THEN** HTTP 403，配置不变且审计denied

#### Scenario: 跨班提交拒绝
- **GIVEN** A班学生、B班submission存在
- **WHEN** 原SEC-04操作B班提交
- **THEN** HTTP 404，与不存在同形，task和outbox不新增

#### Scenario: 业务依赖不可达
- **GIVEN** 隔离Compose中MySQL停止
- **WHEN** 原verify请求业务材料列表
- **THEN** HTTP 503，live仍200，不返回业务正文
