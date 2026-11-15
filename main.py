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
