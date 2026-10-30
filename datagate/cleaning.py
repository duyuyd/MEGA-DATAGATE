from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .contracts import load_contract
from .errors import DataGateError
from .readers import open_dataset


def clean_csv(path: str | Path, contract_path: str | Path, output: str | Path) -> dict[str, Any]:
    source = Path(path).resolve()
    target = Path(output).resolve()
    if source == target:
        raise DataGateError("Output must be a different path; DataGate never overwrites the source file.")
    audit_path = target.with_name(target.name + ".audit.json")
    if target.exists():
        raise DataGateError(f"Refusing to overwrite existing output: {target}")
    if audit_path.exists():
        raise DataGateError(f"Refusing to overwrite existing audit file: {audit_path}")
    if source.suffix.lower() not in {".csv", ".tsv"}:
        raise DataGateError("Safe cleaning in MVP currently supports CSV and TSV input only.")
    dataset = open_dataset(source)
    contract = load_contract(contract_path)
    specs = contract["fields"]
    target.parent.mkdir(parents=True, exist_ok=True)
    temp_target = target.with_name(target.name + ".datagate-tmp")
    if temp_target.exists():
        raise DataGateError(f"Temporary output already exists; remove it after checking: {temp_target}")
    changed: Counter[str] = Counter()
    rows_written = 0
    try:
        with temp_target.open("w", encoding="utf-8", newline="") as handle:
            delimiter = "\t" if source.suffix.lower() == ".tsv" else ","
            writer = csv.DictWriter(handle, fieldnames=dataset.columns, extrasaction="ignore", delimiter=delimiter, lineterminator="\n")
            writer.writeheader()
            for record in dataset.rows():
                if record.error:
                    raise DataGateError(f"Cannot safely clean malformed row {record.number}: {record.error}. Source was not changed.")
                output_row: dict[str, str] = {}
                for field in dataset.columns:
                    raw = record.values.get(field)
                    value = "" if raw is None else str(raw)
                    spec = specs.get(field, {})
                    before = value
                    if spec.get("trim"):
                        value = value.strip()
                    case = spec.get("case")
                    if case == "lower":
                        value = value.lower()
                    elif case == "upper":
                        value = value.upper()
                    elif case == "title":
                        value = value.title()
                    elif case not in {None, "lower", "upper", "title"}:
                        raise DataGateError(f"Unsupported case transform '{case}' for field '{field}'.")
                    if spec.get("empty_as_null") and value.strip() == "":
                        value = ""
                    if value != before:
                        changed[field] += 1
                    output_row[field] = value
                writer.writerow(output_row)
                rows_written += 1
        temp_target.replace(target)
    except Exception:
        if temp_target.exists():
            temp_target.unlink()
        raise

    audit = {
        "format": "datagate-clean-audit/v1",
        "source_name": source.name,
        "output_name": target.name,
        "rows_written": rows_written,
        "changed_cells_by_field": dict(changed),
        "changed_cell_count": sum(changed.values()),
        "transform_policy": "Only explicitly declared trim/case/empty_as_null operations were applied.",
        "raw_values_recorded": False,
    }
    audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return audit
