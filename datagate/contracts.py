from __future__ import annotations

import ipaddress
import json
import math
import re
import sqlite3
import uuid
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .errors import ContractError, DataGateError
from .readers import open_dataset

_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_TYPE_NAMES = {"string", "integer", "number", "boolean", "email", "date", "url", "uuid", "ip"}
_TOP_LEVEL_KEYS = {"format", "dataset", "strict_columns", "notes", "fields"}
_FIELD_KEYS = {"type", "required", "nullable", "unique", "min", "max", "allowed", "pattern", "trim", "empty_as_null", "case"}


def load_contract(path: str | Path) -> dict[str, Any]:
    try:
        contract = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"Could not read contract JSON: {exc}") from exc
    if not isinstance(contract, dict) or contract.get("format") != "datagate-contract/v1":
        raise ContractError("Contract must be a JSON object with format='datagate-contract/v1'.")
    unknown_top_level = set(contract) - _TOP_LEVEL_KEYS
    if unknown_top_level:
        raise ContractError(f"Unknown contract key(s): {', '.join(sorted(unknown_top_level))}.")
    fields = contract.get("fields")
    if not isinstance(fields, dict) or not fields:
        raise ContractError("Contract must define a non-empty 'fields' object.")
    if "strict_columns" in contract and not isinstance(contract["strict_columns"], bool):
        raise ContractError("'strict_columns' must be true or false.")
    for name, spec in fields.items():
        if not isinstance(name, str) or not name or not isinstance(spec, dict):
            raise ContractError("Each contract field must have a non-empty name and an object of rules.")
        unknown_field_keys = set(spec) - _FIELD_KEYS
        if unknown_field_keys:
            raise ContractError(f"Field '{name}' has unknown rule(s): {', '.join(sorted(unknown_field_keys))}.")
        kind = spec.get("type", "string")
        if not isinstance(kind, str) or kind not in _TYPE_NAMES:
            raise ContractError(f"Unsupported type '{kind}' for field '{name}'. Supported: {', '.join(sorted(_TYPE_NAMES))}.")
        for key in ("required", "nullable", "unique", "trim", "empty_as_null"):
            if key in spec and not isinstance(spec[key], bool):
                raise ContractError(f"Field '{name}': '{key}' must be true or false.")
        for key in ("min", "max"):
            if key in spec and (isinstance(spec[key], bool) or not isinstance(spec[key], (int, float)) or not math.isfinite(spec[key])):
                raise ContractError(f"Field '{name}': '{key}' must be a finite number.")
        if ("min" in spec or "max" in spec) and kind not in {"integer", "number"}:
            raise ContractError(f"Field '{name}': min/max can only be used with integer or number types.")
        if "min" in spec and "max" in spec and spec["min"] > spec["max"]:
            raise ContractError(f"Field '{name}': min cannot be greater than max.")
        if "pattern" in spec:
            if not isinstance(spec["pattern"], str):
                raise ContractError(f"Field '{name}': 'pattern' must be a string.")
            try:
                re.compile(spec["pattern"])
            except re.error as exc:
                raise ContractError(f"Invalid regex pattern for field '{name}': {exc}") from exc
        if "allowed" in spec:
            if not isinstance(spec["allowed"], list):
                raise ContractError(f"Field '{name}': 'allowed' must be a JSON array.")
            if any(not isinstance(value, (str, int, float, bool)) and value is not None for value in spec["allowed"]):
                raise ContractError(f"Field '{name}': allowed values must be JSON scalars.")
        if "case" in spec and (not isinstance(spec["case"], str) or spec["case"] not in {"lower", "upper", "title"}):
            raise ContractError(f"Field '{name}': case must be lower, upper, or title.")
    return contract


def _is_type(value: str, kind: str) -> bool:
    if kind == "string":
        return True
    if kind == "integer":
        return bool(re.fullmatch(r"[+-]?\d+", value.strip()))
    if kind == "number":
        try:
            number = float(value)
            return number == number and number not in {float("inf"), float("-inf")}
        except ValueError:
            return False
    if kind == "boolean":
        return value.strip().lower() in {"true", "false", "yes", "no", "1", "0"}
    if kind == "email":
        return bool(_EMAIL.fullmatch(value.strip()))
    if kind == "url":
        try:
            parsed = urlparse(value.strip())
            return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
        except ValueError:
            return False
    if kind == "uuid":
        try:
            uuid.UUID(value.strip())
            return True
        except ValueError:
            return False
    if kind == "ip":
        try:
            ipaddress.ip_address(value.strip())
            return True
        except ValueError:
            return False
    if kind == "date":
        try:
            date.fromisoformat(value.strip())
            return True
        except ValueError:
            return False
    return False


class IssueCollector:
    def __init__(self, example_limit: int = 12) -> None:
        self.counts: Counter[tuple[str, str]] = Counter()
        self.examples: list[dict[str, Any]] = []
        self.example_limit = example_limit
        self.total = 0

    def add(self, code: str, field: str | None, row: int | None, message: str) -> None:
        key = (code, field or "")
        self.counts[key] += 1
        self.total += 1
        if len(self.examples) < self.example_limit:
            self.examples.append({"code": code, "field": field, "row": row, "message": message})

    def summary(self) -> list[dict[str, Any]]:
        return [
            {"code": code, "field": field or None, "count": count}
            for (code, field), count in sorted(self.counts.items())
        ]


