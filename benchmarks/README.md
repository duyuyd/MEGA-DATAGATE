# Benchmarks

## Recorded development run

A synthetic CSV with 200,000 rows, 5 columns, and 10,677,818 bytes was profiled on Python 3.13.5 / Linux x86_64.

- Elapsed: 10.323 seconds
- Throughput: 19374.18 rows/second
- Peak traced Python allocations: 235316 bytes

The run is recorded in `python-3.13.5-linux-200k.json`. The memory number is from `tracemalloc`, not process RSS; it excludes some native/runtime allocations and must not be presented as total process memory.

Reproduce with:

```bash
python scripts/benchmark.py --rows 200000
```

Results vary by hardware, filesystem, Python build, and data shape. Treat this as one reproducible point, not a universal speed claim.
