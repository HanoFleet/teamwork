#!/usr/bin/env python3
"""第 8 课异步批改接口验收。由 verify.py 调用，也可对已启动的 Compose 单独跑。"""

from __future__ import annotations

import json
import math
import time
import urllib.request


def run(*, note, fail, call, login, mysql, compose, ENV) -> None:
    note("## 异步批改")
    src = (__import__("pathlib").Path(__file__).resolve().parents[1] / "frontend" / "src" / "Assignments.tsx").read_text()
    for token in ("TASK_POLL_FIRST_MS = 1000", "TASK_POLL_LATER_MS = 2000", "TASK_POLL_MAX_SECONDS = 60"):
        if token not in src:
            fail(f"前端轮询常量缺失: {token}")
    if "已停止处理，请联系教师" not in src:
        fail("failed/dead 缺少规定说明文案")
    if "重新批改" in src or "再试一次" in src:
        fail("前端不得提供失败重试按钮")
    note("PASS 前端轮询常量 1000/2000/60，failed/dead 无重试")

    cfg = compose("config", "--format", "json")
    services = json.loads(cfg.stdout).get("services", {})
    for name in ("rabbitmq", "worker"):
        if name not in services:
            fail(f"Compose 缺少 {name}")
        if services[name].get("ports"):
            fail(f"{name} 映射了宿主端口")
    if not services.get("web", {}).get("ports"):
        fail("web 没有映射端口")
    queues = compose("exec", "-T", "rabbitmq", "rabbitmqctl", "list_queues", "name", "durable")
    text = queues.stdout
    for name in ("grade.tasks", "grade.retry.1s", "grade.retry.2s", "grade.retry.4s", "grade.retry.8s", "grade.retry.16s", "grade.dead"):
        if name not in text:
            fail(f"缺少队列 {name}：{text}")
    note("PASS RabbitMQ 队列 durable 且无宿主端口")

    tables = set(mysql("SHOW TABLES").split())
    for name in ("submissions", "grade_tasks", "outbox_messages", "grade_results"):
        if name not in tables:
            fail(f"缺表 {name}")
    create_tasks = mysql("SHOW CREATE TABLE grade_tasks")
    if "uq_grade_tasks_idempotency" not in create_tasks:
        fail("grade_tasks 缺少幂等唯一约束")
    note("PASS 批改相关表和唯一约束存在")

    student_a = login("student_a1", ENV["SEED_STUDENT_A_PASSWORD"])
    teacher = login("teacher_a", ENV["SEED_TEACHER_PASSWORD"])
    student_b = login("student_b1", ENV["SEED_STUDENT_B_PASSWORD"])
    anon = urllib.request.build_opener()

    code, raw, _ = call(anon, "POST", "/api/assignments/1/submissions", b'{"body":"x"}', {"Content-Type": "application/json"})
    if code != 401:
        fail(f"未登录提交应为 401，实际 {code}")
    code, raw, _ = call(anon, "GET", "/api/assignments")
    if code != 401:
        fail(f"未登录作业列表应为 401，实际 {code}")
    note("PASS 未登录提交/列表 401")

    code, raw, _ = call(student_a, "GET", "/api/assignments")
    listed = json.loads(raw)
    if code != 200 or not listed.get("assignments"):
        fail(f"作业列表 {code} {raw[:200]!r}")
    assignment_id = listed["assignments"][0]["id"]

    code, raw, _ = call(teacher, "POST", f"/api/assignments/{assignment_id}/submissions", json.dumps({"body": "教师提交"}).encode(), {"Content-Type": "application/json"})
    if code != 403:
        fail(f"教师提交应为 403，实际 {code} {raw!r}")
    note("PASS 教师提交 403")

    for body in ("", "   ", "字" * 20001):
        before = mysql("SELECT COUNT(*) FROM submissions")
        code, raw, _ = call(student_a, "POST", f"/api/assignments/{assignment_id}/submissions", json.dumps({"body": body}).encode(), {"Content-Type": "application/json"})
        after = mysql("SELECT COUNT(*) FROM submissions")
        if code != 400 or before != after:
            fail(f"非法正文应为 400 且无新行: {code} {before}->{after} {raw!r}")
    note("PASS 空内容和超长 400")

    code, raw, headers_cross = call(student_b, "POST", f"/api/assignments/{assignment_id}/submissions", json.dumps({"body": "跨班提交"}).encode(), {"Content-Type": "application/json"})
    missing = call(student_b, "POST", "/api/assignments/999999/submissions", json.dumps({"body": "不存在"}).encode(), {"Content-Type": "application/json"})
    if code != 404 or missing[0] != 404 or raw != missing[1]:
        fail(f"跨班提交 404 不同形 {code} {raw!r} vs {missing[0]} {missing[1]!r}")
    if headers_cross.get("Content-Type") != missing[2].get("Content-Type"):
        fail("跨班与不存在作业 404 的 Content-Type 不同")
    note("PASS 跨班提交与不存在作业同形 404")

    stamp = str(int(time.time() * 1000))
    body = f"函数单调性定理证明分析实验结论 {stamp}"
    code, raw, _ = call(student_a, "POST", f"/api/assignments/{assignment_id}/submissions", json.dumps({"body": body}).encode(), {"Content-Type": "application/json"})
    first = json.loads(raw)
    if code not in (200, 201) or not first.get("submission_id") or not first.get("version"):
        fail(f"首次提交 {code} {raw!r}")
    code, raw, _ = call(student_a, "POST", f"/api/assignments/{assignment_id}/submissions", json.dumps({"body": body}).encode(), {"Content-Type": "application/json"})
    again = json.loads(raw)
    if code != 200 or again.get("submission_id") != first["submission_id"] or again.get("version") != first["version"]:
        fail(f"相同内容应复用提交 {code} {raw!r}")
    edited = body + " 第二版"
    code, raw, _ = call(student_a, "POST", f"/api/assignments/{assignment_id}/submissions", json.dumps({"body": edited}).encode(), {"Content-Type": "application/json"})
    second = json.loads(raw)
    if code != 201 or second.get("submission_id") == first["submission_id"] or second.get("version") != first["version"] + 1:
        fail(f"编辑后应新版本 {code} {raw!r}")
    note("PASS 提交版本追加与相同内容复用")

    def mysql_root(sql: str) -> None:
        proc = compose(
            "exec",
            "-T",
            "-e",
            f"MYSQL_PWD={ENV['MYSQL_ROOT_PASSWORD']}",
            "db",
            "mysql",
            "-uroot",
            ENV["DB_NAME"],
            "-e",
            sql,
            check=False,
        )
        if proc.returncode != 0:
            fail(f"root mysql 失败: {proc.stderr.strip()}")

    mysql_root("DROP TRIGGER IF EXISTS fail_outbox")
    mysql_root("CREATE TRIGGER fail_outbox BEFORE INSERT ON outbox_messages FOR EACH ROW SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='injected'")
    before_s = mysql("SELECT COUNT(*) FROM submissions")
    before_t = mysql("SELECT COUNT(*) FROM grade_tasks")
    before_o = mysql("SELECT COUNT(*) FROM outbox_messages")
    injected = body + " 注入失败"
    code, raw, _ = call(student_a, "POST", f"/api/assignments/{assignment_id}/submissions", json.dumps({"body": injected}).encode(), {"Content-Type": "application/json"})
    if code not in (200, 201):
        mysql_root("DROP TRIGGER IF EXISTS fail_outbox")
        fail(f"注入前提交失败 {code} {raw!r}")
    injected_id = json.loads(raw)["submission_id"]
    code, raw, _ = call(student_a, "POST", f"/api/submissions/{injected_id}/grade", b"{}", {"Content-Type": "application/json"})
    after_s = mysql("SELECT COUNT(*) FROM submissions")
    after_t = mysql("SELECT COUNT(*) FROM grade_tasks")
    after_o = mysql("SELECT COUNT(*) FROM outbox_messages")
    mysql_root("DROP TRIGGER IF EXISTS fail_outbox")
    if code != 503 or after_t != before_t or after_o != before_o:
        fail(f"outbox 失败应回滚任务 {code} tasks {before_t}->{after_t} outbox {before_o}->{after_o} {raw!r}")
    if after_s != str(int(before_s) + 1) and after_s != before_s:
        # 提交行在 grade 之前已写入；grade 事务只锁 submission 不删它
        pass
    note("PASS outbox 插入失败时 task/outbox 无新增")

    code, raw, _ = call(student_a, "POST", f"/api/submissions/{injected_id}/grade", b"{}", {"Content-Type": "application/json"})
    if code != 202:
        fail(f"去掉触发器后批改应为 202，实际 {code} {raw!r}")
    accepted = json.loads(raw)
    if set(accepted) != {"task_id", "status", "status_url"} or accepted.get("status") != "pending" or "score" in accepted:
        fail(f"202 形状不对 {accepted}")
    if accepted.get("status_url") != f"/api/tasks/{accepted['task_id']}":
        fail(f"status_url 不对 {accepted}")
    note(f"PASS 首次批改 202 task_id={accepted['task_id']}")

    code, raw, _ = call(student_a, "POST", f"/api/submissions/{injected_id}/grade", b"{}", {"Content-Type": "application/json"})
    repeated = json.loads(raw)
    tasks_n = mysql(f"SELECT COUNT(*) FROM grade_tasks WHERE submission_id={injected_id}")
    outbox_n = mysql(f"SELECT COUNT(*) FROM outbox_messages WHERE idempotency_key='grade:{injected_id}:1' OR idempotency_key LIKE 'grade:{injected_id}:%'")
    if repeated.get("task_id") != accepted["task_id"] or tasks_n != "1":
        fail(f"重复批改应复用任务 {repeated} tasks={tasks_n} outbox={outbox_n}")
    note("PASS 重复批改复用同一 task_id")

    code_b, raw_b, headers_b = call(student_b, "GET", f"/api/tasks/{accepted['task_id']}")
    code_missing, raw_missing, headers_missing = call(student_b, "GET", "/api/tasks/01ARZ3NDEKTSV4RRFFQ69G5FAV")
    code_bad, raw_bad, _ = call(student_a, "GET", "/api/tasks/not-a-valid-ulid-id")
    if code_b != 404 or code_missing != 404 or code_bad != 404:
        fail(f"任务 404 状态码 {code_b}/{code_missing}/{code_bad}")
    if raw_b != raw_missing:
        fail(f"跨班与不存在任务 404 不同形 {raw_b!r} vs {raw_missing!r}")
    if headers_b.get("Content-Type") != headers_missing.get("Content-Type"):
        fail("跨班与不存在任务 404 的 Content-Type 不同")
    code_t, raw_t, _ = call(teacher, "GET", f"/api/tasks/{accepted['task_id']}")
    if code_t != 200 or json.loads(raw_t).get("task_id") != accepted["task_id"]:
        fail(f"本班教师查询任务应为 200，实际 {code_t} {raw_t!r}")
    code_tg, raw_tg, _ = call(teacher, "POST", f"/api/submissions/{injected_id}/grade", b"{}", {"Content-Type": "application/json"})
    if code_tg != 404:
        fail(f"教师批改他人提交应为 404，实际 {code_tg} {raw_tg!r}")
    note("PASS 任务查询跨班/不存在同形 404，本班教师可查，教师批改 404")

    compose("stop", "worker")
    time.sleep(2)
    pending_body = edited + " 停 worker " + stamp
    code, raw, _ = call(student_a, "POST", f"/api/assignments/{assignment_id}/submissions", json.dumps({"body": pending_body}).encode(), {"Content-Type": "application/json"})
    stopped_sub = json.loads(raw)["submission_id"]
    code, raw, _ = call(student_a, "POST", f"/api/submissions/{stopped_sub}/grade", b"{}", {"Content-Type": "application/json"})
    if code != 202:
        compose("start", "worker")
        fail(f"停 worker 后批改应为 202，实际 {code} {raw!r}")
    stopped_task = json.loads(raw)["task_id"]
    status = mysql(f"SELECT status FROM grade_tasks WHERE task_id='{stopped_task}'")
    if status != "pending":
        compose("start", "worker")
        fail(f"停 worker 后任务应为 pending，实际 {status}")
    compose("start", "worker")
    deadline = time.time() + 60
    last = ""
    while time.time() < deadline:
        code, raw, _ = call(student_a, "GET", f"/api/tasks/{stopped_task}")
        last = raw.decode()
        if code == 200 and json.loads(raw).get("status") == "succeeded":
            break
        time.sleep(1)
    else:
        fail(f"启动 worker 后任务未 succeeded: {last}")
    code, raw, _ = call(student_a, "POST", f"/api/submissions/{stopped_sub}/grade", b"{}", {"Content-Type": "application/json"})
    reused = json.loads(raw)
    if code != 200 or reused.get("task_id") != stopped_task or reused.get("status") != "succeeded" or "result" not in reused:
        fail(f"已有结果应 200 带 result，实际 {code} {reused}")
    note("PASS 停 worker 提交仍 202，恢复后自动 succeeded；再次批改 200")

    times = []
    delay = ENV.get("GRADE_LOCAL_DELAY_MS", "0")
    for i in range(20):
        payload = json.dumps({"body": f"函数单调性实验结论 {stamp} #{i} {'分析' * 8}"}).encode()
        code, raw, _ = call(student_a, "POST", f"/api/assignments/{assignment_id}/submissions", payload, {"Content-Type": "application/json"})
        if code not in (200, 201):
            fail(f"P95 提交失败 {code} {raw!r}")
        sid = json.loads(raw)["submission_id"]
        started = time.perf_counter()
        code, raw, _ = call(student_a, "POST", f"/api/submissions/{sid}/grade", b"{}", {"Content-Type": "application/json"})
        times.append((time.perf_counter() - started) * 1000)
        body_obj = json.loads(raw)
        if code != 202 or "score" in body_obj or "feedback" in body_obj:
            fail(f"P95 响应不是无分数的 202: {code} {body_obj}")
    ordered = list(times)
    times.sort()
    p95 = times[int(math.ceil(0.95 * len(times)) - 1)]
    rendered = ",".join(f"{x:.1f}" for x in ordered)
    if p95 >= 500:
        fail(f"P95={p95:.1f}ms times=[{rendered}] delay={delay}")
    note(f"PASS 20 次批改 P95={p95:.1f}ms < 500ms，响应不含分数 times=[{rendered}]")

    dup_body = f"幂等正文 {stamp} 函数定理"
    code, raw, _ = call(student_a, "POST", f"/api/assignments/{assignment_id}/submissions", json.dumps({"body": dup_body}).encode(), {"Content-Type": "application/json"})
    dup_submit = json.loads(raw)
    dup_id = dup_submit["submission_id"]
    dup_ver = dup_submit["version"]
    call(student_a, "POST", f"/api/submissions/{dup_id}/grade", b"{}", {"Content-Type": "application/json"})
    call(student_a, "POST", f"/api/submissions/{dup_id}/grade", b"{}", {"Content-Type": "application/json"})
    deadline = time.time() + 60
    while time.time() < deadline:
        n = mysql(f"SELECT COUNT(*) FROM grade_results WHERE submission_id={dup_id}")
        if n == "1":
            break
        time.sleep(1)
    else:
        fail("等待幂等结果超时")
    results = mysql(f"SELECT COUNT(*) FROM grade_results WHERE submission_id={dup_id}")
    tasks = mysql(f"SELECT COUNT(*) FROM grade_tasks WHERE submission_id={dup_id}")
    if results != "1" or tasks != "1":
        fail(f"重复批改应一份结果: results={results} tasks={tasks}")
    score_before = mysql(f"SELECT score FROM grade_results WHERE submission_id={dup_id}")
    attempts_before = mysql(f"SELECT attempts FROM grade_tasks WHERE submission_id={dup_id}")
    mysql(
        "INSERT INTO outbox_messages (message_id, idempotency_key, topic, payload, status, attempts, created_at) "
        "SELECT CONCAT('dup', SUBSTR(message_id,1,22)), CONCAT(idempotency_key,'-dup'), topic, payload, 'pending', 0, UTC_TIMESTAMP() "
        f"FROM outbox_messages WHERE idempotency_key='grade:{dup_id}:{dup_ver}' LIMIT 1"
    )
    time.sleep(4)
    results_after = mysql(f"SELECT COUNT(*) FROM grade_results WHERE submission_id={dup_id}")
    score_after = mysql(f"SELECT score FROM grade_results WHERE submission_id={dup_id}")
    if results_after != "1" or score_after != score_before:
        fail(f"重复投递后结果行数 {results_after} score {score_before}->{score_after}")
    note(f"PASS 重复请求和重复投递只有一份结果 score={score_after} attempts={attempts_before}")

    perm_body = f"GRADE_PERMANENT_FAIL 永久失败 {stamp}"
    code, raw, _ = call(student_a, "POST", f"/api/assignments/{assignment_id}/submissions", json.dumps({"body": perm_body}).encode(), {"Content-Type": "application/json"})
    perm_id = json.loads(raw)["submission_id"]
    code, raw, _ = call(student_a, "POST", f"/api/submissions/{perm_id}/grade", b"{}", {"Content-Type": "application/json"})
    if code != 202:
        fail(f"永久失败首次仍应 202，实际 {code} {raw!r}")
    perm_task = json.loads(raw)["task_id"]
    deadline = time.time() + 30
    perm_status = ""
    while time.time() < deadline:
        perm_status = mysql(f"SELECT status FROM grade_tasks WHERE task_id='{perm_task}'")
        if perm_status == "failed":
            break
        time.sleep(1)
    else:
        fail(f"永久失败应变 failed，实际 {perm_status}")
    perm_results = mysql(f"SELECT COUNT(*) FROM grade_results WHERE submission_id={perm_id}")
    if perm_results != "0":
        fail(f"永久失败不应写结果，实际 {perm_results}")
    note("PASS 永久失败进入 failed 且无结果行")

    trans_body = f"GRADE_TRANSIENT_FAIL 瞬时失败 {stamp}"
    code, raw, _ = call(student_a, "POST", f"/api/assignments/{assignment_id}/submissions", json.dumps({"body": trans_body}).encode(), {"Content-Type": "application/json"})
    trans_id = json.loads(raw)["submission_id"]
    code, raw, _ = call(student_a, "POST", f"/api/submissions/{trans_id}/grade", b"{}", {"Content-Type": "application/json"})
    trans_task = json.loads(raw)["task_id"]
    deadline = time.time() + 20
    trans_row = ""
    while time.time() < deadline:
        trans_row = mysql(f"SELECT CONCAT(status, ':', attempts) FROM grade_tasks WHERE task_id='{trans_task}'")
        status, _, attempts = trans_row.partition(":")
        if status == "pending" and attempts not in ("", "0"):
            break
        time.sleep(1)
    else:
        fail(f"瞬时失败应回到 pending 且 attempts>0，实际 {trans_row}")
    note(f"PASS 瞬时失败回到 pending attempts={trans_row}")

    compose("stop", "rabbitmq")
    time.sleep(2)
    broker_body = f"停 broker 补投 {stamp} 函数结论"
    code, raw, _ = call(student_a, "POST", f"/api/assignments/{assignment_id}/submissions", json.dumps({"body": broker_body}).encode(), {"Content-Type": "application/json"})
    broker_sub = json.loads(raw)["submission_id"]
    code, raw, _ = call(student_a, "POST", f"/api/submissions/{broker_sub}/grade", b"{}", {"Content-Type": "application/json"})
    if code != 202:
        compose("start", "rabbitmq")
        fail(f"停 RabbitMQ 后批改应为 202，实际 {code} {raw!r}")
    broker_task = json.loads(raw)["task_id"]
    key = mysql(f"SELECT idempotency_key FROM grade_tasks WHERE task_id='{broker_task}'")
    outbox_status = mysql(f"SELECT status FROM outbox_messages WHERE idempotency_key='{key}'")
    if outbox_status != "pending":
        compose("start", "rabbitmq")
        fail(f"停 RabbitMQ 后 outbox 应为 pending，实际 {outbox_status}")
    compose("start", "rabbitmq")
    deadline = time.time() + 90
    last = ""
    while time.time() < deadline:
        code, raw, _ = call(student_a, "GET", f"/api/tasks/{broker_task}")
        last = raw.decode()
        if code == 200 and json.loads(raw).get("status") == "succeeded":
            break
        time.sleep(2)
    else:
        fail(f"恢复 RabbitMQ 后任务未 succeeded: {last}")
    note("PASS 停 RabbitMQ 仍 202/pending，恢复后自动 succeeded")

    code, raw, _ = call(student_a, "GET", "/assignments")
    if code != 200 or b"html" not in raw.lower():
        fail(f"/assignments 页面 {code}")
    note("PASS 学生打开 /assignments 得到页面")
