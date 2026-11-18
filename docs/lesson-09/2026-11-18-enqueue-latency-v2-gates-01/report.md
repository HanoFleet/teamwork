# 第9课 enqueue-latency-v2 完整门禁验收报告

本轮本机自动化门禁在环境重试后全部通过。首次失败和重试记录分别保留。GitHub原始日志确认最近三次check失败停在npm依赖审计。当前工作树尚无针对新提交的云端CI结果。用户尚未授权提交、推送或归档，本轮没有执行这些动作。

工作树为 `E:/proj/teamwork-main-latest/qa/lesson9/fix-worktree`，分支 `change/2026-11-18-fix-lesson9-retest`，HEAD前后均为 `2d2900bf34b52d8df21513c6ef2ebc873df9f345`，暂存区为空。另两个工作树分别为根目录security-precheck分支和test-main detached HEAD，未切换或修改。

当前完整差异包含此前的outbox事务隔离、前端工具链与锁文件、安全测试档案、工程规范及enqueue-latency-v2规则修订。本轮新增内容为本目录的验收脚本、日志、CI原始证据，以及两个新teacher报告和独立tests/output运行产物。业务源码本轮新增修改为0。开始时已存在的reports/xss-page-source.md修改也保持原字节。开始和结束状态见[git-status-before.txt](git-status-before.txt)、[git-status-after.log](git-status-after.log)、[git-diff-stat.txt](git-diff-stat.txt)。

**CI执行路径和判定依据**

`.github/workflows/check.yml`在push、pull_request、workflow_dispatch触发，Ubuntu runner上执行三个独立job。当前workflow原文保存在[workflow-check.yml.txt](workflow-check.yml.txt)，入口和源码哈希见[entrypoint-audit.json](entrypoint-audit.json)。本轮未修改workflow。

|job|执行命令|判定依据|
|---|---|---|
|check，30分钟|setup-node 24 → make check-security → make check|每一步退出0才继续。安全门禁先检查密钥、npm audit --audit-level=high、实时govulncheck；check再检查规约结构、八类规范、13项延迟合同测试、安全静态用例、OpenSpec strict、分层/密钥/变异、Go格式/test/vet、前端npm ci及build|
|grade，30分钟|sh scripts/grade.sh → python3 scripts/acceptance.py；始终上传teacher-report|隔离Compose构建启动成功且18项检查全通过，报告passed与退出0同时成立。覆盖健康、隔离、异步、SQLi、CSRF、配置/审计、依赖恢复、端口及停机|
|verify，45分钟|ci_env.py → docker compose up --build -d --wait → python3 scripts/verify.py → frontend/e2e npm ci → npx playwright test；最后down -v|完整verify断言和浏览器测试退出0。异步20次响应P95严格小于500ms、全部202无分数；恢复、幂等、事务与安全断言继续适用。清理只在CI隔离runner执行|

**此前GitHub Actions失败的原始证据**

公开API可读运行和步骤信息，匿名日志下载返回403。随后使用本机已存Git凭据只读下载原始日志，成功200。凭据只在内存中使用，未打印、未存入报告。访问状态见[github-access.json](github-access.json)、[github-details-access.json](github-details-access.json)。原始ZIP、job JSON及提取的check日志保存在本目录。

