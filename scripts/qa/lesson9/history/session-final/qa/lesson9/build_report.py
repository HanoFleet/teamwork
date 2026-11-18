import csv, json, pathlib, collections, hashlib, datetime, subprocess
B=pathlib.Path(__file__).resolve().parent
R=B/'test-main'
OUT=B.parents[1]/'reports'/'lesson9-20261118'
V=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
rows=[]
def add(i,req,pre,op,expect,actual,status,evidence):
 rows.append(dict(用例编号=i,关联需求=req,前置条件=pre,输入与操作=op,预期结果=expect,实际结果=actual,状态=status,证据位置=evidence,执行时间=now,被测提交=V))
execs=json.loads((B/'execution.json').read_text(encoding='utf-8'))
for e in execs:
 if e['id'] in ['go','openspec','gate-selftest']:continue
 status='通过' if e['exit']==0 else '阻塞'
 add('G-'+e['id'],'项目门禁','独立工作树；Windows；Python/Node/Go 已安装',' '.join(e['command']),'退出0',f"退出{e['exit']}；见原始输出",status,e['evidence'])
 rows[-1]['执行时间']=e['time']
for i,log in [('openspec','openspec-retry.txt'),('gate-selftest','gate-selftest-retry.txt')]:
 add('G-'+i,'规约严格验证' if i=='openspec' else 'security-hardening/门禁先红后绿','允许读取工具缓存','见日志；权限重试','整体退出0','退出0；自测红项1、绿项0' if i=='gate-selftest' else '6 items passed','通过','logs/'+log)
events=[]
for line in (B/'logs/go-retry.jsonl').read_text(encoding='utf-8-sig').splitlines():
 try:events.append(json.loads(line))
 except ValueError:pass
tests=[e for e in events if e.get('Test') and e.get('Action') in ['pass','fail','skip']]
packages=[e for e in events if not e.get('Test') and e.get('Action') in ['pass','fail']]
add('G-go','backend 单元回归','GOPROXY=https://goproxy.cn,direct','go test -json ./...','退出0，无失败',f"退出0；{len(tests)}个测试终态；包结果{dict(collections.Counter(e['Action'] for e in packages))}",'通过','logs/go-retry.jsonl')
audit=json.loads((B/'logs/npm-audit-retry.json').read_text(encoding='utf-8-sig'))
add('SEC-06','资产/依赖审计','最新 main 的 frontend/package-lock.json','npm audit --json --audit-level=high --package-lock-only --registry=https://registry.npmjs.org','高危0、严重0，退出0',str(audit['metadata']['vulnerabilities']),'失败','logs/npm-audit-retry.json')
sec=[('SEC-01','授权','无认证逐个请求受保护接口','全部401'),('SEC-02','授权','A1读取B材料；B检索A关键词；同班对照','跨班404/空；同班正常'),('SEC-03','授权','学生持有效token PATCH skills/assistants；前后核对数据','403且数据不变'),('SEC-04','授权','绕过技能入口直接调用批改入口操作他人提交；核对task/outbox/result','拒绝且无残留'),('SEC-07','日志','运行技能；教师按技能标识、学生与时间窗查日志；学生查询','七列齐全；拒绝有记录；学生403'),('SEC-08','日志/提示词注入','恶意讲义、索要提示词、改规则、绕权限四步','记录前三步现象；第四步拒绝且有审计'),('SQLI','注入','搜索提交 OR 恒真、%与_','不泄漏跨班数据，不返回500'),('XSS','注入','标题含script上传；打开列表查看页面源码','源码转义无执行'),('CSRF','注入','恶意Origin/缺token伪造配置写；检查SameSite','403且数据不变；Cookie属性正确'),('ASYNC','异步回归','执行第8课三条异步判据','202/P95、停worker、重复投递和恢复符合规约'),('DEMO','四步演示','登录→202→轮询终态→跨班404','四步全绿并留录屏')]
for i,cat,op,ex in sec:
 add(i,cat,'隔离Compose健康；A/B班测试账号和测试数据',op,ex,'未发送业务请求：Docker daemon 管道不存在；独立工作树无.env','阻塞','logs/docker.txt；logs/verify.txt')
for i,op in [('BUILD','前端npm ci及npm run build'),('E2E','Playwright桌面与移动端'),('GOVULN','当日govulncheck源码与部署二进制审计'),('FAULT','依赖故障和恢复集成回归')]:
 add(i,'完整回归','依赖与隔离运行环境可用',op,'按项目规范通过','本轮未运行；需依赖下载、浏览器或Docker环境','未执行','测试与复测报告.md')
