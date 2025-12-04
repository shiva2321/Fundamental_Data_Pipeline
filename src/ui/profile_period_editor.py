"""
Profile Period Editor Dialog
Allows users to edit the date range for existing profiles and regenerate with specific periods.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QCheckBox, QMessageBox,
                               QDateEdit, QGroupBox, QTextEdit)
from PySide6.QtCore import Qt, QDate, Signal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ProfilePeriodEditorDialog(QDialog):
    """Dialog for editing profile date range."""

    period_updated = Signal(str, str, str, bool)  # ticker, from_date, to_date, incremental

    def __init__(self, ticker, cik, current_from, current_to, parent=None):
        super().__init__(parent)
        self.ticker = ticker
        self.cik = cik
        self.current_from = current_from
        self.current_to = current_to

        self.setWindowTitle(f"Edit Profile Period - {ticker}")
        self.setMinimumWidth(500)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"Edit Profile Period for {self.ticker}")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #4da6ff; padding: 10px;")
        layout.addWidget(header)

        # Current period info
        info_group = QGroupBox("Current Profile Information")
        info_layout = QVBoxLayout(info_group)

        current_info = QTextEdit()
        current_info.setReadOnly(True)
        current_info.setMaximumHeight(100)
        current_info.setText(f"""Current Period:
  From: {self.current_from}
  To: {self.current_to}
  
CIK: {self.cik}""")
        info_layout.addWidget(current_info)
        layout.addWidget(info_group)

        # New period selection
        period_group = QGroupBox("New Period Selection")
        period_layout = QVBoxLayout(period_group)

        # From date
        from_layout = QHBoxLayout()
        from_layout.addWidget(QLabel("From Date:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")

        # Parse current from date
        try:
            from_date = datetime.strptime(self.current_from, "%Y-%m-%d")
            self.date_from.setDate(QDate(from_date.year, from_date.month, from_date.day))
        except:
            self.date_from.setDate(QDate.currentDate().addYears(-10))

        from_layout.addWidget(self.date_from)
        period_layout.addLayout(from_layout)

        # To date
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("To Date:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")

        # Parse current to date
        try:
            to_date = datetime.strptime(self.current_to, "%Y-%m-%d")
            self.date_to.setDate(QDate(to_date.year, to_date.month, to_date.day))
        except:
            self.date_to.setDate(QDate.currentDate())

        to_layout.addWidget(self.date_to)
        period_layout.addLayout(to_layout)

        # Quick date range buttons
        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("Quick Select:"))

        btn_5y = QPushButton("Last 5 Years")
        btn_5y.clicked.connect(lambda: self.set_quick_range(5))
        quick_layout.addWidget(btn_5y)

        btn_10y = QPushButton("Last 10 Years")
        btn_10y.clicked.connect(lambda: self.set_quick_range(10))
        quick_layout.addWidget(btn_10y)

        btn_all = QPushButton("All Available")
        btn_all.clicked.connect(lambda: self.set_quick_range(30))
        quick_layout.addWidget(btn_all)

        quick_layout.addStretch()
        period_layout.addLayout(quick_layout)

        layout.addWidget(period_group)

        # Update options
        options_group = QGroupBox("Update Options")
        options_layout = QVBoxLayout(options_group)

        self.chk_incremental = QCheckBox("Incremental Update (Keep existing data, add new filings)")
        self.chk_incremental.setChecked(False)
        options_layout.addWidget(self.chk_incremental)

        self.chk_full = QCheckBox("Full Regeneration (Replace entire profile)")
        self.chk_full.setChecked(True)
        options_layout.addWidget(self.chk_full)

        # Make them mutually exclusive
        self.chk_incremental.toggled.connect(lambda checked: self.chk_full.setChecked(not checked))
        self.chk_full.toggled.connect(lambda checked: self.chk_incremental.setChecked(not checked))

        options_layout.addWidget(QLabel("⚠ Full regeneration will replace all existing data for this profile."))

        layout.addWidget(options_group)

        # Warning
        warning = QLabel("Note: This will re-fetch and re-process all filings for the selected period.")
        warning.setStyleSheet("color: #ffc107; padding: 10px;")
        warning.setWordWrap(True)
        layout.addWidget(warning)

        # Buttons
        btn_layout = QHBoxLayout()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        btn_layout.addStretch()

        btn_update = QPushButton("Update Profile")
        btn_update.setObjectName("SuccessButton")
        btn_update.clicked.connect(self.update_profile)
        btn_layout.addWidget(btn_update)

        layout.addLayout(btn_layout)

    def set_quick_range(self, years):
        """Set date range to last N years."""
        self.date_to.setDate(QDate.currentDate())
        self.date_from.setDate(QDate.currentDate().addYears(-years))

    def update_profile(self):
        """Emit signal to update the profile."""
        from_date = self.date_from.date().toString("yyyy-MM-dd")
        to_date = self.date_to.date().toString("yyyy-MM-dd")
        incremental = self.chk_incremental.isChecked()

        # Validate dates
        if self.date_from.date() > self.date_to.date():
            QMessageBox.warning(self, "Invalid Date Range",
                              "From date must be before To date.")
            return

        # Confirm
        mode = "incrementally update" if incremental else "fully regenerate"
        reply = QMessageBox.question(
            self,
            "Confirm Update",
            f"Are you sure you want to {mode} the profile for {self.ticker}?\n\n"
            f"Period: {from_date} to {to_date}\n\n"
            f"This will re-process all filings in this date range.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.period_updated.emit(self.ticker, from_date, to_date, incremental)
            self.accept()

