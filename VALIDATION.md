# Verification record — 1.5.0

## Successful Windows release

- [Workflow and logs](https://github.com/felixzax/construction-project-coordinator/actions/runs/44035589933)
- [Download Windows ZIP](https://github.com/felixzax/construction-project-coordinator/actions/runs/44035589933/artifacts/14307312064)
- Build commit: `581fdb9f211e77afb5ead6615639ea7a50994598`.
- Runner: GitHub windows-latest, Python 3.12.10, PySide6 6.8.3, pytest 8.3.5, python-docx 1.2.0.
- Result: **147 tests passed in 65.15 seconds**.
- PyInstaller packaging: succeeded.
- Packaged executable check: succeeded. It verified existing navigation, permits, bidding, receipts, copy, refresh/recovery and exports, plus Corrections/Violations page contents, site address, required corrective action, resolution date, removal of resolved violations from outstanding dashboard work and issue DOCX output.
- Workflow conclusion: **success**. JUnit results are available in the test-results artifact.
- Artifact size: 56671268 bytes.
- Artifact digest: `sha256:bfb76225b9d00e2c10a6538cf4a64ca1725a0f773140b1f3c229298b5f87c9c4`.

This verification record and the direct README link were added after the successful build, without application code changes.

## Local verification

Linux, Python 3.12.14: **147 tests passed in 12.31 seconds**. The expanded `main.py --smoke-test` also exited successfully.

## Added coverage

Separate corrections/violations, site-address autofill, preservation of custom addresses, project switching and filtering, exact locations, required actions, status/date validation, resolution/reopening dates, related-permit project/type validation and unlinking, retained evidence, outstanding dashboard/timeline and overdue highlights, search, department/project reports, CSV/DOCX exports, draft recovery, backed-up project deletion and v5-to-v6 upgrade/restore preservation. Previous test coverage remains included.

## Limits

All test data is fictional. No real code-compliance determination, inspection approval, agency submission or physical Windows/printer acceptance test is implied. Statuses and required actions are maintained manually. Notice/photo files need independent document-folder backup. The app remains unsigned.
