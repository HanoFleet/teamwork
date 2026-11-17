# 复评记录 02：AI 自审（规约与代码）

- 手段：按 `.cursor/rules/campusclaw-standards.mdc`、`docs/standards/03-security.md`、`docs/standards/06-ai.md` 对照第 9 课 spec 和代码。
- 查了什么：CSRF token/Origin、`requireUser`、`catalog`、`audit`、`skills`/`assistants` 路由、`skill.run` 权限、审计字段、SQL 参数化、前端 raw HTML/localStorage。
- 判据：学生写配置 403；跨班/他人 404；技能入口不写结果；审计七列且无正文/密钥；XSS JSON 转义；无 raw HTML。
- 结果：`make check`、`python3 scripts/verify.py` 通过；安全回归 6 项全部 PASS；未发现规约与实现冲突。
- 说明：这是 AI/脚本自审记录，不是人工签字；人工复核仍需组内另一人执行。
