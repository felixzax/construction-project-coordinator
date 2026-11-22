# Phase 2 review only

This is schema/migration and shared manual tracking work only. Application version remains **1.11.0**; database schema becomes **12**. Main, README, CHANGELOG and VALIDATION release documentation are unchanged. No agency requirements, templates, rule text or sources are seeded. No external service is contacted. No release build is produced.

## Working shared tracking

- One optional Regulatory & Permits sidebar entry with internal tabs. Restore it from Hidden sections or Sections. Existing hide/reorder, per-project preferences, All projects preferences and light/dark themes apply.
- Project Profile: Subject to CA Construction General Permit (Undecided / Yes / No / Not Applicable), plus a single regulatory jurisdiction. Values use a companion table so existing profile columns and exports remain unchanged.
- Multiple contact roles per project; eAuthorization Unknown / Yes / No plus date only. Reassignment or contact deletion resets authorization. Contact deletion preserves requests and roles while unassigning the contact.
- Document Requests: optional permit/filing link, responsible contact, date, all six requested statuses, notes, provenance, text filtering, search, draft recovery, backed-up deletion and the existing Files manager (original upload, working edits, save copy).
- Inspection metadata belongs to the existing Inspection register. Inspector and deadline remain on the register; result, performed date, inspection kind, jurisdiction, findings and existing Correction link use a companion. Photos use the same register's Files. Changing the parent project/type is blocked while tracking is linked.
- Read-only project overview: separate permit jurisdictions/stages, outstanding document requests and dated tracker/filing records, passed/open inspections, days since recorded weekly inspection, open Corrections, Water Board site status, Waiting on Agency without overdue classification.
- References accept manual source metadata. Opening a link requires an explicit confirmation. No regulatory facts have been verified or presented as current.

As approved in the Phase 1 plan, City/County and Water Board workflow tabs and the Reports tab remain shells. Agency templates/checkers belong to Phase 3; Water Board filing, certification and calculator logic to Phase 4; compliance CSV/DOCX, existing dashboard/timeline and project/department report integration to Phase 5. Existing exports retain their layouts.

## Verification

See [baseline-tests.log](baseline-tests.log), [existing-tests.log](existing-tests.log), [tests.log](tests.log) and the corresponding JUnit XML files. The baseline ran all 297 original tests unchanged. The post-change existing suite still contains all 297 test cases; schema expectations were updated from 11 to 12 and sidebar assertions account for the newly hidden optional category. No cases were removed or skipped. Additional tests cover the new shared workflows and safety rules.

[Migration and rollback evidence](migration-and-rollback.json) records both empty and populated schema-11 **copies**. All original table definitions/columns and rows compare equal, including hidden-section and both section-order settings. Original database hashes remain unchanged. A real signed/stamped fictional PDF reference and bytes are preserved. Each upgrade creates `.before-v1.12.0.sqlite3` at schema 11 before DDL. Existing safety copies are not overwritten.

Rollback copied each safety database into a separate restored file and opened it successfully with the actual schema-11 application code pinned to baseline commit `6ed7592190c940ed21f3819ce2e31a626e819f94`: schema 11, no new regulatory tables, integrity `ok`, all original rows equal. Restoring that backup through the current application's restore path was also tested: it re-upgrades safely to schema 12 while preserving rows and preferences. Rollback requires the old application; opening a schema-12 database directly with version 1.11 is intentionally rejected. Database rollback does not delete or revert separately stored files.

Reproduce with `python scripts/verify_phase2_migration.py` from a clone containing the pinned baseline commit. The script creates only temporary fictional databases. Run tests with `QT_QPA_PLATFORM=offscreen python -m pytest -q`. Local environment is Linux, Python 3.12.14, PySide6 6.8.3. Windows execution and packaging are **not** claimed for Phase 2; the existing build workflow is deliberately skipped to honor the review gate.

## Decisions and limits

