from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .errors import InputFormatError


@dataclass
class RowRecord:
    number: int
    values: dict[str, Any]
    error: str | None = None


@dataclass
class DatasetStream:
    path: Path
    format: str
    columns: list[str]
    _rows: Iterator[RowRecord]

    def rows(self) -> Iterator[RowRecord]:
        yield from self._rows


def _detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv"}:
        return "csv"
    if suffix in {".jsonl", ".ndjson"}:
        return "jsonl"
    raise InputFormatError(
        f"Unsupported input extension '{suffix or '(none)'}'. MVP supports CSV, TSV, JSONL, and NDJSON."
    )


def open_dataset(path: str | Path) -> DatasetStream:
    source = Path(path)
    if not source.exists() or not source.is_file():
        raise InputFormatError(f"Input file does not exist or is not a file: {source}")
    fmt = _detect_format(source)
    if fmt == "csv":
        return _open_csv(source)
    return _open_jsonl(source)


def _open_csv(path: Path) -> DatasetStream:
    handle = path.open("r", encoding="utf-8-sig", newline="")
    sample = handle.read(8192)
    handle.seek(0)
    delimiter = "\t" if path.suffix.lower() == ".tsv" else ","
    if path.suffix.lower() != ".tsv" and sample:
        try:
            delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except csv.Error:
            delimiter = ","
    reader = csv.DictReader(handle, delimiter=delimiter, strict=True)
    try:
        columns = list(reader.fieldnames or [])
        if not columns:
            handle.close()
            raise InputFormatError("CSV/TSV has no header row.")
        if len(columns) != len(set(columns)):
            handle.close()
            raise InputFormatError("CSV/TSV contains duplicate column names; rename them before intake.")
    except csv.Error as exc:
        handle.close()
        raise InputFormatError(f"Could not read CSV header: {exc}") from exc

    def generate() -> Iterator[RowRecord]:
        try:
            for row_number, raw in enumerate(reader, start=2):
                extra = raw.pop(None, None)
                values = {key: raw.get(key) for key in columns}
                short = any(value is None for value in values.values())
                error = None
                if extra is not None or short:
                    if extra is not None:
                        error = "row_has_extra_cells"
                    else:
                        error = "row_has_missing_cells"
                yield RowRecord(row_number, values, error)
        except csv.Error as exc:
            raise InputFormatError(f"Malformed CSV near physical line {reader.line_num}: {exc}") from exc
        finally:
            handle.close()

    return DatasetStream(path, "csv", columns, generate())


def _json_scalar(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _open_jsonl(path: Path) -> DatasetStream:
    handle = path.open("r", encoding="utf-8-sig")
    first_object: dict[str, Any] | None = None
    first_line_no = 0
    for line_no, line in enumerate(handle, start=1):
        if not line.strip():
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError as exc:
            handle.close()
            raise InputFormatError(f"First non-empty JSONL line is invalid (line {line_no}): {exc.msg}") from exc
        if not isinstance(parsed, dict):
            handle.close()
            raise InputFormatError(f"JSONL records must be objects; line {line_no} is {type(parsed).__name__}.")
        first_object = parsed
        first_line_no = line_no
        break
    if first_object is None:
        handle.close()
        raise InputFormatError("JSONL contains no records.")
    columns = list(first_object.keys())

    def generate() -> Iterator[RowRecord]:
        nonlocal first_object
        try:
            first_record = {str(k): _json_scalar(v) for k, v in first_object.items()}
            first_object = None
            yield RowRecord(first_line_no, first_record)
            for line_no, line in enumerate(handle, start=first_line_no + 1):
                if not line.strip():
                    continue
                try:
                    parsed = json.loads(line)
                except json.JSONDecodeError:
                    yield RowRecord(line_no, {}, "invalid_json")
                    continue
                if not isinstance(parsed, dict):
                    yield RowRecord(line_no, {}, "record_not_object")
                    continue
                values = {str(k): _json_scalar(v) for k, v in parsed.items()}
                for key in values:
                    if key not in columns:
                        columns.append(key)
                yield RowRecord(line_no, values)
        finally:
            handle.close()

    return DatasetStream(path, "jsonl", columns, generate())
