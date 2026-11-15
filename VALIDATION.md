# Verification record

Local environment: Linux x86_64, Python 3.12.14, PySide6 6.8.3, pytest 8.3.5.

Executed from the project root on 2026-11-15:

```
python -m pytest -v --junitxml=test-results.xml
```

Result: 12 tests passed, including headless Qt navigation and task editing, retained file versions and timeline task editing. The JUnit report is included. A test invocation initially made from outside the project root failed import collection; running from the documented project root resolved it.

Not performed: Windows runner tests, Windows PyInstaller build, Windows executable launch, printer hardware testing, GitHub artifact publication. GitHub authentication in this session is invalid and no target repository URL was supplied. The workflow is provided but no successful workflow or artifact URL is claimed.

Additional manual scripted check: instantiated the populated Qt window, captured its dashboard, and rendered a project report to PDF successfully on Linux. This does not establish Windows printer compatibility.
