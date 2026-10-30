# Architecture

## Design principles

- Local-first and offline by default.
- Streaming over whole-file materialization.
- Explicit data transformations; no silent repair.
- Stable JSON artifacts before GUI work.
- Keep the engine independent of a specific shell, desktop UI, or CI provider.
- Treat source data as sensitive; reports should not contain raw cells.

## Current MVP components

```text
CLI (argparse)
  ├── inspect ──> readers ──> streaming profiler ──> profile.json + report.html
  ├── compare ──> profile snapshots ──> drift matcher ──> drift.json + report.html
  ├── contract-init ──> profile snapshot ──> contract draft JSON
  ├── validate ──> readers + contract ──> issue collector + temporary SQLite uniqueness index
  │                                              └── validation.json + report.html
  └── clean ──> readers + explicit contract transforms ──> new CSV/TSV + audit sidecar
```

## Reader boundary

`readers.py` exposes `open_dataset()` and yields numbered records. Format-specific details (UTF-8 BOM, delimiter selection, JSONL line parsing, malformed rows) remain at this boundary. The profiler and validator consume records rather than owning file parsing.

MVP readers support CSV, TSV, JSONL, and NDJSON. They do not silently coerce arbitrary nested JSON into columns: nested JSON objects/arrays are serialized to compact JSON strings for profiling.

## Profiling algorithm

For each column the profiler tracks:

- null and non-null counts;
- type evidence counters, including email, URL, UUID, IP, date, and primitive numeric/boolean types;
- numeric min/max where applicable;
- distinct cardinality;
- per-column observed count.

Cardinality uses a hybrid strategy:

1. Keep an exact set while cardinality is at most 512.
2. On the 513th distinct value, initialize a 4,096-register HyperLogLog (precision 12) with the set contents and stop retaining raw distinct values.
3. Use linear counting for the small-cardinality range and standard HLL estimation otherwise.

This bounds the cardinality structure per column. It does not mean total memory is constant: it scales with the number of columns and other profile state. The current type inference and delimiter sniffing are heuristics, not schema guarantees.

## Schema drift matcher

The current matcher compares removed and added fields using:

- normalized-name SequenceMatcher similarity;
- token Jaccard similarity;
- inferred-type compatibility.

It greedily selects one-to-one suggestions in descending score order. Suggestions are advisory; the drift output states that no rename is automatically applied. The similarity score is a ranking heuristic, not a calibrated probability.

Future work should evaluate matching against labeled rename pairs and measure precision/recall before tuning thresholds or marketing confidence as a probability.

## Contract validation

Contracts are JSON files with an explicit version. CSV header presence is validated before row checks. JSONL required fields are checked per record because JSONL has no header row and keys may vary by record.

Unique checks use a temporary SQLite database with a uniqueness constraint on `(field, value)`. This avoids an unbounded Python set, but disk use grows with unique values. The temporary directory is removed at the end of validation. This is normal file deletion, not cryptographic secure erasure; sensitive deployments should select an appropriately protected temporary filesystem and storage policy.

Validation reports store rule IDs, field names, row numbers, and messages — not values.

## Safe cleaning

Cleaning is separate from validation. It only applies explicit per-field rules:

- `trim: true`
- `empty_as_null: true`
- `case: lower | upper | title`

The operation writes a new file and an audit JSON sidecar. It refuses source/output collisions and existing outputs. It does not drop rows, invent replacement values, or claim that the result is valid. Run `validate` after cleaning.

## Report security

HTML reports:

- escape all rendered values;
- include a restrictive Content Security Policy;
- load no external JavaScript, CSS, fonts, images, or network resources;
- do not include raw cell examples.

## Future architecture direction

Do not introduce Rust or a dataframe dependency merely for prestige. First define workload and benchmark data. If profiling shows that the Python engine cannot meet a demonstrated user requirement, isolate hot-path interfaces and consider a Rust implementation behind the same stable profile/contract schema. Keep Python bindings/SDK as an integration surface rather than the only user interface.

Potential future adapters should implement a narrow `DatasetReader` contract and share the same profiler, drift, validator, report format, and safety rules.
