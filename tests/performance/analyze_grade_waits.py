"""Correlate retained client/API samples and normalized DB observations.

Analysis success does not mean the separate P95 < 500ms gate passed.
"""
import argparse
import csv
import json
from pathlib import Path


def analyze(root):
    report = []
    for phase in ["before", "after"]:
        for i in [1, 2]:
            folder = root / phase
            data = json.loads((folder / f"performance-{i}.json").read_bytes())
            assert len(data["samples"]) == 20
            epoch, timer = map(float, data["db_anchor"].split("\t"))
            def rows(name):
                with (folder / name).open(encoding="utf8", newline="") as stream:
                    return list(csv.DictReader(stream, delimiter="\t"))
            statements = rows(f"sql-statements-{i}.tsv")
            waits = rows(f"db-waits-{i}.tsv")
            edges = rows(f"lock-edges-{i}.tsv")
            access = {x["request_id"]: x for x in json.loads((folder / f"api-timings-{i}.json").read_bytes())}
            entry = {"phase": phase, "round": i, "max_ms": data["max_ms"], "over_100_ms": data["over_100_ms"],
                     "outbox_lock_edges": sum(x["table"] == "outbox_messages" for x in edges), "slow_requests": []}
            for sample in data["samples"]:
                if sample["elapsed_ms"] <= 100: continue
                start = timer + (sample["start_epoch_ms"] - epoch) * 1e9
                end = start + sample["elapsed_ms"] * 1e9
                def overlap(observations):
                    matches = [x for x in observations if float(x["start_ps"]) < end and float(x["end_ps"]) > start]
                    return sorted(matches, key=lambda x: float(x["duration_ms"]), reverse=True)[:5]
                entry["slow_requests"].append({"index": sample["index"], "request_id": sample["request_id"],
                    "client_ms": sample["elapsed_ms"], "api_ms": access.get(sample["request_id"], {}).get("duration_ms"),
                    "overlapping_statements": overlap(statements), "overlapping_db_waits": overlap(waits)})
            report.append(entry)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparison", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_bytes((json.dumps(analyze(args.comparison), indent=2) + "\n").encode())
