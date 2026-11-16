# Verification record — 1.3.0

Local final verification: Python 3.12.14, PySide6 6.8.3, pytest 8.3.5 on Linux. The final full suite completed with **100 passed in 7.50 seconds**, and the expanded smoke check exited successfully, including real CSV and DOCX file generation. Final Windows evidence will be added after the successful build.

New tests exercise transactional/cascading deletion, preserved contact/meeting work, recoverable full reset, document-file retention, failed snapshot protection, discount rollback, rotating snapshot integrity, draft backup/restore, schema v3 upgrades, real keyboard/cell copying and Delete actions, filtered deletion, typed reset confirmation, cache refresh preservation, draft recovery, form cancellation and continuous-typing autosave.

A subprocess test creates a committed record and a real autosaved Qt form, exits immediately via os._exit(17) without cleanup, then verifies record/draft recovery and crash-session detection after reopening.

Tests use fictional data and disposable folders. No production records are deleted by verification. No physical Windows desktop/printer acceptance test or power-loss/disk-failure guarantee is claimed. Document files need independent backup.

Export tests cover valid Word files for all seven department groups, project/text filters, related bid cost details, permit checklists, CSV contents, Word text escaping, actual export actions, and empty reports.
