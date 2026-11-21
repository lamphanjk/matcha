# Changelog

## v0.1.0-rc.3

Fix currency digit grouping. Python app version: `0.1.0rc3`.

- Replace hardcoded Indian digit grouping with three-digit thousands groups throughout the shared money formatter.
- Display integral VND balances without `.00`, retaining up to two actual fractional digits when present.
- Preserve configured currency symbols, symbol position and existing sign handling.
- Add six formatting tests and audit the original amount calculation helpers.

For example, `VND 10,00,00,000.00` becomes `VND 100,000,000`.
Allocation, amount conversion, rounding and accounting functions are unchanged.
The release includes rebuilt SPA assets and the Settings fix from rc.2.
No new schema or migration patch is included.

## v0.1.0-rc.2

Fix the Matcha Settings metadata request on Frappe v15. Python app version: `0.1.0rc2`.

- Send GET explicitly when loading invoice fields from Desk. Frappe defaults to POST, which the GET-only API rejects.
- Handle failed metadata requests within each invoice section and catch form refresh errors.
- Preserve saved field choices when a metadata request fails.
- Add three Desk script tests for the request method and failure handling.

No API permission expansion, schema change, accounting change or new migration patch is included.
Existing rc.1 installations need the new code, cache clearing, service restart and browser reload.
Missing assets from Frappe or other apps require a separate diagnosis.

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
