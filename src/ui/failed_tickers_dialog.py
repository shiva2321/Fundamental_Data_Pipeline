"""
UI Dialog for viewing and managing failed tickers from processing runs.
Allows users to view failure details, retry, or delete failed tickers.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QPushButton, QLabel, QTextEdit,
                               QMessageBox, QHeaderView, QTabWidget, QWidget)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
import logging

logger = logging.getLogger(__name__)


class FailedTickersDialog(QDialog):
    """Dialog for viewing and managing failed tickers."""

    # Signals
    retry_tickers = Signal(list)  # List of tickers to retry
    delete_tickers = Signal(list)  # List of tickers to delete

    def __init__(self, failure_tracker, parent=None):
        super().__init__(parent)
        self.failure_tracker = failure_tracker
        self.setWindowTitle("Failed Tickers Management")
        self.resize(1000, 600)
        self.setup_ui()
        self.populate_data()

    def setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)

        # Summary label
        self.lbl_summary = QLabel()
        summary_font = QFont()
        summary_font.setBold(True)
        summary_font.setPointSize(12)
        self.lbl_summary.setFont(summary_font)
        layout.addWidget(self.lbl_summary)

        # Tabs for different views
        self.tabs = QTabWidget()

        # Tab 1: All failures
        self.tab_all = QWidget()
        self.setup_failures_table()
        tab_layout = QVBoxLayout(self.tab_all)
        tab_layout.addWidget(self.table_failures)
        self.tabs.addTab(self.tab_all, "All Failures")

        # Tab 2: Failures by reason
        self.tab_by_reason = QWidget()
        self.setup_reason_table()
        reason_layout = QVBoxLayout(self.tab_by_reason)
        reason_layout.addWidget(self.table_by_reason)
        self.tabs.addTab(self.tab_by_reason, "By Reason")

        # Tab 3: Details
        self.tab_details = QWidget()
        details_layout = QVBoxLayout(self.tab_details)
        self.txt_details = QTextEdit()
        self.txt_details.setReadOnly(True)
        self.txt_details.setFont(QFont("Courier", 9))
        details_layout.addWidget(QLabel("Detailed Failure Report:"))
        details_layout.addWidget(self.txt_details)
        self.tabs.addTab(self.tab_details, "Details")

        layout.addWidget(self.tabs)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.btn_retry_selected = QPushButton("Retry Selected")
        self.btn_retry_selected.setObjectName("SuccessButton")
        self.btn_retry_selected.clicked.connect(self.retry_selected)
        btn_layout.addWidget(self.btn_retry_selected)

        self.btn_retry_all = QPushButton("Retry All Failed")
        self.btn_retry_all.setObjectName("SuccessButton")
        self.btn_retry_all.clicked.connect(self.retry_all)
        btn_layout.addWidget(self.btn_retry_all)

        btn_layout.addSpacing(20)

        self.btn_delete_selected = QPushButton("Delete Selected")
        self.btn_delete_selected.setObjectName("DangerButton")
        self.btn_delete_selected.clicked.connect(self.delete_selected)
        btn_layout.addWidget(self.btn_delete_selected)

        self.btn_delete_all = QPushButton("Delete All")
        self.btn_delete_all.setObjectName("DangerButton")
        self.btn_delete_all.clicked.connect(self.delete_all)
        btn_layout.addWidget(self.btn_delete_all)

        btn_layout.addStretch()

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def setup_failures_table(self):
        """Setup the failures table."""
        self.table_failures = QTableWidget()
        self.table_failures.setColumnCount(6)
        self.table_failures.setHorizontalHeaderLabels([
            "Ticker", "Reason", "Error Message", "Retries", "Timestamp", "Details"
        ])
        self.table_failures.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_failures.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_failures.setSelectionMode(QTableWidget.MultiSelection)
        self.table_failures.doubleClicked.connect(self.show_failure_details)

    def setup_reason_table(self):
        """Setup the failures by reason table."""
        self.table_by_reason = QTableWidget()
        self.table_by_reason.setColumnCount(3)
        self.table_by_reason.setHorizontalHeaderLabels([
            "Reason", "Count", "Tickers"
        ])
        self.table_by_reason.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

    def populate_data(self):
        """Populate tables with failure data."""
        failures = self.failure_tracker.failures
        summary = self.failure_tracker.get_failure_summary()

        # Update summary
        total = len(failures)
        self.lbl_summary.setText(
            f"Total Failed Tickers: {total} | "
            f"Unique Reasons: {len(summary['failures_by_reason'])} | "
            f"Never Retried: {len(summary['failures_by_retry_count'].get(0, []))}"
        )

        # Populate all failures table
        self.table_failures.setRowCount(0)
        for ticker, info in failures.items():
            row = self.table_failures.rowCount()
            self.table_failures.insertRow(row)

            self.table_failures.setItem(row, 0, QTableWidgetItem(ticker))
            self.table_failures.setItem(row, 1, QTableWidgetItem(info['reason']))

            error_msg = info['error_message'][:50] + "..." if len(info['error_message']) > 50 else info['error_message']
            self.table_failures.setItem(row, 2, QTableWidgetItem(error_msg))

            self.table_failures.setItem(row, 3, QTableWidgetItem(str(info['retry_attempts'])))

            timestamp = info['timestamp'][:10]  # Just the date
            self.table_failures.setItem(row, 4, QTableWidgetItem(timestamp))

            btn_details = QPushButton("View")
            btn_details.setMaximumWidth(60)
            btn_details.clicked.connect(lambda checked, t=ticker: self.show_failure_details_for_ticker(t))
            self.table_failures.setCellWidget(row, 5, btn_details)

        # Populate by reason table
        self.table_by_reason.setRowCount(0)
        for reason_code, tickers in summary['failures_by_reason'].items():
            row = self.table_by_reason.rowCount()
            self.table_by_reason.insertRow(row)

            self.table_by_reason.setItem(row, 0, QTableWidgetItem(reason_code))
            self.table_by_reason.setItem(row, 1, QTableWidgetItem(str(len(tickers))))

            ticker_str = ", ".join(sorted(tickers[:10]))
            if len(tickers) > 10:
                ticker_str += f"... (+{len(tickers) - 10} more)"
            self.table_by_reason.setItem(row, 2, QTableWidgetItem(ticker_str))

        # Populate details tab
        self.txt_details.setPlainText(self.failure_tracker.get_formatted_failure_report())

    def show_failure_details_for_ticker(self, ticker: str):
        """Show details for a specific ticker."""
        info = self.failure_tracker.get_failure_info(ticker)
        if info:
            import json
            details = json.dumps(info, indent=2)
            QMessageBox.information(self, f"Failure Details - {ticker}", details)

    def show_failure_details(self, index):
        """Handle double-click on failure table."""
        row = index.row()
        ticker = self.table_failures.item(row, 0).text()
        self.show_failure_details_for_ticker(ticker)

    def retry_selected(self):
        """Retry selected failed tickers."""
        selected_rows = self.table_failures.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one ticker to retry.")
            return

        tickers = [self.table_failures.item(row.row(), 0).text() for row in selected_rows]

        reply = QMessageBox.question(
            self, "Confirm Retry",
            f"Retry {len(tickers)} ticker(s)?\n\n{', '.join(tickers[:10])}{'...' if len(tickers) > 10 else ''}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.retry_tickers.emit(tickers)
            self.accept()

    def retry_all(self):
        """Retry all failed tickers."""
        tickers = self.failure_tracker.get_failed_tickers()
        if not tickers:
            QMessageBox.information(self, "No Failures", "No failed tickers to retry.")
            return

        reply = QMessageBox.question(
            self, "Confirm Retry All",
            f"Retry all {len(tickers)} failed ticker(s)?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.retry_tickers.emit(tickers)
            self.accept()

    def delete_selected(self):
        """Delete selected failed tickers."""
        selected_rows = self.table_failures.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one ticker to delete.")
            return

        tickers = [self.table_failures.item(row.row(), 0).text() for row in selected_rows]

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {len(tickers)} failed ticker record(s)?\n\n{', '.join(tickers[:10])}{'...' if len(tickers) > 10 else ''}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.delete_tickers.emit(tickers)
            self.populate_data()

    def delete_all(self):
        """Delete all failed ticker records."""
        tickers = self.failure_tracker.get_failed_tickers()
        if not tickers:
            QMessageBox.information(self, "No Failures", "No failed tickers to delete.")
            return

        reply = QMessageBox.question(
            self, "Confirm Delete All",
            f"Delete all {len(tickers)} failed ticker record(s)?\nThis will not delete profiles, only the failure records.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.failure_tracker.clear_failures()
            self.populate_data()
            QMessageBox.information(self, "Cleared", "All failure records cleared.")

