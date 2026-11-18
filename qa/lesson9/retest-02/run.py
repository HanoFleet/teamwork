import pathlib,subprocess,json,os,datetime
B=pathlib.Path(__file__).resolve().parent
R=B.parent/'test-main'
def now():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat()
entries=[]
commands=[('spec',['python','scripts/spec_check.py'],R),('standards',['python','scripts/standards_check.py'],R),('layer',['python','scripts/layer_check.py'],R),('static',['python','scripts/security_static.py'],R),('cases',['python','scripts/security_cases.py'],R),('secrets',['python','scripts/secret_scan.py'],R),('go',['go','test','-json','./...'],R/'backend'),('vet',['go','vet','./...'],R/'backend'),('audit',['cmd','/c','npm audit --json --audit-level=high --package-lock-only --registry=https://registry.npmjs.org'],R/'frontend'),('govuln',['python','scripts/govuln_check.py'],R),('gate-self-test',['python','scripts/security_gate.py','--self-test'],R),('strict',['cmd','/c','npx -y @fission-ai/openspec@1.15.0 validate --all --strict'],R),('make',['make','check'],R)]
for name,cmd,cwd in commands:
 start=now()
 try:
  p=subprocess.run(cmd,cwd=cwd,capture_output=True,timeout=100,env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHONUTF8':'1','GOPROXY':'https://goproxy.cn,direct'});rc=p.returncode;out=p.stdout+p.stderr
 except subprocess.TimeoutExpired as e:rc=124;out=(e.stdout or b'')+(e.stderr or b'')+b'\nTIMEOUT 100s'
 except Exception as e:rc=127;out=str(e).encode('utf-8')
 (B/'logs'/f'{name}.txt').write_bytes(out)
 entries.append(dict(id=name,command=cmd,cwd=str(cwd),started=start,ended=now(),exit=rc,evidence=f'logs/{name}.txt'))
 (B/'execution.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf-8');print(name,rc,flush=True)
