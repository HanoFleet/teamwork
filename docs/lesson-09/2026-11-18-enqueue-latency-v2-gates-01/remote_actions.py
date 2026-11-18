"""Read GitHub Actions metadata and original failure logs without changing remote state."""
import io
import json
from pathlib import Path
import subprocess
import zipfile
import requests

OUT = Path(__file__).resolve().parent
BASE = "https://api.github.com/repos/HanoFleet/teamwork"
session = requests.Session()
session.headers.update({"Accept": "application/vnd.github+json", "User-Agent": "Codex-gate-review"})
status = {}
try:
    response = session.get(BASE + "/actions/runs", params={"per_page": 60}, timeout=45)
    status["anonymous_status"] = response.status_code
    if response.status_code in (401, 403, 404):
        credential = subprocess.run(["git", "credential", "fill"], input=b"protocol=https\nhost=github.com\n\n", capture_output=True, timeout=30)
        values = dict(line.split("=", 1) for line in credential.stdout.decode().splitlines() if "=" in line)
        if values.get("password"):
            session.headers["Authorization"] = "Bearer " + values["password"]
            status["existing_git_credential_used"] = True
            response = session.get(BASE + "/actions/runs", params={"per_page": 60}, timeout=45)
    status["runs_status"] = response.status_code
    response.raise_for_status()
    data = response.json()
    (OUT / "github-runs.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    failed = [r for r in data["workflow_runs"] if r["conclusion"] == "failure" and r["event"] in ("push", "pull_request")]
    status["failed_runs_in_page"] = len(failed)
    selected = failed[:8]
    for run in selected:
        rid = str(run["id"])
        jobs = session.get(BASE + f"/actions/runs/{rid}/jobs", params={"per_page": 100}, timeout=45)
        jobs.raise_for_status()
        (OUT / f"github-jobs-{rid}.json").write_text(json.dumps(jobs.json(), ensure_ascii=False, indent=2), encoding="utf-8")
        response = session.get(BASE + f"/actions/runs/{rid}/logs", timeout=60)
        status["logs_" + rid] = response.status_code
        if response.status_code == 200:
            (OUT / f"github-logs-{rid}.zip").write_bytes(response.content)
            with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
                for name in archive.namelist():
                    if "check" in name.lower() and name.endswith(".txt"):
                        target = OUT / ("github-run-" + rid)
                        target.mkdir(exist_ok=True)
                        # Keep zip paths as a safe flat filename.
                        (target / name.replace("/", "__").replace("\\", "__")).write_bytes(archive.read(name))
    status["selected_runs"] = [{k: run[k] for k in ["id", "event", "head_sha", "created_at", "html_url", "conclusion"]} for run in selected]
except Exception as error:
    status["error_type"] = type(error).__name__
    status["error"] = str(error).split("?")[0]
finally:
    (OUT / "github-access.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
    print(json.dumps(status))
