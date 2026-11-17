# Verification record — 1.5.1

## Verified Windows delivery

- [Successful workflow and logs](https://github.com/felixzax/construction-project-coordinator/actions/runs/44194649007)
- [Download standalone Windows artifact](https://github.com/felixzax/construction-project-coordinator/actions/runs/44194649007/artifacts/14378148252)
- Build commit: `161a235d43003f925cc870ca5c3bf2071f220ecd`.
- Runner: GitHub windows-latest, Python 3.12.10, PySide6 6.8.3, PyInstaller 6.12.0.
- **156 automated tests passed in 69.34 seconds**.
- Standalone one-file executable with explicit Shiboken collection: built successfully.
- Staging manifest: executable and documentation SHA-256 hashes verified; no companion runtime directory allowed.
- ZIP round trip: created ZIP, extracted into a fresh path containing spaces/Unicode, and successfully launched from an external working directory with build-machine Python/Qt paths removed.
- Actual published artifact: uploaded, downloaded through actions/download-artifact, checksums verified, then executable successfully launched with both **offscreen** and **native Windows** Qt platforms in isolation.
- Workflow conclusion: **success**. JUnit results are available as test-results.
- Artifact size: 55485480 bytes.
- Artifact digest: `sha256:48c0e8fff616b9c7f7382484616af33ab80fe4f177fd561096ccd702abc711b5`.

The artifact contains the executable directly rather than a nested application ZIP. This record and the README download link were added after the successful build; application code and shipped files were not changed afterward.

## Local checks and diagnosis

Linux, Python 3.12.14: **156 tests passed in 9.85 seconds**, and the source smoke check exited successfully.

The published 1.5.0 artifact was downloaded and inspected: its inner ZIP includes the Shiboken extension, ABI DLL and supporting runtime files under _internal/shiboken6. PySide6's reported libshiboken fallback ImportError was reproduced in a test by omitting that sibling directory. This establishes the missing-folder error mechanism; the user's local installation was not inspected.

The patch removes reliance on copying an external runtime folder, adds pre-Qt runtime checks and startup logging, and verifies delivery after compression and artifact download. New tests cover runtime completeness, early diagnostics without opening project data, manifest tampering, standalone layout, removal of build environment paths and isolated launch setup.

## Limits

No manual walkthrough on the user's computer is claimed. The executable is unsigned and requires supported 64-bit Windows. Database schema and business features are unchanged. Existing local project data stays in the same data directory; attached files still require independent backup.
