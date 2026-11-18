# 历史测试代码与归档验证索引

## 2026-11-18 后续修复工作树新增测试

以下为归档进入 main 之后的本地未提交整改，历史归档结论不改写。基线为 `2d2900bf34b52d8df21513c6ef2ebc873df9f345` 加实际代码差异；报告在 `reports/lesson9-20261118/retest-02/fix-round/round-02/`（下称 R2）。本轮依赖原门禁通过，100ms 性能仍失败。

|脚本|测试功能、步骤与断言|运行入口/依赖|证据与归档状态|
|---|---|---|---|
|`regression/frontend_toolchain.test.mjs`|真实构建、JS/CSS可读、/assignments深链接；dev/preview转发POST/CSRF/Cookie/health；未知Host403、后端断开503、目录越界不泄漏package|`node --test tests/regression/frontend_toolchain.test.mjs`；frontend npm ci、Node24|R2/logs/toolchain-regression-final.txt；已执行通过；首次失败也保留|
|`performance/grade_latency_diagnostics.py`|原urllib边界，20份fresh提交逐次202、不含分数；保存全部耗时、API ID、规范化SQL、文件等待和脱敏锁关系|`python -X utf8 tests/performance/grade_latency_diagnostics.py --help`；Docker/专属子网；真实执行参数见R2报告|R2/diagnostic-retry、before-lock-fix；已执行；旧部分verify因编码失败，不冒充通过|
|`performance/compare_outbox_isolation.py`|同一Compose/DB/broker/前端，只切换已验证后端镜像，前后各2×20；不删样本，任一>100ms退出1|`python -X utf8 tests/performance/compare_outbox_isolation.py --help`；先构建修复前后镜像|R2/controlled-comparison；已执行退出1；修复后仍有122.062ms|
|`performance/analyze_grade_waits.py`|以数据库anchor关联慢请求/API和重叠SQL/文件等待；统计outbox锁关系，不含SQL字面量|`python tests/performance/analyze_grade_waits.py <comparison-dir> <output.json>`|R2/performance-analysis.json；已执行；分析退出0不代表100ms通过|
|`regression/lesson9_final_regression.py`|原Dockerfile构建、完整verify（事务/幂等/补投/安全）、原2条Playwright；复制新XSS证据并恢复原报告|`python -X utf8 tests/regression/lesson9_final_regression.py --help`；Docker、npm、Chrome|R2/final-regression；已执行退出0；合成账号由隔离环境生成|
|`environment/run_project_gates.sh`|原make check/grade，保留失败退出码；本轮增加可选QA_GO_PROXY构建参数，不进入应用环境|GNU make Linux工具环境；QA_BUILD_PROXY、QA_GO_PROXY、QA_TEST_SUBNET均显式传入|R2/logs/make-check.txt、make-grade.txt；0/0、grade18/18|
|`environment/run_windows_security_gate.py`、`windows_tool_launcher.c`|显式选择官方CI版Node/npm；Windows命令名适配；先验证退出7及空格/引号/反斜线原样转发，再运行原mingw32-make check-security|`python tests/environment/run_windows_security_gate.py --help`；MinGW GCC、GNU make、官方Node/npm路径|R2/native-security-gate；已执行退出0；只写忽略目录中的exe，不改门禁|
|`environment/history/windows_tool_launcher_argument_attempt01.c`|首次环境适配源码，退出码自检发现参数引号丢失；历史失败，不用于正式入口|仅归档，勿替换最终适配器|本轮会话失败输出及R2返工记录；原版本已找回保存|
|`environment/npm`|在Linux工具环境显式转发到官方npm11 CLI，参数/退出码不变|设置QA_NPM_CLI；只在专属容器临时PATH中使用|R2/logs/make-check-security-final-npm11.txt；实际执行因TLS断连失败，未当通过|
|`security/frontend_dependency_candidates.py`|将本轮内联隔离候选实验落盘；仅在忽略目录解析/审计esbuild与Rsbuild，不改正式frontend|`python tests/security/frontend_dependency_candidates.py --help`；显式旧package、Node/npm路径|R2/esbuild-*、rsbuild-*为原内联执行证据；落盘后的CLI仅语法/help核对，未重复解析。Rsbuild audit=0但内嵌picomatch4.0.5，已拒绝|

