#!/usr/bin/env python
"""Quick test script to verify the application can start without errors."""

import sys
import traceback

def test_import():
    """Test if main modules can be imported."""
    print("Testing imports...")
    try:
        from src.ui.desktop_app_pyside import MainWindow
        print("✓ MainWindow imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        traceback.print_exc()
        return False

def test_initialization():
    """Test if MainWindow can be initialized (without showing)."""
    print("\nTesting MainWindow initialization...")
    try:
        from PySide6.QtWidgets import QApplication
        from src.ui.desktop_app_pyside import MainWindow

        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)

        window = MainWindow()
        print("✓ MainWindow initialized successfully")
        print(f"  - Window title: {window.windowTitle()}")
        print(f"  - Has chk_incremental: {hasattr(window, 'chk_incremental')}")
        print(f"  - Has chk_ai_enabled: {hasattr(window, 'chk_ai_enabled')}")
        print(f"  - Has model_checks: {hasattr(window, 'model_checks')}")
        print(f"  - Has feature_checks: {hasattr(window, 'feature_checks')}")

        # Don't show the window, just verify it was created
        return True
    except Exception as e:
        print(f"✗ Initialization failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Desktop App Startup Test")
    print("=" * 60)

    success = True
    success = test_import() and success
    success = test_initialization() and success

    print("\n" + "=" * 60)
    if success:
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        sys.exit(1)

