# 验收记录

目标：`http://127.0.0.1:64833`

## 安全回归（第 9 课）
注入反例：apitest/cases/api/search/POST/case.json、apitest/cases/api/materials/POST/case.json、apitest/cases/api/skills/grade/PATCH/case.json
PASS SQLi 登录/材料/检索不泄露跨班数据
PASS XSS JSON 转义、前端无 raw HTML、无 localStorage token
PASS CSRF 无 token/跨源 403，正确 token 200
PASS SEC-03 学生 403/数据不变，教师成功，跨班 404，时间窗查到 denied
PASS SEC-04 本人 202，他人/教师 404 且无 task/outbox
PASS SEC-07 教师按 skill_key 查到七列，学生 403
