# Construction Project Coordinator 1.0.0

A local, single-user construction office desktop application using Python 3.12, PySide6 and SQLite. No server, email connection, telemetry or subscription.

## Install and run on Windows 10/11 (64-bit)

Install Python 3.12, extract this source folder and open PowerShell in it:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python main.py
```

Choose whether to load fictional samples at first launch. `CPC_DATA_DIR` optionally overrides the storage directory. The status bar displays the exact database path; by default it is under Windows Local AppData. Data stays outside the executable folder.

## Windows executable and GitHub workflow

Push these files, including `.github`, to your GitHub repository root. Actions → Test and build Windows runs tests before PyInstaller on `windows-latest`. It also supports manual runs. After a successful run download the **ConstructionProjectCoordinator-1.0.0-Windows** artifact. Extract it, then extract the contained application ZIP. Keep the entire application folder together and launch `ConstructionProjectCoordinator.exe`. Python is not needed for packaged builds. Artifacts expire after 90 days and may require GitHub sign-in. The workflow does not publish a public GitHub Release.

To test and package manually on Windows:

```powershell
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python -m pytest -v
Remove-Item Env:QT_QPA_PLATFORM
.\.venv\Scripts\python -m PyInstaller --noconfirm --clean --windowed --onedir --name ConstructionProjectCoordinator main.py
```

The result is in `dist/ConstructionProjectCoordinator/`. PyInstaller must run on Windows to build a Windows executable. Builds are unsigned and may trigger Windows reputation prompts. A verified Windows build is available: [download version 1.0.0](https://github.com/Azrempp/construction-project-coordinator/actions/runs/43765753865/artifacts/14182108321). Sign in to GitHub to download from this private repository. See VALIDATION.md for the build evidence.

## Usage

- **Dashboard:** outstanding tasks, red overdue rows, upcoming follow-ups, and recently updated projects. Approved tasks remain outstanding until explicitly Completed.
- **Projects:** create/edit, filter, archive/unarchive, link contacts, view activity and project team, print a report, and export project fields to CSV. Archived records remain searchable but are excluded from dashboard work and outstanding exports.
- **Tasks:** deadlines, priorities, responsible contacts, notes, and six requested statuses. Select Edit or double-click a row. Dates use `YYYY-MM-DD`; optional dates may be blank.
- **Contacts:** local directory, with project associations made through Projects → Link contact and displayed under Activity.
- **Communications:** dated logs and Open/Closed follow-ups. Copy email draft opens a review window with a clipboard button; paste into Outlook yourself. Close communications to clear follow-ups from the dashboard. Nothing sends automatically.
- **Documents:** create a document and then Add revision. Revision labels must be unique within a document. Each entry records submission date, approval status and requirements. A new revision after Approved or Submitted is flagged for resubmission review without changing the previous entry or submitting anything. Record approval changes as a new entry, for example `B-approved`.
- **Files:** attached files are copied into the adjacent `documents` directory under unique names, preserving previous content if the source changes. Version history lists all retained file paths. Open latest file launches the default application. Do not overwrite retained files in external editors; edit a working copy and import a new revision.
- **Timeline:** date-ordered tasks and milestones with phases. Double-click to edit either type. This is a simple schedule list, without dependency calculations or a Gantt chart.
- **Search:** searches projects, contacts, tasks, documents, communications, milestones and revision requirements.
- **Reports:** Projects → Print report opens native print preview for project details, outstanding tasks, latest document requirements, milestones and communications. Print to paper or Microsoft Print to PDF. Tasks → Export outstanding CSV includes all uncompleted work for active projects. Projects → Export CSV exports project fields. CSV values are escaped against spreadsheet formulas.

## Backup and restore

**Back up both SQLite and the documents folder.** Backup & Restore creates a consistent database snapshot. Copy the adjacent `documents` folder separately. Restore validates integrity, schema and relationships before replacing records and first creates a `.before-restore.sqlite3` safety copy beside the live database. Close other instances before restoring. On another computer, document files must be restored to their original paths or reimported as new revisions. Restore only trusted backups.

## Limitations

Single-user, local app; no sync, encryption, access control, installer, automatic updater or notification reminders. Users with access to the Windows account can read local data. Do not enter passwords or sensitive financial data into free-text fields. Metadata revisions are append-only; changing their status requires another history entry. File backups are separate from database backups. Windows tests, packaging and a headless packaged-executable check passed. Manual use on a physical Windows desktop and printer hardware testing have not been performed.

## Automated verification

Run `python -m pytest -v` from the project root after installing `requirements-dev.txt`. Tests cover project creation/edit/archive, task states and validation, revision history and retained file content, search, database backup/restore, invalid restore protection, draft/report/export generation, and headless Qt navigation/edit. See VALIDATION.md for actual results.
