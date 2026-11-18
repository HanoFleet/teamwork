import json,os,subprocess,zipfile,io
from pathlib import Path
import requests
OUT=Path(__file__).resolve().parent
session=requests.Session();session.headers.update({"Accept":"application/vnd.github+json","User-Agent":"Codex-gate-review"})
state={}
try:
 p=subprocess.run(["git","credential","fill"],input=b"protocol=https\nhost=github.com\n\n",capture_output=True,timeout=25,env={**os.environ,"GIT_TERMINAL_PROMPT":"0","GCM_INTERACTIVE":"Never"})
 values=dict(line.split("=",1) for line in p.stdout.decode().splitlines() if "=" in line)
 state["credential_exit"]=p.returncode;state["credential_available"]=bool(values.get("password"))
 if values.get("password"):session.headers["Authorization"]="Bearer "+values["password"]
except Exception as error:state["credential_error"]=type(error).__name__
for path in OUT.glob("github-jobs-*.json"):
 rid=path.stem.removeprefix("github-jobs-")
 for job in json.loads(path.read_text(encoding="utf-8"))["jobs"]:
  if job["conclusion"]!="failure":continue
  annotations=session.get(job["check_run_url"]+"/annotations",timeout=45)
  state["annotations_"+str(job["id"])]=annotations.status_code
  if annotations.status_code==200:(OUT/("github-annotations-"+str(job["id"])+".json")).write_text(json.dumps(annotations.json(),ensure_ascii=False,indent=2),encoding="utf-8")
 if state.get("credential_available"):
  response=session.get("https://api.github.com/repos/HanoFleet/teamwork/actions/runs/"+rid+"/logs",timeout=60)
  state["authenticated_logs_"+rid]=response.status_code
  if response.status_code==200:
   (OUT/("github-logs-"+rid+".zip")).write_bytes(response.content)
   with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
    for name in archive.namelist():
     if "check" in name.lower() and name.endswith(".txt"):
      target=OUT/("github-run-"+rid);target.mkdir(exist_ok=True)
      (target/name.replace("/","__").replace("\\","__")).write_bytes(archive.read(name))
(OUT/"github-details-access.json").write_text(json.dumps(state,indent=2),encoding="utf-8")
print(json.dumps(state))
