> 性能条款由活动change `2026-11-18-observe-enqueue-latency` 替代。下文100ms阻断为旧规则决策记录，现行规则为100ms警告、20次P95 < 500ms硬断言。历史失败完整保留。

# 第9课复测整改

## Why
L9-DEP-001 的5个high依赖条目来自picomatch及其传递链；历史单次179.6ms超过04-testing默认100ms。历次会话测试包装器尚未纳入可提交档案。

## What Changes
- 核对兼容工具链，消除前端已知高危依赖链，锁文件安装、审计、构建和主路径复测。
- 保存20次顺序202样本，保持P95<500ms与单次<=100ms两套判据；不提高阈值、不删慢样本。
- 归档现存历史脚本与精确版本缺口；提供隔离复测入口、原make目标与证据清单。

## Impact
仅security-hardening复测整改及其测试工具；不实现材料库，不发布、不推送、不替真人签字。

## Out of Scope
- 不实现材料库。
- 不修改评分规则和授权边界。
- 不发布、推送或代替真人签字。

## Alternatives Considered
|方案|判定|依据|
|---|---|---|
|audit fix --force|放弃|可能破坏兼容性且降级试验仍高危|
|提高100ms阈值|放弃|掩盖原179.6ms样本|

## Capabilities
security-hardening：既有安全链路的整改与复测证据。

## Capability–Scenario Map
|能力|范围|需求|场景|
|---|---|---|---|
|`security-hardening`|整改证据与工具链|1|8|
|`async-grading`|dispatcher锁范围修复|1|4|

## Failure Path Coverage
复用现有接口的400非法参数、403学生写配置、404跨班、503依赖故障；新测试不得改变这些返回值。

## Success Criteria
- 审计before/after与5条依赖链处置可查，非零高危保持失败。
- 20次采样不丢弃任何值，以100ms默认单次门槛判定。
- 脚本归档、Git状态、SHA256及原入口结果全部落盘。
