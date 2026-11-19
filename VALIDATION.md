# Verification record — 1.10.0

- [Successful Windows workflow](https://github.com/felixzax/construction-project-coordinator/actions/runs/44634654614)
- [Download Windows artifact](https://github.com/felixzax/construction-project-coordinator/actions/runs/44634654614/artifacts/14583990910)
- Build commit: `728423ccf9e3a33c515693927efb540d846e1388`.
- Windows: **279 tests passed in 160.62 seconds**, followed by a successful standalone PyInstaller executable build.
- ZIP extraction and isolated launch passed.
- The uploaded artifact was downloaded, checked against its SHA-256 manifest, and launched successfully with offscreen and native Windows Qt platforms after removing build Python/Qt paths.
- Artifact size: 56461046 bytes.
- Artifact digest: `sha256:a583383d2d5bcb375ce37c7a71935db7403cccd7113d670c4934029549dd3ac3`.
- Local Linux: **279 tests passed in 35.58 seconds**; the expanded source smoke check exited successfully. The 29 focused approval/parts tests also passed after final report-label updates.
- Approval and Receipts & Parts layouts were visually inspected locally.

New coverage includes approval price rounding/unknown/zero states, invalid amounts/dates/currencies, retained prior approved-price snapshots, review reset after scope/price/files change, original supporting-file upload/download, reviewer and contract context, pending deadlines, hidden-section search/report retention, CSV/DOCX reporting and backed-up deletion/restore.

Parts checks include company-stock, company/contractor/employee/owner sources, explicit budget inclusion, direct-budget costs outside labor-only contracts, invoice amounts within inclusive contracts, partial reimbursements and Paid dates without double-counting, reimbursement bounds and receipt re-review. Schema 9 upgrades and restores preserve prior actual costs and custom sidebar order while adding schema 10 fields/tables.

Packaged smoke checks exercise priced approval review/history and supporting files, partial reimbursement without an extra expense, company-stock budget inclusion and new CSV/DOCX exports, alongside previous app checks.

The first workflow's application tests, build and ZIP launch passed, but the immediate artifact-download step reported the just-uploaded artifact as not found: [initial run](https://github.com/felixzax/construction-project-coordinator/actions/runs/44633569672). The artifact became visible afterward. Bounded download retries were added for this metadata timing issue. A new complete workflow reran the tests and successfully downloaded, verified and launched the published artifact; the successful run found its artifact on the first download attempt.

A focused test initially supplied a duplicate supplier keyword; its setup was corrected before the successful full run. README links and this record were updated after workflow success; application code was unchanged. Bundled documentation records verification as pending at build time.

Schema 10 stores manual approval records/history and parts/reimbursement details. Earlier databases receive a .before-v1.10.0.sqlite3 safety copy. Approval prices do not automatically add another budget cost; actual parts cost is counted once, and reimbursement is a portion of it. The app does not transmit payments or maintain inventory quantities. Attached files require a separate documents-folder backup. The executable is unsigned; no manual walkthrough on the user's computer is claimed.
