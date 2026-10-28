# 旧实现归档

`campusclaw-baseline.zip` 是 CampusClaw 2.0 改造前的可运行基线，来自标签 `v2.0.0-baseline`（提交 `4fd4232`）。当前可运行代码已经恢复到根目录的 `backend/`、`frontend/` 和 Compose；本归档保留为历史快照，用于对比、回溯和重新生成基线，不再是唯一的代码副本。

## 包含什么

| 内容 | 说明 |
| --- | --- |
| `backend/` | Go api：登录、班级隔离、材料上传、三种检索、问答 |
| `frontend/` | React + Vite + Nginx |
| `scripts/verify.py` | 迭代 1/2 的验收脚本 |
| `docker-compose.yml`、`.env.example`、`.dockerignore` | 一键启动和配置模板 |
| `README.md`、`ITERATION.md` | 基线说明和迭代 1 设计说明 |
| `docs/verification.md` | 基线验收记录 |
| `docs/基于Token认证与知识库问答的实现说明.docx` | 迭代 1 的实现说明 |

不含：`openspec/`（规约历史仍留在仓库根目录）、`.env`、上传文件、数据库文件、`node_modules`。

## 怎么运行

```bash
unzip archive/campusclaw-baseline.zip
cd campusclaw-baseline
cp .env.example .env
# 填写 SESSION_SECRET、MYSQL_ROOT_PASSWORD、DB_PASSWORD、SEED_*_PASSWORD
docker compose up --build -d
curl -fsS http://localhost:8080/health
python3 scripts/verify.py
```

校验压缩包完整性：

```bash
shasum -a 256 -c archive/campusclaw-baseline.sha256
```

## 怎么重新生成

ZIP 由 `git archive` 从基线标签生成，不手工打包：

```bash
git archive --format=zip --prefix=campusclaw-baseline/ v2.0.0-baseline \
  backend frontend scripts docker-compose.yml .env.example .dockerignore .gitignore \
  ITERATION.md README.md docs/verification.md \
  "docs/基于Token认证与知识库问答的实现说明.docx" \
  -o archive/campusclaw-baseline.zip
```

## 当前代码在哪里

第 7 课要求可运行骨架，所以根目录已经恢复 `backend/`、`frontend/`、`docker-compose.yml` 和 `scripts/verify.py`，并增加了 `/live`、`/health`、`/ready`、JSON 日志和优雅停机。本归档只用于对比和回溯，不需要解压才能运行当前仓库。
