# Verification record — 1.2.0

Final local Linux verification: Python 3.12.14, PySide6 6.8.3, pytest 8.3.5; `python -m pytest -v --junitxml=test-results.xml` completed with **62 passed in 3.25 seconds**. The expanded `main.py --smoke-test` opened a checklist, toggled saved checkmarks and exited successfully. Windows build evidence will be recorded after its workflow finishes.

New coverage includes permit jurisdiction fields, application/requirements links, checkbox persistence and timestamps, keeping permit approval independent of readiness, URL validation, requirement search/reports, checklist CSV export, actual checklist/form interaction, schema v2-to-v3 upgrades with preserved bids/permits, and restoration of older backups.

Tests use fictional jurisdictions and example.com links; no real agency website or email account is contacted. Browser opening is mocked in automated tests. No manual physical Windows desktop/printer or agency compliance acceptance test is claimed.
