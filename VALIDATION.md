# Verification record — 1.7.1

- [Successful Windows workflow](https://github.com/felixzax/construction-project-coordinator/actions/runs/44389381885)
- [Download Windows artifact](https://github.com/felixzax/construction-project-coordinator/actions/runs/44389381885/artifacts/14467831342)
- Build commit: `eccd5a08a3df74869c47f7c4b888c5d887fe6d90`.
- Windows: **228 tests passed in 437.44 seconds**, followed by a successful standalone executable build.
- ZIP extraction and isolated executable launch checks passed.
- The actual published artifact was downloaded, its checksums verified, and its executable successfully launched with offscreen and native Windows Qt platforms after removing build Python/Qt paths.
- Artifact size: 56156862 bytes.
- Artifact digest: `sha256:3205f53f1f11c14a60244dc22eb88866b29ac50ccbdc0e77f6c1e75fd793b9cb`.
- Local Linux: **228 tests passed in 175.09 seconds**; the source smoke check exited successfully. Both themes were visually inspected locally.

New checks cover default dark appearance, toolbar/menu switching, preference persistence after reopening, unchanged project records/schema, fallback for an invalid saved theme, live form palette changes, theme-aware overdue alerts and contrast ratios for normal text, muted text, selection and alert colors. These color checks are not a full accessibility audit. Packaged smoke checks switch both themes, verify palettes and saved preference, and retain the existing project/systems/files/recovery checks.

An older test assumed a fixed light-red overdue background; it was updated to check the active theme's semantic alert color, and the full suite reran successfully. README download links and this record were added after the successful workflow; application code was unchanged. Bundled documentation records verification as pending at build time.

The executable remains unsigned. Windows-owned native dialogs and decorations may follow the operating system theme. Printed/exported reports retain their document appearance. Preferences are stored in appearance.ini beside the database, separately from database-only backups. Schema 8 is unchanged; no manual walkthrough on the user's computer is claimed.
