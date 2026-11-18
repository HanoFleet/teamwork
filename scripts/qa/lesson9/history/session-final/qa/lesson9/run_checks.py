import subprocess,pathlib,json,datetime,os
base=pathlib.Path('qa/lesson9').resolve();root=base/'test-main';rows=[]
commands=[('spec',['python','scripts/spec_check.py']),('standards',['python','scripts/standards_check.py']),('layer',['python','scripts/layer_check.py']),('security-static',['python','scripts/security_static.py']),('injection-cases',['python','scripts/security_cases.py']),('secret',['python','scripts/secret_scan.py']),('make-check',['make','check']),('make-security',['make','check-security']),('make-grade',['make','grade']),('verify',['python','scripts/verify.py']),('docker',['docker','info','--format','{{.ServerVersion}}']),('go',['go','test','-json','./...']),('openspec',['cmd','/c','npx -y @fission-ai/openspec@1.15.0 validate --all --strict']),('gate-selftest',['python','scripts/security_gate.py','--self-test'])]
for name,cmd in commands:
 start=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat();cwd=root/'backend' if name=='go' else root
 try:
  p=subprocess.run(cmd,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=75,env={**os.environ,'PYTHONIOENCODING':'utf-8'});out=p.stdout.decode('utf-8',errors='replace');code=p.returncode
 except subprocess.TimeoutExpired as e:out=(e.stdout or b'').decode('utf-8',errors='replace')+'\nTIMEOUT 75s';code=124
 except Exception as e:out=repr(e);code=127
 (base/'logs'/f'{name}.txt').write_text(out,encoding='utf-8');rows.append(dict(id=name,command=cmd,time=start,exit=code,evidence=f'logs/{name}.txt'));(base/'execution.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print(name,code,flush=True)
