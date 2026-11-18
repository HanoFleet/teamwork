"""Compatibility wrapper for the current 20-sample enqueue collector."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests/performance"))
from grade_enqueue_latency import run