原性能门槛入口仍引用 `scripts/qa/lesson9/check_performance.py`（本工作树既有未提交文件），原业务/安全测试仍引用 `scripts/verify.py`、`async_test.py`、`security_test.py`、`security_static.py`、`security_cases.py`；没有复制成不同判据。R2/code-fingerprint.json、code-diff.patch 和 manifest.json 关联最终源码及证据。新增源码位于项目内，未提交；二进制、凭据、node_modules均在忽略目录，不归档。

## 原测试归档 PR 的历史说明

本 PR 只提交 `tests/`。不修改业务代码、依赖、原测试或原报告，不把历史失败改成通过。

## 来源与版本

|来源|核对结果|版本与证据|
|---|---|---|
|A：`teamwork-main`|没有`.git`，是旧骨架源码副本；不能认定为第9课首测|其verify/acceptance/check与Git历史`635d4651f55807a0e12fbfa79e04d6db413f539d`逐字规范换行后匹配；本地docs/verification.md执行日期2026-10-28|
|B：`teamwork-main-latest`|第8课首测、会话复测及修复工作树所在目录，源文件与未提交改动保留|第9课基线`bd42a6149e975c1ed217fb9349621443a3be53d5`；`qa/lesson9/retest-02/execution.json`、`recovery/summary.json`与日志核对命令|
|B的修复工作树|性能与Playwright历史复测带有未提交前端依赖修改|不是纯bd42提交；见其reports/lesson9-20261118/retest-02/fix-round/code-fingerprint.json。本PR不带入这些业务/依赖修改|

原路径、源码SHA256、归档改动见[provenance.json](provenance.json)。源路径用A/B相对标识，不发布本机用户目录。`tests/evidence/`是已有执行的脱敏记录；`tests/validation/`只记录本次归档验证。两者不能互相替代。源码快照曾有40份受Git跟踪、13份未跟踪；本次不重复复制已跟踪的测试，原件在下表引用。

缺口：早期被覆盖的acceptance/run_online包装器精确执行修订，以及未落盘的一次性命令片段，**原脚本缺失**；最终包装器仍存在并用于适配。没有根据日志重建这些缺失历史版本。未单独找回另一份带版本及缺陷号的第9课独立首测清单。镜像导入、报告生成等一次性工具不是测试用例，仍在只读来源B，不混作功能测试上传。

## 归档文件：用途、步骤、断言与入口

所有命令从仓库根目录运行；Python3.10+。不要使用`python -O`，归档脚本保留了原assert断言。Docker测试仅使用临时合成账号，不接受生产环境。新入口生成随机Compose项目、临时凭据并清理自身资源，不覆盖根`.env`。输出在`tests/output/`，临时配置在`tests/.runtime/`，均忽略提交。

