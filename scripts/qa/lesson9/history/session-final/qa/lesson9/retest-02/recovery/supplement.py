import pathlib,importlib.util,os,json,shutil,time,subprocess
B=pathlib.Path(__file__).resolve().parent;R=B.parents[1]/'test-main'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
a=load('supplement_acceptance',R/'scripts/acceptance.py');a.PROJECT='campusclaw-l9-recovery';a.ENV_FILE=R/'.env.recovery'
os.environ['COMPOSE_PROJECT_NAME']=a.PROJECT;os.environ['COMPOSE_FILE']=str(R/'docker-compose.yml')+';'+str(B/'network.yml')
result={};sandbox=B/'sec08-sandbox';sandbox.mkdir(exist_ok=True)
try:
 a.write_env();a.compose('up','-d','--wait')
 (R/'.env').write_bytes(a.ENV_FILE.read_bytes());v=load('supplement_verify',R/'scripts/verify.py')
 def call(op,method,path,body=None):
  code,raw,headers=v.call(op,method,path,json.dumps(body).encode() if body is not None else None,{'Content-Type':'application/json'} if body is not None else None);return code,json.loads(raw),headers
 student=v.login('student_a1',v.ENV['SEED_STUDENT_A_PASSWORD']);other=v.login('student_b1',v.ENV['SEED_STUDENT_B_PASSWORD'])
 aid=call(other,'GET','/api/assignments')[1]['assignments'][0]['id'];code,data,_=call(other,'POST',f'/api/assignments/{aid}/submissions',{'body':'SEC04 direct defensive regression '+str(time.time_ns())});assert code in (200,201);sid=data['submission_id']
 def counts():return {table:v.mysql(f'SELECT COUNT(*) FROM {table} WHERE submission_id={sid}') for table in ['grade_tasks','grade_results']} | {'outbox':v.mysql(f"SELECT COUNT(*) FROM outbox_messages WHERE idempotency_key LIKE 'grade:{sid}:%'")}
 before=counts();code,body,headers=call(student,'POST',f'/api/submissions/{sid}/grade',{'score':100});code2,body2,headers2=call(student,'POST','/api/submissions/999999999/grade',{'score':100});after=counts()
 result['SEC04_direct']=dict(code=code,nonexistent_code=code2,same_body=body==body2,before=before,after=after,passed=code==404 and code2==404 and body==body2 and before==after)
 (sandbox/'.env').write_bytes(a.ENV_FILE.read_bytes());shutil.copytree(R/'docs/lesson-09/sec08',sandbox/'docs/lesson-09/sec08',dirs_exist_ok=True)
 sec=load('sec08_supplement',R/'scripts/sec08_experiment.py');sec.ROOT=sandbox;result['SEC08']=sec.main()
except Exception as e:result['error']=type(e).__name__+': '+str(e)
finally:
 (R/'.env').unlink(missing_ok=True);(sandbox/'.env').unlink(missing_ok=True);a.cleanup();(B/'supplement-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(result,flush=True)
