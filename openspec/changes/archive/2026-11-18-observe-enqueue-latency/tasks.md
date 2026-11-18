## 0. 基线与规则
- [x] 0.1 核对引用并保存历史哈希；verify: preservation-before.json与preservation-after.json逐项一致。
- [x] 0.2 同步规约与工程规范；verify: python scripts/spec_check.py；python scripts/standards_check.py；npx -y @fission-ai/openspec@1.15.0 validate --all --strict。
## 1. 实现与验证
- [x] 1.1 统一入口与边界测试；verify: python tests/performance/latency_gate_contract.py。
- [x] 1.2 新旧标准独立报告；verify: 原after两份样本只读重评，新输出独立目录，原哈希一致。
## 2. 提交准备
- [x] 2.1 修订现行复现说明；verify: README与v2边界合同测试一致。
- [x] 2.2 字节保护及临时文件别名；verify: 独立Git暂存/tree/checkout往返校验，原index SHA256不变。
- [x] 2.3 历史版本说明及独立现行索引；verify: python scripts/qa/lesson9/verify_release.py。
- [x] 2.4 发布清单与审计复核；verify: OpenSpec strict、结构自查、13项合同测试、npm audit --audit-level=high退出0，证据存于docs/lesson-09/2026-11-18-submission-preparation。
## 完成定义
场景满足、测试通过、门禁通过、文档同步、验证记录齐备。等待用户确认，保持change活动。
