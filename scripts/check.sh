#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

echo "== 规约与规范"
python3 scripts/spec_check.py
python3 scripts/standards_check.py
python3 -m py_compile scripts/async_test.py scripts/security_test.py scripts/security_gate.py scripts/sec08_experiment.py
python3 scripts/security_static.py

echo "== OpenSpec strict"
npx -y @fission-ai/openspec@1.15.0 validate --all --strict

echo "== 分层、密钥与变异"
python3 scripts/layer_check.py
python3 scripts/secret_scan.py
python3 scripts/mutation.py

echo "== Go 格式、测试与 vet"
docker run --rm \
  -v "$PWD/backend:/work" \
  -v campusclaw-go-cache:/go/pkg/mod \
  -w /work \
  -e GOPROXY=https://goproxy.cn,direct \
  golang:1.25-alpine \
  sh -c 'test -z "$(gofmt -l .)" && go test ./... && go vet ./...'

echo "== 前端构建"
docker build --target build --tag campusclaw-frontend-check frontend >/dev/null
docker image rm -f campusclaw-frontend-check >/dev/null 2>&1 || true
echo "前端 npm ci + build：通过"

echo "check 全部通过"
