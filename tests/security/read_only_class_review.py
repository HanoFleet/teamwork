# Archived read-only ownership review; explicit inputs replace machine-bound settings.
import argparse
from urllib.parse import urlsplit
_parser=argparse.ArgumentParser(description="Historical read-only SEC01/SEC02 cross-review; requires original fixture metadata")
_parser.add_argument('--base-url',required=True)
_parser.add_argument('--compose-project',required=True)
_parser.add_argument('--historical-evidence',required=True)
_parser.add_argument('--env-file',required=True)
args=_parser.parse_args()
import json, hashlib, re, subprocess, platform, sys, time, uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parents[2]; TZ=timezone(timedelta(hours=8))
RUN=datetime.now(TZ).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:6]
OUT=ROOT/'tests/output/cross-class-readonly-review'/RUN
OUT.mkdir(parents=True,exist_ok=False)
(OUT/'runner.py').write_text(Path(__file__).read_text(encoding='utf-8'),encoding='utf-8')
def now(): return datetime.now(TZ).isoformat()
def save(name,obj):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def command(name,args):
 t=now();p=subprocess.run(args,cwd=ROOT,capture_output=True,encoding='utf-8',errors='replace',timeout=90)
 d={'command':args,'cwd':str(ROOT),'started_at':t,'finished_at':now(),'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
 save('commands/'+name+'.json',d)
 if p.returncode:raise RuntimeError('Read-only command failed: '+name)
 return p.stdout.strip()
report_names=['security-precheck.md','risk-authz.md','risk-concurrency.md','risk-transaction.md','security-baseline.md']
report_hashes={n:hashlib.sha256((ROOT/'reports'/n).read_bytes()).hexdigest() for n in report_names}
meta={'executor':'Codex工具独立复核，非李同学或韩同学本人执行','started_at':now(),'run_id':RUN,'cwd':str(ROOT),'python':platform.python_version(),'base':args.base_url,'environment_choice':'复用已有configured-project，仅必要登录及读取；无材料/作业/队列写入，无停服务或重投','report_hashes_before':report_hashes}
meta['head']=command('git-head',['git','rev-parse','HEAD'])
meta['branch']=command('git-branch',['git','branch','--show-current'])
meta['git_status']=command('git-status',['git','status','--short'])
project=args.compose_project; api=project+'-api-1';db=project+'-db-1';web=project+'-web-1'
meta['compose_labels']=json.loads(command('api-labels',['docker','inspect','--format','{{json .Config.Labels}}',api]))
assert Path(meta['compose_labels']['com.docker.compose.project.working_dir']).resolve()==ROOT.resolve(),'wrong source directory'
assert meta['compose_labels']['com.docker.compose.project']==project
meta['web_binding']=command('web-port',['docker','port',web,'80/tcp'])
assert meta['web_binding']==urlsplit(args.base_url).netloc
meta['api_binary_sha256']=command('api-binary-sha256',['docker','exec',api,'sha256sum','/server']).split()[0]
meta['container_image_id']=command('api-image-id',['docker','inspect','--format','{{.Image}}',api])
old=json.loads((Path(args.historical_evidence)/'version-start.json').read_text(encoding='utf-8'))
meta['business_source_differences_from_original_run']=[name for name,digest in old['business_sha256'].items() if not (ROOT/name).exists() or hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest]
original_binary=json.loads((Path(args.historical_evidence)/'deployed-binary-sha256.json').read_text(encoding='utf-8'))
meta['api_binary_matches_original_run']=meta['api_binary_sha256']==original_binary['sha256']
def sql(name,query):
 assert query.lstrip().upper().startswith('SELECT ')
 return command(name,['docker','exec',db,'sh','-c','MYSQL_PWD="$MYSQL_PASSWORD" exec mysql -u"$MYSQL_USER" "$MYSQL_DATABASE" -N -B -e "$1"','cross-review-read-only',query])
counts='SELECT (SELECT COUNT(*) FROM materials),(SELECT COUNT(*) FROM knowledge_entries),(SELECT COUNT(*) FROM submissions),(SELECT COUNT(*) FROM grade_tasks),(SELECT COUNT(*) FROM outbox_messages),(SELECT COUNT(*) FROM grade_results)'
meta['business_table_order']=['materials','knowledge_entries','submissions','grade_tasks','outbox_messages','grade_results']
meta['business_counts_before']=sql('business-counts-before',counts)
raw_ids=sql('material-provenance',"SELECT m.id,m.class_id,c.name,m.title FROM materials m JOIN classes c ON c.id=m.class_id WHERE m.title IN ('A班-函数单调性讲义','B班-牛顿定律笔记') ORDER BY m.id")
meta['seed_materials']=raw_ids
missing=int(sql('nonexistent-material-id','SELECT COALESCE(MAX(id),0)+1 FROM materials'))
assert sql('nonexistent-material-proof',f'SELECT COUNT(*) FROM materials WHERE id={missing}')=='0'
meta['nonexistent_material_id']=missing
# Read credential values only in memory; never include .env, passwords or credential hashes in evidence.
env={}
for line in (Path(args.env_file)).read_text(encoding='utf-8-sig').splitlines():
 if line and not line.startswith('#') and '=' in line:
  k,v=line.split('=',1);env[k]=v.strip().strip('"').strip("'")
assert env['WEB_PORT']==str(urlsplit(args.base_url).port)
opener=build_opener(ProxyHandler({}));tokens={};seq=0;http=[]

def redact_response(value):
 if isinstance(value,dict):
  return {k:('<redacted>' if k.lower() in {'token','access_token','csrf_token','password','password_hash','session_id','cookie','authorization'} else redact_response(v)) for k,v in value.items()}
 if isinstance(value,list):return [redact_response(v) for v in value]
 return value
def request(identity,method,path,payload=None,anonymous=False):
 global seq
 headers={'Accept':'application/json','X-Request-ID':'cross-'+uuid.uuid4().hex}
 if not anonymous and identity in tokens:headers['Authorization']='Bearer '+tokens[identity]
 data=None
 if payload is not None:headers['Content-Type']='application/json';data=json.dumps(payload,ensure_ascii=False).encode('utf-8')
 if anonymous:assert 'Authorization' not in headers and 'Cookie' not in headers
 r=Request(meta['base']+path,data=data,headers=headers,method=method);started=now();tick=time.perf_counter()
 try:response=opener.open(r,timeout=30)
 except HTTPError as e:response=e
 with response:
  code=response.code;body=response.read().decode('utf-8',errors='replace')
  hs={k:v for k,v in response.headers.items() if k.lower() in ('content-type','x-request-id','server')}
 try:parsed=json.loads(body)
 except ValueError:parsed=None
 if path=='/api/login':
  if code==200 and isinstance(parsed,dict):tokens[identity]=parsed.get('token','')
  stored_body=json.dumps({'status':parsed.get('status') if isinstance(parsed,dict) else None,'token':'<redacted>','token_type':parsed.get('token_type') if isinstance(parsed,dict) else None},ensure_ascii=False)
  stored_payload={'username':identity,'password':'<redacted>'}
 else:stored_body=json.dumps(redact_response(parsed),ensure_ascii=False) if parsed is not None else body;stored_payload=payload
 seq+=1
 row={'identity':identity,'method':method,'path':path,'request':stored_payload,'authentication':'none' if anonymous or identity not in tokens else 'Bearer value omitted','status':code,'response_headers':hs,'response_body':stored_body,'started_at':started,'finished_at':now(),'elapsed_ms':round((time.perf_counter()-tick)*1000,3),'request_id':headers['X-Request-ID'],'login_body_redacted':path=='/api/login'}
 save(f'http/{seq:03d}.json',row);http.append(row)
 return code,parsed,body,hs,f'http/{seq:03d}.json'
result={}
try:
 health=request('anonymous','GET','/health',anonymous=True);assert health[0]==200,'dependencies unavailable'
 for who,key in [('student_a1','SEED_STUDENT_A_PASSWORD'),('student_b1','SEED_STUDENT_B_PASSWORD')]:
  login=request(who,'POST','/api/login',{'username':who,'password':env[key]});assert login[0]==200 and tokens.get(who),'login failed'
 a=request('student_a1','GET','/api/me');b=request('student_b1','GET','/api/me')
 assert a[0]==b[0]==200
 assert a[1]['role']==b[1]['role']=='student' and a[1]['class_name']=='A' and b[1]['class_name']=='B'
 assert type(a[1]['class_id']) is int and a[1]['class_id']>0 and type(b[1]['class_id']) is int and b[1]['class_id']>0
 listings={who:request(who,'GET','/api/materials') for who in tokens}
 for x in listings.values():assert x[0]==200 and isinstance(x[1].get('materials'),list)
 mb=next(x for x in listings['student_b1'][1]['materials'] if x['title']=='B班-牛顿定律笔记')['id']
 ma=next(x for x in listings['student_a1'][1]['materials'] if x['title']=='A班-函数单调性讲义')['id']
 assignment=request('student_a1','GET','/api/assignments');assert assignment[0]==200 and assignment[1]['assignments'];aid=assignment[1]['assignments'][0]['id']
 protected=[('GET','/api/me'),('GET','/api/materials'),('POST','/api/materials'),('GET',f'/api/materials/{mb}'),('GET',f'/api/materials/{mb}/file'),('POST',f'/api/materials/{mb}/reindex'),('POST','/api/search'),('POST','/api/ask'),('GET','/api/assignments'),('POST',f'/api/assignments/{aid}/submissions'),('POST','/api/submissions/1/grade'),('GET','/api/tasks/01ARZ3NDEKTSV4RRFFQ69G5FAV')]
 observed=[]
 for method,path in protected:
  r=request('anonymous',method,path,{} if method=='POST' else None,anonymous=True)
  observed.append({'method':method,'path':path,'status':r[0],'evidence':r[4]})
 extra=request('anonymous','POST','/api/logout',{},anonymous=True)
 result['SEC-01']={'status':'pass' if all(x['status']==401 for x in observed) else 'fail','listed_route_count':len(observed),'observations':observed,'extra_anonymous_logout':{'status':extra[0],'evidence':extra[4]}}
 owner=request('student_b1','GET',f'/api/materials/{mb}');own_a=request('student_a1','GET',f'/api/materials/{ma}')
 assert owner[0]==own_a[0]==200 and owner[1]['class_id']==b[1]['class_id'] and own_a[1]['class_id']==a[1]['class_id']
 query='单调递增';assert query in own_a[1]['body'] and query not in owner[1]['body']
 visits=[]
 for suffix in ('','/file'):
  cross=request('student_a1','GET',f'/api/materials/{mb}{suffix}')
  absent=request('student_a1','GET',f'/api/materials/{missing}{suffix}')
  visits.append({'kind':'file' if suffix else 'detail','cross_status':cross[0],'nonexistent_status':absent[0],'equal_body':cross[2]==absent[2],'equal_content_type':cross[3].get('Content-Type')==absent[3].get('Content-Type'),'cross_evidence':cross[4],'missing_evidence':absent[4]})
 searches=[]
 for mode in ('keyword','vector','hybrid'):
  pos=request('student_a1','POST','/api/search',{'query':query,'mode':mode})
  cross=request('student_b1','POST','/api/search',{'query':query,'mode':mode,'class_id':a[1]['class_id']})
  assert isinstance(pos[1],dict) and isinstance(pos[1].get('hits'),list) and isinstance(cross[1],dict) and isinstance(cross[1].get('hits'),list),'missing/non-array hits'
  searches.append({'mode':mode,'same_class_status':pos[0],'same_class_count':len(pos[1]['hits']),'cross_status':cross[0],'cross_count':len(cross[1]['hits']),'positive_evidence':pos[4],'cross_evidence':cross[4]})
 ok=all(x['cross_status']==x['nonexistent_status']==404 and x['equal_body'] and x['equal_content_type'] for x in visits) and all(x['same_class_status']==x['cross_status']==200 and x['same_class_count']>0 and x['cross_count']==0 for x in searches)
 result['SEC-02']={'status':'pass' if ok else 'fail','material_a_id':ma,'material_b_id':mb,'class_a_id':a[1]['class_id'],'class_b_id':b[1]['class_id'],'same_class_detail_statuses':{'A1':own_a[0],'B1':owner[0]},'nonexistent_material_id':missing,'query':query,'visits':visits,'searches':searches,'limitation':'本次既有环境、种子材料及三种模式；未验证所有数据、所有权限边界'}
except Exception as e:
 result['execution_error']={'type':type(e).__name__,'message':str(e)}
finally:
 meta['business_counts_after']=sql('business-counts-after',counts)
 meta['business_counts_unchanged']=meta['business_counts_before']==meta['business_counts_after']
 meta['report_hashes_after']={n:hashlib.sha256((ROOT/'reports'/n).read_bytes()).hexdigest() for n in report_names}
 meta['five_reports_unchanged']=meta['report_hashes_before']==meta['report_hashes_after']
 meta['finished_at']=now();save('metadata.json',meta);save('results.json',result)
 save('http-index.json',[{'identity':x['identity'],'method':x['method'],'path':x['path'],'status':x['status']} for x in http])
 manifest={p.relative_to(OUT).as_posix():{'size':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in OUT.rglob('*') if p.is_file()}
 save('manifest.json',{'files':manifest,'scope':'new evidence only; login credentials redacted'})
print(json.dumps({'evidence_dir':OUT.relative_to(ROOT).as_posix(),'results':result,'business_counts_unchanged':meta['business_counts_unchanged'],'five_reports_unchanged':meta['five_reports_unchanged'],'api_binary_matches_original_run':meta['api_binary_matches_original_run'],'business_source_difference_count':len(meta['business_source_differences_from_original_run'])},ensure_ascii=False))
