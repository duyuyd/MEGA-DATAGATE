from __future__ import annotations

import ipaddress
import json
import math
import re
import uuid
from collections import Counter
from datetime import date
from urllib.parse import urlparse
from pathlib import Path
from typing import Any

from . import __version__
from .errors import DataGateError
from .readers import open_dataset
from .sketches import HybridCardinality

_INT = re.compile(r"^[+-]?\d+$")
_FLOAT = re.compile(r"^[+-]?(?:\d+\.\d*|\d*\.\d+|\d+)(?:[eE][+-]?\d+)?$")
_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-8][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$")


def _kind(value: str) -> str:
    candidate = value.strip()
    lowered = candidate.lower()
    if lowered in {"true", "false", "yes", "no"}:
        return "boolean"
    if _INT.fullmatch(candidate):
        return "integer"
    if _FLOAT.fullmatch(candidate):
        try:
            if math.isfinite(float(candidate)):
                return "number"
        except OverflowError:
            pass
    if "@" in candidate and _EMAIL.fullmatch(candidate):
        return "email"
    if len(candidate) == 36 and _UUID.fullmatch(candidate):
        return "uuid"
    if "://" in candidate:
        try:
            parsed_url = urlparse(candidate)
            if parsed_url.scheme in {"http", "https"} and bool(parsed_url.hostname):
                return "url"
        except ValueError:
            pass
    if (":" in candidate or candidate.count(".") == 3) and re.fullmatch(r"[0-9a-fA-F:.]+", candidate):
        try:
            ipaddress.ip_address(candidate)
            return "ip"
        except ValueError:
            pass
    if len(candidate) == 10 and candidate[4] == "-" and candidate[7] == "-":
        try:
            date.fromisoformat(candidate)
            return "date"
        except ValueError:
            pass
    return "string"


def _infer_type(counter: Counter[str], non_null: int) -> str:
    if non_null == 0:
        return "unknown"
    kinds = {kind for kind, count in counter.items() if count}
    if kinds == {"integer"}:
        return "integer"
    if kinds <= {"integer", "number"}:
        return "number"
    if len(kinds) == 1:
        return next(iter(kinds))
    return "mixed"


def profile_file(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    dataset = open_dataset(source)
    columns: dict[str, dict[str, Any]] = {}
    for name in dataset.columns:
        columns[name] = {
            "name": name,
            "null_count": 0,
            "non_null_count": 0,
            "kinds": Counter(),
            "cardinality": HybridCardinality(),
            "minimum": None,
            "maximum": None,
        }
    row_count = 0
    row_errors: Counter[str] = Counter()
    for record in dataset.rows():
        row_count += 1
        if record.error:
            row_errors[record.error] += 1
        for name in record.values:
            if name not in columns:
                columns[name] = {
                    "name": name,
                    "null_count": row_count - 1,
                    "non_null_count": 0,
                    "kinds": Counter(),
                    "cardinality": HybridCardinality(),
                    "minimum": None,
                    "maximum": None,
                }
        for name, stats in columns.items():
            raw_value = record.values.get(name)
            if raw_value is None or (isinstance(raw_value, str) and raw_value.strip() == ""):
                stats["null_count"] += 1
                continue
            value = str(raw_value)
            stats["non_null_count"] += 1
            kind = _kind(value)
            stats["kinds"][kind] += 1
            stats["cardinality"].add(value)
            if kind in {"integer", "number"}:
                numeric = int(value) if kind == "integer" else float(value)
                stats["minimum"] = numeric if stats["minimum"] is None else min(stats["minimum"], numeric)
                stats["maximum"] = numeric if stats["maximum"] is None else max(stats["maximum"], numeric)

    fields = []
    for name, stats in columns.items():
        non_null = stats["non_null_count"]
        nulls = stats["null_count"]
        total = non_null + nulls
        cardinality: HybridCardinality = stats["cardinality"]
        fields.append({
            "name": name,
            "inferred_type": _infer_type(stats["kinds"], non_null),
            "row_count_observed": total,
            "null_count": nulls,
            "null_pct": round((nulls / total) * 100, 3) if total else 0.0,
            "non_null_count": non_null,
            "distinct_estimate": cardinality.estimate(),
            "distinct_is_exact": cardinality.exact,
            "unique_ratio_estimate": round(min(1.0, cardinality.estimate() / non_null), 5) if non_null else 0.0,
            "minimum_numeric": stats["minimum"],
            "maximum_numeric": stats["maximum"],
        })

    return {
        "format": "datagate-profile/v1",
        "datagate_version": __version__,
        "source_name": source.name,
        "source_format": dataset.format,
        "rows": row_count,
        "column_count": len(fields),
        "row_errors": dict(row_errors),
        "fields": fields,
        "privacy": "No raw cell values are stored in this profile.",
        "algorithms": {
            "distinct_count": "exact up to 512 values per column, then HyperLogLog (p=12)",
            "memory": "bounded cardinality sketch per column; rows are streamed",
        },
    }


def save_profile(profile: dict[str, Any], output_dir: str | Path) -> tuple[Path, Path]:
    from .reporting import write_html_report

    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / "profile.json"
    html_path = directory / "report.html"
    json_path.write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_html_report(profile, html_path, title="Data profile")
    return json_path, html_path
