# External user validation plan

The MVP's main risk is not whether the code runs; it is whether the intake workflow solves a repeated problem well enough that someone adopts it.

## Recruit

Invite 8–12 people who regularly receive CSV/JSON exports: data engineers, analysts, software engineers, operations teams, and research groups. Ask for synthetic or anonymized examples only.

## 20-minute task

Ask a participant to:

1. Inspect a file they normally receive.
2. Compare it to a previous schema or baseline.
3. Identify whether a change is a rename, an added field, a missing field, or a type change.
4. Define one or two contract rules.
5. Validate the new file.
6. Decide whether any suggested normalization is safe.

Do not teach the user the correct answer before observing the task.

## Record

- Time to first useful report.
- Whether the report explains the problem without reading raw code.
- False-positive and false-negative schema-drift suggestions.
- Rules the participant expected but could not express.
- Number of steps they would otherwise script manually.
- Whether they would use the tool again on their next delivery.
- Installation friction by OS, Python version, and execution environment.

## Decision thresholds

Continue investment in the workflow if at least 6 of 10 participants complete the core task without maintainer intervention and at least 5 say they would use it on a recurring dataset. Revisit the product thesis if users primarily ask for GUI spreadsheet editing, database lineage, or managed ETL rather than local intake and CI checks.

These thresholds are proposed decision criteria, not measured outcomes.
