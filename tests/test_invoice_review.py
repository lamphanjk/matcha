"""Run with python -m unittest discover -s tests (no bench required)."""

import importlib
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


class Row(dict):
    def __getattr__(self, name):
        return self.get(name)


def load_modules():
    """Isolate the Frappe boundary so these tests also run outside a bench."""
    frappe = ModuleType("frappe")
    frappe.whitelist = lambda **kwargs: lambda fn: fn
    frappe._ = lambda message: message
    frappe.PermissionError = PermissionError
    frappe.parse_json = json.loads
    frappe.throw = lambda message, error=ValueError: (_ for _ in ()).throw(error(message))
    frappe.has_permission = lambda *args: True
    model = ModuleType("frappe.model")
    model.get_permitted_fields = lambda doctype: []
    utils = ModuleType("frappe.utils")
    utils.getdate = lambda value: value if isinstance(value, date) else date.fromisoformat(value)
    utils.nowdate = lambda: "2026-11-21"
    loaded = []
    api_path = Path(__file__).resolve().parents[1] / "matcha" / "api"
    with patch.dict(sys.modules, {"frappe": frappe, "frappe.model": model, "frappe.utils": utils}):
        for name in ("invoice_fields", "exceptions", "party_summary"):
            module_name = "matcha.api." + name
            spec = importlib.util.spec_from_file_location(module_name, api_path / (name + ".py"))
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
            loaded.append(module)
    return frappe, *loaded


frappe, fields_api, exceptions_api, summary_api = load_modules()


