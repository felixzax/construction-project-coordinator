# Phase 3 review only — City & County permits

Phase 3 extends the approved draft PR #1. Do not merge or release. App version remains **1.11.0**, schema remains **12**. README, CHANGELOG and VALIDATION release documentation are unchanged. Phase 4 Water Board workflows/calculations and Phase 5 compliance exports/dashboard integration are not implemented here.

## Implemented

- City & County tab inside the existing optional Regulatory & Permits area, using canonical Permit register records and schema-12 companion tables.
- Single-jurisdiction permit setup, Residential/Commercial and work-type/family context. Confirmed context swaps retain user items, IDs, Files and prior checks while excluding nonmatching generated items from both the new view and canonical checklist reader.
- Explicit idempotent Add standard action. It keeps edits, checked/hidden items and stable-key deletion tombstones. It does not seed agencies/requirements at startup.
- City manual tracker: Planning/PLN, SUB/intake, payment/review, corrections/resubmittal, processing/issuance, Job Set and inspection coordination. County tracker remains generic Verify wording. No 24-hour deadline is auto-created.
- Editable checklist and provenance, per-cycle discipline reviews, City record relationships, manual outside-agency charges, existing Files manager and source-link confirmations.
- City file-name/size warnings, editable limits, SUB upload warnings, Cycle 2+ / >3-cycle guidance, and issued-permit revision/deferred decision aid. All warnings/guidance are manual coordination, not submission or approval.
- Existing draft autosave/recovery, backed-up deletion, F5 refresh, filtering, text selection/copy and themes. Recovery selects the original project/permit and preserves generated tracker keys.

## Sources and verification boundary

[Source / revision register](source-revision-register.csv): **109 catalog items**, every item carrying source document, revision date or explicit unknown/Verify, official link, last-verified date, applicability, Verify state, locator, qualifications and source hash. The catalog is a dated snapshot, not a determination that requirements are currently applicable.

[Sources and conflicts](sources-and-conflicts.json): **14 official sources**, checked **2026-11-20 America/Los_Angeles**. Source document revision dates come from printed PDF footers; official pages without a published revision date remain unknown. A source revision date is the cited guide/form's date, not an invented date for every separately linked form. Directory listings establish form existence; they do not establish mandatory applicability to a project. County form prompts therefore stay editable Verify items.

Only the named City CDD-0269, CDD-0270, CDD-0316, EPC Quick Reference and EPC Guide v27, plus official City forms/PDFs, County BPI/forms pages and City Fire pages were used. No third-party research, other-city templates or fire-district checklists were imported. The named legacy County URLs redirect to BPI; the actual official forms page was followed from that landing page. [Retrieval URLs and hashes](source-retrieval.json) record the reviewed bytes. The app itself only reads its bundled catalog; it never fetches or submits agency data.

Five source conflicts/qualifications are recorded:

1. Guide v27 (2020-02-12), p11, recommends approximately **400 MB** per PDF. CDD-0316 (**2024-12-10**) gives **APP 50 / PLANS 300 / SUPP 150 MB**. Prefer the newer defaults; keep them editable. No REPLY limit was verified.
2. The earlier specification named CDD-0224 revision **2024-02-29**; the retrieved official PDF is **2026-01-01**. The newer file is linked. The earlier file was unavailable for line-by-line comparison.
3. Guide v27 p32 contains an MP `REPY` example; p33 and the newer Quick Reference use `REPLY`. The checker uses REPLY.
4. Quick Reference says complete PLANS on resubmittal; Guide v27 p34 qualifies that unaffected files need not be uploaded and revised files must be complete. The app warns to use complete revised files and verify an unaffected-file exception with intake.
5. Quick Reference p3 describes bookmarks on each PLANS page; newer CDD-0316 explicitly addresses files over 20 pages and separate-document bookmarks. Bookmark coverage remains a manual Verify item, with the newer checklist as the reference. More extensive bookmarks may satisfy both.

CDD-0269 currently prints **2026-01-01**, CDD-0270 **2023-01-14**, Quick Reference **2024-10-17**, Guide v27 **2020-02-12**, CDD-0259 **2026-01-01**, CDD-0278 **2026-07-12**. No claim is made that the older guide overrides newer forms, current code or agency instructions.

## Screens

[Every new screen, dialog and operation, step by step](SCREENS.md) covers setup, City tracker, context-swap confirmation, checklist, cycles/discipline reviews, City records, manual charges, file checks/limits/results, revision questions/results, sources/conflicts, external-link confirmation and recovery. This walkthrough is provided as the requested alternative to screenshots.

