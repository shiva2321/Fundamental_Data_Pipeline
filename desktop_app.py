"""
Desktop Application for Fundamental Data Pipeline
A PyQt5-based desktop interface for managing and visualizing SEC company profiles.
"""
import sys
import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime

# Prefer PySide6 to reduce Windows binary issues; fall back to PyQt5 if needed
try:
    # Try PySide6 first
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QTabWidget, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
        QProgressBar, QComboBox, QSpinBox, QCheckBox, QTextEdit, QMessageBox,
        QFileDialog, QDialog, QInputDialog, QHeaderView, QStatusBar, QMenuBar,
        QMenu, QAction, QSplitter, QScrollArea, QFrame
    )
    from PySide6.QtCore import Qt, QThread, Signal as pyqtSignal, QSize, QTimer, QDateTime
    from PySide6.QtGui import QIcon, QFont, QColor, QPixmap
    from PySide6.QtCharts import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis
    QT_API = 'PySide6'
except Exception:
    try:
        # Fallback to PyQt5
        from PyQt5.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QTabWidget, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
            QProgressBar, QComboBox, QSpinBox, QCheckBox, QTextEdit, QMessageBox,
            QFileDialog, QDialog, QInputDialog, QHeaderView, QStatusBar, QMenuBar,
            QMenu, QAction, QSplitter, QScrollArea, QFrame
        )
        from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize, QTimer, QDateTime
        from PyQt5.QtGui import QIcon, QFont, QColor, QPixmap
        from PyQt5.QtChart import QChart, QChartView, QLineSeries, QDateTimeAxis, QValueAxis
        QT_API = 'PyQt5'
    except Exception:
        print("Error: PySide6 or PyQt5 is required. Install with: pip install PySide6  OR pip install PyQt5 PyQtChart")
        sys.exit(1)

print(f"Using Qt provider: {QT_API}")

from mongo_client import MongoWrapper
from config import load_config
from company_ticker_fetcher import CompanyTickerFetcher
from unified_profile_aggregator import UnifiedSECProfileAggregator
from sec_edgar_api_client import SECEdgarClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("desktop_app")


class ProfileGeneratorWorker(QThread):
    """Worker thread for generating profiles without blocking UI."""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    error = pyqtSignal(str)

    def __init__(self, aggregator, ticker_fetcher, identifiers, collection):
        super().__init__()
        self.aggregator = aggregator
        self.ticker_fetcher = ticker_fetcher
        self.identifiers = identifiers
        self.collection = collection
        self._is_running = True

    def run(self):
        """Execute profile generation in background."""
        try:
            total = len(self.identifiers)
            for i, identifier in enumerate(self.identifiers):
                if not self._is_running:
                    break

                # Find company
                company = self.ticker_fetcher.get_by_ticker(identifier.upper())
                if not company:
                    company = self.ticker_fetcher.get_by_cik(identifier)

                if not company:
                    self.progress.emit(i + 1, f"Company not found: {identifier}")
                    continue

                cik = company['cik']
                self.progress.emit(i + 1, f"Processing {company['ticker']} ({company['title']})")

                try:
                    profile = self.aggregator.aggregate_company_profile(
                        cik, company, self.collection
                    )
                    if profile:
                        self.aggregator.mongo.replace_one(
                            self.collection,
                            {"cik": cik},
                            profile,
                            upsert=True
                        )
                except Exception as e:
                    logger.error(f"Error generating profile for {identifier}: {e}")
                    self.progress.emit(i + 1, f"Error: {identifier} - {str(e)}")

            self.finished.emit(True, f"Successfully processed {total} companies")
        except Exception as e:
            logger.error(f"Worker error: {e}")
            self.error.emit(str(e))

    def stop(self):
        """Stop the worker thread."""
        self._is_running = False


