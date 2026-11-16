# Verification record — 1.2.0

## Successful Windows release

- [Workflow and logs](https://github.com/felixzax/construction-project-coordinator/actions/runs/43794625927)
- [Download Windows application ZIP](https://github.com/felixzax/construction-project-coordinator/actions/runs/43794625927/artifacts/14193872669)
- Build commit: `60cbbc02abed6b54ffa3d26aa5222de2a674041a`.
- Runner: GitHub windows-latest, Python 3.12.10, PySide6 6.8.3, pytest 8.3.5.
- Tests: **62 passed in 40.85 seconds**.
- PyInstaller build: succeeded.
- Packaged executable: launched with disposable data, checked the existing navigation/workspaces/bidding, opened the permit checklist dialog, toggled requirement and review checkmarks and verified their persistence, then exited successfully.
- Workflow conclusion: **success**. JUnit results are available as the test-results artifact.
- Artifact size: 50515027 bytes.
- Artifact digest: `sha256:f77fcf847c2eeefaebcd046476bd7182d449c5b0544e30d5e8819d35395da1ad`.

This record and the README download link were added after the successful build. No application code changed in the documentation update.

## Local verification

Python 3.12.14, PySide6 6.8.3, pytest 8.3.5 on Linux: **62 passed in 3.25 seconds**. The expanded `main.py --smoke-test` also exited successfully.

## Coverage and limits

Includes all prior project, document, discipline, meeting and bidding checks, plus permit jurisdiction fields, application/requirements links, checkbox persistence and completion dates, keeping permit approval independent of readiness, URL validation, requirement search/reports, checklist CSV export, actual form/checklist interaction, schema v2-to-v3 upgrades with preserved permits and bids, and older backup restoration.

Tests use fictional jurisdictions and example.com links. Browser opening is mocked in automated tests. No actual agency requirements page is fetched or verified; users enter and maintain agency requirements themselves. No manual physical Windows desktop, printer or agency compliance acceptance test is claimed. The app remains unsigned.
