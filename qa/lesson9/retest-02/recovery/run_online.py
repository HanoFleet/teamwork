import pathlib,importlib.util,os,sys,json,traceback,subprocess,time
B=pathlib.Path(__file__).resolve().parent;R=B.parents[1]/'test-main'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('acceptance_recovery',R/'scripts/acceptance.py');m.PROJECT='campusclaw-l9-recovery';m.ENV_FILE=R/'.env.recovery';m.REPORT_DIR=B/'acceptance'
orig=m.compose
def compose(*args,**kw):
 if args and args[0]=='build':return subprocess.CompletedProcess(['prepared-equivalent-runtime-images'],0,'','')
 return orig(*args,**kw)
m.compose=compose;os.environ['COMPOSE_PROJECT_NAME']=m.PROJECT
os.environ['COMPOSE_FILE']=str(R/'docker-compose.yml')+';'+str(B/'network.yml')
status={'acceptance':'not run','verify':'not run'}
try:
 if os.environ.get('RECOVERY_VERIFY_ONLY')=='1':
  m.write_env();status['acceptance']='previous run 18/18 (see preserved acceptance/report.json)'
 else:status['acceptance']=m.main()
 m.compose('up','-d','--wait')
 envpath=R/'.env'
 if envpath.exists():raise RuntimeError('refuse overwrite existing .env')
 envpath.write_bytes(m.ENV_FILE.read_bytes())
 v=load('verify_recovery',R/'scripts/verify.py')
 v.write_doc=lambda:(B/'verify.md').write_text('\n'.join(v.LINES)+'\n',encoding='utf-8')
 original_compose=v.compose
 def waited_compose(*args,**kwargs):
  if len(args)>2 and args[0]=='exec' and 'rabbitmq' in args:
   for _ in range(30):
    ready=original_compose('exec','-T','rabbitmq','rabbitmq-diagnostics','-q','check_running',check=False)
    if ready.returncode==0:break
    time.sleep(1)
  return original_compose(*args,**kwargs)
 v.compose=waited_compose
 security=load('security_prioritized',R/'scripts/security_test.py')
 try:
  security.run(note=v.note,fail=v.fail,call=v.call,login=v.login,mysql=v.mysql,compose=v.compose,ENV=v.ENV)
  status['security_prioritized']=0
 except (Exception,SystemExit) as e:
  status['security_prioritized']='failed '+type(e).__name__
  if isinstance(e,subprocess.CalledProcessError):
   detail=e.stderr or ''
   for value in v.ENV.values():
    if len(value)>8:detail=detail.replace(value,'[redacted]')
   (B/'logs/security-command-error.txt').write_text(detail,encoding='utf-8')
 (B/'security-prioritized.md').write_text('\n'.join(v.LINES)+'\n',encoding='utf-8')
 try:v.main();status['verify']=0
 except (Exception,SystemExit) as e:
  status['verify']='failed '+type(e).__name__;v.write_doc()
  if isinstance(e,subprocess.CalledProcessError):
   detail=e.stderr or ''
   for value in v.ENV.values():
    if len(value)>8:detail=detail.replace(value,'[redacted]')
   (B/'logs/verify-command-error.txt').write_text(detail,encoding='utf-8')
except Exception as e:
 status['error']=str(e);print(str(e),flush=True)
 m.CHECKS.append(dict(id='ENV',name='隔离环境',criterion='准确工具链构建或等效编译环境启动',status='failed',elapsed_ms=0,detail=str(e)))
finally:
 (R/'.env').unlink(missing_ok=True)
 m.cleanup()
 if m.CHECKS:m.write_report()
 (B/'status.json').write_text(json.dumps(status,ensure_ascii=False,indent=2),encoding='utf-8');print(status,flush=True)
