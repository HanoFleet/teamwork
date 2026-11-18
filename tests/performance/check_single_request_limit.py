"""Enforce existing 04-testing 100ms threshold on all retained samples."""
import argparse,json,pathlib,sys
p=argparse.ArgumentParser();p.add_argument('files',nargs='+');args=p.parse_args();failed=False
for name in args.files:
 d=json.loads(pathlib.Path(name).read_text(encoding='utf-8'));samples=d['samples'];over=[s for s in samples if s['elapsed_ms']>100]
 valid=len(samples)==20 and all(s['status']==202 for s in samples)
 print(f'{name}: samples={len(samples)} over100={len(over)} max_ms={max(s["elapsed_ms"] for s in samples):.3f} valid={valid}')
 failed=failed or bool(over) or not valid
sys.exit(1 if failed else 0)
