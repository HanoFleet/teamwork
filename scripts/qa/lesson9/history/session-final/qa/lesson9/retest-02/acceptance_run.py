import importlib.util,pathlib,sys,traceback,json
B=pathlib.Path(__file__).resolve().parent
R=B.parent/'test-main'
spec=importlib.util.spec_from_file_location('qa_acceptance',R/'scripts/acceptance.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.PROJECT='campusclaw-l9-retest02'
m.ENV_FILE=R/'.env.retest02'
m.REPORT_DIR=B/'acceptance'
rc=1
try:
 rc=m.main()
except Exception as e:
 m.CHECKS.append(dict(id='ENV',name='隔离验收环境',criterion='构建并启动被测提交',status='failed',elapsed_ms=0,detail=str(e)))
finally:
 m.cleanup();m.write_report()
(B/'acceptance.exit.txt').write_text(str(rc),encoding='utf-8')
sys.exit(rc)
