# 第8课安全自查 · CampusClaw

- 项目名称：CampusClaw 2.0；
- 环境：从零按 `README.md` 启动，测试地址为http://127.0.0.1:18080；Git版本基准为`292eaaff`，测试时包含未提交修改

- 身份与预置数据：班级A、班级B；A班教师`teacher_a`、A班学生`student_a1`、B班学生`student_b1`；预置本班材料及作业提交数据，用于验证登录、跨班隔离和批改入队权限。

- 分工：禹霖（SEC01-SEC07）

- 受保护接口清单：

  | 序号 | 请求方法 | 路径                          |
  | ---- | -------- | ----------------------------------- |
  | 1    | GET      | `/api/me`                           |
  | 2    | GET      | `/api/materials`                    |
  | 3    | POST     | `/api/materials`                    |
  | 4    | GET      | `/api/materials/{id}`               |
  | 5    | GET      | `/api/materials/{id}/file`          |
  | 6    | POST     | `/api/materials/{id}/reindex`       |
  | 7    | POST     | `/api/search`                       |
  | 8    | POST     | `/api/ask`                          |
  | 9    | GET      | `/api/assignments`                  |
  | 10   | POST     | `/api/assignments/{id}/submissions` |
  | 11   | POST     | `/api/submissions/{id}/grade`       |
  | 12   | GET      | `/api/tasks/{task_id}`              |


- 写入类接口清单：

  | 序号 | 请求方法 | 写入类接口路径                      | 用途                         |
  | ---- | -------- | ----------------------------------- | ---------------------------- |
  | 1    | POST     | `/api/login`                        | 登录并创建会话               |
  | 2    | POST     | `/api/logout`                       | 退出登录并注销会话           |
  | 3    | POST     | `/api/materials`                    | 上传材料                     |
  | 4    | POST     | `/api/materials/{id}/reindex`       | 重建材料索引                 |
  | 5    | POST     | `/api/assignments/{id}/submissions` | 创建作业提交记录             |
  | 6    | POST     | `/api/submissions/{id}/grade`       | 将本人的作业提交加入批改队列 |

  说明：`/api/submissions/{id}/grade`是本人作业的批改入队入口，并非任意分数写入接口。

## 七项检测记录

命令约定：以下curl为根据原自动化请求整理的等价复现命令，使用项目支持的会话Cookie；历史请求由Python脚本发出，登录后使用登录响应令牌，并非执行了这些Cookie命令。`$BASE`为测试环境地址，`$A1_COOKIE`、`$B1_COOKIE`分别为A班学生A1、B班学生B1的登录Cookie文件。`$B_MATERIAL_ID`为B班材料ID，`$NONEXISTENT_MATERIAL_ID`为已确认不存在的材料ID，`$OTHER_SUBMISSION_ID`为B1的作业提交ID，`$A_CLASS_ID`为A班实际班级ID；变量均须按测试环境的真实数据填写；JSON请求使用 `Content-Type: application/json`，检索请求包含query、mode、class_id字段（A1同班对照不传class_id）。

`$BINARY`为从实际API容器复制出的后端二进制文件；日志命令中的`$PROJECT`、`$ENV_FILE`、`$NETWORK_FILE`分别为本次隔离环境的Compose项目名、环境文件和网络覆盖配置文件。

