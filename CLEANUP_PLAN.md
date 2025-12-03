# Files to Remove from Codebase

This document lists files that are no longer needed after transitioning from Streamlit dashboard to PyQt5 desktop application.

## Streamlit Dashboard Files
- `dashboard.py` - Old Streamlit web dashboard (replaced by desktop_app.py)
- `DASHBOARD_FIXES.md` - Documentation for Streamlit fixes (no longer relevant)
- `DASHBOARD_IMPLEMENTATION.md` - Documentation for Streamlit implementation (no longer relevant)

## CLI Entry Points (Optional - Keep if needed for reference)
- `main.py` - Old interactive CLI (can be archived if desktop app fully replaces it)

## Documentation Files (Cleanup/Consolidate)
- `BEFORE_AFTER.md` - Historical comparison document
- `SELECTION_FIX_NOTES.md` - Historical fix notes
- `SELECTION_GUIDE.md` - Historical selection guide
- `SYNTAX_ERROR_FIX.md` - Historical error documentation
- `QUICK_REFERENCE.md` - Old quick reference
- `INDEX.md` - Old index file
- `QUICKSTART.md` - Old quick start guide (replaced by DESKTOP_APP_GUIDE.md)

## Duplicate/Archived Code
- `main_unified.py` - CLI version (functionality now in desktop app)
- `sec_profile_aggregator.py` - Old aggregator (replaced by unified_profile_aggregator.py)
- `sec_profile_retriever.py` - Old retriever (functionality integrated into unified_profile_aggregator.py)
- `sec_filing_profile_builder.py` - Old builder (replaced by unified aggregator)

## Test Files (Optional - Keep if using for development)
- `test_system.py` - System tests (can be kept for CI/CD)

## Summary

### Definitely Remove (Streamlit-specific):
1. dashboard.py
2. DASHBOARD_FIXES.md
3. DASHBOARD_IMPLEMENTATION.md

### Recommended Remove (Outdated Documentation):
4. BEFORE_AFTER.md
5. SELECTION_FIX_NOTES.md
6. SELECTION_GUIDE.md
7. SYNTAX_ERROR_FIX.md
8. QUICK_REFERENCE.md
9. INDEX.md
10. QUICKSTART.md

### Optional Remove (Old Code - Can Archive):
11. main.py
12. main_unified.py
13. sec_profile_aggregator.py
14. sec_profile_retriever.py
15. sec_filing_profile_builder.py

### Keep:
- desktop_app.py (new desktop application)
- app.py (entry point)
- run.bat, run.sh (launchers)
- DESKTOP_APP_GUIDE.md (new user guide)
- All core library files (mongo_client.py, config.py, etc.)
- All SEC API client files
- Company ticker fetcher
- Unified profile aggregator
- requirements.txt (updated for PyQt5)
- README.md (updated)
- PROJECT_SUMMARY.md (keep as overview)
- ARCHITECTURE.md (keep as reference)
- config/ directory
- .git, .gitignore, .idea, .venv, __pycache__ (Python dirs)

