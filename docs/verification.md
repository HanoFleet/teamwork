# 验收记录

目标：`http://127.0.0.1:8080`

## 启动与健康检查
PASS GET /health 200 {"status":"ready","version":"v2.0.0-skeleton","time":"2026-11-05T17:33:27Z","checks":{"db":true,"embedding":true,"qdrant":true}}
PASS 未登录 GET /api/materials 401 且不含材料标题
PASS GET /uploads/secret.md -> 404
## 登录失败同形
PASS 不存在账号与错误口令同为 401 {"error":"invalid_credentials"}
## 主路径
PASS teacher_a role=teacher class=A
PASS A 班搜索「牛顿定律」且带 class_id 参数时没有 B 班标题
PASS 教师上传 201 id=7
PASS 详情正文与文件一致，班级仍是会话班级，且没有存储路径
PASS 本班列表能看到新上传和预置讲义
PASS 同班学生可以下载
PASS 学生上传 403，材料行数保持 7
PASS 跨班详情与不存在 id 的 404 响应体相同
PASS B 班看不到 A 班材料，能看到自己的预置笔记
PASS notes.md.exe 返回 400，材料行数不变
## 种子与密钥
PASS 三个预置账号的 password_hash 都是 bcrypt，且不等于明文
PASS 十张表存在，materials.class_id 为 NOT NULL
PASS knowledge_chunks 含 FULLTEXT ngram
PASS api 容器没有 MYSQL_ROOT_PASSWORD
## 本班可追溯检索
PASS Compose 含 qdrant 且无宿主端口
PASS 空查询 400
PASS keyword 命中 A 班讲义且带出处字段
PASS 请求中的 class_id 不能搜到 B 班
PASS 问天气得到空 hits 与固定文案
PASS 学生可以检索，不能重建索引
PASS 问比分不生成，citations 为空
PASS 对预置讲义提问，回答含 [1] 且有 citations
PASS Qdrant 停止时 keyword 仍可用，vector/hybrid 为 503
## 登出
PASS 登出后旧 Cookie 得到 401
## 数据库停止时 /live、/health 与业务接口分离
PASS 停库后 /live 200、/health 503、/api/materials 503
PASS 数据库恢复后可以重新登录
## 限流与口令错误同形
PASS 锁定期内正确口令仍返回与错误口令相同的 401
PASS 重启 api 以清掉内存中的限流计数
## 重建容器后数据仍在
PASS down/up 后仍能看到 验收-上传-1793900007.md，用户数仍为 3
PASS 前端使用 ReactMarkdown，没有 rehype-raw 或 dangerouslySetInnerHTML
## 异步批改
PASS 前端轮询常量 1000/2000/60，failed/dead 无重试
PASS RabbitMQ 队列 durable 且无宿主端口
PASS 批改相关表和唯一约束存在
PASS 未登录提交/列表 401
PASS 教师提交 403
PASS 空内容和超长 400
PASS 跨班提交与不存在作业同形 404
PASS 提交版本追加与相同内容复用
PASS outbox 插入失败时 task/outbox 无新增
PASS 首次批改 202 task_id=01M6PCCXG5RBFTH89THT6C70H2
PASS 重复批改复用同一 task_id
PASS 任务查询跨班/不存在同形 404，本班教师可查，教师批改 404
PASS 停 worker 提交仍 202，恢复后自动 succeeded；再次批改 200
PASS 20 次批改 P95=11.8ms < 500ms，响应不含分数 times=[10.2,9.5,11.8,5.5,6.4,13.9,7.4,8.4,5.8,7.8,6.5,6.7,7.5,5.7,6.1,7.1,5.6,5.6,5.4,5.8]
PASS 重复请求和重复投递只有一份结果 score=12.00 attempts=1
PASS 永久失败进入 failed 且无结果行
PASS 瞬时失败回到 pending attempts=pending:1
PASS 停 RabbitMQ 仍 202/pending，恢复后自动 succeeded
PASS 学生打开 /assignments 得到页面

全部断言通过。
