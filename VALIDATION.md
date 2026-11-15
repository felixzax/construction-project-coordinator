# Verification record

## Windows build 1.0.0

- Build commit: `6be40219576170706809a918692ddd05e2f0f3d3`.
- Runner: GitHub windows-latest, Python 3.12.10, PySide6 6.8.3.
- Automated tests: **12 passed in 4.37 seconds**.
- PyInstaller Windows packaging: successful.
- Packaged executable: launched with disposable data, navigated every page, verified sample tasks, and exited successfully through `--smoke-test` with Qt offscreen.
- Workflow conclusion: **success**.
- [Successful workflow and logs](https://github.com/Azrempp/construction-project-coordinator/actions/runs/43765753865)
- [Download Windows artifact](https://github.com/Azrempp/construction-project-coordinator/actions/runs/43765753865/artifacts/14182108321)
- Artifact size: 50,458,839 bytes; expires February 13, 2027.
- Artifact SHA-256: `a73567c62208652a4d8b9d50c3525fb4ef95a5381914af9b82e47716be7a205e`.

The JUnit results are separately downloadable under the workflow's test-results artifact. The application artifact contains documentation from the build commit; this record was added after its successful completion.

## Local checks

All 12 tests also passed on Linux with Python 3.12.14. A populated Qt dashboard was captured and a project report rendered to PDF successfully. An initial invocation outside the project root failed import collection; running from the documented project root resolved it.

## Limits

No manual physical Windows desktop walkthrough or printer hardware test was performed. The packaged launch check is headless, not a full interactive acceptance test. The app is unsigned. No real company data or credentials are included.
