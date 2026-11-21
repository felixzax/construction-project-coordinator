# 1.12.0 remaining-phase walkthrough

All new pages are inside the existing optional Regulatory & Permits category. Restore it from Hidden sections, select a project, and use the internal tabs. The existing dark/light switch, sidebar order, text selection/copy, F5, drafts and recovery remain available. Dates are stored YYYY-MM-DD; R-period display and Copy dates use MM/DD/YYYY.

## Person Responsible for Seal

Open City & County, select a permit, and choose Set up / Edit. Select **Person Responsible for Seal** from Contacts, then optionally enter seal discipline and responsibility notes. The person's recorded name appears in the permit context and compliance report. The metadata uses schema 12's existing JSON; no column was added. It stores no seal image, signature or certificate. Deleting the contact unassigns its contact reference while retaining the recorded name for history. Clear the selection and save to clear that responsibility.

## Site coverage

In Project Profile set Subject to CA Construction General Permit to Yes, then open Water Board → Site coverage. Record WDID, Regional Water Board, Traditional/Linear, manually verified risk levels, acres, dates, location and status. Blank risk is unknown; the app does not determine coverage/risk from acreage. Construction start means first earth disturbance including vertical build; final stabilization is the R-period end. Optional R×K×LS is off by default.

Site Files uses the same retained-original/working-copy manager as other records. Delete site uses the existing recovery snapshot and removes linked site filings, R periods and its checklist records. Global rules/sources remain. County CEQA records are not children of Water Board sites and survive site deletion.

## Roles and eAuthorization

Use Roles to assign existing Contacts as LRP, DAR, DEP, QSD, QSP or other coordination roles. One person can hold multiple roles. Record eAuthorization **Unknown/Yes/No plus date only**; never attach its form or secrets. Contact reassignment/deletion resets authorization. Unsubmitted Ready filings lose readiness when the certifier's authorization is removed; historical Submitted snapshots remain.

## Filings

Choose Water Board → Filings → New. For an applicable site select NOI, Site COI, Organization COI, NOT, Annual Report or SWPPP Amendment. Without a CGP site, New still offers the separate **County CEQA Notice of Determination** lane. CEQA NOD is not Water Board NOT.

Record reference, preparer, certifier role, readiness, local status, dates, manual fee, reason, changed-field checkboxes and notes. Source/applicability fields remain editable. Status records an action performed elsewhere; Save never submits or certifies anything.

For COI Ready/Submitted the app blocks saving without a reason and an assigned LRP/DAR with eAuthorization Yes. A DEP cannot certify. These blockers cannot be overridden. Source/file/R warnings require a typed override reason when advancing; it is recorded in the override log. Existing historical Submitted notes can be updated without replacing their recorded certifier snapshot.

More → Revised fields stores previous/revised text on a Not Ready draft only. More → Files opens ordinary local originals; the COI guide's 100 MB / 30-character / special-character checks are warnings. Actual required documents and portal acceptance still need verification. Monetary amounts are manual; no fee calculation/payment/budget posting occurs.

## Annual periods

More → New annual period asks for the July starting year. It fills July 1–June 30 and September 1 due dates. Verify applicability, including the guide's active-WDID-duration condition. Marking an annual record Submitted locally creates the next period once. Repeated note saves do not duplicate it. A changed calendar/date generates a warning rather than silently overwriting a user's date.

## R-factor

1. Enter the site's construction start/final stabilization and location.
2. Open R-factor → Generate periods. It creates consecutive calendar-year windows and a final partial window. Replacing existing rows asks for confirmation and makes a recovery snapshot; old R values are replaced by blanks, associated file evidence moves to Site Files, and obsolete row-specific drafts are cleared to prevent ID reuse.
3. Open EPA calculator only after confirmation. The app makes no EPA request or rainfall calculation. Run each period manually in EPA and record its output, calculation date and notes.
4. New/edit a period to type R exactly, including trailing zero precision. Source arithmetic uses Decimal, not float. Empty R is Incomplete; gaps/overlaps/mismatched dates are Invalid. Negative/nonfinite values are rejected.
5. Site date/location changes mark recorded values **Needs recalculation** and overall R **Outdated**. Editing notes does not clear this. Re-enter a changed value or explicitly check **Water recalculated** after manually checking EPA. No dates or EPA numbers are silently changed.
6. Feb 29 boundaries, windows over 365 days and leap-year December 31 endings have Verify warnings. A nontrivial Feb 29-start anniversary cannot be generated safely and requires manual boundaries. One-day Feb 29 is allowed and flagged.
7. More → Copy dates copies MM/DD/YYYY dates; Copy overall R copies a complete current total. Use in draft COI chooses only a Not Ready draft Site COI and copies the total into its revised R field. It never changes filing status or submits.
8. Optional erosion estimate uses manual K and LS, with no Low/Medium/High thresholds. A low-erosivity-waiver hint is verification guidance, not eligibility.

The requested regression dates 2020-11-01–2022-12-28 and values 45.49 + 45.49 + 14.16 produce 105.14. The retrieved February 2024 guide contains a different example totaling 133.11. Neither test proves live EPA output; follow VALIDATION.md's manual EPA checklist.

## Checklist and rules

Explicit More → Add standard items adds missing dated-source items, labeled Verify with the current permit / Regional Water Board. It preserves edits, hidden items and deletion decisions. No REAP requirement is seeded. Standard rule text is read-only; add your own editable rules, and hide/delete either kind. Global rule/source records survive project deletion.

The Include hidden checkbox restores hidden items to the view. Source links open only after confirmation. Eight Water Board PDFs and their revision precision/qualifications are recorded in the source register. Dayless printed revisions remain month-only in source titles/notes; no day is fabricated.

## Inspections and dashboard

Use the existing Inspections register and shared inspection-details editor for weekly/pre/during/post-storm types, performed date, qualifying-event flag, result, findings and linked Corrections. A performed failed weekly inspection counts as an inspection; its corrections remain open. Blank/future/cancelled inspections do not establish the last performed weekly inspection.

Active sites show the requested seven-day coordination flag. No performed record shows a missing-record Verify warning, not a fabricated inspection date. Known late inspection dates and outstanding document/tracker/filing dates feed Dashboard and Timeline. Waiting on Agency is never overdue. Submitted/Approved/Done items drop from outstanding dates. Hiding a sidebar category does not erase its data or follow-up dates.

## Reports and exports

Water Board More, City/County Export and the shared lists offer CSV/DOCX of their current filtered records. Repeated role titles do not leak other filtered-out role records. Reports offers each compliance section or All with source/revision/link/last-verified fields, raw R inputs, warning/ambiguity flags, overrides, roles and the seal name. Printable status report includes compliance records. Tagged records also appear in their appropriate department reports; legacy unextended layouts remain unchanged.

CSV escapes formula-leading text. DOCX is a coordination report, not a form submission. Source dates refer to reviewed guides, not an assertion that a user's site measurements were independently verified. Back up both SQLite and the retained documents folder.

## Limits retained

No agency submission, email account connection, fee calculation, encryption, PDF signature validation or live EPA verification exists. Ordinary signed/stamped PDFs can be attached. Credentials, security answers, standalone signature/certificate files and eAuthorization forms/secrets remain prohibited. The assignment-like harmless sentence `Password: do not put one in this form.` is a known conservative false positive. Plain mentions of “password” are accepted. Screen binary files yourself; the guard is not DLP.