def writecsv(path,data):
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
writecsv(B/'用例执行表.csv',rows)
retests=[]
for i in ['SEC-03','SEC-04','SEC-07']:
 retests.append(dict(缺陷编号=i,类别='授权' if i!='SEC-07' else '日志',首次版本='292eaaff + 历史工作区修改（非纯提交）',首次失败证据='sources/local-week8-security-precheck.md；原reports/evidence/week8/',首次表现={'SEC-03':'无配置写入口，原用例阻塞','SEC-04':'无技能链，原用例仅部分执行','SEC-07':'任务日志缺技能审计语义'}[i],修复提交='7263dda（已在main）；SEC-07时间窗补证090ca01',修复PR='GitHub issues/pulls API均返回[]；无可核验PR',复测版本=V,原用例=i,复测状态='待复测',当前实际='修复代码可访问；Docker不可用，未进行HTTP复测',新证据='logs/docker.txt；sources/developer-fix-log.md',恢复条件='启动Docker Desktop Linux engine，创建隔离Compose和测试账号'))
retests.append(dict(缺陷编号='L9-DEP-001',类别='资产',首次版本=V,首次失败证据='logs/npm-audit-retry.json',首次表现='5个high依赖条目，critical 0；不是5个独立漏洞',修复提交='无',修复PR='无',复测版本='',原用例='SEC-06',复测状态='待复测',当前实际='本轮发现；禁止据历史绿项关闭',新证据='logs/npm-audit-retry.json',恢复条件='开发提交依赖修复或可检查的逐漏洞处置登记；再审计及构建回归'))
writecsv(B/'缺陷复测表.csv',retests)
c=collections.Counter(r['状态'] for r in rows)
summary=dict(测试提交=V,时间=now,执行表统计={s:c[s] for s in ['通过','失败','阻塞','未执行']},待复测=len(retests),通过率=f"{c['通过']}/{c['通过']+c['失败']}（只计有有效判定的检查行；非业务场景通过率）",Go测试终态=dict(collections.Counter(e['Action'] for e in tests)))
(B/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
report=f'''# 第9课独立测试与复测报告

本轮尚未通过验收：依赖审计失败，在线业务复测被环境阻塞。执行时间 {now}，Windows PowerShell，测试版本 `{V}`。不将开发历史记录当作本轮复测证据。

更新前分支 `change/2026-11-06-security-precheck`，HEAD `292eaaffc24fcad07e936ec6b4adf72dd6af8589`。origin 已核对为 https://github.com/HanoFleet/teamwork.git，git fetch origin 成功，取得上述 origin/main。工作区有未提交修改，未pull或切换原分支；独立工作树 `qa/lesson9/test-main` detached HEAD 测试。修复7263dda、090ca01、cfe7e74均在main，无需另测未合并分支。GitHub API返回空列表，不能推断不存在私有缺陷记录。

## 结果

{json.dumps(summary,ensure_ascii=False,indent=2)}

统计单位是执行表检查行（套件级与课程业务级），Go内部测试单独统计、不累加；阻塞不计通过率。待复测是缺陷表状态，不能与用例数相加。首次阻塞/失败和权限、代理重试日志独立保留。本轮没有可判定的在线功能缺陷；资产缺陷 L9-DEP-001 严重程度高，npm报告5个high依赖条目（含传递影响），critical 0。

## 环境与执行

通过：规约、规范、分层、静态安全、注入反例文件校验、工作树/历史密钥扫描、OpenSpec strict、门禁红绿自测和Go单元回归。Go首次权限失败，官方代理超时后按项目指定goproxy.cn重跑退出0。OpenSpec和红绿自测权限重试退出0。红绿自测只证明检测能力，不代表当前正常安全门禁绿。

make不存在，三个make入口实际尝试均无法启动；verify缺.env，Docker Linux engine管道不存在。未启动业务环境，未执行在线SQLi/XSS/CSRF、异步三判据、SEC-08和演示，没有本轮业务截图或录像。前端审计镜像站404后切官方registry，发现高危。未运行完整前端构建/Playwright及在线依赖故障测试，不能宣称回归全绿。恢复条件：可用Docker Linux engine、make/sh、隔离Compose、临时凭据；修依赖后完整重跑。不要用已有共享环境直接破坏性停服务。

## 来源、基线与边界

两课原文已实际读取，完整HTML和文本位于sources/lesson8.*、lesson9.*。首次中文URL经终端编码误传返回课程入口，已以显式UTF-8编码重取正确标题原文。课程要求按reports/课程要求映射.md逐项落实。

第8课材料沿用接口清单、SEC用例和独立原始证据目录；sources/保留本地与main两份precheck及开发修复表。历史SEC-03/04属功能缺失阻塞，不虚构成已实测失败。开发提交的历史绿项仅作参考；本轮复测不得关闭。原始未提交修改保留，未改业务代码、未勾选任务、未提交推送、未替真人签字。

## 交付与提交位置

本轮数据在qa/lesson9/，课程指定名称报告暂存于reports/lesson9-20261118/（同时镜像qa/lesson9/reports/），避免覆盖已有第8课原件。课程最终要求根reports/security-fix-log.md、sec08-experiment.md、security-baseline.md、gate-red-green.md和递增review记录；测试全部完成后由组员整合本轮材料至这些根路径。反例本体已在被测提交apitest/cases/，本轮只静态校验。课程原文未提供额外教学平台地址，本轮未向GitHub或平台发消息。

需组员补齐：可运行Docker测试环境；依赖修复提交或逐漏洞处置登记；SEC-01～08和三组回归实际输出；XSS页面源码、四步演示录像；另一位真人独立复现至少两条；真实返工耗时记录。本轮不编造人工评审或修复耗时。
'''
(B/'测试与复测报告.md').write_text(report,encoding='utf-8')
(OUT/'测试与复测报告.md').write_text(report,encoding='utf-8')
for name,content in {
'security-fix-log.md':'# 修复前后复测表\n\n'+ '\n'.join(f"- {x['缺陷编号']}：{x['首次表现']}；修复 {x['修复提交']}；本轮{ x['复测状态']}。{x['当前实际']}" for x in retests),
'security-baseline.md':'# 当日安全基线\n\n版本 '+V+'。密钥扫描退出0（logs/secret.txt）；npm官方审计high=5、critical=0，未清零。涉及 '+', '.join(audit['vulnerabilities'])+'。完整漏洞编号、影响范围、修复建议见qa/lesson9/logs/npm-audit-retry.json。未执行当日govulncheck；历史快照不算当日扫描。',
'gate-red-green.md':'# 门禁证据\n\n版本 '+V+'。自测红退出1、清理后绿退出0，整体退出0：qa/lesson9/logs/gate-selftest-retry.txt。当前实际依赖审计退出非0，高危5；不能满足“修复后正常make check-security绿”。make入口缺失阻塞。',
'sec08-experiment.md':'# SEC-08 本轮记录\n\n四步（恶意文档/索要提示词/改规则/绕权限）全部阻塞，Docker不可用；没有本轮模型输出、数据库对照或审计证据。素材沿用test-main/docs/lesson-09/sec08/。不复用历史绿项作为本轮结论。',
'review-04.md':'# 脚本复核记录\n\n手段：运行规约/规范/分层/安全静态/注入结构检查及OpenSpec strict。查了什么：main安全加固规约与可执行反例结构。判据：各退出0。结果：全部通过；仅静态范围，业务复测阻塞。详见qa/lesson9/logs/。这是脚本/AI记录，不是人工签字。',
'review-05.md':'# 资产与回归复核\n\n手段：官方npm审计、Go测试、红绿自测。查了什么：依赖风险和单元回归。判据：high/critical为0、测试退出0、红能阻断。结果：Go及红绿自测通过；npm高危5项失败，阻断验收。另一位真人复现两条仍未满足。',
'rework.md':'# 返工素材待补\n\n本轮只测试，无业务修复。开发需填写真实回归、定位耗时、修复耗时、当时怎么错及可执行改法。环境排障不伪装成开发返工。'
}.items():(OUT/name).write_text(content,encoding='utf-8')
mapping=['# 课程要求 → 工作 → 证据 → 状态','', '|要求|已执行工作|证据|状态|','|---|---|---|---|']
items=[('基线与红项分类','保留第8课两版记录；授权03/04、日志07；Go与静态基线已执行','sources/；logs/；缺陷复测表.csv','部分完成，旧版HTTP重放阻塞'),('授权01～04','核对修复已在main；准备同三段式用例','用例执行表.csv；sources/developer-fix-log.md','阻塞'),('注入三件套','反例结构检查通过；在线与XSS页面源码未运行','logs/injection-cases.txt','部分完成'),('资产05～06','密钥0命中；官方npm high5','logs/secret.txt；npm-audit-retry.json','失败，Go审计未执行'),('日志07与实验08','逐条准备执行表、保留历史素材','sec08-experiment.md','阻塞'),('回归三组与四步演示','Go通过，make/HTTP/演示阻塞','logs/；summary.json','部分完成'),('指定归档与返工','本轮报告按指定名暂存独立目录；保留原件','reports/lesson9-20261118/','待合并根reports及补真实返工'),('交叉评审','生成两份AI/脚本记录','review-04.md；review-05.md','人工复现两条待补')]
mapping += ['|'+'|'.join(x)+'|' for x in items]
(OUT/'课程要求映射.md').write_text('\n'.join(mapping),encoding='utf-8')
import shutil
shutil.copytree(OUT,B/'reports',dirs_exist_ok=True)
manifest={str(p.relative_to(B)):hashlib.sha256(p.read_bytes()).hexdigest() for p in B.rglob('*') if p.is_file() and 'test-main' not in p.parts and p.name!='manifest.json'}
(B/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
