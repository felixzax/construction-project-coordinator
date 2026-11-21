# Remaining phases — 1.12.0 review delivery

Phases 4 and 5, plus Person Responsible for Seal, extend the approved Phase-3 work in draft PR #1. Version 1.12.0 is a downloadable review build. Main remains unchanged; PR merging and GitHub Release publication are not performed.

## Features

- Manual Water Board site coverage, roles, filing log, annual periods, existing inspections/corrections, dated rules and checklist; County CEQA NOD stays a separate lane.
- Exact manual R-period arithmetic, stale-input detection, calendar-year generation, explicit leap/Feb-29 verification, optional R×K×LS, draft-only COI copy and clipboard helpers. No EPA/SMARTS calls or rainfall model.
- Non-overridable COI reason/LRP/DAR/eAuthorization blockers; typed, logged warning overrides. Historical submission snapshots are retained.
- Seal-responsible Contact name, discipline and notes in permit setup and reporting; no seal/signature/certificate content is stored.
- Per-list and full compliance CSV/DOCX, printable project integration, correctly tagged department records, outstanding dashboard/timeline dates, weekly coordination warnings and readable search labels.
- Existing local Files, immutable originals/working copies, autosave/recovery, filtering, hide/order and themes. No extra schema bump: **schema remains 12**.

[Every new screen and action](SCREENS.md) documents setup, roles, filings, annual records, calculator, rules/checklist, inspections, exports and limitations.

## Evidence

**409 tests passed on Windows (287.86s) and Linux (57.73s), with zero failures/errors/skips.** This includes all 364 existing cases and 45 new remaining-phase cases. The earlier temporary Phase-4-deferred expectation was updated to the actual COI blocker; no cases were removed. [Windows run](https://github.com/felixzax/construction-project-coordinator/actions/runs/44880476892) tests `ca48e877bbe8196ece759bc2ea509c46fc4296c5`. Source smoke exited 0. The review build succeeded, including ZIP extraction, isolated offscreen/native Windows smoke checks, and verification of the exact downloaded artifact. [Download the verified Windows ZIP](https://github.com/felixzax/construction-project-coordinator/actions/runs/44880476892/artifacts/14698031366). `windows-build.json` and `windows-build.log` record the completed steps, tested commit and artifact digest.

- `linux-test-results.xml` / `linux-tests.log`: actual local pytest results.
- Windows workflow/job summaries, JUnit and logs: recorded after their successful run, with the tested commit.
- `schema-backup-and-golden.json`: empty and populated copies of the approved Phase-3 database preserve schema SQL, every existing row, hidden preferences and section order. Backup/restore passes; the original source hashes remain unchanged. No tables/columns are added. It also verifies 105.14 and the recorded seal name.
- `source-revision-register.csv`: **139 catalog item definitions** across City/County and Water Board, with source, printed revision/unknown precision, URL, verified date and Verify label.
- `water-sources-and-conflicts.json`: eight official Water Board PDFs and five source/policy qualifications. Earlier City/County evidence remains in `review/phase3/`.
- `scripts/verify_phase45.py` reproduces the offline evidence using fictional temporary data and pinned Phase-3 code. It makes no agency request.

No test result or packaged-executable success is claimed until the corresponding command/job completes. Source tests use Python/Qt, whereas the package workflow runs the actual executable with Python/Qt environment paths removed and verifies the exact downloaded artifact.

## Source and policy qualifications

1. The official R guide now says **February 2024**. It shows 2025-11-01–2028-08-15 and values 45.49 + 45.49 + 42.13 = **133.11**. The requested earlier 2020–2022 / **105.14** case remains an independent arithmetic regression. Live EPA output has not been verified.
2. April 2026 Site COI certification passages contain inconsistent NOI/NOT labels. Those button instructions remain Verify. The clear LRP/DAR/eAuthorization introduction and the user's local blocker are used instead.
3. The Organization guide permits some changes by any user; the requested strict COI Ready/Submitted check is an office policy, not a claim that all agency organization edits legally require that role.
4. Annual applicability includes active-WDID duration. Automatic next-period records are reminders labeled Verify, not an applicability determination.
5. Risk-specific weekly/storm requirements need permit verification. The requested active-site seven-day/missing-record flag is coordination only.

Only previously allowed sources and official agency PDFs/pages were used. Month-only printed revisions do not receive an invented day; source titles/notes retain their actual precision. Browser compatibility not established by the reviewed pages remains explicitly unverified. Existing City/County conflicts remain documented, including old 400 MB vs newer 50/300/150 MB limits.

## Decisions and limitations

- Feb 29-start anniversaries require manually verified boundaries rather than an invented February 28/March 1 rule. Known unambiguous calendar windows are generated and flagged when necessary.
- R values retain raw text, sum at sufficient Decimal precision and round half-up to two places. Individual numeric inputs have a 250-character / exponent-magnitude-1000 app safety limit; this is not a regulatory threshold.
- Current/complete totals only can be copied to a Not Ready draft Site COI. The app never marks or submits that filing automatically.
- Changing authorization revokes unsubmitted readiness; historical Submitted certifier snapshots are not rewritten. Notes remain editable on historical submissions.
- Replacing R periods preserves a recovery snapshot/file evidence and clears obsolete row drafts. Standard item deletion decisions persist; global rules/sources survive project deletion.
- County CEQA can be tracked without CGP coverage and is not deleted with a Water Board site.
- Unknown site risk, fees, applicability and source-day precision remain manual/Verify. No fee, risk threshold, agency decision or rainfall output is inferred.
- Ordinary signed/stamped PDF, Word and plain text containing the word “password” passed existing upload/download tests. An assignment-like harmless instruction is a reported false positive. Opaque binary contents are not guaranteed credential-free; the app is not encrypted.
- A review packaging job is authorized after Windows tests. The separate main-only release job stays gated. The final evidence-only commit does not alter tested application code.

The manual EPA checklist and cases the app cannot verify are in VALIDATION.md. Native desktop rendering, agency acceptance, current site conditions and EPA internals cannot be certified by this local coordination tool.
