# Verification record — 1.3.0

## Successful Windows release

- [Workflow and logs](https://github.com/felixzax/construction-project-coordinator/actions/runs/43797469360)
- [Download Windows application ZIP](https://github.com/felixzax/construction-project-coordinator/actions/runs/43797469360/artifacts/14194519768)
- Build commit: `2f70453f38409f5800800b36939337e9c7b1e0dc`.
- Runner: GitHub windows-latest, Python 3.12.10, PySide6 6.8.3, pytest 8.3.5, python-docx 1.2.0.
- Test result: **100 passed in 61.13 seconds**.
- PyInstaller build: succeeded.
- Packaged executable check: succeeded. It checked navigation/workspaces, meetings/bidding, saved permit checkmarks, table copying, refresh preservation, durable draft storage, pre-delete snapshot creation, deletion recovery, and actual CSV and DOCX output generation (including validating the Word ZIP structure).
- Workflow conclusion: **success**. JUnit results are downloadable as the test-results artifact on that run.
- Artifact size: 56642113 bytes.
- Artifact digest: `sha256:b30f13c739a231f7b65a358f823ff52c14c8e2e97b33906b8e29b9ac369023e9`.

This record and the README download link were added after the build completed. No application code changed in that documentation update.

## Local verification

Linux: Python 3.12.14, PySide6 6.8.3, pytest 8.3.5. Final full result: **100 passed in 7.50 seconds**. The expanded `main.py --smoke-test` also exited successfully.

## Added coverage

Transactional/cascading deletion; preserved contact/meeting work; recoverable full reset; retained document files; preventing deletion when a snapshot cannot be saved; invalid-discount rollback; rotating snapshot integrity; drafts in database backups; schema v3 upgrades and v1–v4 restore; real keyboard/cell copy and Delete behavior; filtered deletion; typed reset confirmation; cache refresh preservation; draft resumption/cancellation; and continuous-typing autosave.

The abrupt-exit test starts a subprocess, saves a record and autosaves a real Qt form, then calls `os._exit(17)` without cleanup. Reopening verifies the committed record, draft contents, and crash-session detection. This test passed on both Linux and Windows.

Exports are tested for all seven department groups, readable valid Word documents, project/text filtering, related cost detail and permit requirements, CSV contents, text escaping, actual export actions, and empty reports. An early clipboard test caught ordinary cells being treated as checkboxes; the copy logic was corrected and the full suite passed afterward.

## Limits

Tests use fictional data and disposable folders. No production records are deleted. No manual physical Windows/printer acceptance test or power-loss/disk-failure guarantee is claimed. Draft changes since the last successful autosave may be lost; document files need independent backup. Recovery snapshots are local, rotating database copies, and full-snapshot restoration replaces the whole database. The app remains unsigned.
