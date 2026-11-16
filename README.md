# Construction Project Coordinator 1.1.0

A local Windows desktop workspace for construction and property development coordination, consultant disciplines, drawing registers, meetings and detailed bid estimates. Python 3.12, PySide6 and SQLite. No cloud subscription, email connection or account is required to use the app.

## Download and run

**[Download the verified Windows 1.1.0 build](https://github.com/felixzax/construction-project-coordinator/actions/runs/43792352921/artifacts/14192793594)** · [Successful build and test logs](https://github.com/felixzax/construction-project-coordinator/actions/runs/43792352921). All 41 Windows tests and the packaged-executable check passed.

Open [GitHub Actions](https://github.com/felixzax/construction-project-coordinator/actions/workflows/windows.yml), select a successful **Test and build Windows** run for version 1.1.0, and download the **ConstructionProjectCoordinator-1.1.0-Windows** artifact. Sign in to GitHub to access this private repository. Extract the artifact ZIP, then extract the contained application ZIP. Keep the entire `ConstructionProjectCoordinator` directory together and launch `ConstructionProjectCoordinator.exe`. Python is not required for packaged builds. The app is unsigned and Windows may show a reputation prompt. Workflow artifacts are retained for 90 days.

## Upgrade from 1.0.0

1. In the old app, use Backup & Restore to back up your database. Also copy its adjacent `documents` folder to your backup location. Close all old app instances.
2. Extract the new build into a new application folder. Keep the old executable until you verify the upgrade.
3. Launch version 1.1.0 from the same Windows account. It uses the same Local AppData location, preserves existing projects, contacts, tasks and approved document revisions, and adds the new tables and fields automatically. It creates a `.before-v1.1.0.sqlite3` safety copy before upgrading a v1 database.
4. Existing work is not replaced with demonstration data. New sections begin empty for existing users. Fresh workspaces may load fictional examples at the welcome prompt.

The upgrade is one way: the new schema is version 2. To roll back, close the new app and restore the pre-upgrade v1 database before running version 1.0.0. Do not open the upgraded database with the old app. Version 1.1.0 can restore both v1 and v2 backups; v1 backups are upgraded in a temporary copy before replacing live records.

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
