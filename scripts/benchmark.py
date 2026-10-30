#!/usr/bin/env python3
"""Reproducible synthetic CSV profiling benchmark for MEGA DataGate."""
from __future__ import annotations

import argparse
import csv
import json
import platform
import sys
import tempfile
import time
import tracemalloc
from pathlib import Path

from datagate.profiling import profile_file


def generate_csv(path: Path, rows: int) -> int:
    file_size = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["record_id", "email", "country", "score", "segment"])
        for index in range(rows):
            writer.writerow([
                f"R{index:09d}",
                f"person{index % max(1, rows // 2)}@example.test",
                ("VN", "US", "DE", "JP")[index % 4],
                f"{(index % 10000) / 100:.2f}",
                f"group-{index % 25}",
            ])
    file_size = path.stat().st_size
    return file_size


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=200_000)
    parser.add_argument("--keep-file", default=None, help="Optional path to retain the generated input CSV.")
    args = parser.parse_args()
    if args.rows < 1:
        parser.error("--rows must be positive")

    if args.keep_file:
        input_path = Path(args.keep_file)
        input_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
    else:
        temporary = tempfile.TemporaryDirectory(prefix="datagate-bench-")
        input_path = Path(temporary.name) / "synthetic.csv"

    size_bytes = generate_csv(input_path, args.rows)
    tracemalloc.start()
    started = time.perf_counter()
    profile = profile_file(input_path)
    elapsed = time.perf_counter() - started
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    result = {
        "benchmark": "datagate-profile-v1",
        "rows_requested": args.rows,
        "rows_profiled": profile["rows"],
        "columns": profile["column_count"],
        "input_bytes": size_bytes,
        "elapsed_seconds": round(elapsed, 4),
        "rows_per_second": round(profile["rows"] / elapsed, 2) if elapsed else None,
        "peak_traced_python_bytes": peak_bytes,
        "python_note": "tracemalloc does not include all native/runtime memory; do not equate this with process RSS.",
        "environment": platform.platform(),
        "python_version": platform.python_version(),
    }
    print(json.dumps(result, indent=2))
    if temporary:
        temporary.cleanup()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
