"""
Diagnostic script to inspect the virtualenv, pip-installed packages, and import tracebacks
Run with: .venv\Scripts\python.exe tools\env_check.py
"""
import sys
import platform
import importlib
import traceback
import subprocess
import os

print('PYTHON:', sys.executable)
print('Python version:', platform.python_version())
print('Platform:', platform.platform())
print('Architecture:', platform.architecture())
print('sys.prefix:', sys.prefix)
print('sys.path[0:5]:')
for p in sys.path[:5]:
    print('  ', p)

print('\n--- pip show PyQt5 / PyQtChart / PySide6 ---')
for pkg in ('PyQt5', 'PyQtChart', 'PySide6'):
    try:
        out = subprocess.check_output([sys.executable, '-m', 'pip', 'show', pkg], stderr=subprocess.STDOUT, text=True)
        print(f'\n{pkg} info:\n', out)
    except subprocess.CalledProcessError:
        print(f'\n{pkg}: NOT INSTALLED (or pip show failed)')

print('\n--- Import tests with tracebacks ---')
for provider in ('PySide6', 'PyQt5'):
    print(f'\n== Trying import: {provider} ==')
    try:
        mod = importlib.import_module(provider)
        print(provider, 'package at', getattr(mod, '__file__', 'package namespace'))
        # try submodules
        try:
            if provider == 'PySide6':
                import PySide6.QtWidgets as qw
                print('  PySide6.QtWidgets import OK')
                import PySide6.QtCore as qc
                print('  PySide6.QtCore import OK')
            else:
                import PyQt5.QtWidgets as qw
                print('  PyQt5.QtWidgets import OK')
                import PyQt5.QtCore as qc
                print('  PyQt5.QtCore import OK')
        except Exception:
            print('  Submodule import failed:')
            traceback.print_exc()
    except Exception:
        print(provider, 'import failed:')
        traceback.print_exc()

print('\n--- site-packages listing for PyQt5 / PySide6 ---')
site_packages = os.path.join(sys.prefix, 'Lib', 'site-packages')
print('site-packages:', site_packages)
for name in ('PyQt5','PyQtChart','PySide6'):
    p = os.path.join(site_packages, name)
    print('\nListing', p)
    if os.path.exists(p):
        for root, dirs, files in os.walk(p):
            print(root)
            for f in files[:50]:
                print('  ', f)
            break
    else:
        print('  Not present')

# Show DLLs under site-packages for Qt (Windows)
print('\n--- Potential Qt DLLs under site-packages ---')
if os.path.exists(site_packages):
    for entry in os.listdir(site_packages):
        if entry.lower().startswith('qt') or entry.lower().startswith('pyqt') or entry.lower().startswith('pyside'):
            print('  ', entry)

print('\nDone')