class DesktopApp(QMainWindow):
    """Main desktop application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fundamental Data Pipeline - Desktop Application")
        self.setGeometry(100, 100, 1400, 900)

        # Initialize services
        self.initialize_services()

        # Setup UI
        self.setup_ui()

        # Worker thread
        self.worker = None

        # Show window
        self.show()
        logger.info("Desktop application initialized")

    def initialize_services(self):
        """Initialize and cache all services."""
        try:
            config = load_config()
            self.config = config.config

            self.mongo = MongoWrapper(
                uri=self.config['mongodb']['uri'],
                database=self.config['mongodb']['db_name']
            )

            self.sec_client = SECEdgarClient()
            self.aggregator = UnifiedSECProfileAggregator(self.mongo, self.sec_client)
            self.ticker_fetcher = CompanyTickerFetcher()
            self.collection_name = self.config['mongodb'].get('collection', 'Fundamental_Data_Pipeline')

            logger.info("Services initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing services: {e}")
            QMessageBox.critical(self, "Initialization Error", f"Failed to initialize services:\n{e}")
            sys.exit(1)

    def setup_ui(self):
        """Setup the main user interface."""
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Create menu bar
        self.create_menu_bar()

        # Create status bar
        self.statusBar().showMessage("Ready")

        # Create tab widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # Add tabs
        self.tabs.addTab(self.create_home_tab(), "🏠 Home")
        self.tabs.addTab(self.create_search_tab(), "🔍 Search")
        self.tabs.addTab(self.create_generate_tab(), "📈 Generate Profiles")
        self.tabs.addTab(self.create_profiles_tab(), "📊 View Profiles")
        self.tabs.addTab(self.create_analytics_tab(), "📉 Analytics")
        self.tabs.addTab(self.create_settings_tab(), "⚙️ Settings")

    def create_menu_bar(self):
        """Create the application menu bar."""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("File")

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Tools menu
        tools_menu = menubar.addMenu("Tools")

        refresh_action = QAction("Refresh Database", self)
        refresh_action.triggered.connect(self.refresh_database)
        tools_menu.addAction(refresh_action)

        # Help menu
        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_home_tab(self) -> QWidget:
        """Create the home/dashboard tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Title
        title = QLabel("Fundamental Data Pipeline")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        layout.addWidget(QLabel("Welcome to the Fundamental Data Pipeline Desktop Application"))
        layout.addSpacing(20)

        # Statistics section
        stats_layout = QHBoxLayout()

        # Total companies stat
        self.total_companies_label = QLabel()
        self.update_statistics()
        stats_layout.addWidget(self.create_stat_card("Total Companies in SEC", self.total_companies_label))

        # Profiles in DB stat
        self.profiles_count_label = QLabel()
        stats_layout.addWidget(self.create_stat_card("Generated Profiles", self.profiles_count_label))

        # Database size stat
        self.db_size_label = QLabel()
        stats_layout.addWidget(self.create_stat_card("Database Collections", self.db_size_label))

        layout.addLayout(stats_layout)
        layout.addSpacing(20)

        # Quick links
        layout.addWidget(QLabel("Quick Actions:"))
        quick_buttons_layout = QHBoxLayout()

        search_btn = QPushButton("🔍 Search Companies")
        search_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        quick_buttons_layout.addWidget(search_btn)

        generate_btn = QPushButton("📈 Generate Profile")
        generate_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        quick_buttons_layout.addWidget(generate_btn)

        view_btn = QPushButton("📊 View Profiles")
        view_btn.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        quick_buttons_layout.addWidget(view_btn)

        quick_buttons_layout.addStretch()
        layout.addLayout(quick_buttons_layout)

        # Info text
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setText("""
Database Configuration:
• Database: {} ({})
• Collection: {}

System Features:
• Search companies by ticker, name, or CIK
• Generate comprehensive company profiles from SEC data
• View detailed financial information and trends
• Batch process multiple companies
• Analyze portfolio statistics and comparisons

Getting Started:
1. Use Search to find companies
2. Generate profiles to fetch data
3. View profiles to analyze company data
4. Use Analytics for portfolio insights
        """.format(
            self.config['mongodb']['db_name'],
            self.config['mongodb']['uri'],
            self.collection_name
        ))
        layout.addWidget(info_text)
        layout.addStretch()

        return widget

    def create_stat_card(self, title: str, value_label: QLabel) -> QFrame:
        """Create a statistics card."""
        frame = QFrame()
        frame.setStyleSheet("QFrame { border: 1px solid #cccccc; border-radius: 5px; }")
        layout = QVBoxLayout(frame)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)
        layout.addWidget(value_label)

        return frame

    def update_statistics(self):
        """Update statistics on home tab."""
        try:
            # Total companies
            stats = self.ticker_fetcher.get_stats()
            self.total_companies_label.setText(f"{stats['total_companies']:,} companies")

            # Profiles in database
            profiles = self.mongo.find(self.collection_name, {})
            self.profiles_count_label.setText(f"{len(profiles)} profiles")

            # Database info
            collections = self.mongo.db.list_collection_names()
            self.db_size_label.setText(f"{len(collections)} collections")
        except Exception as e:
            logger.error(f"Error updating statistics: {e}")

    def create_search_tab(self) -> QWidget:
        """Create the search tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Search options
        search_layout = QHBoxLayout()

        search_layout.addWidget(QLabel("Search by:"))
        self.search_type_combo = QComboBox()
        self.search_type_combo.addItems(["Ticker Symbol", "Company Name", "CIK"])
        search_layout.addWidget(self.search_type_combo)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search term...")
        search_layout.addWidget(self.search_input)

        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.perform_search)
        search_layout.addWidget(search_btn)

        layout.addLayout(search_layout)

        # Results table
        self.search_results_table = QTableWidget()
        self.search_results_table.setColumnCount(4)
        self.search_results_table.setHorizontalHeaderLabels(["Ticker", "Company Name", "CIK", "Actions"])
        self.search_results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(self.search_results_table)

        layout.addStretch()

        return widget

    def perform_search(self):
        """Perform company search."""
        search_type = self.search_type_combo.currentText()
        search_term = self.search_input.text().strip()

        if not search_term:
            QMessageBox.warning(self, "Input Error", "Please enter a search term")
            return

        try:
            results = []

            if search_type == "Ticker Symbol":
                company = self.ticker_fetcher.get_by_ticker(search_term.upper())
                results = [company] if company else []
            elif search_type == "Company Name":
                results = self.ticker_fetcher.search_by_name(search_term, limit=20)
            elif search_type == "CIK":
                company = self.ticker_fetcher.get_by_cik(search_term)
                results = [company] if company else []

            # Update table
            self.search_results_table.setRowCount(len(results))
            for i, company in enumerate(results):
                self.search_results_table.setItem(i, 0, QTableWidgetItem(company['ticker']))
                self.search_results_table.setItem(i, 1, QTableWidgetItem(company['title']))
                self.search_results_table.setItem(i, 2, QTableWidgetItem(company['cik']))

                btn = QPushButton("Generate Profile")
                btn.clicked.connect(lambda checked, c=company: self.generate_profile_for_company(c))
                self.search_results_table.setCellWidget(i, 3, btn)

            if not results:
                QMessageBox.information(self, "Search Results", f"No companies found for: {search_term}")
        except Exception as e:
            logger.error(f"Search error: {e}")
            QMessageBox.critical(self, "Search Error", str(e))

    def create_generate_tab(self) -> QWidget:
        """Create the profile generation tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Single profile generation
        layout.addWidget(QLabel("Single Profile Generation:"))
        single_layout = QHBoxLayout()

        single_layout.addWidget(QLabel("Identifier (Ticker/CIK):"))
        self.single_identifier_input = QLineEdit()
        self.single_identifier_input.setPlaceholderText("e.g., AAPL or 0000320193")
        single_layout.addWidget(self.single_identifier_input)

        single_gen_btn = QPushButton("Generate Profile")
        single_gen_btn.clicked.connect(self.generate_single_profile)
        single_layout.addWidget(single_gen_btn)

        single_layout.addStretch()
        layout.addLayout(single_layout)

        # Batch generation
        layout.addSpacing(20)
        layout.addWidget(QLabel("Batch Profile Generation:"))
        batch_layout = QHBoxLayout()

        batch_layout.addWidget(QLabel("Identifiers (comma-separated):"))
        self.batch_identifiers_input = QLineEdit()
        self.batch_identifiers_input.setPlaceholderText("e.g., AAPL, MSFT, GOOGL")
        batch_layout.addWidget(self.batch_identifiers_input)

        batch_gen_btn = QPushButton("Generate Batch")
        batch_gen_btn.clicked.connect(self.generate_batch_profiles)
        batch_layout.addWidget(batch_gen_btn)

        batch_layout.addStretch()
        layout.addLayout(batch_layout)

        # Progress
        layout.addSpacing(20)
        layout.addWidget(QLabel("Progress:"))
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.progress_label = QLabel()
        layout.addWidget(self.progress_label)

        layout.addSpacing(20)

        # Options
        layout.addWidget(QLabel("Options:"))
        self.overwrite_checkbox = QCheckBox("Overwrite existing profiles")
        self.overwrite_checkbox.setChecked(True)
        layout.addWidget(self.overwrite_checkbox)

        layout.addStretch()

        return widget

    def generate_single_profile(self):
        """Generate a profile for a single company."""
        identifier = self.single_identifier_input.text().strip()
        if not identifier:
            QMessageBox.warning(self, "Input Error", "Please enter a company identifier")
            return

        self.generate_profiles([identifier])

    def generate_batch_profiles(self):
        """Generate profiles for multiple companies."""
        identifiers_str = self.batch_identifiers_input.text().strip()
        if not identifiers_str:
            QMessageBox.warning(self, "Input Error", "Please enter company identifiers")
            return

        identifiers = [id.strip() for id in identifiers_str.split(",")]
        self.generate_profiles(identifiers)

    def generate_profiles(self, identifiers: List[str]):
        """Generate profiles for given identifiers."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Already Running", "Profile generation is already in progress")
            return

        # Start worker thread
        self.worker = ProfileGeneratorWorker(
            self.aggregator, self.ticker_fetcher, identifiers, self.collection_name
        )
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.error.connect(self.on_generation_error)
        self.worker.start()

        self.progress_bar.setMaximum(len(identifiers))
        self.progress_bar.setValue(0)

    def update_progress(self, current: int, message: str):
        """Update progress bar."""
        self.progress_bar.setValue(current)
        self.progress_label.setText(message)
        self.statusBar().showMessage(message)

    def on_generation_finished(self, success: bool, message: str):
        """Handle profile generation completion."""
        if success:
            QMessageBox.information(self, "Success", message)
            self.progress_bar.setValue(0)
            self.progress_label.setText("Generation complete")
        else:
            QMessageBox.warning(self, "Partial Success", message)

    def on_generation_error(self, error: str):
        """Handle profile generation error."""
        QMessageBox.critical(self, "Generation Error", f"Error during profile generation:\n{error}")
        self.progress_bar.setValue(0)

    def generate_profile_for_company(self, company: Dict[str, Any]):
        """Generate profile for a specific company."""
        self.single_identifier_input.setText(company['ticker'])
        self.tabs.setCurrentIndex(2)
        self.generate_single_profile()

    def create_profiles_tab(self) -> QWidget:
        """Create the view profiles tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Filter section
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Ticker:"))
        self.profile_ticker_filter = QLineEdit()
        self.profile_ticker_filter.setPlaceholderText("Leave empty to show all")
        filter_layout.addWidget(self.profile_ticker_filter)

        filter_btn = QPushButton("Filter")
        filter_btn.clicked.connect(self.load_profiles)
        filter_layout.addWidget(filter_btn)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.load_profiles)
        filter_layout.addWidget(refresh_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Profiles table
        self.profiles_table = QTableWidget()
        self.profiles_table.setColumnCount(5)
        self.profiles_table.setHorizontalHeaderLabels(["Ticker", "Company Name", "CIK", "Generated At", "Actions"])
        self.profiles_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.profiles_table.itemDoubleClicked.connect(self.show_profile_details)
        layout.addWidget(self.profiles_table)

        layout.addStretch()

        # Load profiles on startup
        self.load_profiles()

        return widget

    def load_profiles(self):
        """Load profiles from database."""
        try:
            ticker_filter = self.profile_ticker_filter.text().strip().upper()

            # Build query
            query = {}
            if ticker_filter:
                query = {"company_info.ticker": {"$regex": ticker_filter, "$options": "i"}}

            profiles = self.mongo.find(self.collection_name, query, limit=100)

            # Update table
            self.profiles_table.setRowCount(len(profiles))
            for i, profile in enumerate(profiles):
                ticker = profile.get('company_info', {}).get('ticker', 'N/A')
                name = profile.get('company_info', {}).get('name', 'N/A')
                cik = profile.get('cik', 'N/A')
                generated = profile.get('generated_at', 'N/A')[:10]

                self.profiles_table.setItem(i, 0, QTableWidgetItem(ticker))
                self.profiles_table.setItem(i, 1, QTableWidgetItem(name))
                self.profiles_table.setItem(i, 2, QTableWidgetItem(cik))
                self.profiles_table.setItem(i, 3, QTableWidgetItem(generated))

                # Delete button
                btn = QPushButton("Delete")
                btn.clicked.connect(lambda checked, p=profile: self.delete_profile(p))
                self.profiles_table.setCellWidget(i, 4, btn)

        except Exception as e:
            logger.error(f"Error loading profiles: {e}")
            QMessageBox.critical(self, "Load Error", f"Error loading profiles:\n{e}")

    def show_profile_details(self):
        """Show detailed profile information."""
        current_row = self.profiles_table.currentRow()
        if current_row < 0:
            return

        ticker = self.profiles_table.item(current_row, 0).text()
        try:
            profile = self.mongo.find_one(
                self.collection_name,
                {"company_info.ticker": ticker}
            )

            if profile:
                # Create detail window
                detail_window = QDialog(self)
                detail_window.setWindowTitle(f"Profile: {ticker}")
                detail_window.setGeometry(200, 200, 800, 600)
                layout = QVBoxLayout(detail_window)

                # Create tabs for different sections
                detail_tabs = QTabWidget()

                # Overview tab
                overview_text = QTextEdit()
                overview_text.setReadOnly(True)
                overview_text.setText(self.format_profile_overview(profile))
                detail_tabs.addTab(overview_text, "Overview")

                # Financials tab
                financials_text = QTextEdit()
                financials_text.setReadOnly(True)
                financials_text.setText(self.format_financials(profile))
                detail_tabs.addTab(financials_text, "Financials")

                # Ratios tab
                ratios_text = QTextEdit()
                ratios_text.setReadOnly(True)
                ratios_text.setText(self.format_ratios(profile))
                detail_tabs.addTab(ratios_text, "Ratios")

                # Health tab
                health_text = QTextEdit()
                health_text.setReadOnly(True)
                health_text.setText(self.format_health(profile))
                detail_tabs.addTab(health_text, "Health")

                # Raw JSON tab
                raw_text = QTextEdit()
                raw_text.setReadOnly(True)
                raw_text.setText(json.dumps(profile, indent=2))
                detail_tabs.addTab(raw_text, "Raw JSON")

                layout.addWidget(detail_tabs)
                detail_window.exec_()
        except Exception as e:
            logger.error(f"Error showing profile details: {e}")
            QMessageBox.critical(self, "Error", f"Error loading profile details:\n{e}")

    def format_profile_overview(self, profile: Dict[str, Any]) -> str:
        """Format profile overview."""
        info = profile.get('company_info', {})
        filing = profile.get('filing_metadata', {})

        text = f"""
Company Information:
  Ticker: {info.get('ticker', 'N/A')}
  Name: {info.get('name', 'N/A')}
  CIK: {info.get('cik_numeric', 'N/A')}

Profile Information:
  Generated: {profile.get('generated_at', 'N/A')}
  Last Updated: {profile.get('last_updated', 'N/A')}

Filing Metadata:
  Total Filings: {filing.get('total_filings', 'N/A')}
  Latest Filing: {filing.get('latest_filing_date', 'N/A')}
  Filing Types: {', '.join(filing.get('filing_types', []))}
        """
        return text.strip()

    def format_financials(self, profile: Dict[str, Any]) -> str:
        """Format financial data."""
        latest = profile.get('latest_financials', {})

        text = "Latest Financial Metrics:\n\n"
        for key, value in latest.items():
            if isinstance(value, (int, float)):
                text += f"{key}: {value:,.2f}\n"
            else:
                text += f"{key}: {value}\n"

        return text.strip()

    def format_ratios(self, profile: Dict[str, Any]) -> str:
        """Format financial ratios."""
        ratios = profile.get('financial_ratios', {})

        text = "Financial Ratios:\n\n"
        for key, value in ratios.items():
            if isinstance(value, (int, float)):
                text += f"{key}: {value:.4f}\n"
            else:
                text += f"{key}: {value}\n"

        return text.strip()

    def format_health(self, profile: Dict[str, Any]) -> str:
        """Format health indicators."""
        health = profile.get('health_indicators', {})

        text = "Health Indicators:\n\n"
        for key, value in health.items():
            if isinstance(value, (int, float)):
                text += f"{key}: {value:.2f}\n"
            else:
                text += f"{key}: {value}\n"

        return text.strip()

    def delete_profile(self, profile: Dict[str, Any]):
        """Delete a profile from the database."""
        ticker = profile.get('company_info', {}).get('ticker', 'Unknown')

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete profile for {ticker}?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.mongo.collection(self.collection_name).delete_one({"cik": profile.get('cik')})
                QMessageBox.information(self, "Success", f"Profile for {ticker} deleted successfully")
                self.load_profiles()
            except Exception as e:
                logger.error(f"Error deleting profile: {e}")
                QMessageBox.critical(self, "Delete Error", f"Error deleting profile:\n{e}")

    def create_analytics_tab(self) -> QWidget:
        """Create the analytics tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Analytics Dashboard"))
        layout.addSpacing(20)

        # Statistics
        stats_layout = QHBoxLayout()

        # Health score distribution
        health_card = QFrame()
        health_card.setStyleSheet("QFrame { border: 1px solid #cccccc; border-radius: 5px; }")
        health_layout = QVBoxLayout(health_card)
        health_layout.addWidget(QLabel("Average Health Score"))
        self.avg_health_label = QLabel("Calculating...")
        health_layout.addWidget(self.avg_health_label)
        stats_layout.addWidget(health_card)

        # Total profiles
        profiles_card = QFrame()
        profiles_card.setStyleSheet("QFrame { border: 1px solid #cccccc; border-radius: 5px; }")
        profiles_layout = QVBoxLayout(profiles_card)
        profiles_layout.addWidget(QLabel("Total Profiles"))
        self.total_profiles_label = QLabel("Calculating...")
        profiles_layout.addWidget(self.total_profiles_label)
        stats_layout.addWidget(profiles_card)

        layout.addLayout(stats_layout)
        layout.addSpacing(20)

        # Company comparison
        layout.addWidget(QLabel("Company Comparison (select up to 5 companies):"))
        comp_layout = QHBoxLayout()

        comp_layout.addWidget(QLabel("Ticker:"))
        self.compare_ticker_input = QLineEdit()
        self.compare_ticker_input.setPlaceholderText("e.g., AAPL")
        comp_layout.addWidget(self.compare_ticker_input)

        add_comp_btn = QPushButton("Add to Comparison")
        add_comp_btn.clicked.connect(self.add_comparison)
        comp_layout.addWidget(add_comp_btn)

        layout.addLayout(comp_layout)

        # Comparison table
        self.comparison_table = QTableWidget()
        self.comparison_table.setColumnCount(5)
        self.comparison_table.setHorizontalHeaderLabels(["Ticker", "Health Score", "Latest Revenue", "Growth Rate", "Remove"])
        self.comparison_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.comparison_table)

        layout.addStretch()

        # Update analytics
        self.update_analytics()

        return widget

    def update_analytics(self):
        """Update analytics data."""
        try:
            profiles = self.mongo.find(self.collection_name, {})

            # Average health score
            health_scores = []
            for p in profiles:
                health = p.get('health_indicators', {}).get('health_score', 0)
                if health:
                    health_scores.append(health)

            avg_health = sum(health_scores) / len(health_scores) if health_scores else 0
            self.avg_health_label.setText(f"{avg_health:.2f}")

            # Total profiles
            self.total_profiles_label.setText(str(len(profiles)))

        except Exception as e:
            logger.error(f"Error updating analytics: {e}")

    def add_comparison(self):
        """Add company to comparison."""
        ticker = self.compare_ticker_input.text().strip().upper()
        if not ticker:
            QMessageBox.warning(self, "Input Error", "Please enter a ticker symbol")
            return

        if self.comparison_table.rowCount() >= 5:
            QMessageBox.warning(self, "Limit Reached", "Maximum 5 companies for comparison")
            return

        try:
            profile = self.mongo.find_one(
                self.collection_name,
                {"company_info.ticker": ticker}
            )

            if not profile:
                QMessageBox.warning(self, "Not Found", f"Profile for {ticker} not found")
                return

            row = self.comparison_table.rowCount()
            self.comparison_table.insertRow(row)

            health = profile.get('health_indicators', {}).get('health_score', 0)
            revenue = profile.get('latest_financials', {}).get('revenue', 0)
            growth = profile.get('growth_rates', {}).get('revenue_growth_1yr', 0)

            self.comparison_table.setItem(row, 0, QTableWidgetItem(ticker))
            self.comparison_table.setItem(row, 1, QTableWidgetItem(f"{health:.2f}"))
            self.comparison_table.setItem(row, 2, QTableWidgetItem(f"{revenue:,.0f}"))
            self.comparison_table.setItem(row, 3, QTableWidgetItem(f"{growth:.2f}%"))

            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(lambda: self.comparison_table.removeRow(row))
            self.comparison_table.setCellWidget(row, 4, remove_btn)

            self.compare_ticker_input.clear()
        except Exception as e:
            logger.error(f"Error adding comparison: {e}")
            QMessageBox.critical(self, "Error", f"Error adding comparison:\n{e}")

    def create_settings_tab(self) -> QWidget:
        """Create the settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Database Settings"))

        # Database URI
        layout.addWidget(QLabel("MongoDB URI:"))
        self.db_uri_input = QLineEdit()
        self.db_uri_input.setText(self.config['mongodb']['uri'])
        layout.addWidget(self.db_uri_input)

        # Database name
        layout.addWidget(QLabel("Database Name:"))
        self.db_name_input = QLineEdit()
        self.db_name_input.setText(self.config['mongodb']['db_name'])
        layout.addWidget(self.db_name_input)

        # Collection name
        layout.addWidget(QLabel("Collection Name:"))
        self.collection_input = QLineEdit()
        self.collection_input.setText(self.collection_name)
        layout.addWidget(self.collection_input)

        layout.addSpacing(20)

        # Save settings button
        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

        layout.addSpacing(20)

        # Database maintenance
        layout.addWidget(QLabel("Database Maintenance"))

        backup_btn = QPushButton("Backup Database")
        backup_btn.clicked.connect(self.backup_database)
        layout.addWidget(backup_btn)

        clear_btn = QPushButton("Clear Cache")
        clear_btn.clicked.connect(self.clear_cache)
        layout.addWidget(clear_btn)

        layout.addStretch()

        return widget

    def save_settings(self):
        """Save application settings."""
        try:
            self.config['mongodb']['uri'] = self.db_uri_input.text()
            self.config['mongodb']['db_name'] = self.db_name_input.text()

            # Reinitialize services with new settings
            self.initialize_services()
            self.load_profiles()
            self.update_statistics()

            QMessageBox.information(self, "Success", "Settings saved successfully")
        except Exception as e:
            logger.error(f"Error saving settings: {e}")
            QMessageBox.critical(self, "Error", f"Error saving settings:\n{e}")

    def backup_database(self):
        """Backup database to file."""
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Save Backup",
                "",
                "JSON Files (*.json)"
            )

            if filename:
                profiles = self.mongo.find(self.collection_name, {})
                with open(filename, 'w') as f:
                    json.dump(profiles, f, indent=2, default=str)

                QMessageBox.information(self, "Success", f"Database backed up to {filename}")
        except Exception as e:
            logger.error(f"Error backing up database: {e}")
            QMessageBox.critical(self, "Backup Error", f"Error backing up database:\n{e}")

    def clear_cache(self):
        """Clear application cache."""
        reply = QMessageBox.question(
            self,
            "Confirm",
            "This will clear the SEC company ticker cache. Proceed?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # Clear ticker fetcher cache
                import os
                cache_file = "sec_company_tickers_cache.json"
                if os.path.exists(cache_file):
                    os.remove(cache_file)

                # Reinitialize ticker fetcher
                self.ticker_fetcher = CompanyTickerFetcher()

                QMessageBox.information(self, "Success", "Cache cleared successfully")
            except Exception as e:
                logger.error(f"Error clearing cache: {e}")
                QMessageBox.critical(self, "Error", f"Error clearing cache:\n{e}")

    def refresh_database(self):
        """Refresh database information."""
        self.update_statistics()
        self.load_profiles()
        self.update_analytics()
        self.statusBar().showMessage("Database refreshed")

    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Fundamental Data Pipeline",
            """
Fundamental Data Pipeline - Desktop Application
Version 1.0

A comprehensive desktop application for fetching, processing, and analyzing 
SEC company fundamental data.

Features:
• Search companies by ticker, name, or CIK
• Generate profiles from SEC EDGAR API
• View detailed financial information
• Batch processing support
• Analytics and company comparison

© 2025
            """
        )

    def closeEvent(self, event):
        """Handle application close event."""
        try:
            if self.worker and self.worker.isRunning():
                self.worker.stop()
                self.worker.wait()

            self.mongo.close()
            event.accept()
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            event.accept()


def main():
    """Main entry point for the desktop application."""
    app = QApplication(sys.argv)
    window = DesktopApp()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

