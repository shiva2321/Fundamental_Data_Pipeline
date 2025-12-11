"""
Dialog for identifying and retrying incomplete/inconsistent profiles.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget,
                               QTableWidgetItem, QPushButton, QLabel, QTextEdit,
                               QMessageBox, QHeaderView, QTabWidget, QWidget, QCheckBox)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
import logging

logger = logging.getLogger(__name__)


class ProblematicProfilesDialog(QDialog):
    """Dialog for viewing and managing problematic profiles."""

    # Signals
    retry_profiles = Signal(list)  # List of CIKs to retry

    def __init__(self, mongo, config, parent=None):
        super().__init__(parent)
        self.mongo = mongo
        self.config = config
        self.problematic_profiles = []
        self.col_name = config.get('collections', {}).get('profiles', 'Fundamental_Data_Pipeline')

        self.setWindowTitle("Problematic Profiles - Find & Retry")
        self.resize(1200, 700)
        self.setup_ui()
        self.scan_profiles()

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

        # Tab 1: All Problematic Profiles
        self.tab_all = QWidget()
        self.setup_profiles_table()
        tab_layout = QVBoxLayout(self.tab_all)
        tab_layout.addWidget(self.table_profiles)
        self.tabs.addTab(self.tab_all, "All Issues")

        # Tab 2: By Category
        self.tab_by_category = QWidget()
        self.setup_category_table()
        category_layout = QVBoxLayout(self.tab_by_category)
        category_layout.addWidget(self.table_by_category)
        self.tabs.addTab(self.tab_by_category, "By Category")

        # Tab 3: Quality Analysis
        self.tab_quality = QWidget()
        quality_layout = QVBoxLayout(self.tab_quality)
        self.txt_quality = QTextEdit()
        self.txt_quality.setReadOnly(True)
        self.txt_quality.setFont(QFont("Courier", 9))
        quality_layout.addWidget(QLabel("Profile Quality Analysis:"))
        quality_layout.addWidget(self.txt_quality)
        self.tabs.addTab(self.tab_quality, "Quality Analysis")

        layout.addWidget(self.tabs)

        # Filters
        filter_layout = QHBoxLayout()
        self.chk_incomplete = QCheckBox("Incomplete")
        self.chk_incomplete.setChecked(True)
        filter_layout.addWidget(self.chk_incomplete)

        self.chk_out_of_order = QCheckBox("Out-of-Order")
        self.chk_out_of_order.setChecked(True)
        filter_layout.addWidget(self.chk_out_of_order)

        self.chk_inconsistent = QCheckBox("Inconsistent")
        self.chk_inconsistent.setChecked(True)
        filter_layout.addWidget(self.chk_inconsistent)

        self.chk_improper = QCheckBox("Improper")
        self.chk_improper.setChecked(True)
        filter_layout.addWidget(self.chk_improper)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Action buttons
        btn_layout = QHBoxLayout()

        self.btn_retry_selected = QPushButton("Retry Selected")
        self.btn_retry_selected.setObjectName("SuccessButton")
        self.btn_retry_selected.clicked.connect(self.retry_selected)
        btn_layout.addWidget(self.btn_retry_selected)

        self.btn_retry_all = QPushButton("Retry All Problematic")
        self.btn_retry_all.setObjectName("SuccessButton")
        self.btn_retry_all.clicked.connect(self.retry_all)
        btn_layout.addWidget(self.btn_retry_all)

        btn_layout.addStretch()

        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def setup_profiles_table(self):
        """Setup the problematic profiles table."""
        self.table_profiles = QTableWidget()
        self.table_profiles.setColumnCount(6)
        self.table_profiles.setHorizontalHeaderLabels([
            "Ticker", "Issues", "Category", "Quality", "Generated", "Details"
        ])
        self.table_profiles.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table_profiles.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_profiles.setSelectionMode(QTableWidget.MultiSelection)
        self.table_profiles.doubleClicked.connect(self.show_profile_details)

    def setup_category_table(self):
        """Setup the by-category table."""
        self.table_by_category = QTableWidget()
        self.table_by_category.setColumnCount(3)
        self.table_by_category.setHorizontalHeaderLabels([
            "Category", "Count", "Examples"
        ])
        self.table_by_category.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)

    def scan_profiles(self):
        """Scan all profiles for issues."""
        try:
            from src.utils.profile_validator import ProfileValidator, ProfileQualityAnalyzer

            self.problematic_profiles = []
            all_profiles = list(self.mongo.find(self.col_name, {}, limit=1000))

            issues_by_category = {
                'INCOMPLETE': [],
                'OUT_OF_ORDER': [],
                'INCONSISTENT': [],
                'IMPROPER': []
            }

            quality_data = []

            for profile in all_profiles:
                is_valid, status, issues = ProfileValidator.validate_profile(profile)

                if not is_valid:
                    quality = ProfileQualityAnalyzer.analyze_profile_quality(profile)

                    self.problematic_profiles.append({
                        'profile': profile,
                        'ticker': profile.get('company_info', {}).get('ticker', 'N/A'),
                        'cik': profile.get('cik', 'N/A'),
                        'is_valid': is_valid,
                        'status': status,
                        'issues': issues,
                        'categories': ProfileValidator.categorize_issues(issues),
                        'quality': quality
                    })

                    # Add to category tracking
                    for category, category_issues in ProfileValidator.categorize_issues(issues).items():
                        if category_issues:
                            issues_by_category[category].append({
                                'ticker': profile.get('company_info', {}).get('ticker', 'N/A'),
                                'count': len(category_issues)
                            })

                    quality_data.append(quality)

            # Update summary
            total = len(all_profiles)
            problematic = len(self.problematic_profiles)
            pct = (problematic / total * 100) if total > 0 else 0

            self.lbl_summary.setText(
                f"Total Profiles: {total} | Problematic: {problematic} ({pct:.1f}%) | "
                f"Incomplete: {len(issues_by_category['INCOMPLETE'])} | "
                f"Out-of-Order: {len(issues_by_category['OUT_OF_ORDER'])} | "
                f"Inconsistent: {len(issues_by_category['INCONSISTENT'])} | "
                f"Improper: {len(issues_by_category['IMPROPER'])}"
            )

            # Populate tables
            self.populate_profiles_table(issues_by_category)
            self.populate_category_table(issues_by_category)
            self.populate_quality_analysis(quality_data)

        except Exception as e:
            logger.exception("Error scanning profiles")
            QMessageBox.critical(self, "Error", f"Failed to scan profiles: {e}")

    def populate_profiles_table(self, issues_by_category):
        """Populate the profiles table."""
        self.table_profiles.setRowCount(0)

        for prob in self.problematic_profiles:
            row = self.table_profiles.rowCount()
            self.table_profiles.insertRow(row)

            # Ticker
            self.table_profiles.setItem(row, 0, QTableWidgetItem(prob['ticker']))

            # Issue count
            issue_count = len(prob['issues'])
            self.table_profiles.setItem(row, 1, QTableWidgetItem(str(issue_count)))

            # Primary category
            categories = prob['categories']
            primary_cat = next((cat for cat, issues in categories.items() if issues), 'UNKNOWN')
            self.table_profiles.setItem(row, 2, QTableWidgetItem(primary_cat))

            # Quality score
            quality = prob['quality']
            quality_label = f"{quality['overall_score']:.0f}% ({quality['status']})"
            item = self.table_profiles.setItem(row, 3, QTableWidgetItem(quality_label))

            # Color code by quality
            score = quality['overall_score']
            if score < 40:
                color = QColor("#dc3545")  # Red
            elif score < 60:
                color = QColor("#ffc107")  # Orange
            elif score < 80:
                color = QColor("#ffc107")  # Yellow
            else:
                color = QColor("#198754")  # Green

            self.table_profiles.item(row, 3).setForeground(color)

            # Generated
            generated = prob['profile'].get('generated_at', 'N/A')
            if isinstance(generated, str):
                generated = generated[:10]  # Just date
            self.table_profiles.setItem(row, 4, QTableWidgetItem(str(generated)))

            # Details button
            btn_details = QPushButton("View")
            btn_details.setMaximumWidth(60)
            btn_details.clicked.connect(lambda checked, idx=row: self.show_details_for_row(idx))
            self.table_profiles.setCellWidget(row, 5, btn_details)

    def populate_category_table(self, issues_by_category):
        """Populate the category table."""
        self.table_by_category.setRowCount(0)

        for category, issues in issues_by_category.items():
            if issues:
                row = self.table_by_category.rowCount()
                self.table_by_category.insertRow(row)

                self.table_by_category.setItem(row, 0, QTableWidgetItem(category))
                self.table_by_category.setItem(row, 1, QTableWidgetItem(str(len(issues))))

                # Examples
                examples = ", ".join([i['ticker'] for i in issues[:5]])
                if len(issues) > 5:
                    examples += f" (+{len(issues) - 5} more)"
                self.table_by_category.setItem(row, 2, QTableWidgetItem(examples))

    def populate_quality_analysis(self, quality_data):
        """Populate quality analysis."""
        if not quality_data:
            self.txt_quality.setPlainText("No problematic profiles to analyze.")
            return

        avg_score = sum(q['overall_score'] for q in quality_data) / len(quality_data)
        avg_completeness = sum(q['completeness_pct'] for q in quality_data) / len(quality_data)
        avg_integrity = sum(q['data_integrity_score'] for q in quality_data) / len(quality_data)

        analysis = f"""