def validate_file(path: str | Path, contract_path: str | Path) -> dict[str, Any]:
    source = Path(path)
    contract = load_contract(contract_path)
    dataset = open_dataset(source)
    specs: dict[str, dict[str, Any]] = contract["fields"]
    fields = list(specs)
    collector = IssueCollector()
    missing_columns = [] if dataset.format == "jsonl" else [
        field for field, spec in specs.items() if spec.get("required", True) and field not in dataset.columns
    ]
    for field in missing_columns:
        collector.add("required_column_missing", field, None, "Required column is not present in the input header.")
    unexpected_columns: set[str] = set()
    if contract.get("strict_columns") and dataset.format != "jsonl":
        for field in dataset.columns:
            if field not in specs:
                unexpected_columns.add(field)
                collector.add("unexpected_column", field, None, "Column is not declared in the strict contract.")

    row_count = 0
    checks = 0
    with tempfile.TemporaryDirectory(prefix="datagate-unique-") as tmpdir:
        db_path = Path(tmpdir) / "unique.sqlite3"
        connection = sqlite3.connect(db_path)
        try:
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=OFF")
            connection.execute("CREATE TABLE seen (field TEXT NOT NULL, value TEXT NOT NULL, UNIQUE(field, value))")
            for record in dataset.rows():
                row_count += 1
                if record.error:
                    collector.add(record.error, None, record.number, "Input row could not be read cleanly.")
                    continue
                if contract.get("strict_columns") and dataset.format == "jsonl":
                    for field_name in record.values:
                        if field_name not in specs and field_name not in unexpected_columns:
                            unexpected_columns.add(field_name)
                            collector.add("unexpected_column", field_name, record.number, "Field is not declared in the strict contract.")
                for field, spec in specs.items():
                    if dataset.format == "csv" and field not in dataset.columns:
                        continue
                    checks += 1
                    present = field in record.values
                    raw = record.values.get(field)
                    empty = not present or raw is None or (isinstance(raw, str) and raw.strip() == "")
                    if empty:
                        if dataset.format == "jsonl" and not present and spec.get("required", True):
                            collector.add("required_value_missing", field, record.number, "Required field is absent from this JSONL record.")
                        elif spec.get("nullable", True) is False:
                            collector.add("null_not_allowed", field, record.number, "A value is required for this field.")
                        continue
                    value = str(raw)
                    kind = spec.get("type", "string")
                    if not _is_type(value, kind):
                        collector.add("type_mismatch", field, record.number, f"Value does not match declared type '{kind}'.")
                        continue
                    if "allowed" in spec and value not in {str(item) for item in spec["allowed"]}:
                        collector.add("value_not_allowed", field, record.number, "Value is not in the allowed set.")
                    if "pattern" in spec and not re.search(spec["pattern"], value):
                        collector.add("pattern_mismatch", field, record.number, "Value does not match the declared pattern.")
                    numeric: float | None = None
                    if kind in {"integer", "number"}:
                        numeric = int(value) if kind == "integer" else float(value)
                    if numeric is not None and "min" in spec and numeric < float(spec["min"]):
                        collector.add("below_minimum", field, record.number, "Numeric value is below the declared minimum.")
                    if numeric is not None and "max" in spec and numeric > float(spec["max"]):
                        collector.add("above_maximum", field, record.number, "Numeric value is above the declared maximum.")
                    if spec.get("unique"):
                        cursor = connection.execute("INSERT OR IGNORE INTO seen(field, value) VALUES (?, ?)", (field, value))
                        if cursor.rowcount == 0:
                            collector.add("duplicate_value", field, record.number, "Value duplicates a previous row.")
            connection.commit()
        finally:
            connection.close()

    return {
        "format": "datagate-validation/v1",
        "source_name": source.name,
        "contract_name": Path(contract_path).name,
        "rows": row_count,
        "checks": checks,
        "valid": collector.total == 0,
        "issue_count": collector.total,
        "issues": collector.summary(),
        "examples": collector.examples,
        "privacy": "Cell values are not included in validation reports; only row numbers and rule identifiers are recorded.",
    }


def contract_from_profile(profile: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(profile, dict) or profile.get("format") != "datagate-profile/v1":
        raise DataGateError("Input must be a DataGate profile/v1 JSON file.")
    profile_fields = profile.get("fields")
    if not isinstance(profile_fields, list):
        raise DataGateError("Profile fields must be a JSON array.")
    fields: dict[str, Any] = {}
    for item in profile_fields:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            raise DataGateError("Each profile field must contain a string name.")
        kind = item.get("inferred_type", "string")
        if kind not in _TYPE_NAMES:
            kind = "string"
        spec: dict[str, Any] = {
            "type": kind,
            "required": True,
            "nullable": item.get("null_count", 0) > 0,
            "unique": False,
        }
        if kind in {"integer", "number"}:
            if item.get("minimum_numeric") is not None:
                spec["min"] = item["minimum_numeric"]
            if item.get("maximum_numeric") is not None:
                spec["max"] = item["maximum_numeric"]
        fields[item["name"]] = spec
    return {
        "format": "datagate-contract/v1",
        "dataset": Path(profile.get("source_name", "dataset")).stem,
        "strict_columns": False,
        "fields": fields,
        "notes": "Draft generated from observed data. Review every rule before using it as a production gate.",
    }


def write_contract(contract: dict[str, Any], output: str | Path) -> Path:
    target = Path(output)
    if target.exists():
        raise DataGateError(f"Refusing to overwrite existing file: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(contract, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target
