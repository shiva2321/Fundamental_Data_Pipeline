"""
Enhanced PySide6-based Desktop Application for Fundamental Data Pipeline.
Features:
- Multi-ticker selection with search
- Queue monitoring and control (pause/resume/cancel)
- Checkpoint system for resuming interrupted processes
- Profile visualization with charts
- Professional Dark Theme
"""
import sys
import os
import json
import logging
import threading
import queue
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QLineEdit, QTextEdit, QTabWidget, 
                               QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, 
                               QSpinBox, QComboBox, QMessageBox, QProgressBar, QGroupBox, 
                               QSplitter, QFrame, QScrollArea, QDialog, QDialogButtonBox)
from PySide6.QtCore import Qt, QTimer, Signal, Slot, QObject
from PySide6.QtGui import QFont, QColor, QPalette, QIcon

from config import load_config
from mongo_client import MongoWrapper
from company_ticker_fetcher import CompanyTickerFetcher
from unified_profile_aggregator import UnifiedSECProfileAggregator
from sec_edgar_api_client import SECEdgarClient
from visualization_window import ProfileVisualizationWindow

# Configure Logging
logger = logging.getLogger("desktop_app_pyside")
logging.basicConfig(level=logging.INFO)

# --- Enums ---
class TickerStatus(Enum):
    QUEUED = "Queued"
    RUNNING = "Running"
    PAUSED = "Paused"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"

# --- Styles ---
DARK_STYLESHEET = """
QMainWindow {
    background-color: #1e1e1e;
    color: #ffffff;
}
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: 'Segoe UI', sans-serif;
    font-size: 14px;
}
QGroupBox {
    border: 1px solid #3e3e3e;
    border-radius: 6px;
    margin-top: 6px;
    padding-top: 10px;
    font-weight: bold;
    color: #4da6ff;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 3px;
}
QLineEdit, QSpinBox, QComboBox {
    background-color: #2d2d2d;
    border: 1px solid #3e3e3e;
    border-radius: 4px;
    padding: 5px;
    color: #ffffff;
}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #4da6ff;
}
QPushButton {
    background-color: #0d6efd;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #0b5ed7;
}
QPushButton:pressed {
    background-color: #0a58ca;
}
QPushButton#SecondaryButton {
    background-color: #495057;
}
QPushButton#SecondaryButton:hover {
    background-color: #3d4246;
}
QPushButton#DangerButton {
    background-color: #dc3545;
}
QPushButton#DangerButton:hover {
    background-color: #bb2d3b;
}
QPushButton#SuccessButton {
    background-color: #198754;
}
QPushButton#SuccessButton:hover {
    background-color: #157347;
}
QPushButton#WarningButton {
    background-color: #ffc107;
    color: #000;
}
QPushButton#WarningButton:hover {
    background-color: #ffca2c;
}
QTableWidget {
    background-color: #2d2d2d;
    gridline-color: #3e3e3e;
    border: 1px solid #3e3e3e;
}
QHeaderView::section {
    background-color: #3e3e3e;
    padding: 4px;
    border: 1px solid #2d2d2d;
    font-weight: bold;
}
QTabWidget::pane {
    border: 1px solid #3e3e3e;
    background-color: #1e1e1e;
}
QTabBar::tab {
    background-color: #2d2d2d;
    padding: 8px 16px;
    margin-right: 2px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    border-bottom: 2px solid #4da6ff;
}
QTextEdit {
    background-color: #121212;
    color: #00ff00;
    font-family: 'Consolas', monospace;
    border: 1px solid #3e3e3e;
}
QProgressBar {
    border: 1px solid #3e3e3e;
    border-radius: 4px;
    text-align: center;
}
QProgressBar::chunk {
    background-color: #4da6ff;
}
"""

# --- Worker Thread with Pause/Resume ---
class WorkerSignals(QObject):
    progress = Signal(str, str, str)  # ticker, type, message
    ticker_status_changed = Signal(str, str, int)  # ticker, status, progress_pct
    finished = Signal()
    error = Signal(str)
    stats_updated = Signal(dict)