Profile Quality Analysis
════════════════════════════════════════════════════════════════

Total Problematic Profiles: {len(quality_data)}

Average Metrics:
  • Overall Score:         {avg_score:.1f}%
  • Completeness:          {avg_completeness:.1f}%
  • Data Integrity:        {avg_integrity:.1f}%

Quality Distribution:
"""

        excellent = sum(1 for q in quality_data if q['overall_score'] >= 95)
        good = sum(1 for q in quality_data if 80 <= q['overall_score'] < 95)
        fair = sum(1 for q in quality_data if 60 <= q['overall_score'] < 80)
        poor = sum(1 for q in quality_data if 40 <= q['overall_score'] < 60)
        critical = sum(1 for q in quality_data if q['overall_score'] < 40)

        analysis += f"""
  • Excellent (95%+):      {excellent}
  • Good (80-95%):         {good}
  • Fair (60-80%):         {fair}
  • Poor (40-60%):         {poor}
  • Critical (<40%):       {critical}

Recommendations:
  • Retry ALL problematic profiles to ensure data completeness
  • Focus on CRITICAL and POOR quality profiles first
  • Monitor for patterns in common issues
  • Consider adjusting profile generation parameters
"""

        self.txt_quality.setPlainText(analysis)

    def show_details_for_row(self, row):
        """Show details for a specific row."""
        ticker = self.table_profiles.item(row, 0).text()
        prob = next((p for p in self.problematic_profiles if p['ticker'] == ticker), None)

        if prob:
            self.show_profile_details_dialog(prob)

    def show_profile_details_dialog(self, prob):
        """Show detailed information about a problematic profile."""
        import json

        details = f"""
