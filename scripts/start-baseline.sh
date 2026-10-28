#!/usr/bin/env bash
# 从归档包启动 CampusClaw 基线。只做解压、配置检查、Compose 启动和健康检查。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ ! -f archive/campusclaw-baseline.zip ]; then
  echo "缺少 archive/campusclaw-baseline.zip" >&2
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "已生成 .env。请先填写 SESSION_SECRET、MYSQL_ROOT_PASSWORD、DB_PASSWORD 和 SEED_*_PASSWORD，再重新运行本脚本。" >&2
  exit 1
fi

if [ ! -d .baseline/campusclaw-baseline ]; then
  mkdir -p .baseline
  unzip -q archive/campusclaw-baseline.zip -d .baseline
fi

cp .env .baseline/campusclaw-baseline/.env

cd .baseline/campusclaw-baseline
docker compose up --build -d

PORT="$(grep -E '^WEB_PORT=' .env | cut -d= -f2)"
PORT="${PORT:-8080}"

echo "等待 /health ..."
for _ in $(seq 1 60); do
  if curl -fsS "http://localhost:${PORT}/health" >/dev/null 2>&1; then
    echo "基线已启动：http://localhost:${PORT}/"
    echo "存活检查：http://localhost:${PORT}/health"
    echo "验收命令：python3 scripts/verify.py"
    exit 0
  fi
  sleep 2
done

echo "启动超时。请查看 docker compose logs。" >&2
exit 1
