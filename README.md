# MEGA DataGate

**Local-first intelligent data intake.** Profile unfamiliar datasets, detect schema drift, validate against explicit contracts, and apply reviewed cleaning rules without overwriting the source.

> MVP status: alpha. This is a working, dependency-free CLI for CSV, TSV, JSONL, and NDJSON. It is not yet a general-purpose ETL platform or a visual data editor.

## Why DataGate exists

Teams repeatedly receive files whose structure and quality change: column names drift, fields disappear, types change, empty values spread, duplicate keys arrive, and formatting differs between suppliers or monthly exports. The resulting work often becomes a pile of one-off scripts.

DataGate provides one local workflow for intake:

1. **Profile** a file as a stream and produce a privacy-conscious snapshot.
2. **Compare** snapshots and suggest likely column renames without silently changing anything.
3. **Validate** rows against a versionable JSON contract.
4. **Clean** only transformations explicitly authorized by that contract, writing to a new file plus an audit record.

## What makes this useful

- **Local-first:** no account, telemetry, server, upload, or network connection is needed by the MVP.
- **Streaming profile:** rows are processed incrementally. Distinct counts are exact for small columns and switch to a fixed-size HyperLogLog sketch after 512 distinct values.
- **Reviewable schema drift:** rename candidates include a heuristic similarity score and are never auto-applied.
- **Contracts as code:** required fields, nullability, types, uniqueness, bounds, allowed values, and regex rules live in version-controlled JSON.
- **Large-file-aware uniqueness checks:** unique values are tracked in a temporary SQLite database rather than an unbounded in-memory set.
- **Safe cleaning:** only explicit `trim`, `case`, and `empty_as_null` operations are applied. The source file is never overwritten; output and audit files are new.
- **Useful artifacts:** every analysis produces machine-readable JSON and a self-contained HTML report suitable for review or CI.
- **No runtime dependencies:** Python standard library only.

