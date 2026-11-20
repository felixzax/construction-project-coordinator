# Verification record — 1.11.0

- [Successful Windows workflow](https://github.com/felixzax/construction-project-coordinator/actions/runs/44827044894)
- [Download Windows artifact](https://github.com/felixzax/construction-project-coordinator/actions/runs/44827044894/artifacts/14674956843)
- Build commit: `2952805f4d969582d8a1092065b80823cdc41a85`.
- Windows: **297 tests passed in 198.82 seconds**, followed by a successful standalone PyInstaller executable build.
- ZIP extraction and isolated launch passed.
- The exact uploaded artifact was downloaded, checked against its SHA-256 manifest, and launched successfully using offscreen and native Windows Qt platforms after removing build Python/Qt paths.
- Artifact size: 56475328 bytes.
- Artifact digest: `sha256:f1c5399e1b1381af845e918153e3faccaee382d5cd2bc5796dbd68e2ad29921f`.
- Local Linux: **297 tests passed in 39.71 seconds**; expanded source smoke check exited successfully.
- Work-order list and adjacent valuation/permit-fee entry fields were visually inspected locally.

New tests cover two-decimal amounts, unknown versus confirmed zero, invalid amounts/currencies/dates, waived/paid fee states and reconfirmation after paid-fee changes, address defaults, same-project permit and contract/currency validation, captured county/city context, preservation after link deletion, and valuation/fee tracking without duplicate budget expenses.

UI checks verify valuation and permit fee share a form row and adjacent list columns, permit selection fills jurisdiction, drafts recover the paired fields, hidden work orders retain deadlines/search/reports, CSV/DOCX exports retain separate amounts, original supporting files download unchanged, and deletion/restore preserves work-order data/files. Schema 10 upgrades preserve approvals, parts costs and sidebar order while adding schema 11.

Packaged smoke checks open the work-order entry form, enter and save the two adjacent amounts, link a permit, verify no budget posting, download original supporting files and generate CSV/DOCX reports, in addition to previous app checks.

README links and this record were added after the successful workflow; application code was unchanged. Bundled documentation records verification as pending at build time.

Schema 11 stores manually entered valuation and permit fees. Earlier databases receive a .before-v1.11.0.sqlite3 safety copy. The app does not calculate jurisdiction fees or transmit payments; budget actuals remain in the existing receipt/contract workflow. Files require a separate documents-folder backup. The executable is unsigned; no manual walkthrough on the user's computer is claimed.
