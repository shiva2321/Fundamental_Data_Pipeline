#!/bin/bash
# This project no longer ships a Streamlit web dashboard. The desktop application
# entrypoint is `python app.py`, which will prefer a PyQt5 GUI when available
# and fall back to a bundled Tkinter GUI otherwise.

echo "This project no longer uses run.sh. Use: python app.py"
