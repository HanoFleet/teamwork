# Playwright 作业页验收

- 执行时间：2026-11-17
- 执行人：自动化脚本（本地 Compose，`GRADE_LOCAL_DELAY_MS=2000`）
- 目录：`frontend/e2e`
- 命令：`npx playwright test`
- 实际输出：

```text
Running 1 test using 1 worker

  ✓  1 assignments.spec.ts:2:1 › 学生从 /assignments 提交并轮询到 succeeded (4.3s)

  1 passed (4.7s)
```

## 判据

- 学生通过 API 登录后打开 `/assignments`，页面显示“A班作业”。
- 选择已发布作业，填入正文并点击“提交并批改”。
- 页面在 60 秒内从 pending/running 轮询到“批改完成”，显示“分数：”。
- 没有前端重试按钮；失败/dead 只显示原因和“已停止处理，请联系教师”。
