# 安全门禁先红后绿

- 执行时间：2026-11-17
- 执行人：自动化脚本
- 入口：`make check-security` → `python3 scripts/security_gate.py`
- 红项：`--self-test` 在临时 git 仓库提交 `SESSION_SECRET=gate-self-test-secret`
- 绿项：清理临时仓库后正常扫描

```text
$ python3 scripts/security_gate.py --self-test
$ 临时仓库：带假 SESSION_SECRET
密钥边界检查失败：
  ✗ leak.env: SESSION_SECRET 有非空值
exit=1
$ 临时仓库：干净
密钥边界检查通过：工作树和提交历史都没有非空密钥赋值。
exit=0
SELF-TEST PASSED: 先红后绿
exit=0

$ python3 scripts/security_gate.py
$ python3 scripts/secret_scan.py
密钥边界检查通过：工作树和提交历史都没有非空密钥赋值。
exit=0
$ npm audit --audit-level=high
found 0 vulnerabilities
exit=0
SECURITY GATE PASSED
exit=0
```

## 结论

- 假密钥命中时退出码 1，正常仓库退出码 0；门禁不是固定返回成功。
- `security_gate.py` 覆盖 SEC-05 密钥扫描和 SEC-06 前端依赖审计；Go `govulncheck` 基线保留在 `reports/security-baseline.md`，未纳入本门禁的阻断条件。
