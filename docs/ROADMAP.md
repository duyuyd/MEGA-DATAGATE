# Roadmap

Roadmap items are hypotheses, not promises. Prioritize based on external usage and issues, not feature count.

## Now — MVP 0.1

- [x] CSV, TSV, JSONL, NDJSON readers
- [x] Streaming profile and bounded cardinality sketch
- [x] Schema comparison and advisory rename suggestions
- [x] Versioned JSON contracts
- [x] Disk-backed unique validation
- [x] Safe CSV/TSV cleaning with audit sidecar
- [x] Privacy-conscious JSON and offline HTML reports
- [x] CLI, sample dataset, tests, Python matrix CI
- [ ] First external pilot feedback

## Next — validate the problem

- Collect anonymized issue descriptions and input-shape requirements from external users; do not ask for production data.
- Add a contract schema document and editor diagnostics.
- Evaluate schema rename precision/recall on a labeled synthetic benchmark.
- Add a machine-readable `--format json` stdout mode for CI and scripting.
- Add optional row-level quarantine output only after retention and privacy semantics are designed.
- Add a polished GitHub Action wrapper around the stable CLI/JSON contract, not a separate validation engine.

## Later — only if users request it

- XLSX/Parquet adapters as optional extras.
- Desktop review UI for accepting/rejecting drift mappings and cleaning plans.
- Plugin API for custom checks and format adapters.
- Database target adapters and import transaction previews.
- Cross-platform binary distribution if Python installation friction is a proven blocker.
- Rust acceleration only for benchmarked hot paths.

## Explicit non-goals

- A cloud upload service as the default.
- Automatic irreversible repair.
- Feature parity with mature data-preparation or dataframe ecosystems.
- Optimizing for vanity metrics such as number of modules or lines of code.
