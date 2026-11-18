"""async-grading/202: original sequential 20-sample protocol, no dropped samples."""
import json, math, time, datetime, pathlib

def run(v, output):
    student = v.login('student_a1', v.ENV['SEED_STUDENT_A_PASSWORD'])
    def post(path, payload, headers=None):
        return v.call(student, 'POST', path, json.dumps(payload).encode(), {'Content-Type': 'application/json', **(headers or {})})
    code, raw, _ = v.call(student, 'GET', '/api/assignments')
    assert code == 200
    aid = json.loads(raw)['assignments'][0]['id']
    stamp = str(time.time_ns()); samples = []
    for i in range(20):
        code, raw, _ = post(f'/api/assignments/{aid}/submissions', {'body': f'函数单调性实验结论 {stamp} #{i} '+ '分析'*8})
        assert code in (200, 201)
        sid = json.loads(raw)['submission_id']; request_id = f'lesson9-perf-{stamp}-{i}'
        started = time.perf_counter()
        code, raw, _ = post(f'/api/submissions/{sid}/grade', {}, {'X-Request-ID': request_id})
        elapsed = (time.perf_counter()-started)*1000
        body = json.loads(raw)
        samples.append(dict(index=i, elapsed_ms=elapsed, status=code, request_id=request_id))
        assert code == 202 and 'score' not in body and 'feedback' not in body
    ordered = sorted(s['elapsed_ms'] for s in samples)
    result = dict(time=datetime.datetime.now(datetime.timezone.utc).isoformat(), protocol='async_test.py: 20 sequential fresh submissions then timed grade POST; no warmup/discard', samples=samples, p95_ms=ordered[math.ceil(.95*len(ordered))-1], max_ms=max(ordered), over_50_ms=sum(x>50 for x in ordered), over_100_ms=sum(x>100 for x in ordered), single_request_pass=max(ordered)<=100, async_p95_pass=ordered[18]<500)
    pathlib.Path(output).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result

if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'support'))
    from isolated_project import Project, arguments
    options = arguments('20 sequential grade enqueue samples; retain all values; 100ms limit')
    with Project('latency', options) as project:
        project.start()
        result = run(project.verifier(), project.output/'latency.json')
        print('Output:', project.output)
        status = 0 if result['single_request_pass'] and result['async_p95_pass'] else 1
    sys.exit(status)
