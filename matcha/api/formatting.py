"""Expose only the site settings needed to display monetary amounts."""

import frappe
from frappe.utils import cint, get_number_format_info


def get_money_format_settings(currencies):
    number_format = frappe.get_system_settings("number_format") or "#,###.##"
    precision = frappe.get_system_settings("currency_precision")
    rounding = frappe.get_system_settings("rounding_method") or "Banker's Rounding (legacy)"
    default = _format_options(number_format, precision, rounding)
    overrides = {}
    if cint(frappe.get_system_settings("use_number_format_from_currency")):
        overrides = {
            row.name: _format_options(row.number_format, precision, rounding)
            for row in currencies if row.get("number_format")
        }
    return {"default": default, "currencies": overrides}


def _format_options(number_format, precision, rounding):
    decimal, group, format_precision = get_number_format_info(number_format)
    digits = format_precision if precision in (None, "") else cint(precision)
    return {
        "number_format": number_format,
        "decimal_separator": decimal,
        "group_separator": group,
        "precision": max(0, min(9, digits)),
        "rounding_method": rounding,
    }
