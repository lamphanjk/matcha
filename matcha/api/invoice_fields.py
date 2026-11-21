"""Invoice fields available to Matcha, including site customizations."""

import frappe
from frappe import _
from frappe.model import get_permitted_fields

INVOICE_TYPES = {"Sales Invoice": ("Customer", "customer", "debit_to"),
                 "Purchase Invoice": ("Supplier", "supplier", "credit_to")}
FIELD_TYPES = {"Data", "Link", "Dynamic Link", "Select", "Date", "Datetime", "Time",
               "Int", "Long Int", "Float", "Currency", "Percent", "Check", "Small Text", "Text"}


@frappe.whitelist(methods=["GET"])
def get_invoice_fields(doctype: str) -> list[dict]:
    if doctype not in INVOICE_TYPES:
        frappe.throw(_("Only Sales Invoice and Purchase Invoice are supported"))
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("Not permitted to read invoices"), frappe.PermissionError)
    permitted = set(get_permitted_fields(doctype))
    return [
        {"fieldname": df.fieldname, "label": _(df.label or df.fieldname),
         "fieldtype": df.fieldtype, "options": df.options or ""}
        for df in frappe.get_meta(doctype).fields
        if df.fieldtype in FIELD_TYPES and not df.hidden and not df.get("is_virtual")
        and df.fieldname in permitted
    ]


def validate_configuration(value):
    config = frappe.parse_json(value) if value else {}
    if not isinstance(config, dict) or set(config) - set(INVOICE_TYPES):
        frappe.throw(_("Invalid invoice field configuration"))
    for doctype, selections in config.items():
        available = {f["fieldname"] for f in get_invoice_fields(doctype)}
        if not isinstance(selections, dict) or set(selections) - {"display", "filter"}:
            frappe.throw(_("Invalid invoice field configuration"))
        for names in selections.values():
            if not isinstance(names, list) or any(not isinstance(n, str) or n not in available for n in names):
                frappe.throw(_("Choose valid, readable invoice fields"))
    return config


@frappe.whitelist(methods=["GET"])
def get_configuration() -> dict:
    saved = frappe.get_single("Matcha Settings").get("invoice_field_config")
    config = frappe.parse_json(saved) if saved else {}
    result = {}
    for doctype in INVOICE_TYPES:
        if not frappe.has_permission(doctype, "read"):
            continue
        selected = config.get(doctype, {})
        available = {f["fieldname"]: f for f in get_invoice_fields(doctype)}
        result[doctype] = {
            key: [available[n] for n in selected.get(key, []) if n in available]
            for key in ("display", "filter")
        }
    return result
