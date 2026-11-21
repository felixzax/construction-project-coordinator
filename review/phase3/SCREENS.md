# Phase 3 screen walkthrough

This is a step-by-step alternative to screenshots. All screens are native PySide6 widgets and use the existing light/dark theme, text selection and Ctrl+C. The Regulatory & Permits header continues to display the local-coordination disclaimer and the exact unencrypted-file warning. No screen submits files, pays fees or resubmits approved documents.

## Start and select a permit

1. Select a project in **Project workspace**.
2. If needed, open **Hidden sections** and restore **Regulatory & Permits** with its eye icon. Existing hide/reorder behavior is unchanged.
3. Open **Regulatory & Permits → City & County**.
4. The permit dropdown lists this project's existing Permit register records. It does not create a second permit database. Select a record to explicitly set it up, or choose **New permit**.
5. **More** holds Add standard checklist / tracker, Open official portal, Source / revision register and Delete permit. **Files** opens the existing versioned local Files manager for the selected permit.

## Permit setup and jurisdiction/template swap confirmation

1. Choose **New permit** or **Set up / Edit**. Set title, one jurisdiction, Residential/Commercial, work type and permit family.
2. Optional fields include reference, fire district (manual text), current stage, three manual valuations, currency, related Water Board records and notes. Water Board cross-links do not enable its deferred filing workflow.
3. City, County unincorporated and Other remain separate. Other, Engineering and Planning have no imported standard checklist. City Fire Development Services has a separate, explicitly Verify tracker. Operational Permit Inspections and Fire Code Enforcement remain empty editable types. No fire-district checklist or other city's requirements are imported.
4. Save. Setting up an existing legacy permit explicitly synchronizes its jurisdiction fields to the selected single jurisdiction. Merely opening a project does not alter legacy records or seed catalog data.
5. Changing jurisdiction, use, work type or family on an already configured permit shows **Confirm jurisdiction / template swap**, naming the old and new context. **No** cancels the save with no database changes; **Yes** swaps generated active items.
6. User-added items, Files and prior checks remain. Nonmatching generated items are kept inactive; returning to a context restores its edits/checks. A City check never checks a County requirement. Matching items within a City work-type change keep their checked state. Deleted generated checklist/tracker/charge items stay deleted.

## Tracker

1. From **More → Add standard checklist / tracker**, confirm the exact jurisdiction/use/work/family. This is an explicit, idempotent action; it adds missing items without overwriting edits.
2. The **Tracker** tab shows title, status, deadline, occurred date, responsible contact, notes and source metadata. City steps cover account confirmation (no credentials), package preparation, Planning clearance, SUB, intake, payment/review, corrections, resubmittal, processing/issuance, Job Set and inspection coordination.
3. County steps are generic and explicitly say **verify with County BPI**. County does not receive City record codes, forms, discipline presets or EPC checkers.
4. Use **New** for a manual step or select a row and **Edit**. Status choices include Waiting on Agency; it is never classified overdue in the shared overview.
5. Use **More** for Files, source link, hide/show or backed-up deletion. Check **Include hidden items for this template** to restore a hidden item. The text filter affects only the view.
6. No 24-hour intake deadline is generated. The dated City guide's response goal is identified as a goal in the intake notes.

## Checklist

1. Open **Checklist**. Generated prompts are filtered by jurisdiction, use, work and family. Forms whose scope applicability has not been established remain editable Verify/if-applicable items.
2. Select a row and use **More → Check / uncheck selected**, or edit its title, completion, notes, form link, source, last-verified date, applicability and Verify label.
3. **New** adds a user-owned requirement. It is retained through context swaps. Standard prompts never replace an existing user's text merely because a title changes.
4. **More → Hide / show**, Include hidden, Files, Open source and Delete work on the selected item. Deletion uses the existing recovery snapshot and records a stable-key tombstone.
5. The canonical Permits checklist reader also excludes inactive/hidden generated items, so a County permit does not display inactive City-generated checklist rows in the existing checklist/report path. Existing unextended permits retain their layouts and behavior.

## Review Cycles and discipline reviews

1. Open **Review Cycles → New**. Enter a positive cycle number, free-text stage, submitted/response dates and notes. Dates use YYYY-MM-DD. Edit the selected cycle to update it.
2. Select a cycle and choose **Discipline reviews**. Add/edit manual discipline rows with status, contact, due/response dates, notes and source metadata. Delete is backed up.
3. For City permits only, **Add City disciplines** adds the missing 12 disciplines shown on CDD-0270. Repeating the action preserves existing responses. County does not show this button or import the City discipline choices.
4. **Cycle warnings** shows Cycle 2+ REPLY/CDD-0270 guidance, complete revised PLANS/SUPP, APP only if changed, signed-stamp/manual formatting checks and the Plan Check Wait warning when that exact stage has not been recorded.
5. Cycle 4+ shows CDD-0270's possible additional hourly fees. No amount or approval is calculated. These are coordination warnings, not a submission blocker.
6. Parent cycles remain linked to their original permit; old-jurisdiction cycles are retained but are not displayed as the new jurisdiction's cycles.

