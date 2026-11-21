"""Compare accounting code with the fork baseline. Run from the repository root."""

import ast
import json
import subprocess
from pathlib import Path

BASELINE = "ba359123e3dd537ade3197b01a53390a73207bac"
ROOT = Path(__file__).resolve().parents[1]


def original(path):
    return subprocess.check_output(["git", "show", f"{BASELINE}:{path}"], cwd=ROOT, text=True)


def audit():
    path = "matcha/api/payment_reconciliation.py"
    before, after = ast.parse(original(path)), ast.parse((ROOT / path).read_text())
    before.body = [n for n in before.body if getattr(n, "name", None) != "get_exceptions"]
    after.body = [n for n in after.body if getattr(n, "name", None) != "get_exceptions"]
    assert ast.dump(before) == ast.dump(after), "Accounting module changed outside get_exceptions"
    for path in ["matcha/api/reconciliation.py", "matcha/api/transactions.py", "matcha/hooks.py",
                 "matcha/patches.txt"]:
        assert original(path) == (ROOT / path).read_text(), f"Changed protected file: {path}"

    path = "matcha/matcha/doctype/matcha_settings/matcha_settings.json"
    old, new = json.loads(original(path)), json.loads((ROOT / path).read_text())
    old_fields = {f["fieldname"]: f for f in old["fields"]}
    new_fields = {f["fieldname"]: f for f in new["fields"]}
    assert all(new_fields.get(name) == field for name, field in old_fields.items())
    assert set(new_fields) - set(old_fields) == {
        "section_invoice_fields", "invoice_field_config", "invoice_fields_editor"
    }
    assert old["permissions"] == new["permissions"]

    forbidden = {"save", "insert", "submit", "cancel", "delete_doc", "set_value", "db_set", "commit", "sql"}
    for path in ["matcha/api/exceptions.py", "matcha/api/invoice_fields.py", "matcha/api/party_summary.py",
                 "matcha/api/formatting.py"]:
        tree = ast.parse((ROOT / path).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in forbidden, f"Review data mutation in {path}: {node.func.attr}"
    print(f"PASS: accounting functions match {BASELINE[:7]}")
    print("PASS: hooks and patches unchanged, existing settings fields and permissions preserved")
    print("PASS: new read APIs contain no direct document writes or raw SQL calls")
    print("Static checks do not replace integration tests on Frappe/ERPNext v15.")


if __name__ == "__main__":
    audit()
