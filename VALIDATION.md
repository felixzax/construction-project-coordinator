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


## 1.12.0 regulatory verification (review build)

Automated test evidence for this work is recorded in `review/phase45/`. Windows test/build results are recorded only after the workflow actually finishes. Source testing uses Python 3.12 and offscreen Qt; packaged checks exercise the actual executable with Python/Qt paths removed. Main/PR merging and GitHub Release publication remain pending review.

### R-factor verification

- `test_requested_golden_three_periods_and_fraction_total`: 2020-11-01–2022-12-28 → 2020-11-01–2021-10-31, 2021-11-01–2022-10-31, 2022-11-01–2022-12-28. Inputs 45.49 + 45.49 + 14.16; expected and actual total **105.14**. Fraction independently verifies the sum.
- `test_single_year_golden_and_current_guide_example`: one-year 45.49 → **45.49**; retrieved February 2024 guide example 2025-11-01–2028-08-15 and 45.49 + 45.49 + 42.13 → **133.11**. These are mathematical fixture checks, not live EPA observations.
- `test_period_edge_dates_never_silently_changed`, `test_feb29_ambiguous_start_requires_manual_dates`, `test_property_windows_cover_every_day_exactly_once`: one-day, 365-day, leap-year and 180 reproducible randomized schedules cover all days exactly once. Ambiguous Feb 29-start anniversaries are blocked for automatic generation; manual boundaries/verification are required. Feb 29 boundaries, >365-day periods and leap-year Dec 31 endings are flagged; never silently shortened.
- Decimal/Fraction cases cover half-up rounding, raw text preservation and values beyond Decimal's default precision. Finite nonnegative inputs only. For resource safety individual numeric entries are limited to 250 characters and exponent magnitude 1000; this is an app limit, not a regulatory threshold.
- Incomplete/gapped/overlapping/mismatched periods, negative values, site changes and explicit recalculation are tested. Outdated results cannot be copied to a COI. Use in COI updates draft revised fields only.

Manual EPA checklist (not performed automatically and not claimed verified):

1. Open https://lew.epa.gov/ yourself after the app confirmation.
2. Use latitude **38.5790**, longitude **-121.4735**.
3. Run **11/01/2020–10/31/2021**, **11/01/2021–10/31/2022**, **11/01/2022–12/28/2022** separately.
4. Compare the real outputs with the earlier supplied example **45.49, 45.49, 14.16** and document differences. EPA may have changed its data or calculator.
5. Independently verify any Feb 29 boundary, 366-day window or leap-year December 31 end. The app does not verify EPA internals or claim the guide's historical calculator behavior still applies.
6. Confirm the construction period and permit applicability with the QSD/Regional Water Board before filing. Do not treat an app result or waiver hint as eligibility/approval.

### Sources and policy differences

Only the previously permitted sources and official agency pages/PDFs were used. The retrieved R guide is February 2024, not the requested 2020-12-30 copy; both example fixtures are retained and distinguished. Site COI and annual guides are April 2026. The COI guide has inconsistent NOI/NOT labels in certification passages, which remain Verify rather than copied button instructions. Organization changes may have different agency permissions; the requested LRP/DAR/eAuthorization blocker is an office policy for Ready/Submitted COIs. Annual applicability includes active-WDID duration; next-period creation does not establish applicability. Weekly flags are coordination only; risk-specific inspection conditions still require verification. Month-only source revision dates remain month-only in source titles/notes, with no invented day.

Ordinary signed/stamped PDF, DOCX and text mentioning “password” were accepted and saved back unchanged. The harmless sentence “Password: do not put one in this form” is a reported false positive. Binary contents and opaque archives are not guaranteed credential-free. No real credentials, certificate files, eAuthorization forms or sensitive payment information are used in test fixtures.
