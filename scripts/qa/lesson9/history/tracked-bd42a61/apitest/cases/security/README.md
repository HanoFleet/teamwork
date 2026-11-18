# 安全反例用例（第 9 课）

三条注入反例的三段式在：

- `apitest/cases/api/search/POST/case.json`
- `apitest/cases/api/materials/POST/case.json`
- `apitest/cases/api/skills/grade/PATCH/case.json`

`make check` 执行 `python3 scripts/security_cases.py`，检查这三份文件并做 XSS 静态断言。在线请求由 `python3 scripts/security_test.py` 执行，`scripts/verify.py` 负责加载；CI 的 `verify` job 也会跑完整套。

| 用例 | 判据 | 入口 |
| --- | --- | --- |
| SQL 注入 | 登录/材料查询/检索的 `' OR '1'='1`、`%`、`_` 不返回 B 班数据 | `scripts/security_test.py` |
| XSS | `<script>` 在 JSON 中转为 `\u003cscript\u003e`，前端无 raw HTML、无 localStorage token | 同上 + `frontend/src/App.tsx` 静态检查 |
| CSRF | 无 token/恶意 Origin 403，正确 token 同源 200 | 同上 |
| 配置权限 SEC-03 | 学生改技能 403 且数据不变；教师成功；跨班助手 404 | 同上 |
| 技能绕过 SEC-04 | 学生只能运行自己的 grade 技能；他人/教师 404，无 task/outbox/result | 同上 |
| 审计 SEC-07 | 教师按 `skill_key=grade` 查到七列；学生查审计 403 | 同上 |
