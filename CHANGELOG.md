# Changelog

## 1.12.0 — 2026-11-20 (review build)

- Added optional Regulatory & Permits: isolated City/County templates, confirmed context swaps, cycles, checklist provenance, warnings and manual revision guidance.
- Added Person Responsible for Seal linked to Contacts, with discipline/notes and no signature/certificate storage.
- Added manual Water Board site coverage, roles, filings, annual periods, inspections and dated rules/checklists.
- Added manual EPA R-factor period arithmetic, exact Decimal sum, stale-input tracking, leap-year verification flags and optional R×K×LS. No EPA/SMARTS API or submissions.
- Enforced local COI reason/LRP/DAR/eAuthorization blockers and logged warning overrides; retained historical certifier snapshots.
- Added per-list/compliance CSV/DOCX, printable project reports and appropriately tagged department/dashboard/timeline integration.
- Added schema 12 migration with pre-upgrade safety copy; later regulatory work adds no further tables or columns. Existing records and sidebar settings/orders are preserved.
- Bundled dated official sources; unknown/conflicting requirements remain Verify. Kept originals/working copies, backup/recovery and privacy warnings.
- Review artifacts build only after Windows tests, with both catalogs and isolated frozen-executable verification. No merge or GitHub Release publication is automatic.

## 1.11.0 — 2026-11-20

- Added Work Orders with adjacent job valuation and permit-fee entry/list columns, currency, valuation basis and fee status.
- Added work-order references, site address, contractor/contact, scope, dates, progress and related city/county permit/contract context.
- Integrated original files, CSV/DOCX/project/department reports, pending deadlines, search, sidebar ordering/hiding and draft recovery.
- Kept valuation/fee coordination amounts separate from actual budget expenses; added amount/date/link validation and paid-fee reconfirmation after fee/currency changes.
- Added schema 11 migration and v1–v11 restores preserving prior approvals, parts costs, documents and sidebar preferences.

## 1.10.0 — 2026-11-19

- Added Approvals with item/work prices, currencies, review status/dates, optional contract context, supporting originals and retained review snapshots.
- Reset Approved requests for review after scope, price, supplier/context or supporting-file changes; included pending deadlines, search and CSV/DOCX/project/department reporting.
- Expanded Receipts into Receipts & Parts with company-stock/company/contractor/employee/owner sources, purchaser, payment responsibility and partial reimbursement amount/status/date/notes.
- Kept budget actuals counted once regardless of payer or reimbursement; retained separate labor/contract cost breakdowns and explicit receipt budget inclusion.
- Added schema 10 upgrades and v1–v10 restore coverage, preserving prior costs, attachments, project data and sidebar preferences.

## 1.9.0 — 2026-11-18

- Added hold-and-drag ordering in both the normal sidebar and Hidden sections, with independent saved orders per project and All projects.
- Added theme-aware insertion lines and row outlines, edge scrolling, cancellation and Alt+Up/Down keyboard ordering.
- Preserved section identities, active pages, hide/restore positions and compact command menus after reordering; added Reset section order under Sections.
- Added schema 9 project-order persistence, pre-upgrade safety copies, v1–v9 backup restore support and project-deletion cleanup.
- Added Qt drag/drop, highlight, persistence, navigation, backup/upgrade and invalid-order regression tests and expanded packaged smoke checks.

## 1.8.0 — 2026-11-18

- Consolidated workspace commands into compact New/Edit/Files headers with More and Export menus; grouped secondary document/checklist/bid/change-order dialog commands.
- Replaced ambiguous Dark mode text with Switch to Light mode / Switch to Dark mode, synchronized with the active theme.
- Added sidebar eye controls and one Hidden sections tab, eye/double-click/keyboard restoration, separate per-project and All projects preferences, and compact scrolling navigation.
- Preserved all record/file/export workflows, confirmation-backed deletion and existing project visibility preferences without changing schema 8.
- Fixed heterogeneous timeline rows with missing fields and retained submenu ownership; added real click, menu, export, deletion and visibility regression tests.

## 1.7.1 — 2026-11-18

- Added a default dark theme and immediate Dark/Light switching from the toolbar or View → Appearance.
- Persisted appearance per local data folder in appearance.ini without changing the database schema.
- Styled tables, forms, menus, toolbars, file editing, selections and disabled controls consistently in both themes.
- Added theme-aware overdue, budget, supplier approval and variance colors, appearance persistence checks and text/alert contrast tests.

## 1.7.0 — 2026-11-18

- Added one-per-project profiles with residential/commercial use, site/building details and explicit Undecided/Yes/No/Not Applicable checkboxes.
- Added Scope & Systems, 26 optional standard prompts, fuel/energy sources, customizable categories/types/specifications and typed custom information with required-value tracking.
- Added rebates/incentives with provider links, eligibility, deadlines and separate estimated/approved/received amounts, without automatically reducing budgets.
- Added per-project sidebar visibility, Minimal view, restoration controls and hideable system rows; hidden records remain searchable/reportable and outstanding deadlines remain visible.
- Added project-wide Change Orders and common original-file upload/download/versioned editing across project records, plus download of retained plan revisions.
- Added schema 8 migration, retained v7 attachment IDs, older-backup restores and new persistence/UI/attachment tests.

## 1.6.0 — 2026-11-17

- Added contracts, awarded-bid snapshots, approved change orders and budgets with receipt allocation and non-double-counted projections.
- Added multiple original attachments, integrity-checked downloads, ZIP manifests and external working-copy/reimport editing.
- Added basic TXT/CSV/DOCX/XLSX editing, versioned saves, ten-second editor autosaves and guarded format conversion including PDF reports.
- Added schema 7 migration/restore, finance search, deletion, recovery and project/department reports.
- Preserved standalone Windows runtime packaging and downloaded-artifact launch checks.

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
