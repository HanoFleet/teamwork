"""async-grading/事务性发件箱与可靠补投: same-Compose before/after comparison.

Use prebuilt verified baseline/final backend images. Only owned image tags change;
database, broker, network, credentials, payload, 2x20 samples and timer stay fixed.
No build or unrelated gate runs during the timed windows.
"""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import time

from grade_latency_diagnostics import ROOT, Project, sample, save, sql
from check_single_request_limit import RULE


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--subnet", required=True)
    p.add_argument("--build-proxy")
    p.add_argument("--before-image", required=True)
    p.add_argument("--after-image", required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    summary = {"rule": RULE, "started": datetime.datetime.now().astimezone().isoformat(), "head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(), "uncommitted": True, "phases": {}}
    try:
        with Project("outbox-comparison", args) as project:
            summary["project"] = project.name
            build = project.a.compose("build", "web", check=False, timeout=600)
            (args.output / "web-build.txt").write_bytes((build.stdout + build.stderr).encode())
            if build.returncode: raise RuntimeError("web build failed")
            for phase, image in [("before", args.before_image), ("after", args.after_image)]:
                out = args.output / phase
                out.mkdir(parents=True, exist_ok=True)
                summary["phases"][phase] = {"image": image, "id": subprocess.check_output(["docker", "image", "inspect", image, "--format", "{{.Id}}"], text=True).strip(), "rounds": []}
                for service in ["api", "worker"]:
                    subprocess.run(["docker", "tag", image, project.name + "-" + service], check=True)
                up = project.a.compose("up", "-d", "--wait", check=False, timeout=300)
                (out / "compose-up.txt").write_bytes((up.stdout + up.stderr).encode())
                if up.returncode: raise RuntimeError("compose up failed")
                sql(project, "UPDATE performance_schema.setup_consumers SET ENABLED='YES' WHERE NAME IN ('events_statements_current','events_statements_history_long','events_waits_current','events_waits_history_long'); UPDATE performance_schema.setup_instruments SET ENABLED='YES',TIMED='YES' WHERE NAME LIKE 'wait/io/file/innodb/%'")
                (out / "db-config.txt").write_bytes((sql(project, "SELECT @@version,@@innodb_flush_log_at_trx_commit,@@sync_binlog,@@innodb_flush_method,@@transaction_isolation") + "\n").encode())
                for i in [1, 2]:
                    # No warm-up requests or discarded samples. Wait only for prior
                    # asynchronous work to finish, making both phases comparable.
                    for _ in range(60):
                        pending = sql(project, f"SELECT COUNT(*) FROM {project.env['DB_NAME']}.outbox_messages WHERE status='pending'")
                        if pending == "0": break
                        time.sleep(1)
                    else: raise RuntimeError("prior outbox backlog did not drain")
                    (out / f"container-stats-{i}.jsonl").write_bytes(subprocess.check_output(["docker", "stats", "--no-stream", "--format", "{{json .}}" ]))
                    result = sample(project, out, i)
                    summary["phases"][phase]["rounds"].append({k: result[k] for k in ["sample_count", "max_ms", "p95_ms", "over_100_ms", "passed"]})
            summary["after_passed"] = all(x["passed"] for x in summary["phases"]["after"]["rounds"])
    finally:
        summary["finished"] = datetime.datetime.now().astimezone().isoformat()
        save(args.output / "summary.json", summary)
    return 0 if summary["after_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
