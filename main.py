import sys


def smoke_test():
    """Exercise the packaged Qt app with disposable data, without opening user data."""
    import tempfile
    from pathlib import Path
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import Qt
    from cpc.store import Store
    from cpc.ui import Window
    app = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as folder:
        store = Store(Path(folder) / 'smoke.sqlite3')
        try:
            store.seed()
            window = Window(store)
            window.show()
            app.processEvents()
            for index in range(window.nav.count()):
                window.nav.setCurrentRow(index)
                app.processEvents()
                if window.stack.currentIndex() != window.navigation.index(window.nav.item(index).data(Qt.UserRole)):
                    raise RuntimeError('Navigation smoke check failed')
            if window.tables['Tasks'].rowCount() != 2:
                raise RuntimeError('Sample task smoke check failed')
            for page in ('Architecture','Engineering','Electrical','Plumbing','Mechanical / HVAC','Meetings','Bidding'):
                if window.tables[page].rowCount() < 1:
                    raise RuntimeError(f'Empty seeded workspace: {page}')
            window.tables['Bidding'].selectRow(0)
            app.processEvents()
            if window.tables['Bids'].rowCount() != 2:
                raise RuntimeError('Bid comparison smoke check failed')
            bid = store.all('bids')[0]
            if store.bid_totals(bid['id'])['total'] <= 0:
                raise RuntimeError('Bid calculation smoke check failed')
            if 'Totals' not in store.bid_report(bid['id']):
                raise RuntimeError('Bid report smoke check failed')
            if window.tables['Permits'].rowCount() != 1:
                raise RuntimeError('Permit workspace smoke check failed')
            window.tables['Permits'].selectRow(0)
            from PySide6.QtCore import QTimer, Qt
            from PySide6.QtWidgets import QTableWidget, QCheckBox
            failures = []
            def check_permit_dialog():
                dialog = app.activeModalWidget()
                try:
                    table = dialog.findChild(QTableWidget)
                    if table is None or table.rowCount() != 2:
                        raise RuntimeError('Permit checklist smoke check failed')
                    table.item(0, 0).setCheckState(Qt.Checked)
                    dialog.findChild(QCheckBox).setChecked(True)
                except Exception as error:
                    failures.append(error)
                finally:
                    if dialog is not None:
                        dialog.accept()
            QTimer.singleShot(0, check_permit_dialog)
            window.permit_checklist()
            if failures:
                raise failures[0]
            permit = next(r for r in store.all('registers') if r['record_type'] == 'Permit')
            if store.permit_progress(permit['id']) != '2/2 checked':
                raise RuntimeError('Permit checklist persistence smoke check failed')
            # Verify packaged clipboard, refresh, draft storage and backed-up deletion.
            task_table = window.tables['Tasks']
            task_table.setCurrentCell(0, 0)
            copied = task_table.copy_selection()
            if not copied or copied == 'No':
                raise RuntimeError('Clipboard smoke check failed')
            count = len(store.all('tasks'))
            window.refresh_from_disk()
            if len(store.all('tasks')) != count:
                raise RuntimeError('Refresh smoke check lost records')
            store.save_draft('smoke-draft', 'tasks', None, {'title': 'Recoverable draft'})
            if not store.drafts():
                raise RuntimeError('Draft persistence smoke check failed')
            task_id = store.all('tasks')[0]['id']
            safety = store.delete_records([('tasks', task_id)])
            if not safety or not safety.is_file():
                raise RuntimeError('Backed-up deletion smoke check failed')
            store.restore(safety)
            if len(store.all('tasks')) != count:
                raise RuntimeError('Deletion recovery smoke check failed')
            from cpc.exports import write_docx, department_rows
            word_path = Path(folder) / 'department-export.docx'
            export_rows = department_rows(store, ['Electrical'])
            write_docx(word_path, 'Electrical department', export_rows)
            import zipfile
            with zipfile.ZipFile(word_path) as archive:
                if 'word/document.xml' not in archive.namelist():
                    raise RuntimeError('Word export smoke check failed')
            csv_path = Path(folder) / 'department-export.csv'
            store.export(csv_path, export_rows)
            if not csv_path.is_file() or not csv_path.stat().st_size:
                raise RuntimeError('CSV export smoke check failed')
            if window.tables['Receipts'].rowCount() != 1:
                raise RuntimeError('Receipts workspace smoke check failed')
            receipt = store.receipt_rows()[0]
            if receipt['variance_amount'] != '45.50' or receipt['status'] != 'Pending Review':
                raise RuntimeError('Receipt pricing smoke check failed')
            store.save('receipts', {'status': 'Approved'}, receipt['id'])
            if store.receipt_rows()[0]['status'] != 'Approved':
                raise RuntimeError('Receipt approval smoke check failed')
            store.save('receipts', {'actual_amount': '1300.00'}, receipt['id'])
            if store.receipt_rows()[0]['status'] != 'Pending Review':
                raise RuntimeError('Receipt re-review smoke check failed')
            receipt_word = Path(folder) / 'receipt-export.docx'
            write_docx(receipt_word, 'Supplier receipts', store.receipt_rows())
            if not receipt_word.is_file():
                raise RuntimeError('Receipt Word export smoke check failed')
            if window.tables['Corrections'].rowCount() != 1 or window.tables['Violations'].rowCount() != 1:
                raise RuntimeError('Corrections/violations workspace smoke check failed')
            violation = store.issue_rows('Violation')[0]
            if violation['site_address'] != '120 Example Avenue' or not violation['required_fix']:
                raise RuntimeError('Issue address/required-fix smoke check failed')
            store.save('issues', {'status': 'Resolved'}, violation['id'])
            window.refresh()
            if any(row.get('_source_table') == 'issues' and row.get('_source_id') == violation['id'] for row in window.data['Dashboard']):
                raise RuntimeError('Resolved violation remained on outstanding dashboard')
            if not store.issue_rows('Violation')[0]['resolved_date']:
                raise RuntimeError('Issue resolution date smoke check failed')
            issue_word = Path(folder) / 'violations-export.docx'
            write_docx(issue_word, 'Project violations', store.issue_rows('Violation'))
            if not issue_word.is_file():
                raise RuntimeError('Issue Word export smoke check failed')
            if window.tables['Contracts'].rowCount() != 1 or window.tables['Budgets'].rowCount() != 1:
                raise RuntimeError('Contracts/budgets workspace smoke check failed')
            budget = store.save('budgets', dict(project_id=store.all('projects')[0]['id'], title='Smoke budget', currency='USD', base_amount='1000'))
            contract = store.save('contracts', dict(project_id=store.all('projects')[0]['id'], title='Smoke contract', contractor_name='Example company', budget_id=budget, currency='USD', original_amount='1000', status='Active'))
            store.save('receipts', dict(project_id=store.all('projects')[0]['id'], title='Contract actual', supplier_name='Example company', contract_id=contract, currency='USD', actual_amount='200'))
            if str(store.budget_totals(budget)['projected_total']) != '1000.00':
                raise RuntimeError('Budget double-count prevention smoke check failed')
            original = Path(folder) / 'contract-notes.txt'
            original.write_text('Original contract terms', encoding='utf-8')
            attachment = store.import_finance_files('contracts', contract, [original])[0]
            downloaded = Path(folder) / 'downloaded-original.txt'
            store.save_finance_copy(attachment, downloaded)
            if downloaded.read_bytes() != original.read_bytes():
                raise RuntimeError('Original attachment download smoke check failed')
            from cpc.file_editor import EditableFile
            editor = EditableFile(original); editor.text = 'Edited contract terms'
            edited_word = Path(folder) / 'edited-contract.docx'; editor.save(edited_word)
            word_editor = EditableFile(edited_word); word_editor.set_cell(0, 1, 'Final contract terms')
            word_editor.save(Path(folder) / 'final-contract.docx')
            csv_source = Path(folder) / 'budget-table.csv'; csv_source.write_text('Item,Cost\nMaterials,100\n', encoding='utf-8')
            sheet_editor = EditableFile(csv_source); workbook = Path(folder) / 'budget-table.xlsx'; sheet_editor.save(workbook)
            workbook_editor = EditableFile(workbook); workbook_editor.set_cell(1, 1, '125')
            workbook_editor.save(Path(folder) / 'updated-budget.xlsx')
            workbook_editor.save(Path(folder) / 'updated-budget.csv')
            workbook_editor.save(Path(folder) / 'updated-budget.pdf')
            store.import_finance_files('budgets', budget, [workbook])
            store.export_finance_zip('budgets', budget, Path(folder) / 'budget-files.zip')
            # Verify new scope decisions, project visibility and files in the packaged app.
            from cpc.ui import Form
            pid = store.all('projects')[0]['id']
            if window.tables['Project Profile'].rowCount() != 1 or window.tables['Scope & Systems'].rowCount() != 1:
                raise RuntimeError('Project profile/systems smoke check failed')
            profile = store.profile(pid)
            form = Form(window, 'Scope decision', ['kitchen'], profile)
            form.inputs['kitchen'].boxes['No'].click()
            store.save('project_profiles', form.values(), profile['id'])
            if store.profile(pid)['kitchen'] != 'No':
                raise RuntimeError('Explicit No decision was not preserved')
            form.reject()
            sid = store.save('scope_items', dict(project_id=pid, title='Smoke elevator', category='Vertical Access', system_type='Elevator / Lift', applicability='Undecided'))
            store.save('custom_fields', dict(project_id=pid, scope_item_id=sid, title='Rated capacity', field_type='Number', value='2500', unit='lb', is_required=1))
            scope_file = store.import_finance_files('scope_items', sid, [original])[0]
            store.save_finance_copy(scope_file, Path(folder) / 'scope-original.txt')
            from cpc.file_editor import FileEditor
            file_editor = FileEditor(window, store, scope_file)
            file_editor.editor.setPlainText('Revised scope specification')
            if not file_editor.save_version(automatic=True):
                raise RuntimeError('Scope file edited version smoke check failed')
            file_editor.close()
            if len(store.finance_files('scope_items', sid)) != 2:
                raise RuntimeError('Scope attachment version smoke check failed')
            store.export_finance_zip('scope_items', sid, Path(folder) / 'system-files.zip')
            store.add_scope_starters(pid)
            window.project_filter.setCurrentIndex(window.project_filter.findData(pid))
            store.set_hidden_sections(pid, ['Electrical', 'Rebates & Incentives'])
            window.refresh()
            if not window.nav_item('Electrical').isHidden():
                raise RuntimeError('Project navigation visibility smoke check failed')
            store.set_hidden_sections(pid, [])
            window.refresh()
            if window.nav_item('Electrical').isHidden():
                raise RuntimeError('Project section restore smoke check failed')
            write_docx(Path(folder) / 'systems.docx', 'Systems', store.scope_rows('scope_items'))
            if 'Rated capacity' not in store.report(pid):
                raise RuntimeError('Scope report smoke check failed')
            # Exercise compact menus and both direct sidebar-eye directions.
            from cpc.sidebar import HIDDEN, eye_rect
            from PySide6.QtTest import QTest
            window.project_filter.setCurrentIndex(0)
            nav_item = window.nav_item('Electrical')
            window.nav.scrollToItem(nav_item)
            app.processEvents()
            QTest.mouseClick(window.nav.viewport(), Qt.LeftButton, pos=eye_rect(window.nav.visualItemRect(nav_item)).center())
            app.processEvents()
            if not nav_item.isHidden() or 'Electrical' not in window.navigation_hidden():
                raise RuntimeError('Sidebar eye hide smoke check failed')
            window.navigate(HIDDEN)
            hidden_item = next(window.hidden_sections_list.item(i) for i in range(window.hidden_sections_list.count()) if window.hidden_sections_list.item(i).data(Qt.UserRole) == 'Electrical')
            window.hidden_sections_list.scrollToItem(hidden_item)
            app.processEvents()
            QTest.mouseClick(window.hidden_sections_list.viewport(), Qt.LeftButton, pos=eye_rect(window.hidden_sections_list.visualItemRect(hidden_item)).center())
            app.processEvents()
            if nav_item.isHidden():
                raise RuntimeError('Sidebar eye restore smoke check failed')
            task_export = Path(folder) / 'compact-menu-tasks.csv'
            from PySide6.QtWidgets import QFileDialog
            original_save = QFileDialog.getSaveFileName
            try:
                QFileDialog.getSaveFileName = lambda *args: (str(task_export), 'CSV')
                next(action for action in window.command_menus['Tasks']['Export'].actions() if action.text() == 'Listed records — CSV').trigger()
            finally:
                QFileDialog.getSaveFileName = original_save
            if not task_export.is_file():
                raise RuntimeError('Compact export menu smoke check failed')
            # Send real Qt drag/drop events and verify identity-based navigation.
            from PySide6.QtCore import QPointF, QPoint
            from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
            def reorder_smoke(view, section):
                view.verticalScrollBar().setValue(0)
                app.processEvents()
                mime = view.drag_mime(section)
                target = QPoint(12, 2)
                enter = QDragEnterEvent(target, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
                QApplication.sendEvent(view.viewport(), enter)
                move = QDragMoveEvent(target, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
                QApplication.sendEvent(view.viewport(), move)
                if not move.isAccepted() or view._drop_boundary is None:
                    raise RuntimeError('Drag highlight smoke check failed')
                drop = QDropEvent(QPointF(target), Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
                QApplication.sendEvent(view.viewport(), drop)
                if not drop.isAccepted() or view.visible_sections()[0] != section:
                    raise RuntimeError('Section reordering smoke check failed')
            window.navigate('Dashboard')
            window.nav.verticalScrollBar().setValue(0)
            reorder_smoke(window.nav, 'Tasks')
            window.navigate('Tasks')
            if window.stack.currentIndex() != window.navigation.index('Tasks'):
                raise RuntimeError('Reordered section opened wrong page')
            window.hide_sidebar_section('Electrical')
            window.hide_sidebar_section('Architecture')
            window.navigate(HIDDEN)
            reorder_smoke(window.hidden_sections_list, 'Electrical')
            window.restore_sidebar_section('Electrical')
            window.navigate('Electrical')
            if window.stack.currentIndex() != window.navigation.index('Electrical'):
                raise RuntimeError('Restored reordered section opened wrong page')
            window.show_all_sections()
            # Exercise saved appearance and semantic table colors in the packaged app.
            from PySide6.QtGui import QPalette
            before_count = len(store.all('projects'))
            window.choose_theme('light')
            if window.dark_mode_action.text() != 'Switch to Dark mode' or app.palette().color(QPalette.Base).lightness() < 200:
                raise RuntimeError('Light palette smoke check failed')
            window.dark_mode_action.setChecked(True)
            if window.dark_mode_action.text() != 'Switch to Light mode' or app.palette().color(QPalette.Base).lightness() > 70:
                raise RuntimeError('Dark palette smoke check failed')
            from cpc.theme import saved_theme
            if saved_theme(window.appearance_settings) != 'dark' or len(store.all('projects')) != before_count:
                raise RuntimeError('Appearance persistence/data smoke check failed')
            window.close()
            app.processEvents()
        finally:
            store.db.close()
    return 0


def launch():
    # This guard uses only the standard library and runs before importing PySide6.
    from cpc.runtime import check_frozen_runtime, report_startup_failure
    quiet = '--smoke-test' in sys.argv
    missing = check_frozen_runtime()
    if missing:
        report_startup_failure(
            'The application runtime is incomplete.\n\n'
            + '\n'.join(missing)
            + '\n\nDownload the latest standalone Windows executable from the project build. '
              'For older folder builds, extract the complete ZIP including _internal. '
              'Do not move only the executable out of an older folder build. '
              'Your project database and documents are not changed.', quiet=quiet)
        return 2
    try:
        if quiet:
            return smoke_test()
        from cpc.ui import main
        return main()
    except ImportError as error:
        report_startup_failure(
            'The application could not load its bundled runtime.\n\n'
            + str(error)
            + '\n\nDownload a fresh copy of the standalone build and extract the ZIP. '
              'Do not copy files over an older installation. '
              'Your project data remains in its local data folder.', quiet=quiet)
        return 2


if __name__ == '__main__':
    raise SystemExit(launch())
