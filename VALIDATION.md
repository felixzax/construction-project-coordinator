# Verification record — 1.9.0

- [Successful Windows workflow](https://github.com/felixzax/construction-project-coordinator/actions/runs/44414162109)
- [Download Windows artifact](https://github.com/felixzax/construction-project-coordinator/actions/runs/44414162109/artifacts/14477848823)
- Build commit: `39d5e5c4cf3ae37b7503e5fdedcab8b8e4e8473f`.
- Windows: **250 tests passed in 131.71 seconds**, then the standalone PyInstaller executable built successfully.
- ZIP extraction and isolated launch succeeded.
- The exact uploaded artifact was downloaded, checked against its SHA-256 manifest, and launched successfully with both offscreen and native Windows Qt platforms after removing build Python/Qt paths.
- Artifact size: 56443212 bytes.
- Artifact digest: `sha256:6699cca77a12d1aeaf8703208fc9ab92690f31e85135d916f483f855e1a490a2`.
- Local Linux: **250 tests passed in 31.53 seconds**; expanded source smoke check exited successfully.
- Drop insertion lines and target-row highlights were visually inspected locally at 1280 × 800 in dark/light modes and in Hidden sections.

New tests send Qt drag-enter/move/drop events through the list viewports, check moves in both directions, verify active-page identity and cross-page shortcuts after reordering, preserve independent hidden/sidebar orders, save separate project/All projects preferences, reopen saved order, cancel/reject foreign or stale-context drags, exercise edge auto-scroll and keyboard movement, check theme-specific indicator pixels, preserve eye controls after reordering, reset order without changing visibility/data, restore saved orders from backups and upgrade schema 8 while preserving records and hidden preferences. Invalid order data/backups are rejected.

Packaged smoke checks send Qt drag/drop events in both lists, verify insertion preview and persisted order, and open reordered/restored pages by section identity, alongside existing project, document, permit, recovery and theme checks. No manual physical drag walkthrough on the user's own computer is claimed.

One test assumed the list was scrolled to the top after selecting a lower category. Its setup was corrected to use the intended viewport position, then the full suite reran successfully.

README links and this record were updated after the successful workflow; application code was unchanged. Bundled documentation records verification as pending at build time.

Schema 9 stores per-project section orders in SQLite. Earlier databases get a .before-v1.9.0.sqlite3 safety copy. All projects order remains local to appearance.ini and is separate from database-only backups. Dragging reorders within a list; eye controls move categories between visible/hidden areas. The executable is unsigned, and Windows-owned dialogs/decorations may follow Windows appearance.