| 编号 | 前置条件 | 操作 | 期望 | 当前实际 | 判定 |
|---|---|---|---|---|---|
| SEC-01 未登录访问受保护接口 | API及依赖已启动且健康；不携带Cookie、Authorization或其他认证凭据 | 执行 `curl -q -sS -i "$BASE/api/me"`；POST示例：`curl -q -sS -i -X POST -H 'Content-Type: application/json' --data '{}' "$BASE/api/search"`。其余接口按前述12项清单各自登记的方法逐一请求：GET请求不带正文，POST请求均发送 `{}` | 12个接口均返回401 | 清单中12个接口逐项均返回401 | 绿 |
| SEC-02 跨班访问与跨班检索       | API、检索依赖正常；A1为A班学生、B1为B班学生且均已登录；B班材料已存在，A班有“单调递增”材料 | A1携带Cookie访问B班材料详情及文件，并与访问不存在材料时的响应进行对照。使用GET请求 `/api/materials/$B_MATERIAL_ID`及其 `/file`路径，对照请求将ID替换为 `$NONEXISTENT_MATERIAL_ID`。B1携带Cookie向 `/api/search`发送POST请求，查询词为“单调递增”，检索模式依次为keyword、vector、hybrid，class_id填写 `$A_CLASS_ID`。正向对照由B1读取B班材料详情，A1使用相同查询词和检索模式检索，但不传class_id | 跨班材料详情和文件返回404；B1检索A班知识库返回空结果；B班学生可正常读取B班材料，A班学生可检索到A班内容 | 跨班详情、文件均404，与不存在资源正文及Content-Type一致；B1读取B班材料详情返回200；三种检索模式中，A1各命中1条，B1均返回200且无命中 | 绿 |
| SEC-03 学生越权修改技能或提示词 | 当前仅有占位技能/助手表和代码内固定系统提示词；无可配置技能资源及写入口 | 静态检索 `rg -n -i -e skill -e prompt -e assistant frontend/src backend openspec`，核对前端页面、后端路由、表结构和提示词生成逻辑；不发送虚构的配置写请求 | 学生调用技能、提示词或助手配置写接口应返回403，数据库不变 | 未实现配置写入口，未执行越权写测试，没有取得403响应或数据库前后核验证据；原脚本直接登记为阻塞状态，功能边界来自后续源码审计 | 红 |
| SEC-04 技能工具绕过鉴权 | A班学生A1、B班学生B1均已登录，B1已有作业提交；当前无技能路由和独立批改结果写入HTTP接口，结果由worker内部写入 | 已做的部分检查：A1携带Cookie执行 `curl -q -sS -i -b "$A1_COOKIE" -H 'Content-Type: application/json' --data '{"score":60}' "$BASE/api/submissions/$OTHER_SUBMISSION_ID/grade"`，并以不存在的提交对照；请求前后核对grade_tasks、grade_results中该提交及outbox_messages中对应提交版本的记录数。此为跨班入队测试，不是绕过技能路由直接写结果 | 学生不走技能路由直接调用批改写入入口应被拒绝，数据库不变 | 跨班入队及不存在对照均404，三项记录数前后均为0条；score是历史请求实际携带但接口不读取的字段，不是分数写入参数；当前版本未实现技能路由及独立的批改结果写入HTTP接口，无法执行完整的绕过鉴权测试；已完成跨班批改入队权限检查。 | 红 |
| SEC-05 密钥明文泄漏扫描 | 本机已拉齐全量提交历史，前端产物及API/worker运行日志可读取。 | 执行 `python scripts/secret_scan.py`；补充用 `git rev-list --objects --all`和 `git cat-file --batch`扫描本地全部引用可达的历史文本，而非仅当前版本；再扫描frontend/dist、从web容器复制的frontend-build，以及api/worker最终日志快照 | 全量提交历史、前端产物、运行日志三类均覆盖，密钥命中为0；候选须核实是否为真实泄漏或误报 | 已扫描本地可达历史、前端产物及API/worker日志，均为0候选 | 绿 |
| SEC-06 依赖漏洞基线 | 前端锁文件、Go源码和实际API部署二进制可读；npm及govulncheck可用 | 在frontend目录执行 `npm audit --json --audit-level=high --package-lock-only --registry=https://registry.npmjs.org`；在backend目录执行 `go run golang.org/x/vuln/cmd/govulncheck@v1.1.4 -json ./...`审计源码，并执行 `go run golang.org/x/vuln/cmd/govulncheck@v1.1.4 -json -mode=binary "$BINARY"`审计部署二进制 | 保存依赖漏洞基线，记录高危、严重数量；高危清零或书面登记处置方式，无法确定的等级明确标注 | npm高危0、严重0（其余等级也为0） | 绿 |
| SEC-07 技能调用审计日志可追溯 | 已有异步批改成功任务及api/worker日志；通用技能调用与专用技能审计未实现 | 执行 `docker compose -p "$PROJECT" --env-file "$ENV_FILE" -f docker-compose.yml -f "$NETWORK_FILE" logs --no-log-prefix api worker`，逐行解析JSON日志，筛选worker_succeeded事件，检查student_id、task_id、status、duration_ms字段 | 对一次真实技能调用回查日志，查到操作人、技能标识、结果状态、耗时、用量 | 仅回查2条成功批改任务日志：有status、duration_ms及student_id、task_id、submission_id、attempts；操作人、技能标识、用量三项语义未覆盖，不能将student_id当操作人、task_id当技能标识；通用技能调用与专用技能审计未实现 | 红 |

## 红项后续处理

- **SEC-03**：当前未实现技能、提示词及助手配置写入口，无法完成学生越权修改测试。下一次change拟补齐配置能力及权限控制，验证教师可正常配置、学生修改返回403且数据库不变。
- **SEC-04**：当前已完成跨班批改入队权限检查，但无法完成技能路由绕过测试。下一次change拟建立技能执行链及写入层权限校验，验证学生绕过正常流程不能写入批改结果，且数据库无变化。不为测试额外开放分数写入接口。
- **SEC-07**：当前任务日志尚不能完整对应技能审计要求。下一次change拟在技能执行链补齐操作人、技能标识、结果状态、耗时和用量记录，并通过一次真实技能调用核验。

以上为后续计划，本次未实施修复。
