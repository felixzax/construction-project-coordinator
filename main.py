import sys


def smoke_test():
    """Exercise the packaged Qt app with disposable data, without opening user data."""
    import tempfile
    from pathlib import Path
    from PySide6.QtWidgets import QApplication
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
                if window.stack.currentIndex() != index:
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
            window.close()
            app.processEvents()
        finally:
            store.db.close()
    return 0


if __name__ == '__main__':
    if '--smoke-test' in sys.argv:
        raise SystemExit(smoke_test())
    from cpc.ui import main
    raise SystemExit(main())
