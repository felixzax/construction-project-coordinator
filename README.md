# Construction Project Coordinator 1.3.0

A local Windows desktop workspace for construction and property development coordination, consultant disciplines, drawing registers, meetings and detailed bid estimates. Python 3.12, PySide6 and SQLite. No cloud subscription, email connection or account is required to use the app.

## Download and run



Open [GitHub Actions](https://github.com/felixzax/construction-project-coordinator/actions/workflows/windows.yml), select a successful **Test and build Windows** run for version 1.3.0, and download the **ConstructionProjectCoordinator-1.3.0-Windows** artifact. Sign in to GitHub to access this private repository. Extract the artifact ZIP, then extract the contained application ZIP. Keep the entire `ConstructionProjectCoordinator` directory together and launch `ConstructionProjectCoordinator.exe`. Python is not required for packaged builds. The app is unsigned and Windows may show a reputation prompt. Workflow artifacts are retained for 90 days.

## Upgrade from 1.0.0, 1.1.0 or 1.2.0

1. In the old app, use Backup & Restore to back up your database. Also copy its adjacent `documents` folder to your backup location. Close all old app instances.
2. Extract the new build into a new application folder. Keep the old executable until you verify the upgrade.
3. Launch version 1.3.0 from the same Windows account. It uses the same Local AppData location, preserves existing projects, contacts, tasks and approved document revisions, and adds the new tables and fields automatically. It creates a `.before-v1.3.0.sqlite3` safety copy before upgrading a v1, v2 or v3 database.
4. Existing work is not replaced with demonstration data. New sections begin empty for existing users. Fresh workspaces may load fictional examples at the welcome prompt.

The upgrade is one way: the new schema is version 4. To roll back, close the new app and restore the matching pre-upgrade database before running an older app. Do not open the upgraded database with the old app. Version 1.3.0 can restore v1, v2, v3 and v4 backups; older backups are upgraded in a temporary copy before replacing live records.

## CSV and Word exports by department

Each department workspace — **Architecture, Engineering, Electrical, Plumbing, Mechanical / HVAC, Site & Civil, and Other Trades** — has **Export department report CSV** and **Export department report DOCX** buttons. These create actual CSV and Microsoft Word `.docx` files. Word does not need to be installed to generate them.

Department reports include matching discipline-tagged coordination packages, tasks, latest plans/document status, development registers and permit requirements, linked contacts with that discipline, bid packages, bidder totals and detailed cost items. CSV uses a common Record Type column to distinguish these records and includes quantity, unit, material, labor rates/hours, cost components, currency and totals for bid items. Do not sum all Total cells indiscriminately: bid estimate rows and cost-item rows describe different levels, and excluded alternates are identified separately. Currencies are not converted.

Choose a project at the top before exporting to limit the department report to that project. Its text filter also applies to exported records. Records without a matching discipline tag are not automatically assigned to a department; edit their discipline first. All projects includes archived projects, matching the coordination lists.

The other section lists have **Export listed records CSV** and **Export listed records DOCX** for their currently listed, filtered records. Word reports use readable headings and field/value tables rather than squeezing a wide database table onto a page. Permit checklists, bid cost breakdowns and document revision history also offer Word exports alongside CSV. The original Projects/Tasks export buttons retain their all-project summary/outstanding-work behavior.

## Select, copy and delete

Tables use Windows/Excel-style **cell selection**. Click a cell, drag to select a range, use Shift to extend a selection, or Ctrl-click for separate selections. **Ctrl+C** copies the selected cells as tab-separated text suitable for Excel, Outlook and text editors. **Ctrl+A** selects the table; right-click offers Copy and Select all. Column/row headers support selection, and text-entry fields retain their normal Windows editing and clipboard shortcuts. Tables remain read-only; use Edit or double-click to change record data.

Every record list has **Delete selected records** and **Delete all listed** actions, also available from its right-click menu. The **Delete** key deletes records represented by selected cells, with each row counted once. Delete all listed respects the current project and text filters. The sidebar sections stay available; these actions remove their records. Dashboard, search and timeline rows delete their underlying source records.

- Deleting a project removes its tasks, meetings, communication, discipline records, documents/history, permits/checklists, bid packages/estimates/items and activity. Global contacts remain.
- Deleting a contact keeps the work and unassigns that person across **all projects**, including designer/bidder links.
- Deleting a meeting keeps its action tasks and clears their meeting link.
- Deleting a document removes its revision records; deleting a permit removes its checklist. Deleting a bid package removes its estimates and cost items; deleting an estimate removes its items.
- Bid items and permit requirements have their own selected/all delete controls inside their dialogs. Plans & CAD → Version history also permits selected/all revision deletion.
- Deleting cost items is blocked and rolled back if it would leave an estimate's fixed discount larger than its remaining total. Reduce the discount first.

The confirmation shows the affected records. Before deletion the app creates a verified database recovery snapshot; deletion is cancelled if the snapshot cannot be saved. Attached document files are retained on disk. This is record removal, not secure erasure.

For a full reset, open **Recovery & Data → Delete ALL application data** and type **DELETE ALL**. This crosses all project filters and removes all application records and unfinished drafts. It keeps document files and recovery snapshots so an accidental reset can be recovered.

## Refresh, autosave and crash recovery

Use **F5**, the toolbar, or **Recovery & Data → Refresh / clear cache** to reload committed records, clear temporary table/display and SQLite memory caches, and free cached graphics. Project/text filters remain. Refresh does not delete records, attached files, saved drafts or recovery snapshots. Open forms are captured as recovery drafts; refresh does not silently submit unfinished forms as completed records.

**Saved records commit immediately.** The database uses SQLite write-ahead journaling and full synchronous commits. The desktop app permits one running instance per data folder; a dead process's lock is released when a new instance starts. After an unclean exit, the app notifies you on reopening. SQLite reopens committed work; use Recovery & Data for additional recovery options.

**Unfinished forms autosave drafts** after a 750 ms typing pause, or every 10 seconds during continuous typing. This covers projects, tasks, contacts, communication, milestones, discipline records, meetings, development registers, permits, requirements, estimates, cost items and document revision forms. A draft is not yet a saved record and may contain incomplete or invalid values. Recovery & Data → Resume selected draft reopens it for review and explicit Save. Successful Save removes its draft; Cancel intentionally discards the form and its draft. Discard selected drafts also requires confirmation. Changes since the last successful autosave can still be lost in a sudden crash.

The app makes consistent database snapshots on startup, every **two minutes** while running, on normal close, and before deleting records. Use **Save recovery snapshot** for an immediate copy. The `recovery` folder beside the database retains the latest five startup snapshots, five automatic/manual snapshots, and ten pre-deletion snapshots. Recovery & Data lists them for restoration. Restoring replaces the entire database, not just one deleted row, and first saves the current database as `.before-restore.sqlite3`. Use Backup & Restore to restore that safety file if needed.

Recovery snapshots include records and unfinished drafts, but document files remain separate. Keep an independent backup of both the database and documents folder. These safeguards cannot guarantee the last keystroke, protect against disk failure, or replace an external backup. If the database itself will not open, keep the data folder intact and restore a known-good database backup with its matching document files.

## Project workspaces

Use **Project workspace** at the top to choose one project or All projects. Tables, search, dashboard work and bidder packages follow this selection. Contacts show the linked project team when a project is selected. Create a contact with All projects selected, then associate it using Projects → Link contact. Text filters narrow each table; horizontal scrollbars expose additional details. Double-click rows to edit.

- **Dashboard / Projects / Tasks:** create and archive projects, maintain tasks with deadlines, priorities and responsible contacts, inspect project activity, export summaries and print status reports. Tasks can be tagged by discipline, building area and meeting. Complete a task explicitly to remove it from outstanding work.
- **Architecture:** architectural scope, designers, requirements, areas, approvals and deliverable dates.
- **Engineering:** structural and geotechnical coordination.
- **Electrical:** electrical and fire-protection scope and requirements.
- **Plumbing / Mechanical-HVAC:** fixture, piping, equipment and HVAC coordination through their own sections.
- **Site & Civil:** civil engineering, site work, landscaping and utilities.
- **Other Trades:** general coordination, interiors, roofing, concrete, masonry, steel and demolition.

Discipline sections contain coordination packages, rather than engineering design calculations. Record scope, responsible consultant, area, outstanding requirements and status, then use Tasks and Plans & CAD for related actions and deliverables. Choose the same project and discipline tags to keep records consistent.

## Meetings and communication

**Meetings** records meeting type, local date, 24-hour time, location, organizer, attendees, agenda, minutes and decisions. Attendees are free text. Select a meeting → **Create action task** to turn a decision into an assigned task linked to that meeting. Review the title, contact, deadline and priority before saving. Meeting and task must belong to the same project. Dates use `YYYY-MM-DD`, times use `HH:MM`; no calendar invitations are sent.

**Communications** records dated discussions and Open/Closed follow-ups. **Copy email draft** opens a professional draft for review and copying into Outlook. Nothing sends automatically. Close communication records when their follow-up is finished.

## Plans, CAD, BIM and document control

**Plans & CAD** stores document category, discipline, sheet/drawing number, drawing type, building/floor/area, scale, designer/consultant and issue purpose. Drawing types include DWG, DXF, BIM/Revit, plan sets, site/floor plans, elevations, sections, details, schedules, shop drawings, specifications, surveys and as-builts.

Create the document record, then **Add revision**. Each revision has a unique label, submission date, approval status, outstanding requirements and optional file. File attachments are copied to the local `documents` directory under unique names. Changing the original source file does not alter retained copies. **Version history** lists every revision and file path; **Open latest file** uses the associated Windows program. AutoCAD/Revit or another suitable viewer must be installed to open their formats; the app does not render or edit CAD geometry.

Once a document has a Submitted or Approved history entry, later revisions retain a resubmission review flag. Prior approvals remain unchanged; nothing is resubmitted automatically. To record an approval change, add a uniquely labeled entry such as `B-approved`. Do not overwrite retained files in external editors; edit your working copy and import a new revision.

## Development registers

Dedicated sections cover **RFIs**, **Submittals**, **Permits**, **Inspections**, and **Punch & Changes** (punch items and change requests). Record the reference number, discipline, area, responsible contact, submission date, deadline, response, notes and status. These are local coordination logs; there are no automatic agency submissions, compliance determinations or contractual approvals.

## City/county permits and application checklists

Select **Permits** in the sidebar. Create or edit a permit and enter:

- Jurisdiction type: City, County, City & County, State, or Other.
- City/county name and the responsible department.
- The official application/portal link and the application requirements link.
- A **Requirements page reviewed** checkmark, plus the existing reference number, status, responsible contact, submission date and deadline.

Select the permit → **Application checklist**. The dialog shows the jurisdiction and saved links with explicit Open buttons. Add each requirement with its description, optional source-page link and notes. Check the **Ready** box when an item is prepared; the checkmark saves immediately, records its completion date and updates progress such as **3/5 checked**. Unchecking clears the completion date. The separate review checkbox saves immediately too. Item edits save through the form's Save button; closing the checklist does not undo saved checkmarks.

Use **Open source link** to visit a selected item's link, falling back to the permit's requirements page when its own link is blank. **Export checklist CSV** includes the city/county, department, requirement links, checkmarks and completion dates. Project status reports include the permit checklist. Permit jurisdiction names, links and requirement descriptions are searchable and checklists are included in database backups.

Links are manually entered official website references and are opened in your browser only when you click Open. No page is fetched automatically and no live requirement list is imported. Demonstration links use example.com and must be replaced with the relevant agency links. Checkmarks track your preparation and review; they never submit the application or change its approval status. Keep the permit's status up to date separately.

## Bidding and estimating

### Typical workflow

1. Choose the project, then open **Bidding** → **New package**. Enter the trade/discipline, building area, scope, due date and bid type (Lump Sum, Unit Price, Time & Materials, Design-Build or Allowance).
2. Select the package → **Bidder estimate**. Select the bidder from Contacts, choose currency, enter received/valid-until dates, exclusions, schedule notes and percentages.
3. Select the bidder estimate → **Cost items & totals**. Add line items for each scope/material. Enter quantities manually or choose Area (length × width), plus the corresponding unit.
4. Enter material cost per unit, waste percentage, labor hours per unit, labor hourly rate, equipment/subcontract cost per unit and any other fixed cost. The form displays a live cost preview. Save, edit or duplicate items. Use item types Base, Allowance or Alternate; uncheck **Include in bid total** to retain an excluded alternate without adding it to the total.
5. Review the calculated totals, then use **Compare bids**, **Export comparison CSV**, **Export cost breakdown CSV**, or **Print estimate**. Print to paper or Microsoft Print to PDF using native print preview.
6. Set bid status to Received, Shortlisted, Awarded, Declined or Withdrawn as appropriate. Only one bid may be Awarded per package. Change the previous award's status before awarding another. Package status is maintained separately; no contracts or notifications are sent.

### Cost rules

| Component | Calculation |
| --- | --- |
| Effective quantity | Manual quantity, or length × width for area basis |
| Materials | Quantity × (1 + waste % / 100) × material cost per unit |
| Labor hours | Quantity × hours per unit |
| Labor cost | Labor hours × hourly rate |
| Equipment / subcontract | Quantity × corresponding cost per unit |
| Other | Fixed per-item cost |
| Direct subtotal | Included items' material + labor + equipment + subcontract + other costs |
| Material tax | Material total × tax percentage |
| Markup | Direct subtotal × markup percentage |
| Contingency | Direct subtotal × contingency percentage |
| Bid total | Direct subtotal + tax + markup + contingency − fixed discount |

Each line cost and bid adjustment is rounded half up to two decimal places using decimal arithmetic. Waste affects materials only. Markup and contingency do not compound. Tax applies only to materials; review tax treatment for your project. Prices are user-entered estimates, with no market-price feed. No unit conversion is performed: length and width must match the chosen area unit, and unit rates must match effective quantity. For a lump-sum allowance, use quantity 1 / unit lot with the fixed amount in an appropriate cost column.

Supported currencies are USD, CAD, EUR, GBP and AUD. Comparisons are grouped by currency; there is no currency conversion. Estimates without included cost items are marked as unpriced and listed after priced estimates within their currency. Review exclusions, alternates and schedule rather than treating the smallest numeric total as equivalent scope. A discount cannot exceed the pre-discount total; add cost items before applying a discount. Negative values, non-finite inputs, percentages above 100 and oversized derived amounts are rejected.

Building/floor/area is a descriptive location field. Length and width are the numeric takeoff fields. There is no automated drawing takeoff, quantity extraction, supplier pricing or accounting/payment processing.

## Search, timeline, reports and exports

Search covers the original records plus discipline scopes, meeting minutes, development registers, bid packages, bidder estimates and material/specification details. Revision requirements remain searchable. The project filter also includes linked contacts in project search.

Timeline shows task and milestone dates plus open coordination, meeting, register and bid deadlines. Double-click tasks/milestones to edit; other entries direct you to their source section. This remains a date-ordered list rather than a dependency/Gantt scheduler.

Projects → **Print report** includes project details, outstanding tasks, latest document requirements, milestones, communication, discipline scopes, meetings, development registers and bidder totals. The per-bid report prints item cost breakdowns. **Export outstanding CSV** exports active projects' outstanding work; **Export CSV** on Projects exports project fields. These two legacy exports cover all projects; per-section exports use the visible filtered table. CSV values are escaped against spreadsheet formulas. A document's latest revision state does not replace earlier approved history.

## Data and backups

Data stays outside the executable folder under Windows Local AppData. The status bar shows the exact SQLite path. `CPC_DATA_DIR` can override the data directory for testing or a separate workspace. Back up **both** the SQLite database and its adjacent `documents` folder. Database backups are consistent SQLite snapshots; attached files are backed up separately. Restore validates integrity, schema and relationships and saves `.before-restore.sqlite3` before replacing records. Only restore trusted backups and close other app instances first. On another computer, restore documents to their original paths or reimport recovered files as new revisions.

The app is single-user and stores data in plain local files. No synchronization, encryption, access control, reminder notifications, installer, automatic updater or email integration is included. Avoid passwords, bank details and sensitive payment information. Ordinary bid estimates and entered construction unit rates are supported. CAD viewing needs an external application. Sample contacts, projects and prices are fictional. No manual physical Windows/printer acceptance test is implied by the automated tests.

## Run from source on Windows 10/11 (64-bit)

Install Python 3.12, then run PowerShell in this folder:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python main.py
```

For a separate sample workspace in PowerShell, set `$env:CPC_DATA_DIR = "$PWD\sample-workspace"` before running. Remove the override with `Remove-Item Env:CPC_DATA_DIR` to return to normal storage.

## Tests and Windows packaging

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python -m pytest -v
Remove-Item Env:QT_QPA_PLATFORM
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean --windowed --onedir --name ConstructionProjectCoordinator main.py
```

PyInstaller must run on Windows to produce the Windows executable. The included Windows Actions workflow runs the full tests first, builds with PyInstaller, exercises the packaged executable with disposable data via `--smoke-test`, and uploads an application ZIP plus JUnit results. See VALIDATION.md for actual run evidence. A successful headless check does not replace manual desktop/printer acceptance testing.