|文件|测什么：步骤与断言|运行入口|依赖/预期/历史证据|
|---|---|---|---|
|[regression/isolated_acceptance.py](regression/isolated_acceptance.py)|原18项隔离验收：构建启动、live/health/ready、方法与参数限制、默认拒绝、Cookie/前端、JSON日志、DB/Qdrant故障恢复、端口隔离、优雅停机、异步202、SQLi、CSRF、配置和审计。空检查列表不得被当成通过|`python tests/regression/isolated_acceptance.py --help`；去掉help执行|Docker/Compose及原镜像；18/18且原入口退出0。历史B/qa/lesson9/retest-02/recovery/acceptance/report.json|
|[regression/business_workflows.py](regression/business_workflows.py)|调用原verify全部断言：登录失败同形、教师上传/下载/列表、学生403无残留、跨班404、文本类型、检索与出处、无依据拒答、数据库/检索故障、锁定、容器重建持久化；再运行异步及安全子套件|`python tests/regression/business_workflows.py`|Docker；全部断言0；历史B/.../recovery/verify.md与fix-round/verify.md。根`.env`只在内存注入，不改原文件|
|[support/isolated_project.py](support/isolated_project.py)|上述入口的隔离支撑：随机项目、不复用现存项目、原acceptance环境生成、可选子网/构建代理、原verify内存配置和输出重定向、RabbitMQ应用就绪等待、退出清理|由隔离/业务/性能/跨班入口调用，不单独测试业务|来自实际acceptance_run.py/run_online.py；更改了根路径、项目名和配置注入，未替换原业务断言。环境缺失不得称通过|
|[performance/grade_enqueue_latency.py](performance/grade_enqueue_latency.py)|20次顺序新提交→计时批改POST；逐次必须202，不含score/feedback；保留全样本、P95、最大值、>50ms和>100ms次数；不预热、不丢弃慢值|`python tests/performance/grade_enqueue_latency.py`|Docker；全部<=100ms且P95<500ms才0。来自实际performance_probe.py，历史证据[两轮样本](evidence/enqueue-latency-round-1.json)，原179.6ms见[历史汇总](evidence/historical-retest-summary.json)|
|[performance/check_single_request_limit.py](performance/check_single_request_limit.py)|离线复核每份20个202；单次>100ms、数量错误或非202则非零。P95通过不能覆盖单次失败|`python tests/performance/check_single_request_limit.py tests/evidence/enqueue-latency-round-1.json tests/evidence/enqueue-latency-round-2.json`|仅Python；这两份真实历史数据应退出1，不能把预期红项当归档失败或改绿|
|[performance/latency_gate_contract.py](performance/latency_gate_contract.py)|本次新增的门槛合同测试：100ms边界通过、100.001ms失败、19条失败、状态200失败；防止门槛检查出现假绿|`python tests/performance/latency_gate_contract.py`|标准库unittest；4条均通过，结果见validation/archive-validation.json。不是冒称历史脚本|
|[security/cross_class_grading.py](security/cross_class_grading.py)|SEC-04直接入口：B班创建真实合成提交，A班直接批改→404，与不存在提交正文相同；task/result/outbox计数前后不变|`python tests/security/cross_class_grading.py`|Docker；拒绝与无残留全部满足才0；来自实际supplement.py，历史B/.../recovery/supplement-result.json。本文件不再包含已在仓库跟踪的SEC08脚本副本|
|[security/security_precheck.py](security/security_precheck.py)|历史首测9项：SEC01未登录、SEC02跨班、SEC03配置越权、SEC04绕鉴权、SEC05源码/历史/产物/日志密钥、SEC06 npm/Go依赖、SEC07审计语义；CONCURRENCY幂等、TRANSACTION停消费者与回滚。旧版本缺失功能会blocked，不伪造403/审计成功|`python tests/security/security_precheck.py --help`；`--baseline-only`仅资产；`--gates`增加旧功能门禁|Docker、Go、npm；旧govulncheck版本保留，不能代替当前security_gate。原输出仍按旧reports结构写入，应在可丢弃检出中执行。历史B/scripts/week8_security.py及reports/evidence/week8/run-index.json。当前仅语法和CLI验证，完整旧首测未重放|
|[security/precheck_report_consistency.py](security/precheck_report_consistency.py)|核对旧报告六列、详细五字段、SEC01–07状态/判定一致、阻塞无绿红结论、证据清单/哈希等实际代码检查|`python tests/security/precheck_report_consistency.py`|要求旧reports/evidence/week8/latest.json及对应旧报告；缺失则阻塞，不可用新报告冒充。源week8_validate.py；本次语法验证，未补造缺失旧报告夹具|
|[security/read_only_class_review.py](security/read_only_class_review.py)|旧独立交叉复核：受保护路由匿名401，A/B角色与材料归属真实存在，同班读取/检索阳性对照、跨班详情/文件同形404、keyword/vector/hybrid跨班空结果；检查测试前后报告与版本/二进制证据。仅登录和只读业务请求|`python tests/security/read_only_class_review.py --help`|显式传`--base-url --compose-project --historical-evidence --env-file`，不再含本机端口/容器名。原runner.py及metadata为2026-11-06、292eaaff+工作区。须原夹具及合成账号；当前未对旧数据库重放|
|[environment/Dockerfile.validation-tools](environment/Dockerfile.validation-tools)|历史真实make工具镜像：固定Go1.26.11与Node22基础，安装make/Python/Git/Docker CLI。没有代理地址或凭据|`docker build -f tests/environment/Dockerfile.validation-tools -t teamwork-validation-tools tests/environment`|Docker；APK依赖版本随源变化，历史工具构建/目标输出来自B/fix-worktree/.../fix-round。当前未重装整套工具，不能以文件存在宣称make已重跑|

可选运行参数：隔离、业务、性能和跨班入口都支持`--subnet "$QA_TEST_SUBNET" --build-proxy "$QA_BUILD_PROXY"`。代理只作为构建参数，不注入应用运行时。不要复制本机IP/端口到仓库配置。默认无子网覆盖，需要Docker默认池可用；指定子网须先检查不重叠。镜像下载、浏览器安装、旧夹具缺失都应记录环境阻塞。