|运行|事件 / 北京时间|原始报错及退出码|证据|
|---|---|---|---|
|[44233303139](https://github.com/HanoFleet/teamwork/actions/runs/44233303139)|push / 2026-11-18 11:51|picomatch ReDoS及fdir、tinyglobby、vite、@vitejs/plugin-react传递链，共5 high；npm audit退出1，make步骤退出2|[原始check日志](github-run-44233303139/2_check.txt)，约130–161行|
|[44233461559](https://github.com/HanoFleet/teamwork/actions/runs/44233461559)|pull_request / 2026-11-18 11:52|同一依赖审计失败，npm audit退出1，make步骤退出2|[原始check日志](github-run-44233461559/1_check.txt)，约146–177行|
|[44260682697](https://github.com/HanoFleet/teamwork/actions/runs/44260682697)|push / 2026-11-18 15:40|同一依赖审计失败，npm audit退出1，make步骤退出2|[原始check日志](github-run-44260682697/2_check.txt)，约130–161行|

三次均对应已提交的2d2900b版本。check job在 `make check-security` 失败后未执行 `make check`，100ms性能检查未进入这条失败路径。同期grade和verify两个job均为success。另取得的11月17日44041821128运行中check成功，workflow失败发生在verify的Install Playwright browser步骤，详见remote-job-summary.json。

当前本机工作树包含此前尚未提交的前端工具链整改，npm审计现为零漏洞。本轮enqueue-latency-v2规则修改与此前依赖整改各自保留来源，不能据新性能规则声称远程依赖问题已经通过新提交的CI验证。

**运行条件、环境适配和历史保护**

运行前Docker 29.8.0可用，Node v24.21.0、npm 11.19.0、Python 3.12.7、Windows GNU mingw32-make及Git sh可用，Chrome存在。`.env`、`.env.acceptance`、变异检查临时文件均不存在，campusclaw-acceptance无现存容器，campusclaw-frontend-check临时镜像标签不存在。版本、检查命令和返回码见[results.jsonl](results.jsonl)、[conditions.json](conditions.json)。

本机以 `mingw32-make` 执行原Makefile目标，现有Windows命令适配器仅转发python3/npm参数和退出码。Makefile、workflow、断言和阈值均未修改。Go检查使用1.26.11。verify使用既有Project.verifier适配器调用原verify.main全部断言，只注入本轮独立环境并重定向报告输出，保留既有RabbitMQ恢复就绪探测。未直接运行会读取根.env并覆盖docs/verification.md的原命令。

首次grade构建失败。随后隔离原参数构建的完整日志确认 `proxy.golang.org:443 connect: connection refused`。重试仅通过Dockerfile已有GOPROXY构建参数使用 `https://goproxy.cn,direct`，并选择无冲突子网。grade使用10.254.2.0/24，verify使用10.254.1.0/24，未改变服务持久化、超时、重试或验收断言。grade环境overlay见[grade-network-retry.json](grade-network-retry.json)。

浏览器测试源码复制到本轮独立目录，逐文件哈希验证一致，执行相同两条spec，使用真实登录和上传路径。输出路径因副本目录变化而隔离，历史XSS报告未被覆盖。没有启用测试跳过或mock模式。测试副本安装和浏览器执行见live-attempt-04，实际调用命令在其results.jsonl。

历史与业务文件617项前后SHA256一致，enqueue-latency-v2修订记录中的24个源码文件哈希一致。原122.06220000007306ms、旧passed=false及此前失败日志完整保留。对应证据为[preservation-before.json](preservation-before.json)、[preservation-after.json](preservation-after.json)、[v2-source-integrity.json](v2-source-integrity.json)。

原有228个容器均存在，运行/停止状态保持一致。本轮Compose容器已全部清理，临时.env.acceptance和变异文件已移除。保留2个本轮失败构建留下的已退出中间容器63dfde2f0a0e、cd44803dddff及构建缓存/镜像，未执行全局prune或清理原有资源。见[environment-preservation.json](environment-preservation.json)。

**逐项执行结果**

|命令 / 检查|退出码|本轮判定|证据|
|---|---|---|---|
|mingw32-make check|0|通过，含13项合同测试、OpenSpec strict 8/8、Go test/vet和前端构建|[make-check.log](make-check.log)|
|mingw32-make check-security|0|通过，密钥扫描通过、npm零漏洞、实时govulncheck No vulnerabilities found|[make-check-security.log](make-check-security.log)|
|mingw32-make grade，首次原环境|2|失败，构建阶段退出1；18项业务检查尚未运行|[make-grade.log](make-grade.log)、[首次teacher报告](../../../reports/teacher-20261118T105031Z/report.json)|
|本轮verify环境检查首次|1|失败，辅助脚本未处理Docker IPAM Config=null；仅修正新建验收脚本，尚无业务请求|[live-error.log](live-error.log)|
|隔离verify构建，live-attempt-02|1|失败，完整输出确认Go默认模块代理连接被拒绝|[verify-build.log](live-attempt-02/verify-build.log)、[summary](live-attempt-02/live-summary.json)|
|隔离verify启动，live-attempt-03|1|构建0、启动1，RabbitMQ容器退出1；当次清理前未采集broker内部日志，内部原因未确认。后续串行同配置启动成功|[verify-up.log](live-attempt-03/verify-up.log)、[summary](live-attempt-03/live-summary.json)|
|mingw32-make grade，GOPROXY环境重试|0|通过18/18，保留首次失败|[重试日志](make-grade-network-retry.log)、[teacher报告](../../../reports/teacher-20261118T105445Z/report.json)|
|隔离原verify.main，live-attempt-04|0|全部原断言通过，包含事务回滚、跨班、停worker/kill重投、broker恢复、幂等、failed/dead与SEC-03/04/07|[verify.md](live-attempt-04/verify.md)、[summary](live-attempt-04/live-summary.json)|
|实际v2采样，grade_enqueue_latency.run|0|20个202，P95=95.28799999998228ms，最大111.12800000000789ms，1条WARN且整轮通过|[live-v2-samples.json](live-attempt-04/live-v2-samples.json)|
|独立浏览器副本npm ci|0|通过，安装完成，审计零漏洞|[e2e-install.log](live-attempt-04/e2e-install.log)|
|Playwright同源副本两条spec|0|2/2通过，跳过0，作业提交轮询和真实XSS上传/页面源码检查通过|[playwright.log](live-attempt-04/playwright.log)、[新XSS报告](live-attempt-04/xss-page-source.md)|
|python tests/performance/latency_gate_contract.py|0|13项合同测试通过|[latency-contracts.log](latency-contracts.log)|
|两个检查CLI，100.001ms边界样本|均0|按预期警告并通过|[current](current-cli-boundary-warning.log)、[compat](compat-cli-boundary-warning.log)|
|两个检查CLI，P95=500ms反例|均1|按预期拒绝，证明硬断言继续生效|[current](current-cli-boundary-p95-500.log)、[compat](compat-cli-boundary-p95-500.log)|
|原after两份样本只读新规则重评|0|通过并保留122.06220000007306ms警告；旧标准失败继续保留|[独立新评估](old-samples-v2-evaluation.json)|
|git diff --check|0|通过|[diff-check-after.log](diff-check-after.log)|
|针对本轮新提交的GitHub Actions|未执行|用户禁止提交和推送，云端当前仍是旧提交的运行记录|github-runs.json、git-head-after.log|
|OpenSpec归档、Git提交/推送|未执行|依用户限制保持原状，暂存区为空|git-status-after.log；活动change目录仍存在|

首次失败、预期反例失败和最终重试通过分别列出，未将历史失败重写为通过。原verify自身另一组20样本P95=38.8ms，与专用v2的20条新采样独立保存。

**新规则的实际接入范围**

`scripts/check.sh`直接运行13项合同测试，因此当前CI check入口会验证两条CLI的100ms警告和500ms失败边界。`check_single_request_limit.py`与兼容`check_performance.py`共用evaluate_samples；实际采样及诊断入口grade_enqueue_latency、performance_probe、grade_latency_diagnostics、compare_outbox_isolation沿用同一判定，结果passed决定退出码。

原grade/acceptance及verify/async_test继续执行各自既有业务验收，async_test保留20次P95 < 500ms硬断言。它们没有单次100ms失败条件，也没有直接调用专用v2采样CLI。现有workflow通过合同测试验证v2边界，本轮另在真实隔离环境实测专用v2采样，完整保留1条111.12800000000789ms警告。没有新增CI workflow步骤。

**提交与推送条件**

当前完整工作树已满足本机自动化门禁条件，包括环境重试后的grade、完整verify和浏览器回归。本轮保留了可复现的源码哈希、命令、退出码和原始CI失败日志。首次RabbitMQ启动退出1的内部原因尚未确认，后续同配置串行启动及全部断言通过，该不确定性保留在本报告。

技术门禁结果支持进入提交审阅。当前差异同时包含此前整改和v2规则调整，应按既定change边界审阅和选择提交内容。用户仍禁止实际提交、推送和归档，本轮全部保持待确认；本机通过也不代表已有新提交的云端CI通过记录。未修改业务代码、workflow、测试断言或既有证据。