## Schema and privacy evidence

[Schema and privacy report](schema-and-privacy.json): opening a **copy** of a populated approved Phase-2 database preserves every schema SQL definition and existing row, hidden setting and section-order setting. **Zero new tables; zero new columns; no schema bump.** The untouched source database hash matches. Schema 12's explicit columns and existing JSON metadata cover this phase.

Files tests used fictional ordinary fixtures, without real personal or credential data:

| File | Result | Save-copy bytes |
| --- | --- | --- |
| Signed/stamped permit PDF (fictional ink/stamp representation; no certificate) | Accepted | Identical SHA-256 |
| Ordinary Word permit form | Accepted | Identical SHA-256 |
| Text saying “Use a password manager. Never share your password…” | Accepted | Identical SHA-256 |
| Harmless instruction `Password: do not put one in this form.` | **Blocked: known false positive** | No attachment stored |

The last sentence resembles a credential assignment, so the existing conservative privacy heuristic blocks it even though it contains no password. That limitation is reported rather than silently bypassed. The privacy checks themselves were not weakened. PDFs/CAD/images/opaque binary content are not semantically inspected. These checks are neither encryption nor a guaranteed secret detector. The existing visible note and exact additional unencrypted-file warning remain. Ordinary signed/stamped PDFs are allowed; digital signature/certificate files and eAuthorization forms/secrets remain prohibited.

## Verification results

**Windows: 364 passed in 282.74s; Linux: 364 passed in 49.19s.** Zero failures/errors/skips on either platform. [Successful Windows test-only run](https://github.com/felixzax/construction-project-coordinator/actions/runs/44846250490) tests commit `fc04b8073c2386d2fea4f5e26810312183694864`. Its packaging job is skipped with zero steps. The later review-evidence-only commit does not change tested application code.

Final Linux and Windows results and job links are recorded in [test-summary.json](test-summary.json), [linux-tests.log](linux-tests.log), and the Windows job evidence. All original 297 tests and the 25 approved Phase-2 cases remain, plus 42 Phase-3 cases. No existing test cases were removed or skipped for Phase 3. The Phase-3 suite covers jurisdiction isolation, context swaps/cancellation/transaction rollback, idempotence/edits/hidden/deleted items, file retention, form/source provenance, record relationships, cycles/warnings, file names/editable limits, revision guidance, ordinary file privacy and draft resume.

Windows CI is test-only. The `windows-tests` job runs pytest; the old packaging job requires an explicit `build_release=true` manual dispatch on **main** and is skipped for this branch. No executable/ZIP release, staging, launch verification or publishing job runs for Phase 3. Test-result XML artifacts are test evidence, not application builds. The workflow retains its historical name “Test and build Windows”, but its actual job/step results show this restriction.

Reproduce local evidence with `QT_QPA_PLATFORM=offscreen python scripts/verify_phase3.py` in a clone containing the approved Phase-2 commit. Run tests with `QT_QPA_PLATFORM=offscreen python -m pytest -q`. The evidence script uses only fictional temporary databases/files and does not contact agencies.

## Decisions and remaining limits

- Context changes archive generated items in existing metadata instead of discarding their edits, checked state or Files. Only explicit setup changes a legacy permit's jurisdiction; existing unextended projects/exports are not rewritten.
- Other/Engineering/Planning and the two separate City operational/enforcement types receive no preset checklist. County fire-district identification remains manual; no fire district is selected by the app.
- Dates and fees are manual. No City intake goal becomes an app deadline. Outside charges start blank and do not automatically post to budgets or make payments.
- File sizes use decimal MB (1,000,000 bytes). Checks are warnings, and REPLY size/FPP naming remain Verify rather than fabricated limits/patterns. Actual address/APN/model content and PDF formatting still need manual review.
- The built-in register describes the shipped catalog. User-edited project items and references remain on their project records; complete project compliance exports remain Phase 5.
- New schema-12 metadata stores context activation, preserved visibility, generated charge identity and revision answers. No schema changes were needed.
- The existing workflow gained a main-only, explicit release opt-in so authorized Windows tests can run without packaging. No release authorization is inferred.
- Source coverage is limited to the permitted reviewed documents/pages; agency application of the listed forms, site-specific conditions, current fees and all unknown source dates remain Verify. No compliance determination or current-law guarantee is made.

Stopped after Phase 3. PR #1 remains a draft, main is unchanged, and neither version bump nor release notes were produced.
