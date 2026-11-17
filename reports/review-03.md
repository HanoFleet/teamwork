# 复评记录 03：脚本复现

- 手段：在本地 Compose 上执行 `python3 scripts/verify.py`，再执行 `python3 scripts/security_gate.py --self-test` 和正常门禁。
- 查了什么：SQLi 登录/材料/搜索、XSS 上传与 JSON 转义、CSRF 无 token/恶意 Origin、SEC-03 配置权限、SEC-04 技能绕过、SEC-07 审计查询、SEC-08 第四步写入拒绝。
- 判据：输出以 `PASS`/`FAIL` 和退出码为准，不以“看起来正常”判断。
- 结果：`verify.py` 全部断言通过；安全回归 6 项 PASS；门禁自测先红后绿；正常门禁 0 漏洞、0 密钥命中。
- 说明：这是脚本输出记录，不是人工签字；人工复核仍由角色三执行。
