"""Current invoice balances for a posting-date cohort, grouped by account currency."""

from decimal import Decimal

import frappe
from frappe import _

from matcha.api.exceptions import Exceptions
from matcha.api.invoice_fields import INVOICE_TYPES


@frappe.whitelist(methods=["GET"])
def search_parties(party_type: str, search: str = "") -> list[dict]:
    if party_type not in {"Customer", "Supplier"}:
        frappe.throw(_("Select a Customer or Supplier"))
    name_field = party_type.lower() + "_name"
    term = "%" + search.strip() + "%"
    return frappe.get_list(party_type, fields=["name", name_field + " as label"],
                           or_filters=[["name", "like", term], [name_field, "like", term]],
                           order_by=name_field + " asc", page_length=20)


@frappe.whitelist(methods=["GET"])
def get_party_summary(company: str, party_type: str, party: str,
                      from_date: str | None = None, to_date: str | None = None) -> dict:
    doctype = {"Customer": "Sales Invoice", "Supplier": "Purchase Invoice"}.get(party_type)
    if not doctype or not party:
        frappe.throw(_("Select a Customer or Supplier"))
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("Not permitted to read invoices"), frappe.PermissionError)
    party_field, account_field = INVOICE_TYPES[doctype][1:]
    filters = Exceptions(company, from_date, to_date).filters + [[party_field, "=", party]]
    base_currency = frappe.get_cached_value("Company", company, "default_currency")
    totals, account_currencies, offset = {}, {}, 0
    while True:
        rows = frappe.get_list(
            doctype, filters=filters,
            fields=["name", "currency", account_field, "grand_total", "rounded_total",
                    "base_grand_total", "base_rounded_total", "outstanding_amount"],
            order_by="name asc", start=offset, page_length=500,
        )
        for row in rows:
            required = {account_field, "currency", "grand_total", "rounded_total",
                        "base_grand_total", "base_rounded_total", "outstanding_amount"}
            if not required.issubset(row):
                frappe.throw(_("Not permitted to read invoice balance fields"), frappe.PermissionError)
            account = row.get(account_field)
            if account not in account_currencies:
                account_currencies[account] = frappe.get_cached_value("Account", account, "account_currency")
            currency = account_currencies[account] or base_currency
            # ERPNext outstanding_amount is denominated in the receivable/payable account currency.
            if currency == base_currency:
                billing = row.base_rounded_total or row.base_grand_total
            elif currency == row.currency:
                billing = row.rounded_total or row.grand_total
            else:
                frappe.throw(_("Invoice and account currencies do not match"))
            total = totals.setdefault(currency, {"billing": Decimal(0), "unpaid": Decimal(0)})
            total["billing"] += Decimal(str(billing or 0))
            total["unpaid"] += Decimal(str(row.outstanding_amount or 0))
        offset += len(rows)
        if len(rows) < 500:
            break
    return {"totals": [{"currency": currency, "billing": float(t["billing"]),
                        "paid": float(t["billing"] - t["unpaid"]), "unpaid": float(t["unpaid"])}
                       for currency, t in sorted(totals.items())]}