1. The optional category is hidden for new projects and All projects too, not only existing users. No preference rows are inserted during migration. New order entries normalize at the end without rewriting stored order.
2. Inspection progress treats a recorded past/present Pass as passed, Cancelled as excluded, and everything else as open. A performed weekly inspection with Fail/Correction still counts toward days since an inspection; a blank, future or cancelled result does not. No regulatory seven-day alert is implemented before Phase 4 verification.
3. Document requests remain outstanding until Approved or N/A; Received and In Review still need coordination. Waiting on Agency applies to tracker records; it does not change old task/permit statuses or overdue logic.
4. Provenance is normalized: `source_id` links document title, publisher, revision date and URL; each template/rule/item additionally stores its own last-verified date, applicability and Verify label. No global content is inserted. Global references/templates/rules survive project deletion.
5. Future flexible metadata uses validated JSON alongside explicit core columns. These columns reserve all fields in the approved A/B/C scope. **Phases 3–5 as specified need no further schema bump**; they will add verified content, logic, UI and exports within schema 12. This does not promise arbitrary future scope can never require migration.
6. Manual fees/valuations are not automatically posted to budgets. No filings can be marked Ready or submitted through the Phase 2 data API before Phase 4 implements verified blockers. Historical rows remain when profile applicability changes.
7. Privacy checks are prospective and reject obvious credential assignments/URLs, private keys, certificate/signature file types, eAuthorization form filenames and detectable sensitive text/ZIP entries. Ordinary signed/stamped PDFs are allowed. Text inspection is limited to 20 MB and expanded inspectable ZIP contents to 100 MB; encrypted ZIPs are rejected. PDFs/CAD/images and opaque archive formats are not parsed; the app cannot guarantee detection of secrets inside them. Existing records/files are preserved, not retroactively scanned or removed. Users must screen those files. These checks are not encryption or a DLP guarantee.
8. The exact additional warning is visible in Regulatory & Permits and the shared Files dialog: "Do not attach files containing logins, passwords or payment details; this app is not encrypted." The existing Files editing guidance remains.

No agency requirement text or source conflict assessment was written. Phase 3 will use only the user's supplied sources and official agency pages; unverified material remains an editable Verify item.

## Every added table and column

There are **21 new tables, 280 columns including primary-key ids, and zero added columns on existing tables**. [schema-inventory.csv](schema-inventory.csv) also lists types, defaults, nullability and primary keys. Source definitions and constraints are in `cpc/regulatory_schema.py`.

- **reg_project_settings**: `id`, `project_id`, `cgp_subject`, `jurisdiction`, `sidebar_visible`, `notes`.

- **reg_sources**: `id`, `title`, `publisher`, `source_kind`, `document_revision_date`, `url`, `last_verified_date`, `verification_status`, `conflict_notes`, `notes`.

- **reg_project_roles**: `id`, `project_id`, `contact_id`, `role`, `delegate_for_role`, `eauthorization_status`, `eauthorization_date`, `notes`.

- **reg_templates**: `id`, `template_key`, `jurisdiction_key`, `occupancy_type`, `work_type`, `permit_family`, `title`, `source_id`, `last_verified_date`, `if_applicable`, `verify_label`, `active`, `builtin`, `details_json`.

- **reg_template_items**: `id`, `template_id`, `item_key`, `title`, `check_kind`, `source_id`, `last_verified_date`, `if_applicable`, `verify_label`, `sort_order`, `details_json`.

- **reg_wb_sites**: `id`, `project_id`, `wdid`, `regional_board`, `permit_type`, `risk_level`, `sediment_risk`, `receiving_water_risk`, `combined_risk`, `total_acres`, `disturbed_acres`, `construction_start`, `grading_complete`, `final_stabilization`, `status`, `location_address`, `latitude`, `longitude`, `r_inputs_fingerprint`, `r_overall_text`, `r_state`, `k_text`, `ls_text`, `erosion_enabled`, `notes`, `details_json`.

