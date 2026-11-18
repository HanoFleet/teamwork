import pathlib,json,csv,collections,subprocess,datetime,hashlib,shutil
B=pathlib.Path(__file__).resolve().parent
R=B.parent/'test-main';ROOT=B.parents[2];O=ROOT/'reports/lesson9-20261118/retest-02';O.mkdir(parents=True,exist_ok=True)
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
V=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
cmds=json.loads((B/'execution.json').read_text(encoding='utf-8'))
for name in ['security-precheck.md','security-fix-log.md','sec08-experiment.md','govuln-disposition.md','xss-page-source.md','README.md']:
 shutil.copyfile(R/'reports'/name,B/'sources'/name)
shutil.copyfile(R/'docs/verification.md',B/'sources/developer-verification.md')
def git(*args):return subprocess.check_output(['git',*args],text=True).strip()
version=dict(recorded_at=now,fetch='success',origin=git('remote','get-url','origin'),original_branch=git('branch','--show-current'),original_head=git('rev-parse','HEAD'),origin_main=git('rev-parse','origin/main'),tested=V,previous_attempt='2026-11-18 08:31–08:36 +08:00 / '+V,fixes={h:dict(commit=git('rev-parse',h),in_main=subprocess.run(['git','merge-base','--is-ancestor',h,'origin/main']).returncode==0) for h in ['7263dda','090ca01','cfe7e74']},worktree_status=subprocess.check_output(['git','status','--porcelain'],cwd=R,text=True).strip(),new_frontend_fix='not found; frontend lockfile unchanged since previous attempt')
version['fetched_at']=datetime.datetime.fromtimestamp((ROOT/'.git/FETCH_HEAD').stat().st_mtime,datetime.timezone(datetime.timedelta(hours=8))).isoformat()
(B/'version.json').write_text(json.dumps(version,ensure_ascii=False,indent=2),encoding='utf-8')
audit=json.loads((B/'logs/audit.txt').read_text(encoding='utf-8'));events=[]
for l in (B/'logs/go.txt').read_text(encoding='utf-8').splitlines():
 try:events.append(json.loads(l))
 except ValueError:pass
go=collections.Counter(e['Action'] for e in events if e.get('Test') and e.get('Action') in ['pass','fail','skip'])
rows=[]
for e in cmds:
 rows.append(dict(用例编号='G-'+e['id'],关联需求='项目既有防御性门禁/回归',前置条件='独立工作树 '+V,输入与操作=' '.join(e['command']),预期结果='退出0；audit高危及严重均0',实际结果=f"退出{e['exit']}"+(f"；{dict(go)}" if e['id']=='go' else ''),状态='通过' if e['exit']==0 else ('失败' if e['id']=='audit' else '阻塞'),证据位置=e['evidence'],执行时间=e['started'],被测提交=V))
blocked=[('ENV','隔离验收','运行既有acceptance.py，项目campusclaw-l9-retest02','Compose构建启动并执行18项','Docker29.8.0已恢复；golang:1.26.11-alpine从Docker Hub拉取超时','acceptance/report.json'),('SEC-01','认证','沿用受保护路由清单','无认证全部401'),('SEC-02','班级隔离','沿用A/B班访问与检索对照','跨班404/空；同班正常'),('SEC-03','配置授权','沿用学生写技能与助手配置及数据前后对照','403且数据不变'),('SEC-04','写入归属','沿用直接批改入口/技能入口与无残留核对','拒绝他人提交且无新增结果'),('SEC-07','审计','沿用技能调用与学生+时间窗查询','七列、denied与学生查询拒绝'),('SEC-08','四步实验','沿用恶意讲义和三条提问','前三步留现象；第四步拒绝留日志'),('INJECTION','在线注入回归','沿用项目防御性SQLi/XSS/CSRF套件','反例绿、页面源码转义'),('ASYNC','异步三判据','执行项目既有三条判据','符合202/P95、恢复及幂等判据'),('DEMO','四步演示与录像','登录→202→状态→跨班404','四步通过，录像可复核')]
for item in blocked:
 i,req,op,expect,*rest=item
 rows.append(dict(用例编号=i,关联需求=req,前置条件='被测提交的隔离Compose健康、A/B班预置账号数据',输入与操作=op,预期结果=expect,实际结果=rest[0] if rest else '环境构建未成功；未发业务请求，历史结果不代替本轮',状态='阻塞',证据位置='acceptance/report.json',执行时间=now+'（记录时间；业务请求未执行）',被测提交=V))
