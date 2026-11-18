import json,subprocess,os
from pathlib import Path
OUT=Path(__file__).resolve().parent
p=subprocess.run(["docker","ps","--format","{{json .}}"],capture_output=True,text=True)
rows=[json.loads(line) for line in p.stdout.splitlines()]
report={"host_proxy_variables_present": {name:bool(os.environ.get(name)) for name in ["HTTP_PROXY","HTTPS_PROXY","ALL_PROXY"]},"build_containers":[]}
for row in rows:
 if "apk add" not in row.get("Command", ""):continue
 item={"id":row["ID"],"name":row["Names"],"status":row["Status"]}
 for label,url in [("apk_index","https://dl-cdn.alpinelinux.org/alpine/v3.21/main/x86_64/APKINDEX.tar.gz")]:
  try:
   probe=subprocess.run(["docker","exec",row["ID"],"wget","-S","--spider","-T","10",url],capture_output=True,timeout=15)
   (OUT/("network-"+row["ID"]+"-"+label+".log")).write_bytes(probe.stdout+probe.stderr)
   item[label]=probe.returncode
  except subprocess.TimeoutExpired:item[label]="timeout"
 report["build_containers"].append(item)
 if len(report["build_containers"])==1:break
(OUT/"network-apk-probe.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
print(json.dumps(report))
