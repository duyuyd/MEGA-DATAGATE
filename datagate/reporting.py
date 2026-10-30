from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any


def _cell(value: Any) -> str:
    return html.escape("—" if value is None else str(value))


def render_html_report(data: dict[str, Any], title: str) -> str:
    fmt = data.get("format", "")
    summary: list[tuple[str, Any]] = []
    tables: list[tuple[str, list[str], list[list[Any]]]] = []
    if fmt == "datagate-profile/v1":
        summary = [("Rows", data.get("rows")), ("Columns", data.get("column_count")), ("Row issues", sum(data.get("row_errors", {}).values()))]
        rows = [[f.get("name"), f.get("inferred_type"), f.get("null_count"), f.get("null_pct"), f.get("distinct_estimate"), "exact" if f.get("distinct_is_exact") else "estimated"] for f in data.get("fields", [])]
        tables.append(("Field profile", ["Field", "Inferred type", "Nulls", "Null %", "Distinct", "Cardinality"], rows))
        if data.get("row_errors"):
            tables.append(("Input row issues", ["Issue", "Count"], [[k, v] for k, v in data["row_errors"].items()]))
    elif fmt == "datagate-drift/v1":
        summary = [("Added", len(data.get("added_fields", []))), ("Removed", len(data.get("removed_fields", []))), ("Type changes", len(data.get("type_changes", []))), ("Rename suggestions", len(data.get("rename_suggestions", [])))]
        tables.extend([
            ("Added fields", ["Field"], [[x] for x in data.get("added_fields", [])]),
            ("Removed fields", ["Field"], [[x] for x in data.get("removed_fields", [])]),
            ("Type changes", ["Field", "From", "To"], [[x["field"], x["from"], x["to"]] for x in data.get("type_changes", [])]),
            ("Rename suggestions (review required)", ["Old name", "New name", "Similarity score", "Action"], [[x["from"], x["to"], x["similarity_score"], "Manual approval"] for x in data.get("rename_suggestions", [])]),
        ])
    elif fmt == "datagate-validation/v1":
        summary = [("Rows", data.get("rows")), ("Checks", data.get("checks")), ("Issues", data.get("issue_count")), ("Valid", "YES" if data.get("valid") else "NO")]
        tables.append(("Issue summary", ["Rule", "Field", "Count"], [[x["code"], x.get("field"), x["count"]] for x in data.get("issues", [])]))
        tables.append(("Example locations (no cell values stored)", ["Rule", "Field", "Row", "Message"], [[x["code"], x.get("field"), x.get("row"), x["message"]] for x in data.get("examples", [])]))
    else:
        summary = [("Report type", fmt or "unknown")]

    cards = "".join(f'<div class="card"><div class="muted">{_cell(label)}</div><strong>{_cell(value)}</strong></div>' for label, value in summary)
    sections = []
    for heading, headers, rows in tables:
        head = "".join(f"<th>{_cell(item)}</th>" for item in headers)
        body = "".join("<tr>" + "".join(f"<td>{_cell(value)}</td>" for value in row) + "</tr>" for row in rows)
        if not rows:
            body = f'<tr><td colspan="{len(headers)}" class="muted">No findings.</td></tr>'
        sections.append(f"<section><h2>{_cell(heading)}</h2><div class=\"table-wrap\"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></section>")
    note = data.get("privacy") or data.get("note") or "Generated locally by MEGA DataGate."
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:">
<title>{_cell(title)} - MEGA DataGate</title>
<style>
:root{{color-scheme:light dark;--bg:#101820;--panel:#17232d;--line:#2b3b48;--text:#edf4f8;--muted:#9fb0bd;--accent:#75d4b2}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:1100px;margin:40px auto;padding:0 20px}}header{{margin-bottom:26px}}h1{{font-size:clamp(28px,4vw,42px);margin:0 0 6px}}h2{{font-size:19px;margin:28px 0 10px}}.muted{{color:var(--muted);font-size:13px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px}}.card{{padding:16px;background:var(--panel);border:1px solid var(--line);border-radius:12px}}.card strong{{display:block;font-size:25px;margin-top:4px}}.table-wrap{{overflow:auto;border:1px solid var(--line);border-radius:10px}}table{{border-collapse:collapse;width:100%;min-width:520px;background:var(--panel)}}th,td{{padding:11px 13px;text-align:left;border-bottom:1px solid var(--line)}}th{{color:var(--accent);font-size:12px;text-transform:uppercase;letter-spacing:.04em}}tr:last-child td{{border-bottom:0}}footer{{margin:28px 0;color:var(--muted);font-size:12px}}
</style></head><body><main><header><div class="muted">MEGA DATAGATE · LOCAL REPORT</div><h1>{_cell(title)}</h1><div class="muted">Generated on this device. Raw cell values are not included in this report.</div></header><div class="cards">{cards}</div>{''.join(sections)}<footer>{_cell(note)}</footer></main></body></html>'''


def write_html_report(data: dict[str, Any], path: str | Path, title: str) -> Path:
    target = Path(path)
    target.write_text(render_html_report(data, title), encoding="utf-8")
    return target


def save_json_and_html(data: dict[str, Any], output_dir: str | Path, stem: str, title: str) -> tuple[Path, Path]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f"{stem}.json"
    html_path = directory / "report.html"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_html_report(data, html_path, title)
    return json_path, html_path
