# MVP release checklist

- [ ] CI green on Python 3.11, 3.12, 3.13, and 3.14.
- [ ] Quick start tested from a clean checkout.
- [ ] `scripts/run_demo.sh` produces profile, drift, validation, cleaned CSV, and audit artifacts.
- [ ] Invalid sample correctly exits 1; operational errors exit 2.
- [ ] Source path and existing output protection tests pass.
- [ ] Profile and validation reports contain no raw sample cell values.
- [ ] HTML output escapes source-controlled field names.
- [ ] Synthetic examples only; no real customer data or secrets.
- [ ] Benchmark JSON is reproducible and accurately caveated.
- [ ] Public repository topics, Issues, code of conduct, license, security policy, and contribution docs reviewed.
- [ ] No release tag until external pilot feedback is reviewed.
