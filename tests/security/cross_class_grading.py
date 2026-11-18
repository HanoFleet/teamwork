"""SEC-04: direct grade entry returns same 404 and makes no cross-class writes."""
import json
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'support'))
from isolated_project import Project, arguments

def main():
    with Project('ownership', arguments(__doc__)) as project:
        project.start()
        v = project.verifier()
        def call(op, method, path, body=None):
            code, raw, _ = v.call(op, method, path, json.dumps(body).encode() if body is not None else None,
                                 {'Content-Type':'application/json'} if body is not None else None)
            return code, json.loads(raw)
        student = v.login('student_a1', v.ENV['SEED_STUDENT_A_PASSWORD'])
        other = v.login('student_b1', v.ENV['SEED_STUDENT_B_PASSWORD'])
        aid = call(other, 'GET', '/api/assignments')[1]['assignments'][0]['id']
        code, data = call(other, 'POST', f'/api/assignments/{aid}/submissions',
                          {'body':'SEC04 defensive fixture '+str(time.time_ns())})
        assert code in (200, 201)
        sid = data['submission_id']
        def counts():
            return {table:v.mysql(f'SELECT COUNT(*) FROM {table} WHERE submission_id={sid}')
                    for table in ['grade_tasks','grade_results']} | {
                    'outbox':v.mysql(f"SELECT COUNT(*) FROM outbox_messages WHERE idempotency_key LIKE 'grade:{sid}:%'")}
        before = counts()
        code, body = call(student, 'POST', f'/api/submissions/{sid}/grade', {'score':100})
        missing, missing_body = call(student, 'POST', '/api/submissions/999999999/grade', {'score':100})
        after = counts()
        passed = code == missing == 404 and body == missing_body and before == after
        result = dict(status=code, missing_status=missing, same_body=body==missing_body,
                      before=before, after=after, passed=passed)
        (project.output/'cross-class-result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        assert passed
        print('Output:', project.output)
    return 0

if __name__ == '__main__':
    sys.exit(main())
