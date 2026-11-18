"""Validate that the archived gate rejects slow, short and non-202 sample sets."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

class LatencyGateContract(unittest.TestCase):
    def run_gate(self, count=20, elapsed=100, status=202):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'samples.json'
            path.write_text(json.dumps({'samples':[{'elapsed_ms':elapsed,'status':status} for _ in range(count)]}))
            result = subprocess.run([sys.executable, str(Path(__file__).with_name('check_single_request_limit.py')), str(path)], capture_output=True)
            return result.returncode

    def test_boundary_100ms_passes(self):
        self.assertEqual(self.run_gate(), 0)

    def test_above_100ms_fails(self):
        self.assertNotEqual(self.run_gate(elapsed=100.001), 0)

    def test_missing_sample_fails(self):
        self.assertNotEqual(self.run_gate(count=19), 0)

    def test_wrong_status_fails(self):
        self.assertNotEqual(self.run_gate(status=200), 0)

if __name__ == '__main__':
    unittest.main()
