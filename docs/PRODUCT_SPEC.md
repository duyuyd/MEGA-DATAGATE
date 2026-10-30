# MEGA DataGate — Product Specification

- Status: MVP / alpha
- Product type: Local-first data intake and quality gate
- Initial interface: CLI + offline HTML/JSON reports
- Runtime: Python 3.11+, standard library only
- Supported inputs in MVP: CSV, TSV, JSONL, NDJSON

## 1. Product thesis

DataGate helps a person or team decide whether an unfamiliar or newly delivered dataset is safe to use, what changed since the previous delivery, which rules it violates, and which explicitly approved normalizations can be applied.

The product is not “a tool that checks more rows.” It is a repeatable intake workflow that replaces scattered one-off inspection and repair scripts.

## 2. Problem and jobs to be done

### Primary problem

Data arrives from vendors, customers, exports, research groups, operational systems, and hand-maintained spreadsheets. Its columns and values are not stable. A consumer must rediscover the structure, detect changes, implement checks, repair formatting, and explain the results every time.

### Jobs to be done

- “When I receive a file I have never seen, show me its structure and quality without uploading it anywhere.”
- “When I receive this month's file, tell me what changed compared with the approved baseline.”
- “Before I import the data, validate it against rules my team can review in Git.”
- “Normalize predictable formatting differences without losing rows or modifying the source.”
- “Give me an artifact I can share with a teammate or attach to a CI run without exposing raw cell values.”

## 3. Target users

1. **Data / analytics engineers** who ingest recurring CSV or JSON exports and need schema-drift and validation gates.
2. **Software engineers** who import vendor/customer datasets into applications or databases.
3. **Operations and research analysts** who receive inconsistent spreadsheets and need a repeatable intake report.
4. **Maintainers of small data pipelines** who want a local CLI without bringing in a large dataframe runtime.

Not the initial target: enterprise governance teams requiring catalog, lineage, role-based approvals, distributed execution, or managed cloud pipelines.

## 4. Core product promise

“Understand a dataset, compare it with what you expected, validate it against explicit rules, and produce a reviewed output — locally, without silently changing your data.”

## 5. MVP user journey

1. `inspect`: stream the input and create `profile.json` plus `report.html`.
2. `compare`: compare a baseline profile and the incoming profile; report added/missing/type-changed fields and probable renames.
3. `contract-init`: optionally generate an editable starting contract from a profile.
4. `validate`: run contract checks and produce JSON/HTML reports. Invalid data returns exit code 1 so CI can fail.
5. `clean`: apply only transformations declared in the contract to a new CSV/TSV file and write an audit sidecar. It never overwrites the source.
6. Re-run `validate` against the output to confirm the result.

## 6. MVP functional requirements

| ID | Requirement | MVP behavior | Acceptance evidence |
|---|---|---|---|
| FR-01 | Local intake | No network calls or service account | Run commands offline |
| FR-02 | CSV/TSV/JSONL reader | Streaming row iteration | Unit tests for each supported format |
| FR-03 | Profile | Rows, columns, nulls, inferred type, cardinality, numeric range | JSON + HTML report |
| FR-04 | Bounded cardinality | Exact through 512 values, then fixed 4,096-register HLL | Test at 20,000 unique values |
| FR-05 | Schema comparison | Added, removed, type changes, rename candidates | Example maps `email` → `customer_email` |
| FR-06 | Contract validation | Required, nullable, type, unique, min/max, allowed, regex, strict columns | Contract tests |
| FR-07 | Privacy | Never include raw cell values in profile or validation examples | Tests assert sample values absent |
| FR-08 | Safe clean | trim, empty_as_null, lower/upper/title; new output only | Tests assert input is not overwritten |
| FR-09 | Auditability | JSON audit records counts and declared operations, no raw values | Sidecar file exists and has no input cell values |
| FR-10 | CI behavior | Valid=0, invalid=1, operational error=2 | CLI tests / workflow |

## 7. Non-functional requirements

- **Memory:** profile path must not retain every row or every unique value. Cardinality is bounded per column. Exact row-level uniqueness uses temporary SQLite storage and therefore trades RAM for disk.
- **Privacy:** no telemetry, upload, raw-value samples, or external report assets in MVP.
- **Safety:** source files remain immutable; transformations are explicit, deterministic, auditable, and written to a new path.
- **Portability:** Python 3.11+ and standard library only; target Windows, macOS, Linux, and Termux where a supported Python runtime is available.
- **Reproducibility:** profile, drift, validation, and audit reports are machine-readable JSON.
- **Usability:** CLI help and a runnable example dataset are included.

## 8. Differentiation and market reality

Data cleaning, validation, reconciliation, and dataframe schemas already have established open-source tools. OpenRefine offers interactive transformations, clustering, and reconciliation; Frictionless offers file/data validation; Pandera offers expressive dataframe schemas and checks. DataGate must not claim to invent these capabilities or replace them feature-for-feature.

The hypothesis to validate is the combination and default behavior:

- one small local workflow from intake through drift review, contract validation, and explicit normalization;
- no data upload and no runtime dependency stack for the first-use path;
- change suggestions that are reviewable and never silently applied;
- safe output and audit generation designed into the cleaning command;
- identical JSON outputs that can be consumed by local tooling and GitHub Actions.

The MVP proves that workflow technically. It does not yet prove market demand. That requires interviews and repeated use by people outside the maintainers.

## 9. Success metrics

### Product validation (first 60–90 days)

- 10 external users complete the core inspect → compare/validate workflow on their own non-sensitive dataset.
- 5 independent repositories or pipelines run DataGate as part of intake or CI.
- 3 external contributors submit a merged issue/PR, rule, adapter, test, or documentation improvement.
- At least 50% of pilot users run the tool more than once on a recurring dataset.
- Every public performance claim is backed by a benchmark script, dataset generator, environment description, and raw result artifact.

These are goals, not existing achievements.

### Technical quality

- CI passes Python 3.11–3.14.
- No raw input values appear in JSON or HTML profile/validation outputs.
- Source-overwrite tests pass.
- Benchmark includes throughput, elapsed time, peak traced Python memory, input size, and row count.
- Schema suggestions expose confidence and remain non-destructive.

## 10. Out of scope for MVP

- XLSX, Parquet, database, S3/object storage, API, Kafka, or cloud adapters.
- GUI / hosted SaaS / user accounts.
- Automatic schema remapping or silent row deletion.
- Fuzzy entity resolution that merges person/customer records without human review.
- Email deliverability verification or network-based identity checks.
- Credential checking, account access, cookie/token handling, or authentication workflows.
- Multi-user approvals, catalog, lineage, or enterprise governance.

## 11. Release gate

An MVP release may be tagged only when:

1. Tests pass on the declared Python matrix.
2. Quick-start commands work from a clean checkout.
3. Examples produce the documented reports and exit codes.
4. Source-overwrite and no-raw-value privacy tests pass.
5. README, spec, limitations, and contribution guide accurately describe what is implemented.
6. No secrets or real user datasets are present in the repository history.
