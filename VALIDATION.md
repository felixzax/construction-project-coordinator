# Verification record — 1.5.1

Local Linux run: Python 3.12.14, PySide6 6.8.3, pytest 8.3.5; **156 tests passed in 9.85 seconds**. The source smoke check also exited successfully. Windows evidence will be added after its release workflow completes.

Diagnosis: the downloaded 1.5.0 artifact ZIP was inspected. It contains `_internal/shiboken6/Shiboken.pyd`, `shiboken6.abi3.dll` and supporting runtime DLLs. The reported libshiboken fallback error is reproduced by PySide6's directory lookup when the sibling shiboken6 folder is absent. This establishes the missing-folder error mechanism; the user's local folder was not inspected.

The correction ships a standalone one-file executable rather than relying on a copied companion runtime folder. New tests cover missing-runtime diagnostics before Qt import, complete runtime layout checks, startup log behavior, release manifest integrity, disallowing companion directories, removal of build dependencies from the launch environment, and launching from an external working directory. The Windows workflow tests the extracted ZIP and exact downloaded artifact, including a native Windows Qt launch, before its run is accepted as successful.

Limits: no inspection of the user's computer or manual physical Windows walkthrough is claimed. The app remains unsigned. No database schema changes are included in this patch.
