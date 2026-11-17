#!/usr/bin/env python3
"""第 9 课安全回归：SQLi、XSS、CSRF、配置权限、技能绕过和审计。"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from security_cases import load_cases  # noqa: E402


def run(*, note, fail, call, login, mysql, compose, ENV) -> None:
    note("## 安全回归（第 9 课）")
    cases = {item["kind"]: item for item in load_cases()}
    note("注入反例：" + "、".join(item["path"] for item in cases.values()))

    student = login("student_a1", ENV["SEED_STUDENT_A_PASSWORD"])
    student_b = login("student_b1", ENV["SEED_STUDENT_B_PASSWORD"])
    teacher = login("teacher_a", ENV["SEED_TEACHER_PASSWORD"])
    stamp = str(int(time.time() * 1000))

    def jcall(op, method, path, payload=None, headers=None):
        code, raw, h = call(op, method, path, payload, headers)
        try:
            parsed = json.loads(raw.decode() or "null")
        except (UnicodeDecodeError, json.JSONDecodeError):
            parsed = {"raw": raw.decode(errors="replace")}
        return code, parsed, h

    # SQL 注入：登录、材料查询、检索都不能返回 B 班内容。
    anon = urllib.request.build_opener()
    code, body, _ = jcall(
        anon,
        "POST",
        "/api/login",
        json.dumps({"username": "' OR '1'='1", "password": "x"}).encode(),
        {"Content-Type": "application/json"},
    )
    if code != 401:
        fail(f"SQLi 登录应为 401，实际 {code} {body}")
    for query in ("' OR '1'='1", "%", "_"):
        code, raw, _ = call(student, "GET", "/api/materials?q=" + urllib.parse.quote(query))
        if code != 200:
            fail(f"材料 SQLi 查询 {query!r} 应为 200，实际 {code}")
        if "B班-牛顿定律笔记" in raw.decode():
            fail(f"材料 SQLi 查询 {query!r} 泄露 B 班标题")
    for query in ("' OR '1'='1", "%", "_"):
        payload = json.dumps({"query": query, "mode": "keyword"}).encode()
        code, raw, _ = call(student, "POST", "/api/search", payload, {"Content-Type": "application/json"})
        if code != 200:
            fail(f"检索 SQLi 查询 {query!r} 应为 200，实际 {code}")
        if "B班-牛顿定律笔记" in raw.decode():
            fail(f"检索 SQLi 查询 {query!r} 泄露 B 班标题")
    note("PASS SQLi 登录/材料/检索不泄露跨班数据")

    # XSS：JSON 转义，前端不渲染 raw HTML，网页不存 Bearer token。
    boundary = "----campusclawxss" + stamp
    xss_body = f"# xss\n\n<script>alert(1)</script> {stamp}\n"
    multipart = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="xss-{stamp}.md"\r\n'
        "Content-Type: text/markdown\r\n\r\n"
        f"{xss_body}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    code, raw, _ = call(teacher, "POST", "/api/materials", multipart, {"Content-Type": f"multipart/form-data; boundary={boundary}"})
    if code != 201:
        fail(f"XSS 上传应为 201，实际 {code} {raw[:200]!r}")
    created = json.loads(raw)
    code, raw, _ = call(teacher, "GET", f"/api/materials/{created['id']}")
    text = raw.decode()
    if "<script>alert(1)</script>" in text:
        fail("材料详情 JSON 未转义 script")
    if "\\u003cscript\\u003e" not in text:
        fail("材料详情 JSON 没有转义形式 \\u003cscript\\u003e")
    for path in ("frontend/src/App.tsx", "frontend/src/Assignments.tsx"):
        src = (ROOT / path).read_text()
        if "rehype-raw" in src or "dangerouslySetInnerHTML" in src:
            fail(f"{path} 使用 raw HTML")
    if "campusclaw_token" in (ROOT / "frontend/src/api.ts").read_text():
        fail("前端 api.ts 仍在 localStorage 存 token")
    note("PASS XSS JSON 转义、前端无 raw HTML、无 localStorage token")

    # CSRF：无 token/跨源 403；正确 token 放行。
    original = jcall(teacher, "GET", "/api/skills")[1]["skills"]
    grade_skill = next((s for s in original if s.get("skill_key") == "grade"), None)
    if not grade_skill:
        fail("缺少 grade 技能")
    original_desc = grade_skill.get("description", "")
    code, body, _ = jcall(student, "PATCH", "/api/skills/grade", json.dumps({"description": "csrf-no-token"}).encode(), {"Content-Type": "application/json", "X-CSRF-Token": ""})
    if code != 403:
        fail(f"无 CSRF token 应为 403，实际 {code} {body}")
    token = getattr(teacher, "csrf_token", "")
    code, body, _ = jcall(teacher, "PATCH", "/api/skills/grade", json.dumps({"description": "csrf-evil"}).encode(), {"Content-Type": "application/json", "X-CSRF-Token": token, "Origin": "https://evil.example"})
    if code != 403:
        fail(f"跨源 Origin 应为 403，实际 {code} {body}")
    code, body, _ = jcall(teacher, "PATCH", "/api/skills/grade", json.dumps({"description": "csrf-ok"}).encode(), {"Content-Type": "application/json", "X-CSRF-Token": token, "Origin": "http://127.0.0.1:" + ENV.get("WEB_PORT", "8080")})
    if code != 200:
        fail(f"正确 CSRF 应为 200，实际 {code} {body}")
    note("PASS CSRF 无 token/跨源 403，正确 token 200")

    # SEC-03：学生写配置 403 且数据不变；教师写成功；跨班助手 404。
    # 拒绝记录按该学生加时间窗从审计接口回查，不靠直接数表。
    student_id = jcall(student, "GET", "/api/me")[1]["id"]
    window_start = datetime.now(timezone.utc) - timedelta(minutes=2)
    before = mysql("SELECT description FROM skills WHERE skill_key='grade'")
    code, body, _ = jcall(student, "PATCH", "/api/skills/grade", json.dumps({"description": "student-must-not"}).encode(), {"Content-Type": "application/json"})
    window_end = datetime.now(timezone.utc) + timedelta(minutes=2)
    after = mysql("SELECT description FROM skills WHERE skill_key='grade'")
    if code != 403 or before != after:
        fail(f"学生改技能应 403 且不变：{code} {before!r}->{after!r}")
    def audit_stamp(value: datetime) -> str:
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    code, body, _ = jcall(
        teacher,
        "GET",
        "/api/audit-logs?operator_id="
        + str(student_id)
        + "&from="
        + urllib.parse.quote(audit_stamp(window_start))
        + "&to="
        + urllib.parse.quote(audit_stamp(window_end))
        + "&limit=20",
    )
    logs = body.get("logs") if isinstance(body, dict) else None
    matched = [
        row
        for row in (logs or [])
        if row.get("operator_username") == "student_a1"
        and row.get("operation") == "config.change"
        and row.get("result_status") == "denied"
        and row.get("error_code") == "forbidden"
    ]
    if code != 200 or not matched:
        fail(f"按学生和时间窗应查到 403 审计：{code} {body}")
    code, old, _ = jcall(
        teacher,
        "GET",
        "/api/audit-logs?operator_id="
        + str(student_id)
        + "&from=2000-01-01T00:00:00Z&to=2000-01-02T00:00:00Z&limit=20",
    )
    old_logs = old.get("logs") if isinstance(old, dict) else None
    if code != 200 or old_logs:
        fail(f"过去时间窗不应返回审计行：{code} {old}")
    code, body, _ = jcall(teacher, "PATCH", "/api/skills/grade", json.dumps({"description": original_desc}).encode(), {"Content-Type": "application/json"})
    if code != 200:
        fail(f"教师恢复技能描述失败：{code} {body}")
    b_assistants = jcall(student_b, "GET", "/api/assistants")[1]["assistants"]
    if not b_assistants:
        fail("B 班没有助手")
    code, body, _ = jcall(teacher, "PATCH", f"/api/assistants/{b_assistants[0]['id']}", json.dumps({"name": "cross-class"}).encode(), {"Content-Type": "application/json"})
    if code != 404:
        fail(f"跨班助手应 404，实际 {code} {body}")
    note("PASS SEC-03 学生 403/数据不变，教师成功，跨班 404，时间窗查到 denied")

    # SEC-04：技能入口只能操作自己的提交；他人/教师 404 且无 task/outbox/result。
    assignments = jcall(student, "GET", "/api/assignments")[1]["assignments"]
    if not assignments:
        fail("没有已发布作业")
    aid = assignments[0]["id"]
    own_body = f"函数单调性 证明 实验 结论 {stamp} own"
    code, own, _ = jcall(student, "POST", f"/api/assignments/{aid}/submissions", json.dumps({"body": own_body}).encode(), {"Content-Type": "application/json"})
    if code not in (200, 201):
        fail(f"学生提交失败：{code} {own}")
    b_assignments = jcall(student_b, "GET", "/api/assignments")[1]["assignments"]
    if not b_assignments:
        fail("B 班没有已发布作业")
    b_aid = b_assignments[0]["id"]
    b_body = f"函数单调性 证明 实验 结论 {stamp} b"
    code, b_submit, _ = jcall(student_b, "POST", f"/api/assignments/{b_aid}/submissions", json.dumps({"body": b_body}).encode(), {"Content-Type": "application/json"})
    if code not in (200, 201):
        fail(f"B 班提交失败：{code} {b_submit}")
    b_sub = b_submit["submission_id"]
    own_id = own["submission_id"]
    code, body, _ = jcall(student, "POST", "/api/skills/grade/run", json.dumps({"submission_id": own_id, "score": 100}).encode(), {"Content-Type": "application/json"})
    if code != 202:
        fail(f"本人技能运行应 202，实际 {code} {body}")
    if "score" in body or "feedback" in body:
        fail("202 响应泄露分数/评语")
    for op, sid, who in ((student, b_sub, "A1 对 B1"), (teacher, own_id, "教师对 A1")):
        code, body, _ = jcall(op, "POST", "/api/skills/grade/run", json.dumps({"submission_id": sid}).encode(), {"Content-Type": "application/json"})
        if code != 404:
            fail(f"{who} 技能运行应 404，实际 {code} {body}")
    if mysql(f"SELECT COUNT(*) FROM grade_tasks WHERE submission_id={b_sub}") != "0":
        fail("他人技能运行留下了 grade_task")
    if mysql(f"SELECT COUNT(*) FROM outbox_messages WHERE idempotency_key LIKE 'grade:{b_sub}:%'") != "0":
        fail("他人技能运行留下了 outbox")
    note("PASS SEC-04 本人 202，他人/教师 404 且无 task/outbox")

    # SEC-07：审计七列、按 skill_key 查询、学生 403。
    student_id = jcall(student, "GET", "/api/me")[1]["id"]
    code, body, _ = jcall(teacher, "GET", f"/api/audit-logs?skill_key=grade&operator_id={student_id}&limit=20")
    if code != 200 or not body.get("logs"):
        fail(f"审计查询失败：{code} {body}")
    row = body["logs"][0]
    needed = {"operator_username", "occurred_at", "operation", "object_type", "object_id", "result_status", "skill_key", "duration_ms"}
    if not needed.issubset(row):
        fail(f"审计缺七列：{needed - set(row)}")
    if row.get("skill_key") != "grade" or row.get("operator_username") != "student_a1":
        fail(f"审计行归属/技能不对：{row}")
    code, body, _ = jcall(student, "GET", "/api/audit-logs")
    if code != 403:
        fail(f"学生查审计应 403，实际 {code} {body}")
    note("PASS SEC-07 教师按 skill_key 查到七列，学生 403")

    # 静态：测试说明落盘。
    if not (ROOT / "apitest" / "cases" / "security" / "README.md").is_file():
        fail("apitest/cases/security/README.md 不存在")
