import hashlib,json,subprocess
from pathlib import Path
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
before=json.loads((OUT/"preservation-before.json").read_text(encoding="utf-8"))
after={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() if (ROOT/name).is_file() else None for name in before}
changed=[name for name in before if before[name]!=after[name]]
(OUT/"preservation-after.json").write_text(json.dumps(dict(count=len(before),changed=changed,files=after),indent=2),encoding="utf-8")
assert not changed,changed
# Verify every current-source hash recorded during the approved v2 adjustment.
source=json.loads((ROOT/"docs/lesson-09/2026-11-18-observe-enqueue-latency/current-source-sha256.json").read_text(encoding="utf-8"))
source_changed=[name for name,digest in source.items() if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
(OUT/"v2-source-integrity.json").write_text(json.dumps(dict(count=len(source),changed=source_changed),indent=2),encoding="utf-8")
assert not source_changed,source_changed
for label,cmd in [("git-status-after",["git","status","--short"]),("git-head-after",["git","rev-parse","HEAD"]),("docker-ps-after",["docker","ps","-a","--format","{{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Label \"com.docker.compose.project\"}}"]),("docker-networks-after",["docker","network","ls","--format","{{.ID}}\t{{.Name}}"]),("docker-owned-projects-after",["docker","ps","-aq","--filter","label=com.docker.compose.project=campusclaw-acceptance"]),("diff-check-after",["git","diff","--check"])]:
 result=subprocess.run(cmd,cwd=ROOT,capture_output=True)
 (OUT/(label+".log")).write_bytes(result.stdout+result.stderr)
 print(label,result.returncode)

def containers(path):
 return {parts[0]:dict(name=parts[1],running=parts[2].startswith("Up")) for line in path.read_text(encoding="utf-8").splitlines() if len(parts:=line.split("\t"))>=3}
original=containers(OUT/"docker-ps-before.log")
current=containers(OUT/"docker-ps-after.log")
missing=[key for key in original if key not in current]
changed_state=[key for key in original if key in current and original[key]!=current[key]]
left_owned=[key for key,row in current.items() if "teamwork-tests-latency-v2-gates-" in row["name"] or "campusclaw-acceptance-" in row["name"]]
state=dict(original_container_count=len(original),missing=missing,changed_running_state=changed_state,owned_compose_containers_remaining=left_owned,new_container_count=len(set(current)-set(original)),acceptance_env_remaining=(ROOT/".env.acceptance").exists(),mutation_file_remaining=(ROOT/"backend/internal/httpapi/zz_violation.go").exists())
(OUT/"environment-preservation.json").write_text(json.dumps(state,indent=2),encoding="utf-8")
print(json.dumps(state));print("Historical files",len(before),"changed",len(changed));print("V2 source files",len(source),"changed",len(source_changed))
assert not missing and not changed_state and not left_owned and not state["acceptance_env_remaining"]