DataGate is not claiming that data profiling, cleaning, or schema validation are new ideas. Established projects such as [OpenRefine](https://openrefine.org/docs.html), [Frictionless](https://framework.frictionlessdata.io/docs/guides/validating-data), and [Pandera](https://pandera.readthedocs.io/en/stable/) already solve important parts of this space. DataGate's product hypothesis is the unified, local intake workflow: inspect → compare → contract-check → explicit repair → audit, with safe defaults and CI-friendly outputs.

## Quick start

Requires Python 3.11 or newer. Works on Windows, macOS, Linux, and Android/Termux where Python is available.

```bash
git clone https://github.com/<OWNER>/MEGA-DATAGATE.git
cd MEGA-DATAGATE
python -m pip install -e .
```

No root permission is required. The first `pip install -e .` may need local build tooling (or access to a package index if it is missing); after installation, DataGate commands run offline and make no network calls. You can also run without installing:

```bash
python -m datagate --help
```

### 1. Inspect an incoming file

```bash
datagate inspect examples/incoming_customers.csv --out build/incoming
```

Creates:

- `build/incoming/profile.json` — portable profile snapshot.
- `build/incoming/report.html` — offline HTML report.

### 2. Detect schema drift

```bash
datagate compare examples/baseline.profile.json build/incoming/profile.json --out build/drift
```

The included example changes `email` to `customer_email`. `examples/baseline.profile.json` is the profile snapshot generated from the synthetic baseline. DataGate should suggest that mapping, but it will not silently rename the field. Regenerate the baseline snapshot with `datagate inspect examples/baseline_customers.csv --out build/baseline` and copy `build/baseline/profile.json` over `examples/baseline.profile.json` when intentionally updating the fixture.

### 3. Validate against a contract

```bash
datagate validate examples/incoming_customers.csv \
  --contract examples/customers.contract.json \
  --out build/validation
```

The sample file intentionally contains bad values, so the command exits with status `1` after writing its report. In CI, a non-zero exit code can block an import or deployment.

### 4. Clean only explicitly authorized fields

```bash
datagate clean examples/incoming_customers.csv \
  --contract examples/customers.contract.json \
  --out build/cleaned_customers.csv
```

Creates `build/cleaned_customers.csv` and `build/cleaned_customers.csv.audit.json`. It trims configured fields and normalizes email/country case. It does **not** drop rows, invent values, or overwrite the original input.

### Use as a GitHub Action

The repository includes a composite action for validating a dataset in CI. In a consuming repository:

```yaml
name: Data intake gate
on: [push, pull_request]
jobs:
  validate-data:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7.0.1
      - uses: <OWNER>/MEGA-DATAGATE@v0.1.0
        with:
          input: data/incoming.csv
          contract: data/contracts/incoming.contract.json
          report-directory: .datagate/incoming-report
```

The action uploads a value-free JSON/HTML report artifact and fails the job if the contract is not satisfied. Replace `<OWNER>` and the tag with the repository owner and a release tag after publishing one.

### 5. Generate a draft contract

```bash
datagate contract-init build/incoming/profile.json --out build/draft.contract.json
```

A generated contract is only a draft. Review its inferred types and nullability before using it as a production gate.

## Command reference

```text
datagate inspect INPUT [--out DIRECTORY]
datagate compare BASELINE_PROFILE CURRENT_PROFILE [--out DIRECTORY]
datagate contract-init PROFILE_JSON --out NEW_CONTRACT_JSON
datagate validate INPUT --contract CONTRACT_JSON [--out DIRECTORY]
datagate clean INPUT --contract CONTRACT_JSON --out NEW_OUTPUT_FILE
```

Supported input formats: `.csv`, `.tsv`, `.jsonl`, `.ndjson`.

## Contract format

```json
{
  "format": "datagate-contract/v1",
  "dataset": "customers",
  "strict_columns": false,
  "fields": {
    "customer_id": {
      "type": "string",
      "required": true,
      "nullable": false,
      "unique": true,
      "pattern": "^C[0-9]{3}$",
      "trim": true
    },
    "email": {
      "type": "email",
      "required": true,
      "nullable": false,
      "unique": true,
      "trim": true,
      "case": "lower"
    },
    "age": {
      "type": "integer",
      "nullable": true,
      "min": 0,
      "max": 120
    }
  }
}
```

Supported types: `string`, `integer`, `number`, `boolean`, `email`, `date`, `url`, `uuid`, `ip` (ISO `YYYY-MM-DD`).

Validation rules: `required`, `nullable`, `unique`, `min`, `max`, `allowed`, `pattern`, `strict_columns`.

Explicit cleaning rules: `trim`, `empty_as_null`, and `case` (`lower`, `upper`, or `title`). Validation does not modify data. Cleaning does not claim that a cleaned file is valid; run `validate` again after cleaning.

## Reports and privacy

- Profiles do not store raw cell values.
- Validation examples contain rule IDs, field names, row numbers, and explanations, not cell values.
- The CLI does not send telemetry or make network requests.
- Uniqueness validation uses a temporary SQLite file and deletes its temporary directory after the run. This is ordinary temporary-file cleanup, not cryptographic secure erasure; consider your device's storage policy before validating highly sensitive data.
- HTML reports are self-contained and have no external assets or scripts.
- Input files remain untouched. Cleaning refuses source/output path collisions and existing output files.

Do not put credentials, access tokens, or production personal data into public sample files or Git history. The local-first design is not a substitute for the user's own storage, access-control, retention, or backup policies.

## Development

```bash
python -m unittest discover -s tests -v
python -m datagate --help
python scripts/benchmark.py --rows 200000
```

The CI matrix tests Python 3.11, 3.12, 3.13, and 3.14. Benchmark output is descriptive, not a universal performance claim; run it on the hardware and file shapes that matter to your workload.

## Current MVP boundaries

- File adapters: CSV, TSV, JSONL, NDJSON only. XLSX, Parquet, databases, cloud object stores, and streaming message queues are not in MVP.
- No GUI yet. The current interface is CLI plus offline HTML reports.
- Type inference is heuristic and should be treated as a profile, not a schema authority.
- Rename suggestions are advisory and based on field-name similarity plus inferred-type compatibility; review before mapping.
- Uniqueness uses temporary disk space proportional to the number and size of unique values.
- Email validation is syntactic and does not send mail or verify mailbox existence.
- Date validation accepts ISO calendar dates only.
- Cleaning transformations are intentionally small and deterministic; advanced joins, fuzzy entity resolution, and row deletion are out of scope.

## Roadmap

See [PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md), [ARCHITECTURE.md](docs/ARCHITECTURE.md), [CONTRIBUTING.md](CONTRIBUTING.md), and [ROADMAP.md](docs/ROADMAP.md).

## License

MIT. See [LICENSE](LICENSE).
