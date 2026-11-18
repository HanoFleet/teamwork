"""Contract tests for async-grading/???????P95??."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from check_single_request_limit import evaluate_samples
import grade_enqueue_latency

ROOT = Path(__file__).resolve().parents[2]
ENTRIES = [ROOT / "tests/performance/check_single_request_limit.py",
           ROOT / "scripts/qa/lesson9/check_performance.py"]


def samples(values=None, status=202):
    values = [100] * 20 if values is None else values
    return [dict(index=i, request_id=f"request-{i}", elapsed_ms=value, status=status)
            for i, value in enumerate(values)]


class LatencyGateContract(unittest.TestCase):
    def run_gate(self, rows, entry=ENTRIES[0], output_exists=False):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "samples.json"
            output = Path(tmp) / "evaluation.json"
            source.write_text(json.dumps(dict(samples=rows, passed=False)), encoding="utf-8")
            before = source.read_bytes()
            if output_exists:
                output.write_text("historical result", encoding="utf-8")
            result = subprocess.run([sys.executable, "-X", "utf8", str(entry), str(source),
                                     "--output", str(output)], capture_output=True, text=True,
                                    encoding="utf-8")
            self.assertEqual(source.read_bytes(), before)
            if output_exists:
                self.assertEqual(output.read_text(encoding="utf-8"), "historical result")
            return result

    def test_100ms_boundary_has_no_warning(self):
        result = self.run_gate(samples())
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("WARN", result.stdout)

    def test_above_100ms_warns_in_both_entries(self):
        for entry in ENTRIES:
            with self.subTest(entry=entry):
                result = self.run_gate(samples([100] * 19 + [100.001]), entry)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("WARN", result.stdout)
                self.assertIn("100.001", result.stdout)
                self.assertIn("request-19", result.stdout)

    def test_original_precision_and_new_rule(self):
        result = self.run_gate(samples([64.5362] * 19 + [122.06220000007306]))
        self.assertEqual(result.returncode, 0)
        self.assertIn("122.06220000007306", result.stdout)
        self.assertIn('"p95_ms": 64.5362', result.stdout)
        self.assertIn("enqueue-latency-v2", result.stdout)

    def test_p95_below_500_passes(self):
        self.assertEqual(self.run_gate(samples([499.999] * 20)).returncode, 0)

    def test_p95_at_or_above_500_fails(self):
        for value in [500, 500.001]:
            for entry in ENTRIES:
                result = self.run_gate(samples([100] * 18 + [value] * 2), entry)
                self.assertEqual(result.returncode, 1)
                self.assertIn("WARN", result.stdout)

    def test_single_outlier_does_not_replace_p95(self):
        self.assertEqual(self.run_gate(samples([100] * 19 + [900])).returncode, 0)

    def test_wrong_counts_fail(self):
        for count in [0, 19, 21]:
            self.assertEqual(self.run_gate(samples([10] * count)).returncode, 1)

    def test_failure_statuses_fail(self):
        for status in [200, 400, 403, 404, 503]:
            self.assertEqual(self.run_gate(samples(status=status)).returncode, 1)

    def test_invalid_elapsed_fails(self):
        for value in [-1, "10", None, True, float("nan"), float("inf")]:
            result = self.run_gate(samples([10] * 19 + [value]))
            self.assertEqual(result.returncode, 1)
            self.assertIn("ERROR", result.stdout)

    def test_result_in_response_fails(self):
        rows = samples()
        rows[0]["accepted_without_result"] = False
        self.assertFalse(evaluate_samples(rows)["passed"])

    def test_existing_output_preserved(self):
        self.assertEqual(self.run_gate(samples(), output_exists=True).returncode, 1)

    def test_malformed_json_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "bad.json"
            source.write_text("{", encoding="utf-8")
            result = subprocess.run([sys.executable, str(ENTRIES[0]), str(source)], capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(source.read_bytes(), b"{")

    def test_live_collector_uses_shared_rule(self):
        class Verifier:
            ENV = {"SEED_STUDENT_A_PASSWORD": "synthetic"}
            def login(self, *args):
                return object()
            def call(self, student, method, path, *args):
                if method == "GET":
                    return 200, b'{"assignments":[{"id":1}]}', {}
                if path.endswith("/submissions"):
                    return 201, b'{"submission_id":1}', {}
                return 202, b'{"task_id":1}', {}
        for elapsed, passed in [(0.1220622, True), (0.5, False)]:
            with tempfile.TemporaryDirectory() as tmp:
                ticks = [tick for i in range(20) for tick in (i * 2, i * 2 + elapsed)]
                with patch.object(grade_enqueue_latency.time, "perf_counter", side_effect=ticks), patch("builtins.print"):
                    result = grade_enqueue_latency.run(Verifier(), Path(tmp) / "fresh.json")
                self.assertEqual(result["passed"], passed)
                self.assertEqual(len(result["warnings"]), 20)


if __name__ == "__main__":
    unittest.main()
