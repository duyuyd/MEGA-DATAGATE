from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from datagate.cleaning import clean_csv
from datagate.cli import main
from datagate.contracts import contract_from_profile, load_contract, validate_file, write_contract
from datagate.drift import compare_profiles
from datagate.errors import ContractError, DataGateError, InputFormatError
from datagate.profiling import profile_file
from datagate.reporting import render_html_report
from datagate.sketches import HybridCardinality

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


class CardinalityTests(unittest.TestCase):
    def test_exact_for_small_columns(self) -> None:
        sketch = HybridCardinality(exact_limit=3)
        for value in ["a", "b", "a", "c"]:
            sketch.add(value)
        self.assertTrue(sketch.exact)
        self.assertEqual(sketch.estimate(), 3)

    def test_switches_to_bounded_sketch(self) -> None:
        sketch = HybridCardinality(exact_limit=100)
        for value in range(20_000):
            sketch.add(str(value))
        self.assertFalse(sketch.exact)
        self.assertLessEqual(len(sketch._registers or []), 4096)
        self.assertLess(abs(sketch.estimate() - 20_000) / 20_000, 0.08)


class ProfileTests(unittest.TestCase):
    def test_csv_profile_has_no_raw_values(self) -> None:
        profile = profile_file(EXAMPLES / "incoming_customers.csv")
        self.assertEqual(profile["rows"], 6)
        self.assertEqual(profile["column_count"], 5)
        serialized = json.dumps(profile)
        self.assertNotIn("Alice@Example.com", serialized)

    def test_jsonl_missing_keys_are_counted_as_null(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.jsonl"
            path.write_text('{"id":1,"name":"A"}\n{"id":2}\n', encoding="utf-8")
            profile = profile_file(path)
        name = next(field for field in profile["fields"] if field["name"] == "name")
        self.assertEqual(name["null_count"], 1)
        self.assertEqual(name["row_count_observed"], 2)


    def test_jsonl_contract_required_field_checked_per_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "records.jsonl"
            contract = root / "contract.json"
            data.write_text('{"id":1,"name":"A"}\n{"id":2}\n', encoding="utf-8")
            contract.write_text(json.dumps({
                "format": "datagate-contract/v1",
                "fields": {"id": {"type": "integer", "required": True}, "name": {"type": "string", "required": True, "nullable": False}},
            }), encoding="utf-8")
            report = validate_file(data, contract)
        self.assertFalse(report["valid"])
        self.assertTrue(any(issue["code"] == "required_value_missing" and issue["field"] == "name" for issue in report["issues"]))


    def test_html_report_escapes_untrusted_column_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "hostile.csv"
            path.write_text('"<img src=x onerror=alert(1)>",value\n1,ok\n', encoding="utf-8")
            profile = profile_file(path)
        html = render_html_report(profile, "Safe report")
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;img src=x", html)

    def test_very_large_integer_does_not_overflow_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "large_integer.csv"
            value = "9" * 500
            path.write_text(f"value\n{value}\n", encoding="utf-8")
            profile = profile_file(path)
        field = profile["fields"][0]
        self.assertEqual(field["inferred_type"], "integer")
        self.assertEqual(len(str(field["maximum_numeric"])), 500)

    def test_semantic_types_are_inferred(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "semantic.csv"
            path.write_text("email,url,ip\na@example.test,https://example.test,127.0.0.1\nb@example.test,https://example.org,::1\n", encoding="utf-8")
            profile = profile_file(path)
        inferred = {item["name"]: item["inferred_type"] for item in profile["fields"]}
        self.assertEqual(inferred, {"email": "email", "url": "url", "ip": "ip"})

    def test_unsupported_format_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.xlsx"
            path.write_text("x")
            with self.assertRaises(InputFormatError):
                profile_file(path)


class DriftTests(unittest.TestCase):
    def test_malformed_profile_is_rejected(self) -> None:
        current = profile_file(EXAMPLES / "incoming_customers.csv")
        with self.assertRaises(DataGateError):
            compare_profiles({"format": "datagate-profile/v1", "fields": [{}]}, current)

    def test_rename_candidate_is_suggested_not_applied(self) -> None:
        baseline = profile_file(EXAMPLES / "baseline_customers.csv")
        current = profile_file(EXAMPLES / "incoming_customers.csv")
        report = compare_profiles(baseline, current)
        self.assertTrue(any(item["from"] == "email" and item["to"] == "customer_email" for item in report["rename_suggestions"]))
        self.assertIn("automatic_action", report["rename_suggestions"][0])
        self.assertFalse(report["rename_suggestions"][0]["automatic_action"])


class ContractTests(unittest.TestCase):
    def test_url_uuid_ip_contract_types(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            data = root / "network.csv"
            contract = root / "network.contract.json"
            data.write_text("url,uuid,ip\nhttps://example.test,550e8400-e29b-41d4-a716-446655440000,2001:4860:4860::8888\n", encoding="utf-8")
            contract.write_text(json.dumps({
                "format": "datagate-contract/v1",
                "fields": {"url": {"type": "url"}, "uuid": {"type": "uuid"}, "ip": {"type": "ip"}},
            }), encoding="utf-8")
            report = validate_file(data, contract)
        self.assertTrue(report["valid"])

    def test_valid_dataset_passes_contract(self) -> None:
        report = validate_file(EXAMPLES / "valid_customers.csv", EXAMPLES / "customers.contract.json")
        self.assertTrue(report["valid"])
        self.assertEqual(report["issue_count"], 0)

    def test_validation_reports_rules_without_raw_values(self) -> None:
        report = validate_file(EXAMPLES / "incoming_customers.csv", EXAMPLES / "customers.contract.json")
        self.assertFalse(report["valid"])
        self.assertGreater(report["issue_count"], 0)
        serialized = json.dumps(report)
        self.assertNotIn("bob(at)example.com", serialized)
        self.assertTrue(any(item["code"] == "duplicate_value" for item in report["issues"]))

    def test_unknown_contract_rule_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "typo.contract.json"
            path.write_text(json.dumps({
                "format": "datagate-contract/v1",
                "fields": {"name": {"type": "string", "trimm": True}},
            }), encoding="utf-8")
            with self.assertRaises(ContractError):
                load_contract(path)

    def test_invalid_contract_rules_fail_before_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.contract.json"
            path.write_text(json.dumps({
                "format": "datagate-contract/v1",
                "fields": {"age": {"type": "integer", "min": "young"}},
            }), encoding="utf-8")
            with self.assertRaises(ContractError):
                load_contract(path)

    def test_contract_draft_from_profile(self) -> None:
        profile = profile_file(EXAMPLES / "baseline_customers.csv")
        contract = contract_from_profile(profile)
        self.assertEqual(contract["format"], "datagate-contract/v1")
        self.assertIn("email", contract["fields"])

    def test_write_contract_refuses_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "contract.json"
            path.write_text("{}")
            with self.assertRaises(DataGateError):
                write_contract({}, path)


class CleaningTests(unittest.TestCase):
    def test_clean_writes_new_file_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "cleaned.csv"
            audit = clean_csv(EXAMPLES / "incoming_customers.csv", EXAMPLES / "customers.contract.json", output)
            self.assertTrue(output.exists())
            self.assertTrue(Path(str(output) + ".audit.json").exists())
            self.assertEqual(audit["rows_written"], 6)
            with output.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["customer_email"], "alice@example.com")
            self.assertEqual(rows[0]["country"], "US")
            self.assertEqual(rows[1]["customer_email"], "bob(at)example.com")


    def test_cli_inspect_and_validate_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "profile"
            self.assertEqual(main(["inspect", str(EXAMPLES / "baseline_customers.csv"), "--out", str(output)]), 0)
            self.assertTrue((output / "profile.json").exists())
            report_dir = Path(temp) / "validation"
            self.assertEqual(main([
                "validate", str(EXAMPLES / "incoming_customers.csv"),
                "--contract", str(EXAMPLES / "customers.contract.json"),
                "--out", str(report_dir),
            ]), 1)
            self.assertTrue((report_dir / "validation.json").exists())


    def test_tsv_clean_preserves_tab_delimiter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.tsv"
            contract = root / "contract.json"
            output = root / "cleaned.tsv"
            source.write_text("name\tregion\n Alice \t vn \n", encoding="utf-8")
            contract.write_text(json.dumps({
                "format": "datagate-contract/v1",
                "fields": {"name": {"trim": True}, "region": {"trim": True, "case": "upper"}},
            }), encoding="utf-8")
            clean_csv(source, contract, output)
            contents = output.read_text(encoding="utf-8")
        self.assertIn("name\tregion", contents)
        self.assertIn("Alice\tVN", contents)

    def test_clean_refuses_to_overwrite_source(self) -> None:
        with self.assertRaises(DataGateError):
            clean_csv(EXAMPLES / "incoming_customers.csv", EXAMPLES / "customers.contract.json", EXAMPLES / "incoming_customers.csv")

    def test_clean_refuses_existing_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "cleaned.csv"
            output.write_text("existing")
            with self.assertRaises(DataGateError):
                clean_csv(EXAMPLES / "incoming_customers.csv", EXAMPLES / "customers.contract.json", output)


if __name__ == "__main__":
    unittest.main()
