#!/bin/sh
set -eu
cd "$(dirname "$0")/.."

echo "== 规约与规范"
python3 scripts/spec_check.py
python3 scripts/standards_check.py

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
docker run --rm \
  -v "$PWD/frontend:/work" \
  -v campusclaw-frontend-modules:/work/node_modules \
  -w /work \
  node:22-alpine \
  sh -c 'npm ci && npm run build'

echo "check 全部通过"
