# Publishing checklist

The MVP ZIP is prepared for a **separate repository** named `MEGA-DATAGATE`. It is not automatically pushed and does not modify the existing private MEGA CHECKER repository.

## Before making the repository public

- [ ] Create a new GitHub repository named `MEGA-DATAGATE`.
- [ ] Choose Public only after reviewing the source tree and Git history. Do not make the existing private MEGA CHECKER repository public as a shortcut.
- [ ] Set the repository description to: `Local-first data intake: profile, schema drift, contract validation, and safe cleaning.`
- [ ] Add topics: `data-quality`, `data-validation`, `schema-drift`, `data-profiling`, `csv`, `jsonl`, `local-first`.
- [ ] Keep Issues enabled; enable Discussions when there is capacity to moderate and answer questions.
- [ ] Keep Actions enabled with least-privilege workflow permissions.
- [ ] Confirm the synthetic examples contain no real personal data or secrets.
- [ ] Review the license, security notes, and the limitations in README.
- [ ] Replace `<OWNER>` placeholders in `.github/ISSUE_TEMPLATE/config.yml` and documentation examples.

## Initial push (one-command helper)

From the extracted project directory, install/authenticate GitHub CLI (`gh auth login`), then run:

```bash
bash scripts/publish_github.sh
```

The script creates a **separate public** `MEGA-DATAGATE` repository only after the operator types `PUBLIC`. It never modifies or publishes `MEGA-CHECKER-ULTIMATE`. Review the remote first if `MEGA-DATAGATE` already exists.

## First release

1. Wait for the Python 3.11–3.14 CI matrix to pass on the new repository.
2. Run the quick-start and the included benchmark on a second machine/OS.
3. Resolve issues discovered by at least a few external testers.
4. Only then create a `v0.1.0` release/tag. The documented GitHub Action example references that tag.
5. Do not advertise performance figures without publishing the environment, command, and benchmark JSON.

## Community launch

- Pin the README quick-start and the product spec.
- Keep a small number of genuine `good first issue` tasks with expected behavior and tests.
- Ask users about their intake workflow; do not ask them to upload private datasets.
- Prioritize recurring problems reported by multiple users over feature requests from maintainers alone.