def csvwrite(p,data):
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
csvwrite(B/'用例执行表.csv',rows)
defects=[]
for i,old in [('SEC-03','无配置写入口'),('SEC-04','无技能链，原检查部分执行'),('SEC-07','缺操作人/技能标识/用量语义')]:
 defects.append(dict(缺陷编号=i,首测来源='第8课延续红项；未发现独立第9课首测清单',原失败用例=i,首次提交='292eaaff+历史未提交修改；并非纯提交',首次实际=old,首次证据='../sources/local-week8-security-precheck.md；原reports/evidence/week8/',修复提交=version['fixes']['7263dda']['commit'],补证提交=version['fixes']['090ca01']['commit'] if i=='SEC-07' else '',修复PR='本地无对应PR信息；以Git提交归属核验',实际复测提交=V,执行时间=now,预期={'SEC-03':'学生403且配置不变','SEC-04':'直接与技能写入拒绝且无残留','SEC-07':'七列审计和学生时间窗denied查询'}[i],实际='源码修复在main；防御性静态及Go回归通过；镜像拉取失败，未在线复现',复测状态='复测阻塞',本轮证据='logs/static.txt；logs/go.txt；acceptance/report.json',所需材料='恢复Docker Hub镜像访问，执行原用例、数据库对照与审计查询'))
defects.append(dict(缺陷编号='L9-DEP-001',首测来源='上次独立复测新发现，不是已确认的第9课首测缺陷',原失败用例='SEC-06',首次提交=V,首次实际='2026-11-18 08:32 官方npm审计high5 critical0',首次证据='../logs/npm-audit-retry.json',修复提交='',补证提交='',修复PR='尚未提供或在远程定位到',实际复测提交=V,执行时间=next(x['started'] for x in cmds if x['id']=='audit'),预期='high0 critical0或逐漏洞处置登记',实际='同版本重跑audit退出1；high5 critical0。cfe7e74仅改Go依赖及工具链，不是此缺陷修复',复测状态='待确认修复版本',本轮证据='logs/audit.txt；sources/frontend-dependency-history.txt',所需材料='提供针对前端依赖的PR/分支/提交或处置登记；当前版本失败不能关闭'))
csvwrite(B/'缺陷复测表.csv',defects)
fixpaths={
 'SEC-03':'backend/internal/httpapi/config.go; backend/internal/catalog/catalog.go; scripts/security_test.py',
 'SEC-04':'backend/internal/httpapi/skill.go; backend/internal/httpapi/grading.go; backend/internal/grading/service.go; backend/internal/grading/store.go; scripts/security_test.py',
 'SEC-07':'backend/internal/httpapi/audit.go; backend/internal/audit/audit.go; backend/internal/httpapi/config.go; scripts/security_test.py',
 'L9-DEP-001':'frontend/package.json; frontend/package-lock.json（未定位到修复变更）'
}
for d in defects:
 d['修复文件路径']=fixpaths[d['缺陷编号']]
 d['防御性核验']='本轮静态检查及源码配置审查通过；数据库/HTTP仍未执行' if d['缺陷编号']!='L9-DEP-001' else '官方npm审计失败；cfe7e74为Go修复，与前端漏洞无关'
 if d['缺陷编号']=='SEC-04':d['底层归属校验提交']='4f8414285f7ff7508f6b2658e58734c32d4b4d52（第8课既有）；7263dda增加技能复用'
 else:d['底层归属校验提交']=''
