#!/bin/sh
# Adapted from executed run_make/run_grade_buildproxy wrappers; no host constants.
set -u
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$ROOT" || exit 2
mkdir -p tests/output
OUT=$(mktemp -d "$ROOT/tests/output/project-gates.XXXXXX")
export QA_GATE_OVERLAY="$OUT/compose.json"
python3 - <<'PY'
import ipaddress,json,os
overlay={}
proxy=os.environ.get('QA_BUILD_PROXY')
if proxy:
    overlay['services']={name:{'build':{'args':{'HTTP_PROXY':proxy,'HTTPS_PROXY':proxy}},
        'environment':{'HTTP_PROXY':'','HTTPS_PROXY':'','http_proxy':'','https_proxy':''}}
        for name in ['api','worker','web']}
goproxy=os.environ.get('QA_GO_PROXY')
if goproxy:
    for name in ['api','worker']:
        overlay.setdefault('services',{}).setdefault(name,{}).setdefault('build',{}).setdefault('args',{})['GOPROXY']=goproxy
subnet=os.environ.get('QA_TEST_SUBNET')
if subnet:
    ipaddress.ip_network(subnet,strict=True)
    overlay['networks']={'default':{'ipam':{'config':[{'subnet':subnet}]}}}
with open(os.environ['QA_GATE_OVERLAY'],'w',encoding='utf-8') as f:json.dump(overlay,f)
PY
if [ "$?" -ne 0 ]; then exit 2; fi
case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) SEP=';' ;; *) SEP=':' ;; esac
export COMPOSE_FILE="$ROOT/docker-compose.yml$SEP$QA_GATE_OVERLAY"
if [ "$#" -eq 0 ]; then set -- check check-security grade; fi
failed=0
for target in "$@"; do
    case "$target" in check|check-security|grade) ;; *) printf 'Unsupported target: %s\n' "$target" >&2; exit 2 ;; esac
    if [ "$target" = grade ] && [ -n "$(docker ps -aq --filter label=com.docker.compose.project=campusclaw-acceptance)" ]; then
        printf '%s\n' 'Refusing to reuse an existing campusclaw-acceptance project' >&2
        exit 2
    fi
    make "$target" > "$OUT/$target.log" 2>&1
    code=$?
    printf '%s\t%s\n' "$target" "$code" >> "$OUT/results.tsv"
    if [ "$code" -ne 0 ]; then failed=1; fi
done
printf 'Output: %s\n' "$OUT"
exit "$failed"
