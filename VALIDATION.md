# Verification record — 1.6.0

- [Successful Windows workflow](https://github.com/felixzax/construction-project-coordinator/actions/runs/44201623124)
- [Download Windows artifact](https://github.com/felixzax/construction-project-coordinator/actions/runs/44201623124/artifacts/14381392666)
- Build commit: `6300cdc8479f4183f4e2c4dbd595c64f4c6f355c`.
- Windows runner: **190 tests passed in 73.61 seconds**, followed by a successful standalone PyInstaller build.
- ZIP extraction and isolated launch checks passed.
- The uploaded artifact was downloaded, its checksums verified, and its executable successfully launched with offscreen and native Windows Qt platforms after removing build Python/Qt paths.
- Artifact size: 56118005 bytes.
- Artifact digest: `sha256:82a4f7205a2eb863d3313dfc1609da6db56ecc774fb33707ccd86ae19a2fbf09`.
- Local Linux: **190 tests passed**, zero failures/errors/skips, in 13.321 seconds. Source smoke check exited successfully.

Coverage includes schema 6 to 7 upgrades, older backup restore, budget double-count prevention, contract/change-order validation, receipt allocation, original-file integrity/downloads, ZIP manifests, external working-copy isolation, basic Word/Excel editing, guarded conversions, autosaved versions and editor cancellation. Packaged smoke checks exercise text/Word/Excel editing and PDF/CSV/ZIP exports.

README download links and this record were updated after the successful workflow; application code was unchanged. The artifact's bundled documentation records the then-pending verification.

The executable is unsigned; no manual walkthrough on the user's own computer is claimed. Basic document editing is supported; PDF/CAD/complex Office files require their external application. Conversion reports may differ from Office page layout. Database backups require a separate documents-folder backup.
