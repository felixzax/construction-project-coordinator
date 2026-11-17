# Changelog

## 1.5.1 — 2026-11-17

- Changed Windows delivery to a standalone single-file executable with explicit Shiboken collection, preventing loss of a companion runtime folder during copying/extraction.
- Removed the nested application ZIP: the Actions artifact contains the executable directly.
- Added pre-Qt runtime checks and a useful startup diagnostic instead of an unhandled Shiboken import traceback.
- Added file checksums, isolated ZIP round-trip launch, actual downloaded-artifact verification, and native Windows Qt launch with Python/Qt build paths removed.
- No database schema or business-feature changes.

## 1.5.0 — 2026-11-16

- Added project Corrections and Violations workspaces with address, precise location, required corrective action and notice/code/sheet references.
- Added authority, related permit, responsible contact, priority, deadlines, progress states and resolution dates/notes.
- Added address autofill with preserved custom addresses and project shortcuts to filtered issue lists.
- Added unresolved issue coverage in dashboard/timeline, overdue highlights, retained notice/photo attachments, search and CSV/DOCX exports.
- Integrated department/project reports, draft recovery, backed-up deletion and schema v6 upgrades with v1–v6 restore support.
- Added issue-specific tests and Windows packaged-application checks.

## 1.4.0 — 2026-11-15

- Added Receipts workspace with supplier/company/contact, project, reference, receipt date, discipline, area and notes.
- Added supplier estimated/actual totals, precise differences and over/under/on-estimate comparison, preserving unknown versus zero prices.
- Added approval statuses, reviewer/date/notes and re-review when approved supplier/pricing/currency/attachment changes.
- Added retained local receipt attachments, search, CSV/DOCX and department/project report coverage.
- Integrated receipt deletion, draft recovery, backups and schema v5 upgrades with restoration of v1–v5 databases.
- Added receipt-specific persistence, validation, pricing, approval, attachment, upgrade, export and UI tests.

## 1.3.0 — 2026-11-15

- Added CSV and Word (.docx) exports for every department, including tagged related work, plan status, permit requirements, contacts and bid cost detail.
- Added filtered CSV/DOCX section-list exports and Word exports for nested permit, estimate and revision lists.

- Added selected/multiple/all-listed record deletion across sections and nested bid, permit and revision lists, plus a typed-confirmation application reset.
- Added transactional child cleanup, contact/meeting unlinking, pre-delete recovery snapshots and protection against invalid remaining bid discounts.
- Added Windows-style cell/multiple selection, Ctrl+C/Ctrl+A, Delete key and right-click table actions while preserving native text field editing.
- Added F5 refresh and cache clearing without deleting saved data.
- Added WAL/full-sync database durability, autosaved form drafts, draft recovery and periodic/startup/shutdown database snapshots with rotation.
- Added recovery workspace, crash-session detection and single-instance data-folder lock.
- Added schema v4 upgrades and restoration of v1–v4 backups.
- Added actual abrupt-process-exit tests, clipboard/deletion tests, refresh preservation, snapshot/draft recovery and expanded packaged-executable checks.

## 1.2.0 — 2026-11-15

- Added city/county jurisdiction type, name and department to permits.
- Added application and requirements website links with explicit browser buttons and a requirements-page-reviewed checkmark.
- Added per-permit application requirement checklists, source links, saved ready checkmarks, completion dates and progress counts.
- Added checklist CSV exports, search and project report coverage.
- Preserved earlier data with schema v3 upgrades and v1/v2/v3 backup restoration.
- Added permit-specific persistence, URL, migration, checklist UI and packaged-executable checks.

## 1.1.0 — 2026-11-15

- Added dedicated architecture, engineering, electrical/fire, plumbing, mechanical/HVAC, site/civil and other-trade workspaces.
- Added project-wide filtering and discipline/area tags for tasks and contacts.
- Added meetings with agendas, attendance, minutes, decisions and linked action tasks.
- Added plan/CAD/BIM metadata, sheet numbers, drawing types, scales, designers and issue purposes while preserving file revision history.
- Added RFI, submittal, permit, inspection, punch-item and change-request registers.
- Added trade bid packages, multiple bidder estimates, detailed quantities/area takeoff, material waste, labor hours/rates, equipment/subcontract/fixed costs, allowances and alternates.
- Added precise decimal totals, material tax, markup, contingency, discount validation, currency-separated comparison, award protection, CSV cost exports and printable estimates.
- Added safe v1 database upgrades with pre-upgrade snapshots and v1/v2 backup restoration.
- Expanded search, project reports, dashboard and timeline coverage.
- Expanded automated tests and Windows packaged-executable checks for new workspaces and bidding.

## 1.0.0 — 2026-11-15

- Local projects, contacts, tasks, communications and milestones.
- Document version history, file retention and resubmission review flags.
- Dashboard, cross-record search, CSV exports, printable reports and email drafts.
- SQLite backup/validated restore, fictional samples and automated tests.
- Windows PyInstaller build and artifact workflow.
