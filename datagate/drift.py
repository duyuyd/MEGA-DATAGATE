from __future__ import annotations

import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .errors import DataGateError

_NUMERIC = {"integer", "number"}


def _name_similarity(left: str, right: str) -> float:
    a, b = left.lower().replace("-", "_").replace(" ", "_").split("_"), right.lower().replace("-", "_").replace(" ", "_").split("_")
    a = {part for part in a if part}
    b = {part for part in b if part}
    jaccard = len(a & b) / len(a | b) if a | b else 0.0
    sequence = SequenceMatcher(None, left.lower(), right.lower()).ratio()
    return 0.65 * sequence + 0.35 * jaccard


def _compatibility(left: str, right: str) -> float:
    if left == right:
        return 1.0
    if left in _NUMERIC and right in _NUMERIC:
        return 0.8
    if "unknown" in {left, right}:
        return 0.5
    if "mixed" in {left, right}:
        return 0.45
    return 0.0


def compare_profiles(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    for item in (baseline, current):
        if not isinstance(item, dict) or item.get("format") != "datagate-profile/v1":
            raise DataGateError("Both inputs must be DataGate profile/v1 JSON files.")
    def field_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
        fields = snapshot.get("fields")
        if not isinstance(fields, list):
            raise DataGateError("Profile fields must be a JSON array.")
        result: dict[str, dict[str, Any]] = {}
        for field in fields:
            if not isinstance(field, dict) or not isinstance(field.get("name"), str) or not isinstance(field.get("inferred_type"), str):
                raise DataGateError("Each profile field must include string 'name' and 'inferred_type' values.")
            if field["name"] in result:
                raise DataGateError(f"Profile contains duplicate field name: {field['name']}")
            result[field["name"]] = field
        return result

    old = field_map(baseline)
    new = field_map(current)
    common = sorted(old.keys() & new.keys())
    added = sorted(new.keys() - old.keys())
    removed = sorted(old.keys() - new.keys())
    type_changes = [
        {"field": name, "from": old[name].get("inferred_type"), "to": new[name].get("inferred_type")}
        for name in common if old[name].get("inferred_type") != new[name].get("inferred_type")
    ]
    candidates = []
    for old_name in removed:
        for new_name in added:
            name_score = _name_similarity(old_name, new_name)
            type_score = _compatibility(old[old_name].get("inferred_type", "unknown"), new[new_name].get("inferred_type", "unknown"))
            score = 0.82 * name_score + 0.18 * type_score
            if score >= 0.48:
                candidates.append((score, old_name, new_name))
    candidates.sort(reverse=True)
    used_old: set[str] = set()
    used_new: set[str] = set()
    rename_suggestions = []
    for score, old_name, new_name in candidates:
        if old_name in used_old or new_name in used_new:
            continue
        used_old.add(old_name)
        used_new.add(new_name)
        rename_suggestions.append({
            "from": old_name,
            "to": new_name,
            "similarity_score": round(score, 3),
            "reason": "name similarity and inferred-type compatibility",
            "automatic_action": False,
        })

    return {
        "format": "datagate-drift/v1",
        "baseline_source": baseline.get("source_name"),
        "current_source": current.get("source_name"),
        "baseline_rows": baseline.get("rows", 0),
        "current_rows": current.get("rows", 0),
        "unchanged_fields": common,
        "added_fields": [name for name in added if name not in used_new],
        "removed_fields": [name for name in removed if name not in used_old],
        "type_changes": type_changes,
        "rename_suggestions": rename_suggestions,
        "note": "Rename suggestions are advisory only; DataGate never silently remaps columns.",
    }


def compare_profile_files(baseline_path: str | Path, current_path: str | Path) -> dict[str, Any]:
    try:
        baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
        current = json.loads(Path(current_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DataGateError(f"Could not read profile JSON: {exc}") from exc
    return compare_profiles(baseline, current)
