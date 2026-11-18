"""security-hardening/复测整改证据: retain every fresh-grade sample and DB evidence.

Run at repository root. Never logs SQL literals, credentials or request bodies.
The original urllib request boundary, 20 sequential fresh submissions, and P95 < 500ms
hard assertion are retained. Individual latency >100ms emits warnings. SQL observation happens outside timed calls.
"""
import argparse
import datetime
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests/support"))
from isolated_project import Project
from check_single_request_limit import RULE, evaluate_samples, print_evaluation


def save(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode())


def sql(project, statement):
    # Password expands inside the owned container, never in command args or logs.
    result = project.a.compose("exec", "-T", "db", "sh", "-c",
        'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --batch --raw --skip-column-names -e "$1"',
        "qa-sql", statement)
    return result.stdout.strip()


def sample(project, output, round_id):
    v = project.verifier()
    student = v.login("student_a1", v.ENV["SEED_STUDENT_A_PASSWORD"])
    code, raw, _ = v.call(student, "GET", "/api/assignments")
    assert code == 200 and json.loads(raw)["assignments"]
    assignment = json.loads(raw)["assignments"][0]["id"]
    anchor = sql(project, "SELECT UNIX_TIMESTAMP(NOW(6))*1000,TIMER_START FROM performance_schema.events_statements_current WHERE THREAD_ID=(SELECT THREAD_ID FROM performance_schema.threads WHERE PROCESSLIST_ID=CONNECTION_ID())")
    # Observe lock edges through one root connection; never save business keys.
    lock_query = "SELECT UNIX_TIMESTAMP(NOW(6))*1000,w.REQUESTING_THREAD_ID,w.BLOCKING_THREAD_ID,b.OBJECT_NAME,b.INDEX_NAME,b.LOCK_TYPE,b.LOCK_MODE,CASE WHEN b.LOCK_DATA='supremum pseudo-record' THEN b.LOCK_DATA ELSE 'record-key-redacted' END FROM performance_schema.data_lock_waits w JOIN performance_schema.data_locks b ON w.BLOCKING_ENGINE_LOCK_ID=b.ENGINE_LOCK_ID; DO SLEEP(0.01);\n"
    pool = ThreadPoolExecutor(max_workers=1)
    def observe():
        return subprocess.run(["docker", "compose", "-p", project.name, "--env-file", str(project.a.ENV_FILE),
            "exec", "-T", "db", "sh", "-c", 'MYSQL_PWD="$MYSQL_ROOT_PASSWORD" mysql -uroot --batch --raw --skip-column-names'],
            input=lock_query * 1000, capture_output=True, text=True, timeout=60)
    observer = pool.submit(observe)
    stamp = str(time.time_ns())
    samples = []
    for i in range(20):
        code, raw, _ = v.call(student, "POST", f"/api/assignments/{assignment}/submissions",
            json.dumps({"body": f"函数单调性实验结论 {stamp} #{i} " + "分析" * 8}).encode(), {"Content-Type": "application/json"})
        assert code in (200, 201)
        sid = json.loads(raw)["submission_id"]
        rid = f"l9-diagnostic-{round_id}-{stamp}-{i}"
        headers = {"Content-Type": "application/json", "X-Request-ID": rid}
        # Same boundary as async_test.py: includes call(), request and response read.
        payload = json.dumps({}).encode()
        epoch_ms = time.time_ns() / 1e6
        start = time.perf_counter()
        code, raw, _ = v.call(student, "POST", f"/api/submissions/{sid}/grade", payload, headers)
        elapsed = (time.perf_counter() - start) * 1000
        body = json.loads(raw)
        row = {"index": i, "submission_id": sid, "request_id": rid, "start_epoch_ms": epoch_ms,
               "elapsed_ms": elapsed, "status": code, "accepted_without_result": code == 202 and "score" not in body and "feedback" not in body}
        samples.append(row)
        # Persist even partial runs if an assertion fails.
        save(output / f"performance-{round_id}.json", {"samples": samples, "complete": False})
        assert row["accepted_without_result"], row
    ordered = sorted(x["elapsed_ms"] for x in samples)
    result = {"time": datetime.datetime.now().astimezone().isoformat(), "samples": samples,
              "sample_count": len(samples), "max_ms": max(ordered), "p95_ms": ordered[18],
              "over_100_ms": sum(x > 100 for x in ordered), "observation_threshold_ms": 100,
              "complete": True, "db_anchor": anchor}
    result.update(evaluate_samples(samples))
    print_evaluation(result)
    save(output / f"performance-{round_id}.json", result)
    try:
        observed = observer.result(timeout=65)
        (output / f"lock-edges-{round_id}.tsv").write_bytes(("epoch_ms\twaiter_thread\tblocker_thread\ttable\tindex\tlock_type\tlock_mode\tkey_class\n" + observed.stdout).encode())
        if observed.returncode:
            (output / f"lock-observer-{round_id}.stderr.txt").write_bytes(observed.stderr.encode())
    finally:
        pool.shutdown(wait=True)
    if anchor:
        timer = int(anchor.split("\t")[1])
        rows = sql(project, f"SELECT THREAD_ID,EVENT_ID,TIMER_START,TIMER_END,ROUND(TIMER_WAIT/1000000000,3),ROUND(LOCK_TIME/1000000000,3),COALESCE(DIGEST_TEXT,EVENT_NAME),ROWS_AFFECTED FROM performance_schema.events_statements_history_long WHERE TIMER_START>={timer} AND CURRENT_SCHEMA IS NOT NULL ORDER BY TIMER_START")
        (output / f"sql-statements-{round_id}.tsv").write_bytes(("thread_id\tevent_id\tstart_ps\tend_ps\tduration_ms\tlock_ms\tdigest\trows_affected\n" + rows + "\n").encode())
        waits = sql(project, f"SELECT THREAD_ID,EVENT_ID,TIMER_START,TIMER_END,ROUND(TIMER_WAIT/1000000000,3),EVENT_NAME,OPERATION,CASE WHEN EVENT_NAME='wait/io/table/sql/handler' THEN COALESCE(OBJECT_NAME,'') ELSE '' END FROM performance_schema.events_waits_history_long WHERE TIMER_START>={timer} AND TIMER_WAIT>1000000000 AND EVENT_NAME<>'idle' ORDER BY TIMER_START")
        (output / f"db-waits-{round_id}.tsv").write_bytes(("thread_id\tevent_id\tstart_ps\tend_ps\tduration_ms\tevent\toperation\ttable\n" + waits + "\n").encode())
    logs = project.a.compose("logs", "--no-log-prefix", "api").stdout
    access = []
    for line in logs.splitlines():
        try: entry = json.loads(line)
        except (ValueError, TypeError): continue
        if entry.get("request_id", "").startswith(f"l9-diagnostic-{round_id}-"):
            access.append({k: entry[k] for k in ["ts", "request_id", "duration_ms", "status", "method"] if k in entry})
    save(output / f"api-timings-{round_id}.json", access)
    print(json.dumps({"round": round_id, "max_ms": result["max_ms"], "over_100_ms": result["over_100_ms"]}), flush=True)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--subnet", required=True)
    p.add_argument("--build-proxy")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--label", default="baseline")
    p.add_argument("--regression", action="store_true")
    p.add_argument("--backend-image", help="Reuse a previously verified image only if backend has no changes")
    p.add_argument("--goproxy", help="Optional backend build arg, never passed to application runtime")
    options = p.parse_args()
    options.output.mkdir(parents=True, exist_ok=False)
    summary = {"rule": RULE, "started": datetime.datetime.now().astimezone().isoformat(), "label": options.label,
               "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "uncommitted": True}
    try:
        with Project("latency-diagnosis", options) as project:
            summary["project"] = project.name
            build = ("build",)
            if options.goproxy:
                build += ("--build-arg", "GOPROXY=" + options.goproxy)
            if options.backend_image:
                subprocess.run(["git", "diff", "--exit-code", "HEAD", "--", "backend"], check=True, stdout=subprocess.DEVNULL)
                summary["backend_image"] = subprocess.check_output(["docker", "image", "inspect", options.backend_image, "--format", "{{.Id}}"], text=True).strip()
                summary["backend_tree"] = subprocess.check_output(["git", "rev-parse", "HEAD:backend"], text=True).strip()
                for service in ["api", "worker"]:
                    subprocess.run(["docker", "tag", options.backend_image, project.name + "-" + service], check=True)
                build = ("build", "web")
            for name, args, timeout in [("compose-build", build, 600), ("compose-up", ("up", "-d", "--wait"), 300)]:
                result = project.a.compose(*args, check=False, timeout=timeout)
                (options.output / (name + ".txt")).write_bytes((result.stdout + result.stderr).encode())
                if result.returncode:
                    raise RuntimeError(f"{name} failed: exit {result.returncode}; see saved output")
            sql(project, "UPDATE performance_schema.setup_consumers SET ENABLED='YES' WHERE NAME IN ('events_statements_current','events_statements_history_long','events_waits_current','events_waits_history_long'); UPDATE performance_schema.setup_instruments SET ENABLED='YES',TIMED='YES' WHERE NAME LIKE 'wait/io/file/innodb/%'")
            config = sql(project, "SELECT @@version,@@innodb_flush_log_at_trx_commit,@@sync_binlog,@@innodb_flush_method,@@innodb_use_native_aio; SHOW GLOBAL STATUS WHERE Variable_name IN ('Innodb_os_log_fsyncs','Innodb_log_waits','Threads_running'); SELECT @@performance_schema_events_statements_history_long_size,@@performance_schema_events_waits_history_long_size")
            (options.output / "db-config.txt").write_bytes((config + "\n").encode())
            summary["rounds"] = []
            for i in [1, 2]:
                stats = subprocess.check_output(["docker", "stats", "--no-stream", "--format", "{{json .}}"], text=True)
                (options.output / f"container-stats-{i}.jsonl").write_bytes(stats.encode())
                result = sample(project, options.output, i)
                summary["rounds"].append({k: result[k] for k in ["sample_count", "max_ms", "p95_ms", "over_100_ms", "passed"]})
            if options.regression:
                v = project.verifier()
                v.write_doc = lambda: (options.output / "verify.md").write_bytes(("\n".join(v.LINES) + "\n").encode())
                try: v.main(); summary["verify"] = 0
                except SystemExit as e: summary["verify"] = e.code
                except Exception as e:
                    import traceback
                    summary["verify"] = type(e).__name__
                    (options.output / "verify-error.txt").write_bytes(traceback.format_exc().encode())
                    v.write_doc()
                import os
                env = {**os.environ, **project.env, "E2E_BASE_URL": v.BASE, "PLAYWRIGHT_CHANNEL": "chrome"}
                for label, command in [("e2e-install", ["cmd", "/c", "npm ci --registry=https://registry.npmjs.org"]), ("playwright", ["cmd", "/c", "npx playwright test"])]:
                    run = subprocess.run(command, cwd=ROOT / "frontend/e2e", env=env, capture_output=True, timeout=240)
                    # Original specs report only synthetic account names and assertions.
                    (options.output / (label + ".txt")).write_bytes(run.stdout + run.stderr)
                    summary[label] = run.returncode
    except Exception as e:
        summary["error"] = type(e).__name__ + ": " + str(e)
        raise
    finally:
        summary["finished"] = datetime.datetime.now().astimezone().isoformat()
        save(options.output / "summary.json", summary)
    return 0 if all(x["passed"] for x in summary["rounds"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