## 已在仓库跟踪的测试：引用原路径，不重复归档

补充归档文件：

|文件|覆盖步骤与断言|入口与本次验证|
|---|---|---|
|[security/redaction_contract.py](security/redaction_contract.py)|嵌套token/CSRF/password字段被删除，原输入不变；404、class_id、denied等非敏感判据保持|`python tests/security/redaction_contract.py`，2条通过；新增的归档脱敏验证，不冒称历史用例|
|[environment/run_project_gates.sh](environment/run_project_gates.sh)|从原run_make/run_grade包装器适配：原make check/check-security/grade逐条日志与退出码；拒绝复用现存grade项目；仅构建代理；合并状态非零，不改Makefile断言|`sh tests/environment/run_project_gates.sh check check-security grade`；需要真实make/Python/Node/Docker CLI；本次仅shell语法验证，不声称又跑了原make目标|

归档适配时额外补上旧脚本未覆盖的新CSRF响应字段脱敏。CLI环境通过COMPOSE_ENV_FILES传给原verify的Compose子进程，密码只在生成的忽略文件内；不改根.env或源目录。上述shell入口需从可运行原Makefile的环境调用；Docker工具镜像使用时需正确挂载工作树和Docker socket。

本节当前版本均为bd42a614；A目录旧骨架版本可用`git show 635d465:<原路径>`核对。表中的多步骤是实际代码覆盖，不代表本次归档又运行了全部门禁。

