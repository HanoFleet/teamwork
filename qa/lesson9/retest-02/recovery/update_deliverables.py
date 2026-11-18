import pathlib,json,csv,collections,hashlib,datetime,shutil,re
B=pathlib.Path(__file__).resolve().parent;P=B.parent;ROOT=B.parents[3];O=ROOT/'reports/lesson9-20261118/retest-02';V='bd42a6149e975c1ed217fb9349621443a3be53d5';ROUND='第二轮环境恢复补跑'
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat();status=json.loads((B/'status.json').read_text(encoding='utf-8'));supp=json.loads((B/'supplement-result.json').read_text(encoding='utf-8'))
def readcsv(p):
 with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def writecsv(p,rows):
 fields=list(dict.fromkeys(k for r in rows for k in r))
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
defect_path=P/'缺陷复测表.csv';old=readcsv(defect_path)
if not (B/'defects-before.csv').exists():shutil.copyfile(defect_path,B/'defects-before.csv')
base=[r for r in old if r.get('轮次')!=ROUND];latest=[]
for r in base:
 if r['缺陷编号'] in {x['缺陷编号'] for x in latest}:continue
 n=dict(r);n['轮次']=ROUND;n['执行时间']=now;n['实际复测提交']=V;n['本轮证据']='qa/lesson9/retest-02/recovery/security-prioritized.md；verify.md；supplement-result.json'
 if n['缺陷编号'] in ['SEC-03','SEC-07']:
  n['复测状态']='复测通过' if status.get('security_prioritized')==0 else '复测失败'
  n['实际']='原安全套件实测通过；403/数据不变、教师配置、跨班404及学生时间窗denied核对' if n['缺陷编号']=='SEC-03' else '原安全套件实测通过；教师技能查询七列、学生查询403'
 elif n['缺陷编号']=='SEC-04':
  passed=status.get('security_prioritized')==0 and supp.get('SEC04_direct',{}).get('passed')
  n['复测状态']='复测通过' if passed else '复测失败';n['实际']='技能入口本人202、他人/教师404；补跑直接批改入口跨班404，与不存在同形，task/result/outbox前后均无新增'
 else:
  n['复测状态']='待确认修复版本';n['实际']='沿用本轮logs/audit.txt：high5、critical0；本次未发现依赖修复版本，不关闭，不冒充再次审计';n['本轮证据']='qa/lesson9/retest-02/logs/audit.txt'
 latest.append(n)
writecsv(defect_path,base+latest);shutil.copyfile(defect_path,O/defect_path.name)
casespath=P/'用例执行表.csv';cases=readcsv(casespath)
if not (B/'cases-before.csv').exists():shutil.copyfile(casespath,B/'cases-before.csv')
cases=[r for r in cases if r.get('轮次')!=ROUND]
items=[('IMAGE','官方同版本镜像恢复','通过','官方清单与全层SHA256/diff_ids校验后docker load成功','official-manifest.json；logs/image-load.txt'),('BACKEND-BUILD','原后端Dockerfile','通过','原Dockerfile构建成功，Go1.26.11','logs/official-backend-build.txt'),('FRONTEND-BUILD','原前端Dockerfile','通过','npm ci和build成功，Node22 Alpine','logs/official-frontend-build.txt'),('GO','官方Go容器test/vet','通过','原版golang:1.26.11-alpine中go test与go vet退出0','logs/official-go-test.txt'),('MUTATION','变异门禁','通过','退出0','logs/mutation.txt'),('FORMAT','提交原始blob格式','通过','54份Go原始blob格式差异0；Windows工作树54份CRLF另记','logs/format-git-blobs.json'),('ACCEPTANCE','项目18项隔离验收','通过','18通过、0失败','acceptance/report.json'),('SEC-03','原配置授权失败用例','通过' if status.get('security_prioritized')==0 else '失败','学生403且数据不变，教师成功；跨班404；时间窗denied','security-prioritized.md'),('SEC-04','原技能入口与直接入口','通过' if supp.get('SEC04_direct',{}).get('passed') and status.get('security_prioritized')==0 else '失败','本人202、他人/教师404；直接跨班404且无残留','security-prioritized.md；supplement-result.json'),('SEC-07','七列审计与查询授权','通过' if status.get('security_prioritized')==0 else '失败','教师按skill_key查七列，学生403','security-prioritized.md'),('INJECTION','项目防御性SQLi/XSS/CSRF','通过' if status.get('security_prioritized')==0 else '失败','三件套原脚本断言通过；XSS本轮为JSON/源码静态范围','security-prioritized.md'),('VERIFY','原verify全量含三条异步判据','通过' if status.get('verify')==0 else '失败',str(status.get('verify')),'verify.md；logs/verify-final.txt'),('SEC-08','原四步实验','通过' if supp.get('SEC08')==0 else '失败','原脚本四步实际现象已归档；第四步拒绝并留审计','sec08-sandbox/reports/sec08-experiment.md')]
verify_text=(B/'verify.md').read_text(encoding='utf-8');sample=re.search(r'P95=([0-9.]+)ms.*times=(\[[^\]]+\])',verify_text)
performance={}
if sample:
 times=json.loads(sample.group(2));performance=dict(p95_ms=float(sample.group(1)),max_ms=max(times),default_single_request_limit_ms=100,over_limit_count=sum(t>100 for t in times),samples_ms=times)
 (B/'performance-observation.json').write_text(json.dumps(performance,indent=2),encoding='utf-8')
 items.append(('PERF-OBS','04-testing默认单次100ms判据','失败' if performance['over_limit_count'] else '通过',f"P95={performance['p95_ms']}ms满足async500ms；max={max(times)}ms，{performance['over_limit_count']}条超过默认100ms。需记录环境调整或处置，不直接宣称全规范通过",'performance-observation.json'))