PROFILE ISSUES REPORT
════════════════════════════════════════════════════════════════

Ticker: {prob['ticker']}
CIK: {prob['cik']}

ISSUES FOUND ({len(prob['issues'])}):
"""

        categories = prob['categories']
        for category, issues in categories.items():
            if issues:
                details += f"\n{category} ({len(issues)}):\n"
                for issue in issues:
                    details += f"  • {issue}\n"

        details += f"""
QUALITY ANALYSIS:
  • Overall Score:     {prob['quality']['overall_score']:.1f}%
  • Completeness:      {prob['quality']['completeness_pct']:.1f}%
  • Data Integrity:    {prob['quality']['data_integrity_score']:.1f}%
  • Status:            {prob['quality']['status']}

RECOMMENDATION: RETRY PROFILE
This profile should be regenerated to fix the identified issues.
"""

        msg = QMessageBox(self)
        msg.setWindowTitle(f"Profile Issues - {prob['ticker']}")
        msg.setText(details)
        msg.setFont(QFont("Courier", 9))
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    def show_profile_details(self, index):
        """Handle double-click on profile table."""
        row = index.row()
        ticker = self.table_profiles.item(row, 0).text()
        prob = next((p for p in self.problematic_profiles if p['ticker'] == ticker), None)

        if prob:
            self.show_profile_details_dialog(prob)

    def retry_selected(self):
        """Retry selected problematic profiles."""
        selected_rows = self.table_profiles.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one profile to retry.")
            return

        tickers = []
        for row in selected_rows:
            ticker = self.table_profiles.item(row.row(), 0).text()
            tickers.append(ticker)

        reply = QMessageBox.question(
            self, "Confirm Retry",
            f"Retry {len(tickers)} profile(s)?\n\n{', '.join(tickers[:10])}{'...' if len(tickers) > 10 else ''}",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.retry_profiles.emit(tickers)
            self.accept()

    def retry_all(self):
        """Retry all problematic profiles."""
        if not self.problematic_profiles:
            QMessageBox.information(self, "No Issues", "No problematic profiles found.")
            return

        tickers = [p['ticker'] for p in self.problematic_profiles]

        reply = QMessageBox.question(
            self, "Confirm Retry All",
            f"Retry all {len(tickers)} problematic profile(s)?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.retry_profiles.emit(tickers)
            self.accept()