- **reg_filings**: `id`, `project_id`, `wb_site_id`, `filing_type`, `regulatory_lane`, `reference`, `prepared_by_contact_id`, `certifier_role_id`, `certifier_name_snapshot`, `certifier_role_snapshot`, `certifier_eauth_snapshot`, `certifier_eauth_date_snapshot`, `readiness_flag`, `status`, `deadline`, `submitted_date`, `decision_date`, `manual_fee`, `currency`, `reason_for_change`, `fields_changed_json`, `report_period_start`, `report_period_end`, `notes`, `source_id`, `last_verified_date`, `if_applicable`, `verify_label`, `details_json`.

- **reg_permit_details**: `id`, `register_id`, `jurisdiction_key`, `permit_family`, `occupancy_type`, `work_type`, `local_reference`, `fire_district`, `cycle_no`, `stage`, `current_template_id`, `related_wb_site_id`, `related_wb_filing_id`, `valuation_total`, `valuation_addition`, `valuation_remodel`, `currency`, `notes`, `details_json`.

- **reg_document_requests**: `id`, `project_id`, `register_id`, `filing_id`, `requested_from_contact_id`, `title`, `needed_by`, `status`, `notes`, `source_id`, `last_verified_date`, `if_applicable`, `verify_label`.

- **reg_inspection_details**: `id`, `register_id`, `inspection_kind`, `inspection_date`, `jurisdiction`, `result`, `qualifying_event`, `findings`, `corrective_action`, `correction_id`, `source_id`, `last_verified_date`, `if_applicable`, `verify_label`, `notes`.

- **reg_requirement_details**: `id`, `requirement_id`, `template_item_id`, `template_key`, `origin`, `jurisdiction_key`, `hidden`, `deleted`, `source_id`, `last_verified_date`, `if_applicable`, `verify_label`, `details_json`.

- **reg_city_records**: `id`, `project_id`, `permit_register_id`, `record_kind`, `reference`, `parent_sub_id`, `notes`, `details_json`.

- **reg_review_cycles**: `id`, `project_id`, `register_id`, `cycle_no`, `stage`, `submitted_date`, `agency_response_date`, `notes`, `details_json`.

- **reg_cycle_reviews**: `id`, `cycle_id`, `discipline`, `status`, `contact_id`, `due_date`, `response_date`, `notes`, `source_id`, `last_verified_date`, `if_applicable`, `verify_label`.

- **reg_tracker_steps**: `id`, `project_id`, `register_id`, `filing_id`, `template_item_id`, `step_key`, `title`, `status`, `deadline`, `occurred_date`, `contact_id`, `cycle_id`, `source_id`, `last_verified_date`, `if_applicable`, `verify_label`, `notes`, `hidden`, `deleted`, `sort_order`, `details_json`.

- **reg_manual_charges**: `id`, `project_id`, `register_id`, `filing_id`, `title`, `amount`, `currency`, `status`, `paid_date`, `source_id`, `last_verified_date`, `if_applicable`, `verify_label`, `notes`.

- **reg_filing_changes**: `id`, `filing_id`, `field_name`, `previous_value`, `revised_value`, `source_id`, `notes`.

- **reg_rfactor_periods**: `id`, `wb_site_id`, `position`, `start_date`, `end_date`, `r_value_text`, `calculated_on`, `notes`, `needs_recalculation`, `verification_flags_json`, `inputs_fingerprint`, `source_id`, `last_verified_date`, `if_applicable`, `verify_label`.

- **reg_rules**: `id`, `rule_key`, `title`, `body`, `applies_to_role`, `source_id`, `last_verified_date`, `if_applicable`, `verify_label`, `origin`, `builtin`, `hidden`, `deleted`, `details_json`.

- **reg_rule_overrides**: `id`, `project_id`, `rule_id`, `record_table`, `record_id`, `warning_code`, `reason`, `occurred`, `user_label`, `details_json`.

- **reg_template_tombstones**: `id`, `project_id`, `register_id`, `template_item_key`, `reason`, `occurred`.

