# Verification record — 1.8.0

- [Successful Windows workflow](https://github.com/felixzax/construction-project-coordinator/actions/runs/44402054054)
- [Download Windows artifact](https://github.com/felixzax/construction-project-coordinator/actions/runs/44402054054/artifacts/14473721974)
- Build commit: `7d15f4dd6e9fd8a14767f9355d8df0381e849ca8`.
- Windows: **237 tests passed in 309.83 seconds**, followed by a successful standalone PyInstaller executable build.
- ZIP extraction and isolated launch passed.
- The actual uploaded artifact was downloaded, checked against its SHA-256 manifest, and launched successfully with offscreen and native Windows Qt platforms after removing build Python/Qt paths.
- Artifact size: 56429222 bytes.
- Artifact digest: `sha256:1450ce57d67b735e5846c2877b5fd7763d30b6a3414dde425eaa5c90b01c3b7e`.
- Local Linux: **237 tests passed in 26.67 seconds**; expanded application smoke check exited successfully.
- Compact workspace and Hidden sections layouts were visually inspected locally at 1280 × 800 in both dark and light themes.

New interaction tests click sidebar hide/restore eyes and the theme switch in both directions, use keyboard hide/restore, verify scrollable navigation, preserve separate project/All projects preferences, restore from an otherwise fully hidden sidebar, execute filtered CSV export from the compact menu, exercise deletion confirmation/recovery snapshots, and upload/download original documents from the compact file dialog. Hidden system deadlines, search, reports and original file bytes are retained.

Automated checks exposed submenu-lifetime and heterogeneous-timeline-field problems. Both were fixed and the tests reran successfully. Existing test-owned Qt windows are now explicitly disposed between tests so later theme checks do not restyle stale windows.

Packaged smoke checks click sidebar eyes in both directions, execute the new export menu and verify both theme-switch labels, in addition to existing project, scope, permit, file editing, backup and recovery checks.

README links and this record were updated after the successful workflow; application code was unchanged. Bundled documentation records verification as pending at build time.

Schema 8 is unchanged. The executable remains unsigned. Hidden sections is always available; hiding affects navigation rather than record existence. All projects preferences are stored locally in appearance.ini, separately from database backups; individual project preferences remain in SQLite. Native Windows dialogs/decorations may follow Windows appearance. No manual walkthrough on the user's computer is claimed.
