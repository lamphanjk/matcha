# Changelog

## v0.1.0-rc.1

Test candidate for Frappe/ERPNext v15. Python app version: `0.1.0rc1`.

- Add party invoice balances grouped by account currency and posting date range.
- Add invoice display and filter field selection in Matcha Settings, including custom fields.
- Share the selected party between exception payments and invoices.
- Keep invoice status, invoice number and custom field filters within the invoice panel.
- Apply read permissions to exception queries and remove the 500-invoice pagination cap.
- Preserve the original allocation, reconciliation, XCO and undo functions.
- Add release audits and 14 unit tests, including foreign-currency payment display.

Database changes add settings fields only. No accounting data migration patch is included.
Server integration tests and the RC → baseline → RC test remain required before stable release.

See [change audit](docs/release-audit.md) and [server test and rollback](docs/server-test-and-rollback.md).

## v0.0.1-baseline

Original fork commit: `ba359123e3dd537ade3197b01a53390a73207bac`.
This tag identifies the source baseline, not a newly validated server deployment.