newcases=[]
for i,req,state,actual,evidence in items:
 newcases.append(dict(用例编号=i,关联需求=req,前置条件='专属Compose；官方后端镜像、隔离测试账号；版本'+V,输入与操作='项目既有入口或原用例；见对应日志和recovery脚本',预期结果='符合原用例可观测判据，退出0',实际结果=actual,状态=state,证据位置='qa/lesson9/retest-02/recovery/'+evidence,执行时间=now+'（本批记录时间；原始日志记录执行过程）',被测提交=V,轮次=ROUND))
writecsv(casespath,cases+newcases);shutil.copyfile(casespath,O/casespath.name)
summary=dict(version=V,recorded_at=now,round=ROUND,new_check_rows=dict(collections.Counter(r['状态'] for r in newcases)),latest_defects=dict(collections.Counter(r['复测状态'] for r in latest)),acceptance='18/18',verify=status.get('verify'),security_prioritized=status.get('security_prioritized'),supplement=supp,dependency='high5 critical0; retained audit, no dependency fix located')
summary['performance_observation']=performance
(B/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
text=f'''## 环境恢复与实际补跑（{now}）

本节为最新结果；前文的历史阻塞及旧统计保留，不代表当前状态。实际提交仍为 `{V}`。原分支与未提交改动保留。

### 镜像与网络定位

原命令是docker compose build，失败镜像为docker.io/library/golang:1.26.11-alpine，仓库registry-1.docker.io。Docker Desktop29.8.0及守护进程正常。直连DNS返回异常/不稳定地址，请求在TCP443阶段超时，尚未到仓库鉴权或标签检查。Docker内部代理显示http.docker.internal:3128，但错误明确走无外部HTTPS代理的直连。通过本机已有127.0.0.1:7897代理，v2返回标准401挑战、匿名认证200且原标签清单可用，因此不是必须用户登录才能拉取的仓库。

官方Linux/amd64清单摘要为sha256:f496f8c537ed506626ee1a6913afb32c45068a48697163c088f604cc775a0c38。两次有限网络请求重试后，大层下载完毕而后续小层返回401，推测长传输导致匿名令牌过期；刷新匿名令牌，只补剩余小层。所有压缩层SHA256、解压diff_ids及配置摘要核对后导入同一官方镜像；没有使用第三方镜像源、替换标签或修改全局代理。原后端、前端Dockerfile现已成功构建。摘要及完整过程在recovery/official-manifest.json、logs/image-*.txt及official-*-build.txt。

另遇默认地址池耗尽：检查38个现有子网后，本轮仅使用不重叠10.243.91.0/24，不删除其他网络。verify重建后RabbitMQ的Erlang可响应但rabbit应用尚未就绪，原list_queues失败；环境包装器改等候check_running，再运行原断言。原两次未完成输出独立保留。最早网络失败尝试产生的0项passed报告是包装器未登记ENV异常的空报告，不能计为通过；错误及status记录才是该次依据。

make仍缺失；Git自带F:/Git/bin/sh.exe可用。按Makefile/CI逐项执行等效命令：原Dockerfile构建、官方Go容器test/vet、变异检查等。不声称make check原入口已通过。gofmt工作树检查列出54个文件，原因为core.autocrlf=true；用指定Go1.26.11检查54个Git原始blob格式差异0，工作树检查原输出保留。

最初18项验收使用同Go版本、同CGO/GOOS/trimpath参数的本机交叉编译产物及原版前端构建产物；随后SEC03/04/07与最终verify使用原Dockerfile构建的官方后端镜像。前端功能测试使用相同源码npm构建产物装入同nginx基础镜像；原前端Dockerfile构建另有成功日志，不把两种运行方式混写。

### 当前结果

```json
{json.dumps(summary,ensure_ascii=False,indent=2)}
```

缺陷表按“同编号最后一条”确定最新状态，旧阻塞行保留。用例表同样按轮次保留，不把重复执行次数计作独立能力覆盖。18项套件与新增检查行分别统计，不累加计算通过率。L9-DEP-001沿用本轮审计high5/critical0和待处置状态，本次没有新的依赖修复版本，未重复审计或关闭。

证据位于qa/lesson9/retest-02/recovery/：security-prioritized.md、verify.md、supplement-result.json、sec08-sandbox/reports/sec08-experiment.md、acceptance/report.json及logs/。摘要见summary.json，SHA256见manifest.json。没有将代码核验代替实际运行；没有真人代签或发布。

仍需：L9-DEP-001修复/可检查处置登记；真人独立复现至少两条；正式演示录像与真实返工耗时。XSS本轮实测覆盖JSON转义与源码静态检查，浏览器列表页源码/录像仍沿用历史材料，未宣称已新拍。原make入口及WindowsCRLF门禁差异仍需在与CI相同的Linux检出环境完整复现。大型镜像归档与二进制为本机缓存，不属于提交材料。
'''
for p in [P/'复测报告.md',O/'复测报告.md']:
 oldtext=p.read_text(encoding='utf-8');marker='## 环境恢复与实际补跑（'
 if marker in oldtext:oldtext=oldtext.split(marker)[0]
 p.write_text(oldtext+'\n\n'+text,encoding='utf-8')
index='\n## 环境恢复补跑证据\n\n最新结果见qa/lesson9/retest-02/recovery/summary.json；镜像摘要official-manifest.json；原Dockerfile构建logs/official-*-build.txt；功能用例security-prioritized.md、verify.md；直接批改入口supplement-result.json；四步实验sec08-sandbox/reports/sec08-experiment.md；18项验收acceptance/report.json。原失败和部分执行记录以attempt01/02及logs/online*.txt保留。\n'
for p in [P/'证据索引.md',O/'证据索引.md']:
 t=p.read_text(encoding='utf-8')
 if '## 环境恢复补跑证据' not in t:p.write_text(t+index,encoding='utf-8')
for p in [P/'课程要求映射.md',O/'课程要求映射.md']:
 t=p.read_text(encoding='utf-8');marker='## 环境恢复后更新'
 if marker not in t:p.write_text(t+'\n'+marker+'\n\n授权SEC03/04、日志SEC07：实际补跑通过；原注入防御性套件通过，列表页浏览器源码仍待新证据；18项验收通过；全量verify及SEC08以recovery/summary.json实际状态为准。镜像已恢复，make原入口仍缺失；资产前端高危未处置。真人复现、录像和真实返工仍缺。\n',encoding='utf-8')
for name in ['security-fix-log.md','security-baseline.md','sec08-experiment.md','gate-red-green.md']:
 p=ROOT/'reports'/name;t=p.read_text(encoding='utf-8');marker='## 环境恢复补跑'
 if marker not in t:p.write_text(t+'\n'+marker+'\n\n原Go镜像与前后端Dockerfile构建已恢复；SEC03/04/07补跑通过；18项验收通过。详细完整状态及SEC08见[最新报告](lesson9-20261118/retest-02/复测报告.md)和qa/lesson9/retest-02/recovery/summary.json。L9-DEP-001仍待处置；不将门禁自测当正常资产门禁绿。\n',encoding='utf-8')
idx=ROOT/'docs/lesson-09/qa-20261118.md';t=idx.read_text(encoding='utf-8');marker='## 第二轮环境恢复补跑'
if marker not in t:idx.write_text(t+'\n'+marker+'\n\n[最新实际结果](../../reports/lesson9-20261118/retest-02/复测报告.md)：原镜像恢复；SEC03/04/07实际通过；18项验收通过；全量verify与SEC08详见recovery/summary.json。原记录保留，L9-DEP-001未关闭。\n',encoding='utf-8')
excluded={'server','worker','ca-certificates.crt'}
manifest={str(p.relative_to(B)):hashlib.sha256(p.read_bytes()).hexdigest() for p in B.rglob('*') if p.is_file() and p.name not in excluded and p.suffix!='.tar' and 'dist' not in p.parts and p.name not in ['.env','manifest.json']}
(B/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