class InvoiceReviewTests(unittest.TestCase):
    def setUp(self):
        self.config = {doctype: {"display": [], "filter": []} for doctype in fields_api.INVOICE_TYPES}
        self.field = {"fieldname": "custom_contract", "fieldtype": "Data", "label": "Contract", "options": ""}
        self.config["Sales Invoice"] = {"display": [self.field], "filter": [self.field]}

    def query(self, **kwargs):
        with patch.object(exceptions_api, "get_configuration", return_value=self.config):
            return exceptions_api.get_exceptions("Company", **kwargs)

    def test_default_ageing_and_date_range_are_combined(self):
        calls = []

        def get_list(doctype, **kwargs):
            calls.append((doctype, kwargs))
            return [Row(total=0)] if kwargs["fields"] == ["count(name) as total"] else []

        with patch.object(frappe, "get_list", get_list, create=True):
            self.query(from_date="2026-01-01", to_date="2026-10-31")
        filters = next(k["filters"] for dt, k in calls if dt == "Sales Invoice")
        self.assertIn(["posting_date", ">=", "2026-01-01"], filters)
        self.assertIn(["posting_date", "<=", "2026-10-31"], filters)
        self.assertIn(["posting_date", "<=", "2026-10-22"], filters)
        self.assertIn(["outstanding_amount", "!=", 0], filters)

    def test_custom_filter_applies_before_count_and_pagination(self):
        calls = []
        invoice = Row(name="SI-1", customer="C-1", posting_date="2026-01-01", outstanding_amount=5,
                      currency="USD", is_return=0, debit_to="AR", custom_contract="CT-1")

        def get_list(doctype, **kwargs):
            calls.append((doctype, kwargs))
            if kwargs["fields"] == ["count(name) as total"]:
                return [Row(total=601 if doctype == "Sales Invoice" else 0)]
            return [invoice] * 601 if doctype == "Sales Invoice" else []

        selected = json.dumps([["Sales Invoice", "custom_contract", "=", "CT-1"]])
        with patch.object(frappe, "get_list", get_list, create=True), patch.object(
            frappe, "get_cached_value", return_value="USD", create=True
        ):
            result = self.query(invoice_filters=selected, offset_invoices=600, invoice_status="all")
        self.assertEqual(result["total_ageing_invoices"], 601)
        self.assertEqual(len(result["ageing_invoices"]), 1)
        self.assertEqual(result["ageing_invoices"][0]["extra_fields"][0]["value"], "CT-1")
        self.assertFalse(any(dt == "Purchase Invoice" for dt, _ in calls))
        for dt, kwargs in calls:
            if dt == "Sales Invoice":
                self.assertIn(["custom_contract", "=", "CT-1"], kwargs["filters"])
                self.assertFalse(any(f[0] == "outstanding_amount" for f in kwargs["filters"]))

    def test_unconfigured_fields_and_expression_injection_rejected(self):
        for fieldname in ["owner", "sum(grand_total)", "custom_contract OR 1=1"]:
            with self.subTest(fieldname=fieldname), self.assertRaises(ValueError):
                exceptions_api.Exceptions._validate_filters(
                    [["Sales Invoice", fieldname, "=", "x"]], self.config)

    def test_paid_filter(self):
        calls = []

        def get_list(doctype, **kwargs):
            calls.append((doctype, kwargs))
            return [Row(total=0)] if kwargs["fields"] == ["count(name) as total"] else []

        with patch.object(frappe, "get_list", get_list, create=True):
            self.query(invoice_status="paid")
        for dt, kwargs in calls:
            if dt in fields_api.INVOICE_TYPES:
                self.assertIn(["outstanding_amount", "=", 0], kwargs["filters"])

    def test_party_scopes_both_lists_by_type_and_exact_id(self):
        for party_type, doctype, party_field in [
            ("Customer", "Sales Invoice", "customer"), ("Supplier", "Purchase Invoice", "supplier")
        ]:
            with self.subTest(party_type=party_type):
                calls = []

                def get_list(dt, **kwargs):
                    calls.append((dt, kwargs))
                    return [Row(total=0)] if kwargs["fields"] == ["count(name) as total"] else []

                with patch.object(frappe, "get_list", get_list, create=True):
                    self.query(party_type=party_type, party="SAME-ID", search_invoices="INV-001")
                self.assertEqual({dt for dt, kwargs in calls}, {"Payment Entry", doctype})
                for dt, kwargs in calls:
                    if dt == "Payment Entry":
                        self.assertIn(["party_type", "=", party_type], kwargs["filters"])
                        self.assertIn(["party", "=", "SAME-ID"], kwargs["filters"])
                        self.assertEqual(kwargs["or_filters"], [])
                    else:
                        self.assertIn([party_field, "=", "SAME-ID"], kwargs["filters"])
                        self.assertEqual(kwargs["or_filters"], [["name", "like", "%INV-001%"]])

    def test_invoice_filters_do_not_restrict_payments_or_require_payment_results(self):
        calls = []
        invoice = Row(name="SI-1", customer="C-1", posting_date="2026-01-01", outstanding_amount=5,
                      currency="USD", is_return=0, debit_to="AR", custom_contract="CT-1")

        def get_list(doctype, **kwargs):
            calls.append((doctype, kwargs))
            if kwargs["fields"] == ["count(name) as total"]:
                return [Row(total=1 if doctype == "Sales Invoice" else 0)]
            return [invoice] if doctype == "Sales Invoice" else []

        with patch.object(frappe, "get_list", get_list, create=True), patch.object(
            frappe, "get_cached_value", return_value="USD", create=True
        ):
            result = self.query(party_type="Customer", party="C-1",
                                invoice_filters=json.dumps([["Sales Invoice", "custom_contract", "=", "CT-1"]]))
        self.assertEqual(result["unmatched_payments"], [])
        self.assertEqual([row["name"] for row in result["ageing_invoices"]], ["SI-1"])
        for doctype, kwargs in calls:
            self.assertEqual(any(f[0] == "custom_contract" for f in kwargs["filters"]),
                             doctype == "Sales Invoice")

    def test_incomplete_or_unsupported_party_scope_rejected(self):
        for kwargs in [{"party": "C-1"}, {"party_type": "Customer"}, {"party_type": "Employee", "party": "E-1"}]:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                self.query(**kwargs)

    def test_payment_unallocated_currency_matches_original_party_account(self):
        for payment_type, expected_currency in [("Receive", "USD"), ("Pay", "VND")]:
            payment = Row(name="PAY-1", party_type="Customer", party="C-1", unallocated_amount=100,
                          posting_date="2026-01-01", payment_type=payment_type,
                          paid_from_account_currency="USD", paid_to_account_currency="VND")
            with self.subTest(payment_type=payment_type), patch.object(
                frappe, "get_list", side_effect=[[Row(total=1)], [payment]], create=True
            ):
                rows, total = exceptions_api.Exceptions("Company").payments(None, 0, 50)
            self.assertEqual(rows[0]["currency"], expected_currency)
            self.assertEqual(rows[0]["amount"], 100)
            self.assertEqual(total, 1)

    def test_field_metadata_omits_hidden_virtual_and_unreadable_fields(self):
        def field(name, **kwargs):
            return Row(fieldname=name, fieldtype="Data", label=name, options="", hidden=0, **kwargs)

        meta = SimpleNamespace(fields=[field("custom_contract"), field("restricted"),
                                      Row(fieldname="secret", fieldtype="Password"),
                                      field("virtual", is_virtual=1),
                                      Row(fieldname="hidden", fieldtype="Data", hidden=1)])
        with patch.object(frappe, "get_meta", return_value=meta, create=True), patch.object(
            fields_api, "get_permitted_fields", return_value=["custom_contract", "secret", "virtual", "hidden"]
        ):
            self.assertEqual([f["fieldname"] for f in fields_api.get_invoice_fields("Sales Invoice")],
                             ["custom_contract"])

    def test_summary_uses_account_currency_and_includes_settled_and_return_invoices(self):
        invoices = [
            Row(name="SI-1", currency="USD", debit_to="AR-VND", grand_total=100, rounded_total=100,
                base_grand_total=2500000, base_rounded_total=2500000, outstanding_amount=1000000),
            Row(name="SI-2", currency="USD", debit_to="AR-USD", grand_total=50, rounded_total=50,
                base_grand_total=1250000, base_rounded_total=1250000, outstanding_amount=0),
            Row(name="CN-1", currency="USD", debit_to="AR-USD", grand_total=-10, rounded_total=-10,
                base_grand_total=-250000, base_rounded_total=-250000, outstanding_amount=-10),
        ]

        def cached_value(doctype, name, field):
            return "USD" if name == "AR-USD" else "VND"

        with patch.object(frappe, "get_list", return_value=invoices, create=True) as query, patch.object(
            frappe, "get_cached_value", side_effect=cached_value, create=True
        ):
            result = summary_api.get_party_summary("Company", "Customer", "C-1", "2026-01-01", "2026-11-21")
        self.assertEqual(result["totals"], [
            {"currency": "USD", "billing": 40, "paid": 50, "unpaid": -10},
            {"currency": "VND", "billing": 2500000, "paid": 1500000, "unpaid": 1000000},
        ])
        self.assertIn(["customer", "=", "C-1"], query.call_args.kwargs["filters"])
        self.assertFalse(any(f[0] == "outstanding_amount" for f in query.call_args.kwargs["filters"]))

    def test_summary_denies_invoice_access(self):
        with patch.object(frappe, "has_permission", return_value=False), self.assertRaises(PermissionError):
            summary_api.get_party_summary("Company", "Customer", "C-1")

    def test_summary_denies_missing_balance_field_permissions(self):
        with patch.object(frappe, "get_list", return_value=[Row(name="SI-1")], create=True), patch.object(
            frappe, "get_cached_value", return_value="VND", create=True
        ), self.assertRaises(PermissionError):
            summary_api.get_party_summary("Company", "Customer", "C-1")

    def test_summary_totals_continue_beyond_first_page(self):
        invoice = Row(name="SI-1", currency="USD", debit_to="AR", grand_total=10, rounded_total=10,
                      base_grand_total=10, base_rounded_total=10, outstanding_amount=4)
        with patch.object(frappe, "get_list", side_effect=[[invoice] * 500, [invoice]], create=True) as query, patch.object(
            frappe, "get_cached_value", return_value="USD", create=True
        ):
            result = summary_api.get_party_summary("Company", "Customer", "C-1")
        self.assertEqual(result["totals"], [{"currency": "USD", "billing": 5010, "paid": 3006, "unpaid": 2004}])
        self.assertEqual([call.kwargs["start"] for call in query.call_args_list], [0, 500])

    def test_reversed_dates_rejected(self):
        with self.assertRaises(ValueError):
            exceptions_api.Exceptions("Company", "2026-11-21", "2026-01-01")


if __name__ == "__main__":
    unittest.main()
