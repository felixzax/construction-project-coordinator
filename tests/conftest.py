"""Dispose test-owned Qt windows so later palette tests do not restyle old windows."""
import pytest

@pytest.fixture(autouse=True)
def dispose_qt_windows():
 yield
 # Do not create a GUI for persistence-only tests. Tests close their windows normally;
 # deferred deletion releases Qt parent/signal ownership across test boundaries.
 from PySide6.QtWidgets import QApplication
 from PySide6.QtCore import QCoreApplication,QEvent
 app=QApplication.instance()
 if app:
  for widget in app.topLevelWidgets():widget.deleteLater()
  QCoreApplication.sendPostedEvents(None,QEvent.DeferredDelete)