csvwrite(B/'缺陷复测表.csv',defects)
summary=dict(version=V,checks=dict(collections.Counter(r['状态'] for r in rows)),defects=dict(collections.Counter(r['复测状态'] for r in defects)),go_tests=dict(go),npm=audit['metadata']['vulnerabilities'],acceptance='ENV failed; classified blocked (not 18 business failures)')
(B/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
report=f'''# 第9课第二轮独立复测报告

结论：尚未通过验收。实际复测版本 `{V}`。记录时间 {now}（Asia/Shanghai），各命令起止时间见execution.json。本轮复用干净独立工作树qa/lesson9/test-main，未覆盖原分支、业务代码和未提交材料。无发布、推送或平台填报。

## 版本与首测身份

origin为HanoFleet/teamwork，git fetch origin成功，main仍为上述提交，与08:36的上次尝试相同。远程可见分支没有定位到针对本轮新发现的修复。完整SHA及祖先关系见version.json。已请求组员提供修复PR/分支/提交，未拿到前不假定已修复。

可确认的历史基线是第8课SEC-03/04/07红项（含功能缺失阻塞），来源reports/security-precheck.md及原week8证据；2026-11-17的远程security-fix-log.md是开发方修复复跑，不能认作独立首测。2026-11-18 08:31–08:36的qa/lesson9/是上次独立复测尝试，L9-DEP-001在该轮新发现。未查到另一份含独立日期、首测提交和缺陷号的第9课首测清单，因此不声称已覆盖未知首测缺陷；请补该清单及原证据。PR/缺陷单无法从本地材料确认编号，本轮以提交内容和祖先关系核验，不把历史API空列表当新证据。

7263dda实现配置、受控技能与审计，090ca01补学生/时间窗核对；均为main祖先。cfe7e74升级Go工具链及Go模块，未改变前端依赖；不是L9-DEP-001的修复。前端lockfile历史及修复diff见sources/。

## 本轮实际结果

```json
{json.dumps(summary,ensure_ascii=False,indent=2)}
```

逐条缺陷结果：SEC-03、SEC-04、SEC-07均复测阻塞；L9-DEP-001待确认修复版本，当前版本实测依然失败。审计中5个high依赖条目包括传递影响，不等同5个独立漏洞。详情、公告URL、范围和修复建议见logs/audit.txt。

Go测试、vet、实时govulncheck（No vulnerabilities found）、规约/规范/分层/安全静态/反例结构/密钥扫描、strict和门禁红绿自测均在本轮执行。Go计32条终态通过，独立统计，不累计为检查行。缺make使make check入口阻塞，组件通过不等于入口通过。红绿自测证明拦截能力，当前npm仍失败，不宣称正常安全门禁绿。

Docker Desktop从不可连接恢复到29.8.0。实际启动了仓库acceptance.py的隔离构建，专属项目campusclaw-l9-retest02；拉取golang:1.26.11-alpine时Docker Hub连接超时，构建失败，未进入业务用例。已清理专属资源和临时.env.retest02。acceptance/report.json的ENV failed在用例表计为环境阻塞，不计作18条业务失败。没有本轮HTTP响应、截图或录像。在线安全项目仅引用既有防御性检查、配置源码和历史修复记录作辅助，仍待人工运行验证；未将静态通过视作授权复测通过。

统计单位为执行表检查行；通过率只计算有效判定行，通过/(通过+失败)，见summary.json；阻塞排除。缺陷状态与用例状态分表，不能相加。未关闭任何缺陷。新旧执行表独立保留。

## 证据与可提交材料

本轮数据：[用例表](用例执行表.csv)、[缺陷表](缺陷复测表.csv)、[证据索引](证据索引.md)、[课程要求映射](课程要求映射.md)。完整日志位于qa/lesson9/retest-02/，版本见version.json；保留每条命令、时间、退出码和SHA256。

课程原文已从上轮保存的两课HTML读取（sources/lesson8.*、lesson9.*）；报告名称、字段和根reports位置已核对。新增本轮报告位于reports/lesson9-20261118/retest-02/，根指定文件追加本轮链接，不改历史判定。首轮和上次尝试保持原样。本轮可提交的是带阻塞与失败结论的报告和证据，不能作为全绿验收证明。课程没有提供额外教学平台填报地址；发布由用户确认。

## 仍需补齐

- 第9课独立首测清单及组员本次修复版本，尤其L9-DEP-001；当前main未更新。
- Docker Hub网络/代理或准确工具链镜像，make/sh；恢复后跑三组回归、SEC-01～08、原失败用例及相邻功能。
- XSS页面源码与四步演示录像，另一位真人独立复现至少2条、真实返工定位与修复耗时。11月17日开发历史记录可参考，不冒充本轮产物或真人签名。
'''
def write(name,content):
 (B/name).write_text(content,encoding='utf-8');(O/name).write_text(content,encoding='utf-8')
write('复测报告.md',report)
review='''# 按组员指定路径追加的修复定位与防御性复核

本次没有要求额外PR才核验：直接以security-fix-log.md、security-precheck.md、实际代码及Git提交为依据。应用代码、scripts、apitest/cases、CI/Makefile、docs/openspec与reports均已核对。递归报告文件清单及提交证据见qa/lesson9/retest-02/sources/path-review.txt。

|编号|修复文件|提交|本次核验结论|仍需验证|
|---|---|---|---|---|
|SEC-03|backend/internal/httpapi/config.go、internal/catalog/catalog.go|7263dda211139292a7ff8f7539ed25429a9da983|patchSkill/patchAssistant在写入前检查teacher；助手使用会话ClassID；拒绝路径记录审计；防御性源码核验通过|原用例HTTP403、配置前后值与审计落库|
|SEC-04|backend/internal/httpapi/skill.go、grading.go；internal/grading/service.go、store.go|7263dda211139292a7ff8f7539ed25429a9da983；底层4f8414285f7ff7508f6b2658e58734c32d4b4d52|技能调用复用EnqueueGrade；服务核对StudentID与ClassID后才调用store；普通批改入口复用同服务；score不进入技能请求结构；防御性源码核验通过|原直接入口及技能入口拒绝，task/outbox/result无残留|
|SEC-07|backend/internal/httpapi/audit.go、internal/audit/audit.go；scripts/security_test.py|7263dda211139292a7ff8f7539ed25429a9da983；090ca01a08598e099905b3272ee5907bfb02c7ac|审计结构含操作人、UTC时间、类型、对象、状态、技能、用量/耗时；教师查询使用会话班级，学生拒绝；脚本补operator_id和时间窗；防御性源码核验通过|真实调用及403后按学生/时间窗查库|
|SEC-08|docs/lesson-09/sec08/；reports/sec08-experiment.md；skill.go|7263dda211139292a7ff8f7539ed25429a9da983|历史11月17日15:19:40记录四步；当前写入权限仍走上述服务，素材存在|本轮四步现象、工具拒绝及审计在线验证|
|L9-DEP-001|frontend/package.json、package-lock.json|未定位修复|前端lockfile未有本轮新变更；当前audit高危5条，仍失败；Go处置cfe7e74不能替代前端处置|组员仅需补这一缺陷的修复PR/分支/提交，或逐漏洞处置登记|

全部已知修复提交均为bd42a6149e975c1ed217fb9349621443a3be53d5祖先。代码核验只证明防御路径存在，不等价于业务/数据库执行成功。原失败功能用例仍受准确工具链镜像拉取超时阻塞。已有本轮32条Go测试通过不覆盖未运行的在线用例。

reports/review-02.md、review-03.md、e2e-playwright.md、xss-page-source.md、govuln-disposition.md、govuln-snapshot.txt和gate-red-green.md均在被测main中存在；它们的历史执行日期和版本范围保留，不作为新复测输出。没有将AI记录当真人签字。
'''
write('修复定位与防御性复核.md',review)
for p in [B/'复测报告.md',O/'复测报告.md']:
 p.write_text(p.read_text(encoding='utf-8')+'\n## 按用户指定路径补充定位\n\n已完成[逐条文件与提交复核](修复定位与防御性复核.md)，缺陷复测表增加修复文件路径、防御性核验和底层提交字段。SEC03/04/07已定位，无需组员另给PR；仅L9-DEP-001未定位修复。在线结果与阻塞状态保持如实记录。\n',encoding='utf-8')
for f in ['用例执行表.csv','缺陷复测表.csv','summary.json']:shutil.copyfile(B/f,O/f)
write('课程要求映射.md','''# 第9课要求 → 本轮工作 → 证据 → 状态

|课程项|本轮工作|证据|状态|
|---|---|---|---|
|一 基线与红项分类|区分第8课红项、开发11月17日复跑、上次独立尝试|复测报告/version.json、sources/|部分完成；缺独立第9课首测清单|
|二 授权SEC01～04|修复祖先核验、配置/技能源码与静态检查|sources/fix-*、logs/static.txt|在线复测阻塞|
|三 注入三件套|项目既有反例结构和静态检查通过|logs/cases.txt、logs/static.txt|在线/页面源码待验证|
|四 资产05～06|密钥0命中、Go实时扫描0、npm high5|logs/secrets.txt、govuln.txt、audit.txt|失败；前端修复待定位|
|四 门禁红绿|本轮假密钥红1/绿0、自测整体0|logs/gate-self-test.txt|自测完成；正常安全门禁未绿|
|五 日志与SEC08|核对审计修复和历史实验，未复用为本轮通过|sources/security-fix-log.md、sec08-experiment.md|待在线及人工验证|
|六 三组回归/演示|Go32通过、vet通过；实际隔离构建失败|logs/go.txt、vet.txt、acceptance/report.json|部分完成；演示录像缺|
|六 归档与返工|独立本轮目录、指定根报告追加链接|reports/lesson9-20261118/retest-02/|证据已备；真实返工耗时缺|
|七 交叉评审|两份本轮脚本检查记录|review-06.md、review-07.md|真人独立2条缺；不签字代替|
''')
write('证据索引.md','''# 本轮证据索引

所有本轮原始文件位于 `qa/lesson9/retest-02/`（仓库根相对路径）。

- version.json：fetch结果、提交归属、工作树清洁状态。
- execution.json：命令、起止时间、退出码；logs/*.txt：对应完整输出。
- acceptance/report.json、report.html：Docker Hub镜像拉取失败，尚未进入业务验收；acceptance.exit.txt为退出码。
- sources/：两课课程原文副本、开发历史报告、修复diff和前端lockfile历史。来源为上轮原文缓存和被测main，非本轮在线成功证据。
- 上次尝试：qa/lesson9/缺陷复测表.csv、qa/lesson9/logs/npm-audit-retry.json；原基线：qa/lesson9/sources/local-week8-security-precheck.md。
- manifest.json：本轮证据SHA256；不包含业务工作树、临时凭据及自身。

缺少业务截图、录像及本轮在线原失败用例输出；不以占位截图替代。
''')
write('review-06.md','手段：既有防御性静态/规约/规范/分层/反例结构与strict。查了什么：安全修复边界及用例结构。判据：退出0。结果：通过，详见execution.json；静态范围，非真人在线复现。\n')
write('review-07.md','手段：Go test/vet、实时govulncheck、npm audit与门禁自测。查了什么：依赖和回归。判据：测试0、漏洞high/critical0。结果：Go32通过、vet及Go审计通过，npm high5失败；本轮阻断验收。这是脚本/AI记录，不是真人签字。\n')
for name in ['security-fix-log.md','security-baseline.md','sec08-experiment.md','gate-red-green.md']:
 target=ROOT/'reports'/name
 if not target.exists():shutil.copyfile(R/'reports'/name,target)
 text=target.read_text(encoding='utf-8');marker='## 2026-11-18 独立复测第二轮'
 if marker not in text:target.write_text(text+'\n\n'+marker+'\n\n本轮尚未通过：SEC-03/04/07在线复测阻塞；L9-DEP-001当前npm high5，修复版本待确认。Docker已恢复，镜像拉取超时。Go32通过及实时Go漏洞扫描0。详见[本轮复测报告](lesson9-20261118/retest-02/复测报告.md)，历史记录保留。\n',encoding='utf-8')
for n in ['review-06.md','review-07.md']:
 t=ROOT/'reports'/n
 if not t.exists():shutil.copyfile(O/n,t)
idx=ROOT/'docs/lesson-09/qa-20261118.md';text=idx.read_text(encoding='utf-8');marker='## 第二轮独立复测'
if marker not in text:idx.write_text(text+'\n'+marker+'\n\n[本轮报告](../../reports/lesson9-20261118/retest-02/复测报告.md)；[缺陷复测表](../../reports/lesson9-20261118/retest-02/缺陷复测表.csv)。版本仍bd42a614。Docker已恢复，镜像拉取超时；SEC03/04/07阻塞，L9-DEP-001待确认修复版本且当前审计仍失败。\n',encoding='utf-8')
manifest={str(p.relative_to(B)):hashlib.sha256(p.read_bytes()).hexdigest() for p in B.rglob('*') if p.is_file() and p.name!='manifest.json'}
(B/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
assert len(rows)==sum(summary['checks'].values());assert len(defects)==sum(summary['defects'].values());assert version['worktree_status']==''
print(json.dumps(summary,ensure_ascii=False))
