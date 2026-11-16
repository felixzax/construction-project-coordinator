# Verification record — 1.1.0

## Successful Windows release

- [Workflow and logs](https://github.com/felixzax/construction-project-coordinator/actions/runs/43792352921)
- [Download Windows application ZIP](https://github.com/felixzax/construction-project-coordinator/actions/runs/43792352921/artifacts/14192793594)
- Build commit: `b81eaf781768d2f82c9d1025869e357331e4eb1d`.
- Runner: GitHub windows-latest, Python 3.12.10, PySide6 6.8.3, pytest 8.3.5.
- Result: **41 tests passed in 36.64 seconds**.
- PyInstaller build: succeeded.
- Packaged executable: launched successfully with disposable data via `--smoke-test`; all navigation pages, seeded discipline sections, meetings, bid selection, bid calculation and bid report generation were checked.
- Workflow conclusion: **success**. JUnit results are available as the test-results artifact on that run.
- Application artifact size: 50499759 bytes.
- Application artifact digest: `sha256:172e889b034b1532a1f70b4d48a3eb1e8544357b7be5369ff15b775b07dc5e5c`.

The shipped documentation reflects the build commit; this verification record and the direct README download link were added after that build completed. No application code changed in that documentation update.

## Local verification

Linux, Python 3.12.14, PySide6 6.8.3, pytest 8.3.5. Final `python -m pytest -v --junitxml=test-results.xml` result: **41 passed in 2.40 seconds**. The expanded `main.py --smoke-test` also exited successfully. A development SQL string quoting error was fixed before the complete successful local and Windows runs.

## Coverage and limits

Coverage includes v1 upgrade preservation and safety snapshots, restoration of v1/v2 backups, project/task/document behavior, approved revision preservation, discipline and register records, meetings/action links, bid arithmetic, measured areas, rounding, excluded alternates, invalid pricing/date inputs, discount limits, award protection, separate currencies, project filtering, linked-contact search, actual form saves, live cost previews and PDF rendering of both bid and expanded project reports.

No manual physical Windows desktop walkthrough, CAD vendor application integration test, printer hardware test, market-price validation or tax-jurisdiction validation was performed. The app is unsigned. All test contacts, projects and pricing are fictional.
