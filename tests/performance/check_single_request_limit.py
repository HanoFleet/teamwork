"""Observe individual latency above 100ms and enforce 20 samples / P95 < 500ms."""
import argparse
import json
import math
from pathlib import Path

RULE = "enqueue-latency-v2"


def evaluate_samples(samples):
    if not isinstance(samples, list) or len(samples) != 20:
        raise ValueError("expected exactly 20 samples")
    for sample in samples:
        if not isinstance(sample, dict):
            raise ValueError("sample must be an object")
        elapsed = sample.get("elapsed_ms")
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("elapsed_ms must be a finite nonnegative number")
    ordered = sorted(sample["elapsed_ms"] for sample in samples)
    p95 = ordered[math.ceil(0.95 * len(ordered)) - 1]
    warnings = [dict(index=sample.get("index", index),
                     request_id=sample.get("request_id"), elapsed_ms=sample["elapsed_ms"])
                for index, sample in enumerate(samples) if sample["elapsed_ms"] > 100]
    valid = all(sample.get("status") == 202 and
                sample.get("accepted_without_result", True) is True for sample in samples)
    return dict(rule=RULE, sample_count=len(samples), p95_ms=p95, max_ms=max(ordered),
                over_100_ms=len(warnings), warnings=warnings, valid=valid,
                async_p95_pass=p95 < 500, passed=valid and p95 < 500)


def print_evaluation(result):
    for sample in result["warnings"]:
        print("WARN " + json.dumps(sample, ensure_ascii=False))
    print(json.dumps(result, ensure_ascii=False))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="+")
    parser.add_argument("--output", type=Path, help="Create a new evaluation file exclusively")
    args = parser.parse_args(argv)
    evaluations = []
    failed = False
    for name in args.files:
        try:
            data = json.loads(Path(name).read_text(encoding="utf-8"))
            result = evaluate_samples(data["samples"])
            print_evaluation(result)
            evaluations.append(dict(source=name, evaluation=result))
            failed = failed or not result["passed"]
        except (OSError, ValueError, KeyError, TypeError) as error:
            print(f"ERROR {name}: {error}")
            failed = True
    if args.output:
        try:
            with args.output.open("x", encoding="utf-8") as output:
                json.dump(dict(rule=RULE, evaluations=evaluations, passed=not failed),
                          output, ensure_ascii=False, indent=2)
        except OSError as error:
            print(f"ERROR output: {error}")
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
