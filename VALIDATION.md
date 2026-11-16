# Verification record — 1.4.0

## Successful Windows release

- [Workflow and logs](https://github.com/felixzax/construction-project-coordinator/actions/runs/43799355760)
- [Download Windows ZIP](https://github.com/felixzax/construction-project-coordinator/actions/runs/43799355760/artifacts/14195962274)
- Build commit: `0f5ecbd155e296b206eff799c3349b214b0d9d96`.
- Runner: GitHub windows-latest, Python 3.12.10, PySide6 6.8.3, pytest 8.3.5, python-docx 1.2.0.
- Test result: **127 passed in 45.61 seconds**.
- PyInstaller packaging: succeeded.
- Packaged executable: succeeded. Alongside previous navigation, bidding, permits, clipboard, refresh/recovery and CSV/Word checks, it verified the Receipts workspace, estimated/actual difference, approval, resetting an obsolete approval after a price change, and receipt DOCX generation.
- Workflow conclusion: **success**. JUnit results are available in the test-results artifact.
- Artifact size: 56655181 bytes.
- Artifact digest: `sha256:29798c148738f0fa7c403e08839a910adf78393ab3b651160ab6383a05ef372a`.

This verification record and the direct README download link were added after the successful build, without changes to application code.

## Local verification

Linux, Python 3.12.14: **127 passed in 8.72 seconds**. The expanded `main.py --smoke-test` also exited successfully.

## Receipt coverage

Supplier/company/contact handling, estimate/actual amounts, unknown versus zero prices, precise over/under/on-estimate differences, approval/rejection/review dates, resetting obsolete approvals, preserving approval on note-only edits, amount/date/status validation, retained attachment content, search, CSV and Word exports, department/project reports, backup/restore, project/contact deletion, v4-to-v5 upgrade preservation, actual receipt form saves, attachment actions, project filtering and unfinished draft recovery.

All prior project, document, permit, bidding, clipboard, backed-up deletion, refresh and abrupt-process-exit recovery tests remain in the suite. Verification uses fictional suppliers and disposable folders; no production data is modified.

## Limits

Manual physical Windows/printer acceptance and real supplier/tax validation were not performed. Receipts are entered manually, without OCR, supplier synchronization, payment processing or accounting reconciliation. Attachments require a suitable Windows viewer and separate file backup. Drafts may lose changes since their last successful autosave. The app remains unsigned.