## City Records

1. For a City permit, open **City Records → New**. Choose PLN, SUB, COM, RES, FPP or MP and enter the actual reference.
2. A COM/RES/FPP/MP can link to a SUB belonging to this same permit. The existing schema-12 unique index enforces one permit record per parent SUB. Cross-project/permit links are rejected.
3. Use **More → Files** for local copies. COM/RES/FPP/MP Files first warns that City uploads/resubmittals belong to SUB and asks whether to retain a local reference anyway. Cancel leaves Files unopened.
4. County and Other do not display or allow creation of these City record types. No external uploads occur even after accepting the local-reference warning.

## Manual Charges

1. Open **Manual Charges**. Explicit Add standard on a City Building permit offers dated-source suggestions for fire review, C&D, sanitation, schools and a Verify SMUD placeholder.
2. **New/Edit** records title, manual amount, currency, status, paid date, notes and provenance. Use Files for supporting ordinary documents.
3. No fee calculator, payment or automatic budget posting exists. Amounts start blank; the SMUD placeholder does not assert that a fee is owed. No named school/fire districts are imported.
4. Generated City charge suggestions are not presented as County charges after a swap. User-added charges are retained.

## File checks, editable size limits and warning results

1. Open **File checks → Check a local file name / size** and choose an ordinary local file. It is inspected for naming/size warnings only; it is not imported, rewritten or uploaded.
2. Enter the cycle (defaulting to the highest recorded cycle), naming basis (Address/APN/Master Plan), optional expected prefix and intended City record type.
3. Cycle 1 checks the CYC1 APP/PLANS/SUPP PDF shape; APN checks 000-0000-000-0000 shape. Cycle 2+ checks COM/RES/MP, seven digits, the selected cycle, and APP/PLANS/SUPP/REPLY. FPP naming remains explicitly unverified.
4. Results appear in **File warnings (no submission)**. They include a SUB warning for other intended record types, naming mismatches, editable size exceedances and manual PDF checks. A correctly shaped name does not verify its project address/content or agency acceptance.
5. Choose **Edit size warning limits**. APP 50 MB, PLANS 300 MB and SUPP 150 MB are the newer CDD-0316 defaults; REPLY is blank/unverified. Limits are editable per permit, use decimal MB (1,000,000 bytes), and may be left blank to require verification. Invalid/negative/nonfinite limits are rejected.
6. PDFs are not parsed for flattening, security, portfolios, bookmarks, stamps, orientation, scale or north arrow. Those stay manual checklist items. City EPC checks are not applied to County/Other or non-building families.

## Revision guidance questions and result

1. Open **Revision guidance → Review revision / deferred questions**.
2. Record whether a permit is issued, whether scope is expanding and whether the request is deferred. Unknown stays Unknown. Saved answers can be resumed through draft recovery.
3. Without a confirmed issued permit, the City result points to verifying a mid-review scope change in REPLY. Expanding an issued scope says a new separate permit is likely and must be verified. Unknown expansion asks for verification.
4. A potential issued-permit revision/deferred result cites CDD-0269 and the dated guide: new SUB, affected sheets, cloud/delta/date, same licensed professional, change-summary letter/supporting documents. Deferred also asks whether it was approved/listed on the original cover sheet.
5. The app never decides approval or submits the package. County/Other receives only jurisdiction-specific verification guidance, without City revision instructions.

## Sources, conflicts and external-link confirmation

1. Choose **More → Source / revision register** to see the 109 catalog items with their source document, printed revision date (or Not stated — verify), official link, last-verified date, applicability and Verify state.
2. **Conflicts / qualifications** lists five documented differences/qualifications. The newer CDD-0316 size defaults take precedence over the older approximately-400-MB recommendation. The official CDD-0224 now has a 2026 revision; the earlier named version was not available for line-by-line comparison.
3. **Open source** on a tracker/checklist row, or **Open official portal**, displays the URL and requires **Yes** before opening the browser. No account connection or submission exists.
4. **References** remains the shared editable source directory for user additions. The source register is the built-in dated catalog snapshot; current project edits remain on the project records. Full project compliance exports remain Phase 5.

## Recovery and privacy checks

New record forms use existing draft autosave and Recovery & Data. City forms retain their specific context when resumed; F5 refreshes the new lists through the existing refresh path. Delete confirmations use existing pre-delete recovery snapshots. Hide does not delete data.

The three ordinary test fixtures (fictional signed/stamped PDF, Word form, text mentioning “password”) all uploaded and saved back byte-identically. The harmless instruction `Password: do not put one in this form.` was blocked as a conservative false positive because it resembles an assignment. No credential-detection guarantee is made for binary documents; do not use these checks as encryption or DLP.