class EnhancedBackgroundWorker(threading.Thread):
    def __init__(self, task_queue, signals, aggregator, ticker_fetcher, mongo):
        super().__init__(daemon=True)
        self.task_queue = task_queue
        self.signals = signals
        self.aggregator = aggregator
        self.ticker_fetcher = ticker_fetcher
        self.mongo = mongo
        self._stop_event = threading.Event()
        self._pause_events = {}  # ticker -> Event
        self._cancel_flags = {}  # ticker -> bool
        
    def run(self):
        while not self._stop_event.is_set():
            try:
                task = self.task_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            try:
                action = task.get('action')
                if action == 'generate_profiles':
                    self._handle_generate(task)
                elif action == 'pause_ticker':
                    ticker = task.get('ticker')
                    if ticker in self._pause_events:
                        self._pause_events[ticker].clear()
                        self.signals.ticker_status_changed.emit(ticker, TickerStatus.PAUSED.value, 0)
                elif action == 'resume_ticker':
                    ticker = task.get('ticker')
                    if ticker in self._pause_events:
                        self._pause_events[ticker].set()
                        self.signals.ticker_status_changed.emit(ticker, TickerStatus.RUNNING.value, 0)
                elif action == 'cancel_ticker':
                    ticker = task.get('ticker')
                    self._cancel_flags[ticker] = True
                    if ticker in self._pause_events:
                        self._pause_events[ticker].set()  # Unpause to allow cancellation
                elif action == 'refresh_stats':
                    self._handle_stats()
            except Exception as e:
                logger.exception("Worker error")
                self.signals.error.emit(str(e))
            finally:
                if task.get('action') != 'refresh_stats':
                    self.task_queue.task_done()

    def _handle_generate(self, task):
        identifiers = task.get('identifiers', [])
        options = task.get('options', {})
        collection = task.get('collection')

        self.signals.progress.emit('', 'started', f"Starting batch of {len(identifiers)} companies...")

        for idx, identifier in enumerate(identifiers, 1):
            if self._stop_event.is_set():
                self.signals.progress.emit('', 'info', "Process stopped by user.")
                break

            # Initialize pause event for this ticker
            self._pause_events[identifier] = threading.Event()
            self._pause_events[identifier].set()  # Start unpaused
            self._cancel_flags[identifier] = False

            self.signals.ticker_status_changed.emit(identifier, TickerStatus.RUNNING.value, 0)
            self.signals.progress.emit(identifier, 'company_start', f"[{idx}/{len(identifiers)}] Processing {identifier}...")
            
            try:
                # Check for checkpoint
                checkpoint = self._load_checkpoint(identifier, collection)
                
                # Resolve company
                company = self.ticker_fetcher.get_by_ticker(identifier.upper())
                if not company:
                    company = self.ticker_fetcher.get_by_cik(identifier)
                
                if not company:
                    self.signals.progress.emit(identifier, 'error', f"Company not found: {identifier}")
                    self.signals.ticker_status_changed.emit(identifier, TickerStatus.FAILED.value, 0)
                    continue

                cik = company['cik']
                
                # Check for pause/cancel
                if not self._pause_events[identifier].wait(timeout=0.1):
                    self.signals.progress.emit(identifier, 'info', f"Paused: {identifier}")
                    self._pause_events[identifier].wait()  # Wait until resumed
                
                if self._cancel_flags.get(identifier):
                    self.signals.progress.emit(identifier, 'info', f"Cancelled: {identifier}")
                    self.signals.ticker_status_changed.emit(identifier, TickerStatus.CANCELLED.value, 0)
                    self._clear_checkpoint(identifier, collection)
                    continue
                
                # Progress callback for aggregator
                def progress_cb(level, msg):
                    # Check pause/cancel in callback
                    if not self._pause_events[identifier].is_set():
                        self._pause_events[identifier].wait()
                    if self._cancel_flags.get(identifier):
                        raise Exception("Cancelled by user")
                    
                    self.signals.progress.emit(identifier, 'detail', f"  -> {msg}")
                    # Update progress percentage based on stage
                    if 'Fetching' in msg:
                        self.signals.ticker_status_changed.emit(identifier, TickerStatus.RUNNING.value, 20)
                    elif 'Extracting' in msg:
                        self.signals.ticker_status_changed.emit(identifier, TickerStatus.RUNNING.value, 40)
                    elif 'Calculating' in msg:
                        self.signals.ticker_status_changed.emit(identifier, TickerStatus.RUNNING.value, 60)
                    elif 'Generating' in msg:
                        self.signals.ticker_status_changed.emit(identifier, TickerStatus.RUNNING.value, 80)

                profile = self.aggregator.aggregate_company_profile(
                    cik=cik,
                    company_info=company,
                    output_collection=collection,
                    options=options,
                    progress_callback=progress_cb
                )

                if profile:
                    self.signals.progress.emit(identifier, 'company_finish', f"Successfully generated profile for {identifier}")
                    self.signals.ticker_status_changed.emit(identifier, TickerStatus.COMPLETED.value, 100)
                    self._clear_checkpoint(identifier, collection)
                else:
                    self.signals.progress.emit(identifier, 'error', f"Failed to generate profile for {identifier}")
                    self.signals.ticker_status_changed.emit(identifier, TickerStatus.FAILED.value, 0)

            except Exception as e:
                if "Cancelled" in str(e):
                    self.signals.ticker_status_changed.emit(identifier, TickerStatus.CANCELLED.value, 0)
                else:
                    logger.exception(f"Error processing {identifier}")
                    self.signals.progress.emit(identifier, 'error', f"Error processing {identifier}: {str(e)}")
                    self.signals.ticker_status_changed.emit(identifier, TickerStatus.FAILED.value, 0)
                    # Save checkpoint for resume
                    self._save_checkpoint(identifier, collection, {'error': str(e)})
            
            # Cleanup
            if identifier in self._pause_events:
                del self._pause_events[identifier]
            if identifier in self._cancel_flags:
                del self._cancel_flags[identifier]

        self.signals.finished.emit()
        self._handle_stats()

    def _save_checkpoint(self, identifier, collection, data):
        """Save checkpoint to MongoDB for resume capability."""
        try:
            checkpoint_col = 'processing_checkpoints'
            self.mongo.upsert_one(checkpoint_col, 
                                {'identifier': identifier, 'collection': collection},
                                {
                                    'identifier': identifier,
                                    'collection': collection,
                                    'timestamp': datetime.utcnow().isoformat(),
                                    'data': data
                                })
        except Exception as e:
            logger.error(f"Failed to save checkpoint for {identifier}: {e}")

    def _load_checkpoint(self, identifier, collection):
        """Load checkpoint from MongoDB."""
        try:
            checkpoint_col = 'processing_checkpoints'
            return self.mongo.find_one(checkpoint_col, 
                                      {'identifier': identifier, 'collection': collection})
        except Exception:
            return None

    def _clear_checkpoint(self, identifier, collection):
        """Clear checkpoint after successful completion."""
        try:
            checkpoint_col = 'processing_checkpoints'
            self.mongo.delete_one(checkpoint_col, 
                                {'identifier': identifier, 'collection': collection})
        except Exception as e:
            logger.error(f"Failed to clear checkpoint for {identifier}: {e}")

    def _handle_stats(self):
        stats = self.ticker_fetcher.get_stats()
        self.signals.stats_updated.emit(stats)

    def stop(self):
        self._stop_event.set()


# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Fundamental Data Pipeline - Professional Edition")
        self.resize(1400, 900)
        
        # Load Config & Init Backend
        self.config_manager = load_config()
        self.config = self.config_manager.config
        self.init_backend()

        # Setup UI
        self.setup_ui()
        self.apply_styles()

        # Start Worker
        self.start_worker()

    def init_backend(self):
        self.mongo = MongoWrapper(uri=self.config['mongodb']['uri'], database=self.config['mongodb']['db_name'])
        self.sec_client = SECEdgarClient()
        self.aggregator = UnifiedSECProfileAggregator(self.mongo, self.sec_client)
        self.ticker_fetcher = CompanyTickerFetcher()
        
        self.task_queue = queue.Queue()
        self.worker_signals = WorkerSignals()
        self.worker_signals.progress.connect(self.handle_progress)
        self.worker_signals.ticker_status_changed.connect(self.update_ticker_status)
        self.worker_signals.finished.connect(self.handle_finished)
        self.worker_signals.error.connect(self.handle_error)
        self.worker_signals.stats_updated.connect(self.update_stats_ui)

    def start_worker(self):
        self.worker = EnhancedBackgroundWorker(self.task_queue, self.worker_signals, self.aggregator, self.ticker_fetcher, self.mongo)
        self.worker.start()
        # Initial stats
        self.task_queue.put({'action': 'refresh_stats'})

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 1. Top Bar (Stats & Status)
        self.top_bar = QGroupBox("System Status")
        top_layout = QHBoxLayout(self.top_bar)
        
        self.lbl_total_companies = QLabel("Total Companies: ...")
        self.lbl_profiles_db = QLabel("Profiles in DB: ...")
        self.lbl_status = QLabel("Status: Ready")
        self.lbl_status.setStyleSheet("color: #4da6ff; font-weight: bold;")

        top_layout.addWidget(self.lbl_total_companies)
        top_layout.addSpacing(20)
        top_layout.addWidget(self.lbl_profiles_db)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_status)
        
        main_layout.addWidget(self.top_bar)

        # 2. Main Content (Tabs)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_dashboard_tab(), "Dashboard & Generate")
        self.tabs.addTab(self.create_queue_monitor_tab(), "Queue Monitor")
        self.tabs.addTab(self.create_profiles_tab(), "Profile Manager")
        self.tabs.addTab(self.create_settings_tab(), "Settings")
        
        main_layout.addWidget(self.tabs)

        # 3. Logs Panel
        self.logs_group = QGroupBox("Pipeline Execution Logs")
        logs_layout = QVBoxLayout(self.logs_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(180)
        logs_layout.addWidget(self.log_text)
        
        # Clear Logs Button
        btn_clear_logs = QPushButton("Clear Logs")
        btn_clear_logs.setObjectName("SecondaryButton")
        btn_clear_logs.clicked.connect(self.log_text.clear)
        logs_layout.addWidget(btn_clear_logs, alignment=Qt.AlignRight)

        main_layout.addWidget(self.logs_group)

    def create_dashboard_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # Left Column: Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignTop)

        # Multi-Select Search Group
        grp_search = QGroupBox("Ticker Search & Selection")
        search_layout = QVBoxLayout(grp_search)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search by ticker or company name...")
        self.search_bar.returnPressed.connect(self.perform_search)
        search_layout.addWidget(self.search_bar)
        
        btn_search = QPushButton("Search")
        btn_search.clicked.connect(self.perform_search)
        search_layout.addWidget(btn_search)
        
        self.search_results = QTableWidget()
        self.search_results.setColumnCount(3)
        self.search_results.setHorizontalHeaderLabels(["Ticker", "Name", "CIK"])
        self.search_results.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.search_results.setSelectionBehavior(QTableWidget.SelectRows)
        self.search_results.setSelectionMode(QTableWidget.MultiSelection)
        self.search_results.setMaximumHeight(200)
        search_layout.addWidget(self.search_results)
        
        btn_add_to_queue = QPushButton("Add Selected to Queue")
        btn_add_to_queue.setObjectName("SuccessButton")
        btn_add_to_queue.clicked.connect(self.add_selected_to_queue)
        search_layout.addWidget(btn_add_to_queue)
        
        left_layout.addWidget(grp_search)

        # Options Group
        grp_options = QGroupBox("Configuration")
        opts_layout = QVBoxLayout(grp_options)
        
        # Lookback
        h_lookback = QHBoxLayout()
        h_lookback.addWidget(QLabel("Lookback Years:"))
        self.spin_lookback = QSpinBox()
        self.spin_lookback.setRange(1, 50)
        self.spin_lookback.setValue(self.config.get('profile_settings', {}).get('lookback_years', 10))
        h_lookback.addWidget(self.spin_lookback)
        opts_layout.addLayout(h_lookback)

        # Incremental
        self.chk_incremental = QCheckBox("Incremental Update (Merge new filings)")
        self.chk_incremental.setChecked(self.config.get('profile_settings', {}).get('incremental_updates', False))
        opts_layout.addWidget(self.chk_incremental)

        # Features (Collapsible)
        self.feature_checks = {}
        features = self.config.get('profile_settings', {}).get('included_features', {})
        
        for f_key, f_enabled in features.items():
            chk = QCheckBox(f_key.replace('_', ' ').title())
            chk.setChecked(f_enabled)
            self.feature_checks[f_key] = chk
            opts_layout.addWidget(chk)
            
        left_layout.addWidget(grp_options)
        left_layout.addStretch()

        # Right Column: Quick Actions
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        grp_quick = QGroupBox("Quick Actions")
        quick_layout = QVBoxLayout(grp_quick)
        
        self.input_ticker = QLineEdit()
        self.input_ticker.setPlaceholderText("Enter Ticker (e.g. AAPL) or CIK")
        quick_layout.addWidget(QLabel("Single Identifier:"))
        quick_layout.addWidget(self.input_ticker)
        
        self.btn_generate_single = QPushButton("Generate Profile Now")
        self.btn_generate_single.clicked.connect(self.generate_single)
        quick_layout.addWidget(self.btn_generate_single)

        quick_layout.addSpacing(10)
        
        self.input_batch = QTextEdit()
        self.input_batch.setPlaceholderText("Paste comma-separated tickers here...\nAAPL, MSFT, GOOGL")
        self.input_batch.setMaximumHeight(100)
        quick_layout.addWidget(QLabel("Batch Processing:"))
        quick_layout.addWidget(self.input_batch)
        
        self.btn_generate_batch = QPushButton("Process Batch")
        self.btn_generate_batch.clicked.connect(self.generate_batch)
        quick_layout.addWidget(self.btn_generate_batch)
        
        quick_layout.addSpacing(15)
        
        # Bulk Selection
        quick_layout.addWidget(QLabel("Bulk Selection:"))
        
        bulk_h1 = QHBoxLayout()
        self.spin_top_n = QSpinBox()
        self.spin_top_n.setRange(1, 100)
        self.spin_top_n.setValue(10)
        self.spin_top_n.setMaximumWidth(60)
        bulk_h1.addWidget(QLabel("N ="))
        bulk_h1.addWidget(self.spin_top_n)
        quick_layout.addLayout(bulk_h1)
        
        self.btn_top_n_random = QPushButton("Add Top N Random Tickers")
        self.btn_top_n_random.setObjectName("SuccessButton")
        self.btn_top_n_random.clicked.connect(self.add_top_n_random)
        quick_layout.addWidget(self.btn_top_n_random)
        
        self.btn_top_n = QPushButton("Add Top N Tickers (by Market Cap)")
        self.btn_top_n.setObjectName("SuccessButton")
        self.btn_top_n.clicked.connect(self.add_top_n)
        quick_layout.addWidget(self.btn_top_n)
        
        right_layout.addWidget(grp_quick)
        right_layout.addStretch()

        layout.addWidget(left_panel, 1)
        layout.addWidget(right_panel, 1)
        
        return tab

    def create_queue_monitor_tab(self):
        """NEW: Queue monitoring tab with pause/resume/cancel controls."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Controls
        ctrl_layout = QHBoxLayout()
        
        btn_pause = QPushButton("Pause Selected")
        btn_pause.setObjectName("WarningButton")
        btn_pause.clicked.connect(self.pause_selected_ticker)
        ctrl_layout.addWidget(btn_pause)
        
        btn_resume = QPushButton("Resume Selected")
        btn_resume.setObjectName("SuccessButton")
        btn_resume.clicked.connect(self.resume_selected_ticker)
        ctrl_layout.addWidget(btn_resume)
        
        btn_cancel = QPushButton("Cancel Selected")
        btn_cancel.setObjectName("DangerButton")
        btn_cancel.clicked.connect(self.cancel_selected_ticker)
        ctrl_layout.addWidget(btn_cancel)
        
        btn_retry = QPushButton("Retry Failed")
        btn_retry.setObjectName("SecondaryButton")
        btn_retry.clicked.connect(self.retry_failed_ticker)
        ctrl_layout.addWidget(btn_retry)
        
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # Queue Table
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(5)
        self.queue_table.setHorizontalHeaderLabels(["Ticker", "Status", "Progress", "Stage", "Last Update"])
        self.queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.queue_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.queue_table)

        return tab

    def create_profiles_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Controls
        ctrl_layout = QHBoxLayout()
        self.btn_refresh_profiles = QPushButton("Refresh List")
        self.btn_refresh_profiles.clicked.connect(self.load_profiles)
        ctrl_layout.addWidget(self.btn_refresh_profiles)
        
        self.btn_view_profile = QPushButton("View Selected")
        self.btn_view_profile.setObjectName("SecondaryButton")
        self.btn_view_profile.clicked.connect(self.view_profile)
        ctrl_layout.addWidget(self.btn_view_profile)
        
        self.btn_edit_profile = QPushButton("Edit Selected")
        self.btn_edit_profile.setObjectName("SecondaryButton")
        self.btn_edit_profile.clicked.connect(self.edit_profile)
        ctrl_layout.addWidget(self.btn_edit_profile)
        
        self.btn_visualize_profile = QPushButton("Visualize Selected")
        self.btn_visualize_profile.setObjectName("SuccessButton")
        self.btn_visualize_profile.clicked.connect(self.visualize_profile)
        ctrl_layout.addWidget(self.btn_visualize_profile)
        
        self.btn_delete_profile = QPushButton("Delete Selected")
        self.btn_delete_profile.setObjectName("DangerButton")
        self.btn_delete_profile.clicked.connect(self.delete_profile)
        ctrl_layout.addWidget(self.btn_delete_profile)
        
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # Table
        self.profiles_table = QTableWidget()
        self.profiles_table.setColumnCount(4)
        self.profiles_table.setHorizontalHeaderLabels(["Ticker", "Name", "CIK", "Last Generated"])
        self.profiles_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.profiles_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.profiles_table.doubleClicked.connect(self.visualize_profile)  # Double-click to visualize
        layout.addWidget(self.profiles_table)

        return tab

    def create_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignTop)

        grp_mongo = QGroupBox("MongoDB Connection")
        m_layout = QVBoxLayout(grp_mongo)
        
        self.input_mongo_uri = QLineEdit(self.config['mongodb']['uri'])
        m_layout.addWidget(QLabel("URI:"))
        m_layout.addWidget(self.input_mongo_uri)
        
        self.input_mongo_db = QLineEdit(self.config['mongodb']['db_name'])
        m_layout.addWidget(QLabel("Database Name:"))
        m_layout.addWidget(self.input_mongo_db)
        
        layout.addWidget(grp_mongo)

        btn_save = QPushButton("Save Settings")
        btn_save.clicked.connect(self.save_settings)
        layout.addWidget(btn_save)

        return tab

    def apply_styles(self):
        self.setStyleSheet(DARK_STYLESHEET)

    # --- Logic ---

    def get_options_from_ui(self):
        opts = {
            'lookback_years': self.spin_lookback.value(),
            'incremental': self.chk_incremental.isChecked()
        }
        for k, chk in self.feature_checks.items():
            opts[f'include_{k}'] = chk.isChecked()
        return opts

    def perform_search(self):
        term = self.search_bar.text().strip()
        if not term:
            return
        
        try:
            # Search by name or ticker
            results = []
            
            # Try ticker first
            ticker_result = self.ticker_fetcher.get_by_ticker(term.upper())
            if ticker_result:
                results.append(ticker_result)
            else:
                # Search by name
                results = self.ticker_fetcher.search_by_name(term, limit=50)
            
            # Clear and populate table
            self.search_results.setRowCount(0)
            for r in results:
                row = self.search_results.rowCount()
                self.search_results.insertRow(row)
                self.search_results.setItem(row, 0, QTableWidgetItem(r.get('ticker', '')))
                self.search_results.setItem(row, 1, QTableWidgetItem(r.get('title', '')))
                self.search_results.setItem(row, 2, QTableWidgetItem(str(r.get('cik', ''))))
            
            if results:
                self.log_message(f"Found {len(results)} results for '{term}'")
            else:
                self.log_message(f"No results found for '{term}'")
                QMessageBox.information(self, "No Results", f"No companies found matching '{term}'")
                
        except Exception as e:
            self.log_message(f"Search error: {e}")
            logger.exception("Search error")
            QMessageBox.warning(self, "Search Error", f"Error searching: {e}")

    def add_selected_to_queue(self):
        """Add selected tickers from search to processing queue."""
        selected_rows = self.search_results.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one ticker from search results.")
            return
        
        tickers = []
        for row_idx in selected_rows:
            ticker = self.search_results.item(row_idx.row(), 0).text()
            if ticker:
                tickers.append(ticker)
        
        if tickers:
            # Add to queue table
            for ticker in tickers:
                self._add_ticker_to_queue_table(ticker, TickerStatus.QUEUED.value)
            
            # Start processing
            self.task_queue.put({
                'action': 'generate_profiles',
                'identifiers': tickers,
                'options': self.get_options_from_ui(),
                'collection': self.config['collections']['profiles']
            })
            
            self.lbl_status.setText(f"Queued {len(tickers)} tickers")
            self.log_message(f"Added {len(tickers)} tickers to queue: {', '.join(tickers)}")

    def _add_ticker_to_queue_table(self, ticker, status):
        """Add or update ticker in queue table."""
        # Check if ticker already exists
        for row in range(self.queue_table.rowCount()):
            if self.queue_table.item(row, 0) and self.queue_table.item(row, 0).text() == ticker:
                # Update existing
                self.queue_table.setItem(row, 1, QTableWidgetItem(status))
                self.queue_table.setItem(row, 4, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
                return
        
        # Add new
        row = self.queue_table.rowCount()
        self.queue_table.insertRow(row)
        self.queue_table.setItem(row, 0, QTableWidgetItem(ticker))
        self.queue_table.setItem(row, 1, QTableWidgetItem(status))
        
        # Progress bar
        progress_bar = QProgressBar()
        progress_bar.setValue(0)
        self.queue_table.setCellWidget(row, 2, progress_bar)
        
        self.queue_table.setItem(row, 3, QTableWidgetItem("Waiting"))
        self.queue_table.setItem(row, 4, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))

    def generate_single(self):
        ident = self.input_ticker.text().strip()
        if not ident:
            QMessageBox.warning(self, "Input Error", "Please enter a ticker or CIK.")
            return
        
        self._add_ticker_to_queue_table(ident, TickerStatus.QUEUED.value)
        
        self.task_queue.put({
            'action': 'generate_profiles',
            'identifiers': [ident],
            'options': self.get_options_from_ui(),
            'collection': self.config['collections']['profiles']
        })
        self.lbl_status.setText(f"Queued: {ident}")

    def generate_batch(self):
        text = self.input_batch.toPlainText()
        idents = [x.strip() for x in text.replace('\n', ',').split(',') if x.strip()]
        if not idents:
            QMessageBox.warning(self, "Input Error", "Please enter at least one identifier.")
            return
        
        for ident in idents:
            self._add_ticker_to_queue_table(ident, TickerStatus.QUEUED.value)
            
        self.task_queue.put({
            'action': 'generate_profiles',
            'identifiers': idents,
            'options': self.get_options_from_ui(),
            'collection': self.config['collections']['profiles']
        })
        self.lbl_status.setText(f"Queued batch of {len(idents)}")

    def add_top_n_random(self):
        """Add N randomly selected tickers to the queue."""
        import random
        
        n = self.spin_top_n.value()
        
        try:
            # Get all companies
            all_companies = self.ticker_fetcher.get_all_companies()
            
            if not all_companies:
                QMessageBox.warning(self, "No Data", "No companies available in the database.")
                return
            
            # Randomly select N companies
            n = min(n, len(all_companies))
            selected = random.sample(all_companies, n)
            tickers = [c.get('ticker', c.get('cik', '')) for c in selected if c.get('ticker') or c.get('cik')]
            
            if tickers:
                # Add to queue table
                for ticker in tickers:
                    self._add_ticker_to_queue_table(ticker, TickerStatus.QUEUED.value)
                
                # Start processing
                self.task_queue.put({
                    'action': 'generate_profiles',
                    'identifiers': tickers,
                    'options': self.get_options_from_ui(),
                    'collection': self.config['collections']['profiles']
                })
                
                self.lbl_status.setText(f"Queued {len(tickers)} random tickers")
                self.log_message(f"Added {len(tickers)} random tickers to queue")
            else:
                QMessageBox.warning(self, "Error", "Could not extract tickers from selected companies.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to select random tickers: {e}")
            logger.exception("Error selecting random tickers")

    def add_top_n(self):
        """Add top N tickers by market cap to the queue."""
        n = self.spin_top_n.value()
        
        try:
            # Get all companies
            all_companies = self.ticker_fetcher.get_all_companies()
            
            if not all_companies:
                QMessageBox.warning(self, "No Data", "No companies available in the database.")
                return
            
            # Filter companies with tickers (top companies usually have tickers)
            companies_with_tickers = [c for c in all_companies if c.get('ticker')]
            
            # Take first N (assuming they're already sorted by importance/market cap in the source)
            n = min(n, len(companies_with_tickers))
            selected = companies_with_tickers[:n]
            tickers = [c['ticker'] for c in selected]
            
            if tickers:
                # Add to queue table
                for ticker in tickers:
                    self._add_ticker_to_queue_table(ticker, TickerStatus.QUEUED.value)
                
                # Start processing
                self.task_queue.put({
                    'action': 'generate_profiles',
                    'identifiers': tickers,
                    'options': self.get_options_from_ui(),
                    'collection': self.config['collections']['profiles']
                })
                
                self.lbl_status.setText(f"Queued top {len(tickers)} tickers")
                self.log_message(f"Added top {len(tickers)} tickers to queue: {', '.join(tickers[:5])}...")
            else:
                QMessageBox.warning(self, "Error", "Could not extract tickers from top companies.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to select top tickers: {e}")
            logger.exception("Error selecting top tickers")

    def pause_selected_ticker(self):
        """Pause the selected ticker in queue."""
        selected_rows = self.queue_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        ticker = self.queue_table.item(selected_rows[0].row(), 0).text()
        self.task_queue.put({'action': 'pause_ticker', 'ticker': ticker})
        self.log_message(f"Pausing {ticker}...")

    def resume_selected_ticker(self):
        """Resume the selected ticker in queue."""
        selected_rows = self.queue_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        ticker = self.queue_table.item(selected_rows[0].row(), 0).text()
        self.task_queue.put({'action': 'resume_ticker', 'ticker': ticker})
        self.log_message(f"Resuming {ticker}...")

    def cancel_selected_ticker(self):
        """Cancel the selected ticker in queue."""
        selected_rows = self.queue_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        ticker = self.queue_table.item(selected_rows[0].row(), 0).text()
        if QMessageBox.question(self, "Confirm", f"Cancel processing for {ticker}?") == QMessageBox.Yes:
            self.task_queue.put({'action': 'cancel_ticker', 'ticker': ticker})
            self.log_message(f"Cancelling {ticker}...")

    def retry_failed_ticker(self):
        """Retry a failed ticker."""
        selected_rows = self.queue_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        
        ticker = self.queue_table.item(selected_rows[0].row(), 0).text()
        status = self.queue_table.item(selected_rows[0].row(), 1).text()
        
        if status == TickerStatus.FAILED.value:
            self.task_queue.put({
                'action': 'generate_profiles',
                'identifiers': [ticker],
                'options': self.get_options_from_ui(),
                'collection': self.config['collections']['profiles']
            })
            self.log_message(f"Retrying {ticker}...")

    def load_profiles(self):
        try:
            col_name = self.config['collections']['profiles']
            profiles = list(self.mongo.find(col_name, {}, limit=500))
            
            self.profiles_table.setRowCount(0)
            for p in profiles:
                row = self.profiles_table.rowCount()
                self.profiles_table.insertRow(row)
                
                info = p.get('company_info', {})
                self.profiles_table.setItem(row, 0, QTableWidgetItem(info.get('ticker', 'N/A')))
                self.profiles_table.setItem(row, 1, QTableWidgetItem(info.get('name', 'N/A')))
                self.profiles_table.setItem(row, 2, QTableWidgetItem(str(p.get('cik', 'N/A'))))
                self.profiles_table.setItem(row, 3, QTableWidgetItem(str(p.get('generated_at', ''))[:19]))
                
            self.lbl_profiles_db.setText(f"Profiles in DB: {len(profiles)}")
        except Exception as e:
            self.log_message(f"Error loading profiles: {e}")

    def view_profile(self):
        """View profile details in a read-only dialog."""
        rows = self.profiles_table.selectionModel().selectedRows()
        if not rows:
            return
        
        cik = self.profiles_table.item(rows[0].row(), 2).text()
        col_name = self.config['collections']['profiles']
        profile = self.mongo.find_one(col_name, {'cik': cik})
        
        if not profile:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"View Profile - {cik}")
        dlg.resize(700, 700)
        l = QVBoxLayout(dlg)
        
        txt = QTextEdit()
        txt.setPlainText(json.dumps(profile, indent=2, default=str))
        txt.setReadOnly(True)
        l.addWidget(txt)
        
        btns = QDialogButtonBox(QDialogButtonBox.Close)
        btns.rejected.connect(dlg.reject)
        l.addWidget(btns)
        
        dlg.exec()

    def edit_profile(self):
        rows = self.profiles_table.selectionModel().selectedRows()
        if not rows:
            return
        
        cik = self.profiles_table.item(rows[0].row(), 2).text()
        col_name = self.config['collections']['profiles']
        profile = self.mongo.find_one(col_name, {'cik': cik})
        
        if not profile:
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Edit Profile - {cik}")
        dlg.resize(700, 700)
        l = QVBoxLayout(dlg)
        
        txt = QTextEdit()
        txt.setPlainText(json.dumps(profile, indent=2, default=str))
        l.addWidget(txt)
        
        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.accepted.connect(lambda: self.save_profile_edit(dlg, cik, txt.toPlainText()))
        btns.rejected.connect(dlg.reject)
        l.addWidget(btns)
        
        dlg.exec()

    def save_profile_edit(self, dlg, cik, text):
        try:
            new_data = json.loads(text)
            col_name = self.config['collections']['profiles']
            self.mongo.replace_one(col_name, {'cik': cik}, new_data)
            self.log_message(f"Updated profile for {cik}")
            dlg.accept()
            self.load_profiles()
        except Exception as e:
            QMessageBox.critical(dlg, "Error", f"Invalid JSON: {e}")

    def visualize_profile(self):
        """NEW: Open visualization window for selected profile."""
        rows = self.profiles_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "No Selection", "Please select a profile to visualize.")
            return
        
        cik = self.profiles_table.item(rows[0].row(), 2).text()
        col_name = self.config['collections']['profiles']
        profile = self.mongo.find_one(col_name, {'cik': cik})
        
        if not profile:
            QMessageBox.warning(self, "Not Found", f"Profile for CIK {cik} not found.")
            return
        
        try:
            from visualization_window import ProfileVisualizationWindow
            viz_window = ProfileVisualizationWindow(profile, self.config, self)
            viz_window.exec()
        except Exception as e:
            QMessageBox.critical(self, "Visualization Error", f"Failed to open visualization: {e}")
            logger.exception("Visualization error")

    def delete_profile(self):
        """Delete selected profile."""
        rows = self.profiles_table.selectionModel().selectedRows()
        if not rows:
            return
            
        cik = self.profiles_table.item(rows[0].row(), 2).text()
        if QMessageBox.question(self, "Confirm", f"Delete profile for {cik}?") == QMessageBox.Yes:
            col_name = self.config['collections']['profiles']
            self.mongo.delete_one(col_name, {'cik': cik})
            self.log_message(f"Deleted profile {cik}")
            self.load_profiles()

    def save_settings(self):
        self.config['mongodb']['uri'] = self.input_mongo_uri.text()
        self.config['mongodb']['db_name'] = self.input_mongo_db.text()
        self.config_manager.save_config()
        QMessageBox.information(self, "Saved", "Settings saved. Restart application to apply connection changes.")

    # --- Worker Handlers ---
    @Slot(str, str, str)
    def handle_progress(self, ticker, type_, msg):
        self.log_message(msg)
        if type_ == 'started':
            self.lbl_status.setText("Processing...")

    @Slot(str, str, int)
    def update_ticker_status(self, ticker, status, progress_pct):
        """Update ticker status in queue table."""
        for row in range(self.queue_table.rowCount()):
            if self.queue_table.item(row, 0) and self.queue_table.item(row, 0).text() == ticker:
                self.queue_table.setItem(row, 1, QTableWidgetItem(status))
                
                # Update progress bar
                progress_widget = self.queue_table.cellWidget(row, 2)
                if isinstance(progress_widget, QProgressBar):
                    progress_widget.setValue(progress_pct)
                
                self.queue_table.setItem(row, 4, QTableWidgetItem(datetime.now().strftime("%H:%M:%S")))
                break

    @Slot()
    def handle_finished(self):
        self.lbl_status.setText("Ready")
        self.load_profiles()

    @Slot(str)
    def handle_error(self, msg):
        self.log_message(f"ERROR: {msg}")
        self.lbl_status.setText("Error")

    @Slot(dict)
    def update_stats_ui(self, stats):
        self.lbl_total_companies.setText(f"Total Companies: {stats.get('total_companies', 'N/A')}")

    def log_message(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{ts}] {msg}")
        # Auto scroll
        sb = self.log_text.verticalScrollBar()
        sb.setValue(sb.maximum())

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
 