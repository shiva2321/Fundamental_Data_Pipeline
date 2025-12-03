"""
Check which Qt provider the desktop_app module selects.
Run with: .venv\Scripts\python.exe tools\check_desktop_app.py
"""
import importlib, traceback, sys
try:
    m = importlib.import_module('desktop_app')
    print('Imported desktop_app')
    print('QT_API =', getattr(m, 'QT_API', 'NOT SET'))
except Exception:
    traceback.print_exc()
    sys.exit(1)

