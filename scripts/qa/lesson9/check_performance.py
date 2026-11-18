"""Compatibility entry point for the current enqueue latency rule."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests/performance"))
from check_single_request_limit import main

if __name__ == "__main__":
    raise SystemExit(main())
