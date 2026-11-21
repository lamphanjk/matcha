"""Permission-aware exception lists and configurable invoice filters."""

from datetime import timedelta

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from matcha.api.invoice_fields import INVOICE_TYPES, get_configuration


class Exceptions:
    def __init__(self, company, from_date=None, to_date=None, party_type=None, party=None):
        if not company:
            frappe.throw(_("Company is required"))
        if (party_type or party) and (party_type not in {"Customer", "Supplier"} or not party):
            frappe.throw(_("Choose a Customer or Supplier and its Party ID"))
        self.party_type, self.party = party_type, party
        self.today = getdate(nowdate())
        self.filters = [["company", "=", company], ["docstatus", "=", 1]]
        if from_date and to_date and getdate(from_date) > getdate(to_date):
            frappe.throw(_("From date must be before to date"))
        if from_date:
            self.filters.append(["posting_date", ">=", str(getdate(from_date))])
        if to_date:
            self.filters.append(["posting_date", "<=", str(getdate(to_date))])

    def invoices(self, status, search, field_filters, offset, limit):
        if status not in {"ageing", "open", "paid", "all"}:
            frappe.throw(_("Invalid invoice status"))
        config = get_configuration()
        selected = frappe.parse_json(field_filters) if field_filters else []
        if not isinstance(selected, list) or len(selected) > 30:
            frappe.throw(_("Invalid invoice filters"))
        filters_by_type = self._validate_filters(selected, config)
        rows, counts = [], {}
        # Filters on one invoice type must not admit unrelated invoices of the other type.
        scoped_types = {f[0] for f in selected}
        for doctype, (party_type, party_field, account) in INVOICE_TYPES.items():
            counts[doctype] = 0
            if doctype not in config or (scoped_types and doctype not in scoped_types):
                continue
            if self.party_type and self.party_type != party_type:
                continue
            filters = list(self.filters) + filters_by_type.get(doctype, [])
            if self.party:
                filters.append([party_field, "=", self.party])
            if status in {"ageing", "open"}:
                filters.append(["outstanding_amount", "!=", 0])
            elif status == "paid":
                filters.append(["outstanding_amount", "=", 0])
            if status == "ageing":
                filters.append(["posting_date", "<=", str(self.today - timedelta(days=30))])
            or_filters = self._search_filters(search, ["name"])
            counts[doctype] = self._count(doctype, filters, or_filters)
            display = config[doctype]["display"]
            fields = list(dict.fromkeys([
                "name", party_field, "posting_date", "outstanding_amount", "currency", "is_return", account,
                *[f["fieldname"] for f in display],
            ]))
            invoices = frappe.get_list(doctype, filters=filters, or_filters=or_filters, fields=fields,
                                       order_by="posting_date asc, name asc", page_length=offset + limit)
            for inv in invoices:
                rows.append({
                    "doctype": doctype, "name": inv.name, "party_type": party_type,
                    "party": inv.get(party_field), "amount": float(inv.outstanding_amount or 0),
                    "date": str(inv.posting_date), "age_days": (self.today - getdate(inv.posting_date)).days,
                    "currency": frappe.get_cached_value("Account", inv.get(account), "account_currency") or inv.currency,
                    "is_return": inv.is_return,
                    "receivable_payable_account": inv.get(account),
                    "extra_fields": [{**f, "value": inv.get(f["fieldname"])} for f in display],
                })
        rows.sort(key=lambda r: (r["date"], r["doctype"], r["name"]))
        return rows[offset:offset + limit], counts

    def payments(self, search, offset, limit):
        if not frappe.has_permission("Payment Entry", "read"):
            return [], 0
        filters = self.filters + [["unallocated_amount", ">", 0]]
        if self.party:
            filters.extend([["party_type", "=", self.party_type], ["party", "=", self.party]])
        or_filters = self._search_filters(search, ["party", "party_name", "name"])
        count = self._count("Payment Entry", filters, or_filters)
        rows = frappe.get_list(
            "Payment Entry", filters=filters, or_filters=or_filters,
            fields=["name", "party_type", "party", "unallocated_amount", "posting_date", "payment_type",
                    "paid_from_account_currency", "paid_to_account_currency"],
            order_by="posting_date asc, name asc", start=offset, page_length=limit,
        )
        return [{
            "doctype": "Payment Entry", "name": r.name, "party_type": r.party_type,
            "party": r.party, "amount": float(r.unallocated_amount or 0), "date": str(r.posting_date),
            "age_days": (self.today - getdate(r.posting_date)).days, "payment_type": r.payment_type,
            "currency": r.paid_from_account_currency if r.payment_type == "Receive" else r.paid_to_account_currency,
        } for r in rows], count

    @staticmethod
    def _validate_filters(selected, config):
        result = {}
        for item in selected:
            if not isinstance(item, list) or len(item) != 4:
                frappe.throw(_("Invalid invoice filter"))
            doctype, fieldname, operator, value = item
            available = {f["fieldname"]: f for f in config.get(doctype, {}).get("filter", [])}
            if fieldname not in available or operator not in {"=", "!=", "like", ">", "<", ">=", "<="}:
                frappe.throw(_("Field or operator is not enabled for filtering"))
            if not isinstance(value, (str, int, float)):
                frappe.throw(_("Invalid filter value"))
            if operator == "like" and available[fieldname]["fieldtype"] not in {
                "Data", "Link", "Dynamic Link", "Select", "Small Text", "Text"
            }:
                frappe.throw(_("Contains is only available for text fields"))
            result.setdefault(doctype, []).append([fieldname, operator, value])
        return result

    @staticmethod
    def _count(doctype, filters, or_filters):
        rows = frappe.get_list(doctype, filters=filters, or_filters=or_filters,
                               fields=["count(name) as total"], order_by="", page_length=1)
        return int(rows[0].total or 0) if rows else 0

    @staticmethod
    def _search_filters(search, fields):
        return [[f, "like", "%" + search.strip() + "%"] for f in fields] if search else []


def get_exceptions(company, limit_per_type=50, offset_payments=0, offset_invoices=0,
                   search_payments=None, search_invoices=None, from_date=None, to_date=None,
                   invoice_status="ageing", invoice_filters=None, party_type=None, party=None):
    limit = max(1, min(100, int(limit_per_type or 50)))
    pay_offset, inv_offset = max(0, int(offset_payments or 0)), max(0, int(offset_invoices or 0))
    query = Exceptions(company, from_date, to_date, party_type, party)
    payments, pay_count = query.payments(search_payments, pay_offset, limit)
    invoices, counts = query.invoices(invoice_status, search_invoices, invoice_filters, inv_offset, limit)
    inv_count = sum(counts.values())
    return {
        "unmatched_payments": payments, "ageing_invoices": invoices,
        "total_count": len(payments) + len(invoices), "total_in_system": pay_count + inv_count,
        "total_unmatched_payments": pay_count, "total_ageing_invoices": inv_count,
        "total_ageing_si": counts["Sales Invoice"], "total_ageing_pi": counts["Purchase Invoice"],
        "offset_payments": pay_offset, "offset_invoices": inv_offset,
    }
