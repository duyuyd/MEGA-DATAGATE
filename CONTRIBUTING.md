# Contributing

Thank you for considering a contribution. DataGate should solve recurring data-intake problems for real users, not accumulate features without evidence.

## Before opening an issue

- Search existing issues first.
- Describe the input shape and the workflow that fails.
- Use synthetic or anonymized examples. Do not upload production personal data, credentials, tokens, or private customer records.
- State what outcome you expected and what happened instead.

## Good first contributions

- Add CSV/TSV/JSONL parser edge-case tests.
- Improve documentation or translated examples.
- Add synthetic datasets for schema drift evaluation.
- Add contract validation rules with tests and clear privacy semantics.
- Improve HTML accessibility without external network assets.
- Add benchmark scenarios with a reproducible generator.

## Development setup

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python -m datagate --help
```

No runtime dependency is required. Keep the test suite runnable with the Python standard library.

## Pull request expectations

- Explain the user problem and why the change belongs in DataGate.
- Add tests for behavior and edge cases.
- Preserve source immutability and no-raw-value report guarantees.
- Avoid silently applying mappings or destructive cleaning.
- Update README/spec/limitations when behavior changes.
- Include benchmark evidence for performance claims.
- Keep changes focused; avoid unrelated formatting churn.

## Design discussion

A good feature should answer all of these:

1. Who needs it and how often?
2. What work does it replace?
3. What is the failure mode if the heuristic is wrong?
4. Can the result be reviewed or rolled back?
5. Can it run locally with bounded resource use?
6. How will we test and benchmark it?
