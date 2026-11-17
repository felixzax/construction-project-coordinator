"""Pre-Qt checks for incomplete frozen Windows distributions."""
from pathlib import Path
import os
import sys
import tempfile

WINDOWS_RUNTIME_FILES=(
 'shiboken6/Shiboken.pyd',
 'shiboken6/shiboken6.abi3.dll',
 'PySide6/QtCore.pyd',
 'PySide6/Qt6Core.dll',
 'PySide6/plugins/platforms/qwindows.dll',
)

def missing_runtime_files(root):
 root=Path(root)
 return [name for name in WINDOWS_RUNTIME_FILES if not (root/name).is_file()]

def check_frozen_runtime():
 if not getattr(sys,'frozen',False) or sys.platform!='win32':return []
 return missing_runtime_files(sys._MEIPASS)

def report_startup_failure(message,quiet=False):
 """Give a useful error before PySide6 can initialize. Never open project data."""
 folder=Path(os.environ.get('LOCALAPPDATA') or tempfile.gettempdir())/'Construction Project Coordinator'
 try:
  folder.mkdir(parents=True,exist_ok=True)
  (folder/'startup-error.txt').write_text(message,encoding='utf-8')
 except OSError:pass
 if sys.stderr is not None:print(message,file=sys.stderr)
 if sys.platform=='win32' and not quiet:
  import ctypes
  ctypes.windll.user32.MessageBoxW(None,message,'Construction Project Coordinator — startup error',0x10)