|原文件|覆盖步骤与断言|命令/依赖|历史证据|
|---|---|---|---|
|[scripts/verify.py](../scripts/verify.py)|完整业务主路径与正常/失败/越权/故障；末尾调用async_test、security_test|根目录`python scripts/verify.py`；已配置隔离Compose|B/recovery/verify.md；本次归档业务入口日志|
|[scripts/acceptance.py](../scripts/acceptance.py)|18项A01–A18，以实际report的id/name/criterion为准；失败非零|`make grade`或`python scripts/acceptance.py`|B/recovery/acceptance/report.json；本次validation/isolated-acceptance.json|
|[scripts/async_test.py](../scripts/async_test.py)|队列durable/端口、提交非法400、跨班404、版本复用/追加、事务故障回滚、202/复用task、权限查询、停/kill worker恢复、20次P95、重复消息一份结果、永久/瞬时/死信、停broker补投|由verify调用；MySQL/RabbitMQ/worker|B/recovery/verify.md；历史延迟样本保留|
|[scripts/security_test.py](../scripts/security_test.py)|SQLi登录/材料/检索；XSS JSON与无raw HTML/localStorage；CSRF缺token/跨源/正确token；SEC03学生403不变/教师更新/跨班404/denied时间窗；SEC04技能202/他人教师404无残留；SEC07七列与学生403|由verify调用|B/recovery/security-prioritized.md；本次业务回归|
|[scripts/security_cases.py](../scripts/security_cases.py)|加载三条case字段并核对静态XSS禁止项|`python scripts/security_cases.py`|B/retest-02/logs/cases.txt|
|[scripts/security_static.py](../scripts/security_static.py)|前端token/raw HTML相关静态防御检查|`python scripts/security_static.py`|B/retest-02/logs/static.txt|
|[scripts/security_gate.py](../scripts/security_gate.py)|源码历史密钥、npm高危、Go审计门禁；self-test临时假密钥红→干净绿|`make check-security`；`python scripts/security_gate.py --self-test`|B/recovery及fix-round make输出；历史high5仍未处置，不在本PR修依赖|
|[scripts/secret_scan.py](../scripts/secret_scan.py)|已跟踪工作树与Git历史密钥非空赋值检查|`python scripts/secret_scan.py`|B/retest-02/logs/secrets.txt|
|[scripts/govuln_check.py](../scripts/govuln_check.py)|指定Go实时审计；无工具时核对go.sum快照对应，不把旧快照冒充新扫描|`python scripts/govuln_check.py`|B/retest-02/logs/govuln.txt|
|[scripts/sec08_experiment.py](../scripts/sec08_experiment.py)|恶意文档、索要提示词、改规则、绕权限四步；第四步404并审计denied必须通过|`python scripts/sec08_experiment.py`；隔离.env与docs/lesson-09/sec08素材|B/recovery/sec08-sandbox/reports/sec08-experiment.md|
|[scripts/layer_check.py](../scripts/layer_check.py)|新httpapi不得SQL，legacy仅登记三文件|`python scripts/layer_check.py`|B/retest-02/logs/layer.txt|
|[scripts/mutation.py](../scripts/mutation.py)|临时破坏分层，断言门禁能变红|`python scripts/mutation.py`|B/recovery/logs/mutation.txt|
|[scripts/spec_check.py](../scripts/spec_check.py)|change四文件、场景字段/失败路径、能力映射与任务verify结构|`python scripts/spec_check.py`|B/retest-02/logs/spec.txt|
|[scripts/standards_check.py](../scripts/standards_check.py)|8类规范、规则、数据字典、README等入口结构|`python scripts/standards_check.py`|B/retest-02/logs/standards.txt|
|[scripts/check.sh](../scripts/check.sh)|串联结构/strict/安全静态/分层/密钥/变异/Go格式测试vet/前端build|`make check`；sh、Docker、Node、Python|B/fix-round/logs/make-check.txt；本PR未改此入口|
|[scripts/grade.sh](../scripts/grade.sh)|exec原acceptance入口，保持退出码|`make grade`|B/fix-round/logs/make-grade-buildproxy.txt 18/18|
|[scripts/ci_env.py](../scripts/ci_env.py)|CI随机隔离凭据配置生成，不是功能用例|`python scripts/ci_env.py`；仅新检出，生成.env不提交|原CI及历史运行入口|
|[apitest/cases/api/search/POST/case.json](../apitest/cases/api/search/POST/case.json)|SQLi payload与前置/操作/期望，登录拒绝、无跨班数据|security_cases/verify加载|B安全回归日志|
|[apitest/cases/api/materials/POST/case.json](../apitest/cases/api/materials/POST/case.json)|XSS文件名/JSON/页面源码转义前置和判据|security_cases/Playwright加载|B reports/xss-page-source.md|
|[apitest/cases/api/skills/grade/PATCH/case.json](../apitest/cases/api/skills/grade/PATCH/case.json)|CSRF无token/跨源拒绝、正确token成功|security_cases/verify加载|B安全回归日志|
|[apitest/cases/async/README.md](../apitest/cases/async/README.md)|三条异步判据说明，不是独立执行脚本|verify对应函数|B/recovery/verify.md|
|[apitest/cases/security/README.md](../apitest/cases/security/README.md)|防御性反例说明，不是独立脚本|verify对应函数|B/recovery/security-prioritized.md|
|[frontend/e2e/assignments.spec.ts](../frontend/e2e/assignments.spec.ts)|学生登录→选择作业→提交→轮询完成→显示分数；缺凭据skip必须登记|`cd frontend/e2e && npx playwright test`|历史2条通过，见evidence/historical-business-validation.json|
|[frontend/e2e/xss-materials.spec.ts](../frontend/e2e/xss-materials.spec.ts)|教师上传脚本标题→列表源码转义、无执行对话框；支持显式mock，与真实模式区分|同上，教师凭据；历史本轮为真实上传|B/fix-round/logs/playwright.txt 2/2|
|[frontend/e2e/playwright.config.ts](../frontend/e2e/playwright.config.ts)|baseURL/channel、超时和失败trace配置；本身不是断言|同上；浏览器与测试环境|历史E2E运行配置|
|[frontend/e2e/package.json](../frontend/e2e/package.json)、[package-lock.json](../frontend/e2e/package-lock.json)|E2E依赖与锁定，不是用例|该目录npm ci|历史安装日志|

Go单元文件逐项如下；统一从`backend/`运行`go test ./...`，Go1.26.11，历史官方容器测试通过。原用例名保留，避免凭文件名猜覆盖范围。

