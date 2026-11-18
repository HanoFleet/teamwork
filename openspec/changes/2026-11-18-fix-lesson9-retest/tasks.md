> 性能条款由活动change `2026-11-18-observe-enqueue-latency` 替代。下文100ms阻断为旧规则决策记录，现行规则为100ms警告、20次P95 < 500ms硬断言。历史失败完整保留。

## 0. 基线与复测整改
- [ ] 0.1 归档历史测试源及缺口；verify: 核对 docs/lesson-09/2026-11-18-observe-enqueue-latency/report.md 与 preservation-after.json（历史生成器冻结）
- [ ] 0.2 依赖兼容调整；verify: npm ci && npm audit && npm run build；frontend/e2e npx playwright test。
- [ ] 0.3 同口径性能复测；verify: python scripts/qa/lesson9/check_performance.py reports/lesson9-20261118/retest-02/fix-round/performance-1.json reports/lesson9-20261118/retest-02/fix-round/performance-2.json
- [ ] 0.4 原入口与回归；verify: make check && make check-security && make grade；python scripts/verify.py。
- [ ] 0.5 报告与返工；verify: 核对 docs/lesson-09/2026-11-18-observe-enqueue-latency/report.md 与 preservation-after.json（历史生成器冻结）

## 完成定义
场景满足、用例通过、门禁通过、文档同步、验证归档五项缺一不可。高危或P95 >= 500ms、样本非法及原功能门禁失败不勾选。单次100ms超限记录WARN，原失败保持原样。
