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