|原文件|实际用例与断言|
|---|---|
|backend/internal/auth/jwt_test.go|JWTRoundTrip、JWTRejectsExpired：签发解析、过期拒绝|
|backend/internal/chat/chat_test.go|PickAnswerMagnet：本地摘录选择|
|backend/internal/chunk/chunk_test.go|AutoDefaultWindow、StrategiesDifferOnTitledDoc、OffsetsOnSource、PreprocessDoesNotChangeCaller：窗口/策略/原文偏移/输入不变|
|backend/internal/config/config_test.go|LoadRejectsMissingSecret、LoadAcceptsExplicitEnv：缺密钥拒绝与显式配置|
|backend/internal/grading/keys_test.go|IdempotencyKey：提交版本幂等键|
|backend/internal/grading/score_test.go|ScoreLocalRange、ClassifySentinels：本地分数范围与失败类别|
|backend/internal/grading/state_test.go|StateMachineHappyPath、TransientThenDead、PermanentFailed、IllegalTransfers、RetrySeconds：状态/非法转换/退避|
|backend/internal/health/health_test.go|Live、ReadyAllUp、ReadyDatabaseDown、ReadyQdrantDown：存活/依赖就绪与故障|
|backend/internal/lifecycle/server_test.go|ServeDrainsInflightRequest、ServeForceClosesAfterTimeout：排空与超时关闭|
|backend/internal/logging/logging_test.go|ValidRequestID、MiddlewareGeneratesAndEchoesRequestID、MiddlewareKeepsValidRequestID：ID验证/生成/保留|
|backend/internal/materials/text_test.go|AllowedExt、DisplayTitleStripsPath、ValidateText：白名单/显示名/文本校验|
|backend/internal/queue/topology_test.go|RetryQueueNames：重试队列名|
|backend/internal/retrieval/rrf_test.go|RRFPrefersOverlap、RRFMissingListAddsNothing：融合排序与缺列表|

## 历史结果与本次验证结果

历史：bd42a61隔离验收18/18、原verify通过、SEC03/04/07及SEC08第四步通过；修复工作树Playwright2/2。历史179.6ms以及后续253.72/349.70ms慢样本保留；high5与100ms门槛没有因本PR归档而关闭。

本次：见[validation/archive-validation.json](validation/archive-validation.json)和该目录运行结果。4条门槛合同测试通过，两份历史慢样本按预期退出1；全部Python语法及可用CLI帮助验证。隔离/业务入口的实际执行与环境失败分别记录，不把help/语法通过当成业务通过。旧首测报告校验和只读交叉复核缺原夹具，完整执行未重放；旧工具镜像未重装。正式录像与真人签字不由本PR代替。

归档只包含常规、性能和防御性验证；没有凭据、真实账号数据、镜像、数据库、上传文件或node_modules。原代码中的teacher_a/student_a1/student_b1是项目合成测试账号名，密码运行时生成/显式注入，不存入索引或证据。

### 本次归档实际运行结论

隔离入口18/18、业务入口原verify全部断言、直接跨班入口404/无残留均通过。性能CLI实际完成20次采样，最大318.3293ms、超过100ms一次，按原门槛退出1；并非环境阻塞或性能修复成功。4条门槛合同测试及2条脱敏合同测试通过。旧报告一致性脚本实跑因缺reports/evidence/week8/latest.json而失败，归类缺夹具；只读旧交叉复核未完整重跑。构建瞬时失败与首次配置适配失败均保存为脱敏失败记录，修正CLI环境来源后重跑成功。完整机器可读结果见validation/live-validation.json。

辅助文件：`.gitignore`只排除输出/临时凭据/缓存；`.gitattributes`保留归档字节；`provenance.json`保存来源和改动；`manifest.json`保存发布文件SHA256。`evidence/`四份JSON分别为两轮历史延迟、历史复测汇总、历史业务/浏览器执行汇总；它们没有重新执行的含义。`validation/`中`archive-validation.json`为CLI/合同测试，`live-validation.json`为实时退出码，`isolated-acceptance.json`为18项明细，`direct-cross-class.json`为拒绝与数据库计数，`grade-latency.json`为本次20样本，`business-verification.md`为全量断言记录；其余`*.log`/`*.exit.txt`按同名入口保存含失败尝试的脱敏输出，不含口令或真实账号。清单与结果应一并审阅。

## 2026-11-18 性能规则修订

现行enqueue-latency-v2对单次100ms超限输出警告，20条202和P95 < 500ms继续硬断言。上述归档结果和tests/manifest.json属于旧版本记录，原样保留。当前源码清单及验证见docs/lesson-09/2026-11-18-observe-enqueue-latency。历史报告生成器冻结入口以保护旧证据。

## 提交准备后的现行发布索引

`tests/release/lesson9-v2-publication.json`为当前2d2900b基线上的显式发布增量，使用`python scripts/qa/lesson9/verify_release.py`校验。原`tests/manifest.json`及两个旧docs证据目录的索引均为不可变历史快照，版本和路径别名见`tests/release/history-context.json`。v2阶段的24项current-source-sha256也保留其当时源码快照含义，后续授权的文档和规约变化由新的现行索引覆盖。
