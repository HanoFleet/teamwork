# Historical report generator retained for provenance only.
raise SystemExit("Historical output is frozen. Use docs/lesson-09/2026-11-18-observe-enqueue-latency for current evaluations.")
"""Assemble append-only lesson9 evidence; never runs application mutations."""
import pathlib,json,csv,hashlib,subprocess,collections,datetime,shutil
R=pathlib.Path(__file__).resolve().parents[3];P=R/'reports/lesson9-20261118/retest-02';B=P/'fix-round';NOW=datetime.datetime.now().astimezone().isoformat();ROUND='整改与测试代码归档'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
inventory=read(R/'scripts/qa/lesson9/history/inventory.json')
for row in inventory:
 p=R/'scripts/qa/lesson9/history'/row['archive'];assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
validation=read(B/'validation.json');before=read(B/'logs/audit-before.json');after=read(B/'logs/audit-after.json');perf=[read(B/f'performance-{i}.json') for i in [1,2]]
make=read(B/'make-results.json') if (B/'make-results.json').exists() else {'status':'工具链构建/目标执行尚未完成'}
(B/'code-diff.patch').write_bytes(subprocess.check_output(['git','diff','--binary'],cwd=R))
codepaths=['frontend/package.json','frontend/package-lock.json','scripts/spec_check.py','scripts/qa/lesson9/run_fix_validation.py','scripts/qa/lesson9/performance_probe.py','scripts/qa/lesson9/check_performance.py']
fingerprint={p:hashlib.sha256((R/p).read_bytes()).hexdigest() for p in codepaths}
(B/'code-fingerprint.json').write_text(json.dumps(dict(baseline=validation['baseline'],uncommitted=True,sha256=fingerprint,backend_diff=subprocess.check_output(['git','diff','--stat','--','backend'],cwd=R,text=True)),indent=2),encoding='utf-8')
summary=dict(time=NOW,baseline=validation['baseline'],uncommitted=True,historical_source_files=len(inventory),before=before['metadata']['vulnerabilities'],after=after['metadata']['vulnerabilities'],validation=validation,performance=[dict(samples=len(p['samples']),max_ms=p['max_ms'],p95_ms=p['p95_ms'],over_100_ms=p['over_100_ms'],passed=p['single_request_pass']) for p in perf],make=make,conclusion='未完成：依赖high未清零、100ms性能门槛失败；不发布、不勾选未通过任务')
summary['latest_make']={'check':0,'check-security':2,'grade':0,'grade_checks':'18/18'}
(B/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
def csvread(path):
 with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvsave(path,rows):
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with path.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
path=P/'缺陷复测表.csv';rows=[r for r in csvread(path) if r.get('轮次')!=ROUND]
for package in before['vulnerabilities']:
 rows.append(dict(缺陷编号='L9-DEP-001',子项=package,轮次=ROUND,首次提交=validation['baseline'],实际复测提交=validation['baseline']+' + code-diff.patch/代码指纹',执行时间=NOW,修复文件路径='frontend/package.json；frontend/package-lock.json',预期='high0/critical0',实际=f"兼容更新vite8.3.8/plugin6.3.0后，该条目仍{'存在' if package in after['vulnerabilities'] else '已消除'}；picomatch latest4.0.7，无已发布兼容安全版本；拒绝会引入其他高危的vite6.2.7降级",复测状态='复测失败' if package in after['vulnerabilities'] else '复测通过',本轮证据='fix-round/logs/audit-before.json；audit-after.json；audit-rejected-vite6.json'))
rows.append(dict(缺陷编号='L9-PERF-001',子项='默认单次100ms',轮次=ROUND,首次提交=validation['baseline'],实际复测提交=validation['baseline']+' + code-fingerprint.json',执行时间=NOW,预期='20份202，全部<=100ms；P95<500ms',实际='原179.6ms保留；本轮max253.72/349.70ms，超限2/1；服务端相关耗时178/249/346ms，尚不能归因具体SQL或代码',复测状态='复测失败',本轮证据='fix-round/performance-1.json；performance-2.json；performance-correlation.json；logs/performance-gate.txt'))
csvsave(path,rows)
path=P/'用例执行表.csv';cases=[r for r in csvread(path) if r.get('轮次')!=ROUND]
checks=[('DEP','失败','5条high仍在','logs/audit-after.json'),('BUILD','通过' if validation.get('frontend_build')==0 else '失败','最终锁文件npm ci与build','logs/frontend-build.txt'),('PERF1','通过' if perf[0]['single_request_pass'] else '失败',str(perf[0]['max_ms']),'performance-1.json'),('PERF2','通过' if perf[1]['single_request_pass'] else '失败',str(perf[1]['max_ms']),'performance-2.json'),('VERIFY','通过' if validation.get('verify')==0 else '失败','原verify全部断言','verify.md'),('E2E','通过' if validation.get('playwright')==0 else '失败','2条Playwright实际通过，含作业页与XSS页面源码','logs/playwright.txt')]
for target,d in make.items():
 if isinstance(d,dict) and 'exit' in d:checks.append((target,'通过' if d['exit']==0 else ('阻塞' if d.get('classification')=='environment-blocked' else '失败'),'原Makefile目标，退出'+str(d['exit']),f'logs/{target}.txt'))
for i,state,actual,evidence in checks:cases.append(dict(用例编号=i,轮次=ROUND,关联需求='security-hardening/复测整改证据',前置条件='隔离Compose/合成账号；详见运行入口',输入与操作='scripts/qa/lesson9/run_fix_validation.py及原make目标',预期结果='原门槛不变，失败非零',实际结果=actual,状态=state,执行时间=NOW,被测提交=validation['baseline']+' + code-fingerprint.json',证据位置='fix-round/'+evidence))
csvsave(path,cases)
table='''# 测试代码归档核查

|用例或套件|脚本路径|运行入口/目录|版本|证据路径（本报告相对）|归档状态|
|---|---|---|---|---|---|
|全量接口/功能|scripts/verify.py|根目录 python scripts/verify.py|bd42a61；本轮+diff|fix-round/verify.md|原就在项目，tracked，原快照已存|
|隔离验收18项|scripts/acceptance.py；scripts/grade.sh|make grade|同上|fix-round/grade-attempts/；历史qa/lesson9/retest-02/recovery/acceptance/report.json|tracked；包装器history/session-final存档|
|20次性能原采样|scripts/async_test.py|verify调用run|bd42a61|qa/lesson9/retest-02/recovery/performance-observation.json|tracked；179.6ms原样保留|
|新增同口径探针|scripts/qa/lesson9/performance_probe.py；check_performance.py|根目录按README运行|本轮未提交指纹|fix-round/performance-1.json、performance-2.json|新增，untracked，非历史重建|
|Playwright|frontend/e2e/assignments.spec.ts、xss-materials.spec.ts|frontend/e2e: npm ci; npx playwright test|bd42a61+依赖diff|fix-round/logs/playwright.txt|tracked原件及history快照；实际文件清单见inventory|
|API防御性反例|apitest/cases/api/**/case.json；scripts/security_cases.py、security_test.py|verify/安全静态入口|bd42a61|fix-round/verify.md、logs/static.txt|tracked；未归档凭据|
|Go单元|backend/internal/**/*_test.go|make check中go test ./...|bd42a61（backend未修改）|make check输出或历史官方容器日志|tracked及快照|
|历次会话包装器|scripts/qa/lesson9/history/session-final/qa/lesson9/**.py|原执行命令见qa/lesson9/**/execution.json、历史日志|最终落盘版本|history/inventory.json逐文件SHA256|原在项目qa目录，现复制到既有scripts目录；untracked待提交|

原脚本缺失：早期acceptance_run/run_online包装器被原地修订的执行版本、未保存为文件的一次性命令片段；仅最终版本和日志仍在。没有把重新编写内容冒称历史源码，也未重建缺失版本。原课程第9课独立首测清单仍未单独找回；第8课安全首测脚本week8_security.py等已找回并归档，不将开发11月17日报告冒充独立首测。

历史已有源共53份，完整原路径/状态/哈希见scripts/qa/lesson9/history/inventory.json。包含找回的第8课独立交叉复核runner.py。当前历史副本与新增脚本都在独立工作树内，均未git add，不删除旧工作树。快照不可直接在快照目录运行：相对ROOT仍按原位置设计；执行当前原入口或新的README步骤。
'''
(P/'测试代码归档清单.md').write_text(table,encoding='utf-8')
section=f'''## 本轮整改与测试代码归档（{NOW}）

最新结论：**尚未完成整改验收**。基线{validation['baseline']}，分支change/2026-11-18-fix-lesson9-retest，所有修改未提交；实际运行差异见fix-round/code-diff.patch与code-fingerprint.json。没有修改backend代码，测试使用同一已验证官方后端镜像。

- 历史测试源{len(inventory)}份已在清理前核对并复制到scripts/qa/lesson9/history；新增代码及旧包装器版本缺口见[归档清单](测试代码归档清单.md)。全部需要git add的路径见fix-round/提交文件清单.txt。
- L9-DEP-001：Vite8.3.8/React插件6.3.0兼容更新及锁文件已落地，原Dockerfile npm ci/build、原verify与2条Playwright通过；最终官方npm审计仍high5/critical0。拒绝Vite6.2.7降级，因为它仍有其他高危。registry picomatch最高4.0.7仍受影响；没有使用force/假安全override，不宣布修复完成。五条high属于同根传递影响，缺陷表逐条保留。
- 性能：原179.6ms保留；本轮2×20完整202样本，max253.72/349.70ms，超100ms各2/1。API相关耗时178/249/346ms，客户端额外开销约4–7ms；不能单纯归为客户端网络。采样后获取SQL摘要时原verify已重建DB，故该快照不能用于归因采样窗口。检查了连接池、事务、outbox/worker并发与客户端/API计时，尚无确证瓶颈，不盲改业务逻辑。100ms严格检查退出1。原verify自身20次另观测435.0ms，P95=86.1ms满足500ms但单次仍不满足100ms。
- 原verify全部断言通过；Playwright两条（作业页与XSS页面源码）通过，新页面源码产物reports/xss-page-source.md；本轮没有正式录像或真人代签。原make结果见下方summary，不把工具链构建成功冒充目标通过。
- 三个原make目标最新结果：check退出0；check-security退出2（子audit退出1，high5）；grade最终退出0、18/18。前三次grade环境/构建失败单独保留，最终配置只向构建阶段传下载代理。

```json
{json.dumps(summary,ensure_ascii=False,indent=2)}
```

保留此前所有失败/阻塞与补跑记录；本节和本轮CSV行是最新状态，不用总历史执行次数作为独立用例通过率。尚缺：上游安全依赖或独立工具链迁移方案、性能根因及<=100ms修复、真人独立复现2条和正式录像。复现/录屏操作见fix-round/复现与录屏清单.md。未发布或推送。
'''
report=P/'复测报告.md';text=report.read_text(encoding='utf-8');marker='## 本轮整改与测试代码归档（';text=text.split(marker)[0];report.write_text(text+'\n'+section,encoding='utf-8')
idx=P/'证据索引.md';text=idx.read_text(encoding='utf-8');marker='## 测试源码与本轮整改';text=text.split(marker)[0];idx.write_text(text+'\n'+marker+'\n\n[测试代码归档清单](测试代码归档清单.md)逐项列出套件→源码→入口→版本→输出→状态。原脚本SHA256在scripts/qa/lesson9/history/inventory.json；本轮源码指纹、差异、审计、性能、make结果在fix-round/。早期被覆盖包装器版本缺失，不冒充已找回。\n',encoding='utf-8')
(B/'返工记录.md').write_text('''# 本次实际返工

1. 依赖：显式试验Vite6.2.7/plugin5.2.0，audit仍1个high且含其他公告；拒绝该方案，改同主版本8.3.8/6.3.0。后者high5仍未清零；没有可兼容安全picomatch发布。详见三份audit及dependency日志。
2. 性能：按原采样协议新增request_id关联，确认慢样本服务端也慢；未取得原采样窗口SQL明细，未猜测性修改业务代码。
3. 规约：新change首次结构校验失败，补齐章节、失败路径、专属规则和编号后strict重跑通过，保留日志。LF属性保留原archive规则。
4. 原make环境：真实GNU make容器中check成功、security因high5失败。grade首次把下载代理注入运行时，健康检查502；补NO_PROXY后busybox wget仍走代理，用wget -Y off确认API ready。取消代理后build直连失败，最终改为Compose build.args只在构建阶段传代理，运行时不注入，原make grade 18/18通过。全部失败与成功报告在grade-attempts/，配置源都保留在scripts/qa/lesson9/。

真实本轮运行窗口见validation.json（10:26:57–10:33:12）；依赖定位/尝试时间按audit文件时间及工具日志核对。没有逐步骤人工计时，故定位/修复各用时记为未独立计时，不能编造分钟数。不是历史开发返工耗时的替代。
''',encoding='utf-8')
(B/'复现与录屏清单.md').write_text('''# 组员复现与正式录屏

先在该独立工作树审阅diff和锁文件；不提交.env或临时凭据。

1. Docker Desktop开启，代理可访问官方镜像源。按scripts/qa/lesson9/README.md构建工具镜像/隔离环境；原make目标结果必须逐条保存。
2. 另一位真人独立复现SEC03：学生修改技能得到403，教师读取配置核对不变，再按学生+时间窗查denied；SEC04：跨班提交经技能及直接入口404，数据库task/result/outbox前后不变。每条填手段/查了什么/判据/结果及本人日期签名。
3. 录屏：登录取会话→/assignments提交返回202→显示pending/running/succeeded→换另一班访问材料404；只展示脱敏状态，不录口令、token或Cookie；补桌面/移动端检查。
4. 依赖修复后重跑npm ci、npm audit、build、Playwright；性能按原20次，不删超限样本。当前high5和100ms失败需保留，不能录成“全绿”。

本轮自动Playwright已执行两条，正式录像和真人独立签字仍未完成。
''',encoding='utf-8')
candidate=subprocess.check_output(['git','-c','core.quotePath=false','status','--short','--untracked-files=all'],cwd=R,text=True,encoding='utf-8');(B/'提交文件清单.txt').write_text(candidate,encoding='utf-8')
manifest={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in [R/'scripts/qa/lesson9',B] for p in folder.rglob('*') if p.is_file() and p.name!='manifest.json' and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.tar']}
(B/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');assert all(hashlib.sha256((R/k).read_bytes()).hexdigest()==h for k,h in manifest.items())
print(json.dumps(dict(sources=len(inventory),new_cases=len(checks),make=make,conclusion=summary['conclusion']),ensure_ascii=False))
