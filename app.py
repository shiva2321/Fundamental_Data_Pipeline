"""
Application Entry Point for Fundamental Data Pipeline
This script launches the desktop application. It will try the PyQt5-based GUI first and
fall back to a Tkinter-based desktop GUI if PyQt5 isn't available or fails to load.
"""
import sys
import os
import importlib

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    """Try to launch the PySide6 GUI; fall back to Tkinter GUI on failure."""
    # Try PySide6-based desktop app (New Modern UI)
    try:
        desktop_app = importlib.import_module('desktop_app_pyside')
        if hasattr(desktop_app, 'main'):
            desktop_app.main()
            return
    except ImportError as e:
        print(f"PySide6 app failed to load (missing dependency?): {e}")
    except Exception as e:
        print(f"Error launching PySide6 app: {e}")
        import traceback
        traceback.print_exc()

    # Fallback to Tkinter-based GUI
    print("Falling back to Tkinter GUI...")
    try:
        tk_app = importlib.import_module('desktop_app_tk')
        if hasattr(tk_app, 'main'):
            tk_app.main()
            return
    except Exception as e:
        print("Failed to start any GUI:", str(e))
        raise


if __name__ == "__main__":
    main()
