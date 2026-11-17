# 第 9 课安全修复对照

- 执行时间：2026-11-17
- 执行人：自动化实现 + 本地 Compose 复跑
- 基线：第 8 课 `reports/security-precheck.md`（SEC-03/04/07 红，SEC-08 未做）
- 修复后命令：`python3 scripts/verify.py`、`make check`、`make check-security`
- 实际输出：`docs/verification.md`、`reports/gate-red-green.md`、`reports/sec08-experiment.md`

| 编号 | 修复前实际 | 修复后实际 | 判定 |
| --- | --- | --- | --- |
| SEC-03 学生修改技能/提示词 | 无配置写接口，无法执行，红 | 学生 `PATCH /api/skills/grade` → 403，技能描述不变；教师同请求 → 200；A 教师改 B 助手 → 404；审计有 denied 行 | 绿 |
| SEC-04 技能工具绕过鉴权 | 无技能执行链，只测了跨班入队，红 | 学生 `POST /api/skills/grade/run` 自己的提交 → 202；对 B 班提交 → 404；教师对 A 提交 → 404；`grade_tasks`/`outbox_messages` 无残留；响应不接受 `score` | 绿 |
| SEC-07 技能调用审计 | 只有 worker 任务日志，缺操作人、技能标识、用量，红 | `audit_logs` 落库；教师按 `skill_key=grade` 查到操作人、UTC 时间、`skill.run`、submission 对象、accepted、`grade`、耗时、usage；学生查询 403 | 绿 |
| SEC-08 恶意文档/提示词注入 | 未准备素材，未做 | 恶意讲义 + 3 条诱导提问已归档；四步实验记录在 `reports/sec08-experiment.md`；第四步写入层 404 且审计 denied | 绿（第四步） |

## 复跑命令

```bash
make check
make check-security
python3 scripts/security_gate.py --self-test
python3 scripts/verify.py
```

## 说明

- SEC-01/02/05/06 沿用第 8 课绿项；第 9 课未降低其要求。
- 审计行不包含提交正文、提示词、密钥或模型原始输出。
- `SEC-08` 前三步只记录现象；本地 `CHAT_URL=local` 仍会引用恶意材料原文，但评分结果不被带偏（实际 score=0），第四步由 API/技能层拒绝。
