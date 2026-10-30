from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .cleaning import clean_csv
from .contracts import contract_from_profile, validate_file, write_contract
from .drift import compare_profile_files
from .errors import DataGateError
from .profiling import profile_file, save_profile
from .reporting import save_json_and_html


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="datagate",
        description="Local-first data intake: profile, compare schema, validate contracts, and clean safely.",
        epilog="All MVP operations run locally. DataGate does not upload input files or raw cell values.",
    )
    parser.add_argument("--version", action="version", version=f"MEGA DataGate {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect = sub.add_parser("inspect", help="Stream a CSV/TSV/JSONL file and create a profile report.")
    inspect.add_argument("input")
    inspect.add_argument("--out", default=None, help="Output directory (default: <input>.datagate)")

    compare = sub.add_parser("compare", help="Compare two DataGate profile JSON files for schema drift.")
    compare.add_argument("baseline")
    compare.add_argument("current")
    compare.add_argument("--out", default="datagate-drift-report")

    contract = sub.add_parser("contract-init", help="Generate an editable contract draft from a profile JSON.")
    contract.add_argument("profile")
    contract.add_argument("--out", required=True, help="New contract JSON path; existing files are never overwritten.")

    validate = sub.add_parser("validate", help="Validate CSV/TSV/JSONL input against a DataGate contract.")
    validate.add_argument("input")
    validate.add_argument("--contract", required=True)
    validate.add_argument("--out", default="datagate-validation-report")

    clean = sub.add_parser("clean", help="Apply only explicitly declared, safe CSV/TSV transforms to a new file.")
    clean.add_argument("input")
    clean.add_argument("--contract", required=True)
    clean.add_argument("--out", required=True, help="New output file. Existing files and source are never overwritten.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            output = args.out or f"{Path(args.input).name}.datagate"
            profile = profile_file(args.input)
            json_path, html_path = save_profile(profile, output)
            print(f"PROFILED  rows={profile['rows']}  columns={profile['column_count']}")
            print(f"JSON      {json_path}")
            print(f"HTML      {html_path}")
            return 0

        if args.command == "compare":
            report = compare_profile_files(args.baseline, args.current)
            json_path, html_path = save_json_and_html(report, args.out, "drift", "Schema drift report")
            print(f"DRIFT     added={len(report['added_fields'])}  removed={len(report['removed_fields'])}  type_changes={len(report['type_changes'])}")
            print(f"RENAMES   suggestions={len(report['rename_suggestions'])} (manual review required)")
            print(f"JSON      {json_path}\nHTML      {html_path}")
            return 0

        if args.command == "contract-init":
            profile = json.loads(Path(args.profile).read_text(encoding="utf-8"))
            contract = contract_from_profile(profile)
            path = write_contract(contract, args.out)
            print(f"CONTRACT  {path}")
            print("Review generated rules before using this draft as a production gate.")
            return 0

        if args.command == "validate":
            report = validate_file(args.input, args.contract)
            json_path, html_path = save_json_and_html(report, args.out, "validation", "Data validation report")
            status = "PASS" if report["valid"] else "FAIL"
            print(f"{status}      rows={report['rows']}  checks={report['checks']}  issues={report['issue_count']}")
            print(f"JSON      {json_path}\nHTML      {html_path}")
            return 0 if report["valid"] else 1

        if args.command == "clean":
            audit = clean_csv(args.input, args.contract, args.out)
            print(f"CLEANED   rows={audit['rows_written']}  changed_cells={audit['changed_cell_count']}")
            print(f"OUTPUT    {args.out}")
            print(f"AUDIT     {args.out}.audit.json")
            return 0
    except (DataGateError, OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
