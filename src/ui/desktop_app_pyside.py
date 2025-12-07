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
import json
import logging
import threading
import queue
from datetime import datetime
from typing import List
from enum import Enum

from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QPushButton, QLineEdit, QTextEdit, QTabWidget, 
                               QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, 
                               QSpinBox, QComboBox, QMessageBox, QProgressBar, QGroupBox, 
                               QSplitter, QDialog, QDialogButtonBox)
from PySide6.QtCore import Qt, Signal, Slot, QObject
from PySide6.QtGui import QFont, QColor

from src.utils.config import load_config
from src.clients.mongo_client import MongoWrapper
from src.clients.company_ticker_fetcher import CompanyTickerFetcher
from src.analysis.unified_profile_aggregator import UnifiedSECProfileAggregator
from src.clients.sec_edgar_api_client import SECEdgarClient
from src.ui.visualization_window import ProfileVisualizationWindow

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
QPushButton#OllamaStatusButton {
    background-color: #6c757d;
    color: white;
    font-weight: bold;
    padding: 5px 10px;
    border-radius: 4px;
    border: none;
}
QPushButton#OllamaStatusButton:hover {
    opacity: 0.9;
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
    def __init__(self, task_queue, signals, aggregator, ticker_fetcher, mongo, config):
        super().__init__(daemon=True)
        self.task_queue = task_queue
        self.signals = signals
        self.aggregator = aggregator
        self.ticker_fetcher = ticker_fetcher
        self.mongo = mongo
        self.config = config
        self._stop_event = threading.Event()
        self._pause_events = {}  # ticker -> Event
        self._cancel_flags = {}  # ticker -> bool
        
        # Email notification support
        try:
            from src.utils.email_notifier import EmailNotifier
            self.email_notifier = EmailNotifier(config)
        except Exception as e:
            logger.warning(f"Email notifier initialization failed: {e}")
            self.email_notifier = None

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
                    self.signals.progress.emit(ticker, 'info', f"Cancellation requested for {ticker}")
                elif action == 'cancel_all':
                    # Cancel all running tickers
                    for ticker in list(self._cancel_flags.keys()):
                        self._cancel_flags[ticker] = True
                        if ticker in self._pause_events:
                            self._pause_events[ticker].set()
                    self.signals.progress.emit('', 'info', "Cancellation requested for all tickers")
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

        # Initialize email tracking
        email_results = {
            'total': len(identifiers),
            'successful': 0,
            'failed': 0,
            'tickers': [],
            'failed_tickers': [],
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'database': self.config.get('mongodb', {}).get('db_name', 'N/A'),
            'collection': collection or 'N/A'
        }
        start_time = datetime.now()

        self.signals.progress.emit('', 'started', f"Starting batch of {len(identifiers)} companies...")

        for idx, identifier in enumerate(identifiers, 1):
            # Early cancellation check - before any processing
            if self._stop_event.is_set() or self._cancel_flags.get(identifier, False):
                self.signals.progress.emit(identifier, 'info', f"Skipping cancelled ticker: {identifier}")
                self.signals.ticker_status_changed.emit(identifier, TickerStatus.CANCELLED.value, 0)
                continue

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
                    email_results['successful'] += 1
                    email_results['tickers'].append(identifier)
                else:
                    self.signals.progress.emit(identifier, 'error', f"Failed to generate profile for {identifier}")
                    self.signals.ticker_status_changed.emit(identifier, TickerStatus.FAILED.value, 0)
                    email_results['failed'] += 1
                    email_results['failed_tickers'].append(identifier)

            except Exception as e:
                if "Cancelled" in str(e):
                    self.signals.ticker_status_changed.emit(identifier, TickerStatus.CANCELLED.value, 0)
                else:
                    logger.exception(f"Error processing {identifier}")
                    self.signals.progress.emit(identifier, 'error', f"Error processing {identifier}: {str(e)}")
                    self.signals.ticker_status_changed.emit(identifier, TickerStatus.FAILED.value, 0)
                    # Save checkpoint for resume
                    self._save_checkpoint(identifier, collection, {'error': str(e)})
                    email_results['failed'] += 1
                    email_results['failed_tickers'].append(identifier)

                    # Send ticker failure notification if enabled
                    if self.email_notifier:
                        try:
                            context = {
                                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                'attempt': 1,
                                'max_attempts': 1,
                                'lookback_years': options.get('lookback_years', 'N/A'),
                                'filing_limit': options.get('filing_limit', 'N/A')
                            }
                            self.email_notifier.send_ticker_failure_report(identifier, str(e), context)
                        except Exception as email_err:
                            logger.error(f"Failed to send ticker failure email: {email_err}")

            # Cleanup
            if identifier in self._pause_events:
                del self._pause_events[identifier]
            if identifier in self._cancel_flags:
                del self._cancel_flags[identifier]

        # Send completion email
        end_time = datetime.now()
        email_results['end_time'] = end_time.strftime('%Y-%m-%d %H:%M:%S')
        email_results['duration'] = str(end_time - start_time).split('.')[0]

        if self.email_notifier:
            try:
                self.email_notifier.send_completion_report(email_results)
            except Exception as e:
                logger.error(f"Failed to send completion email: {e}")

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

        # Restore window geometry
        self._restore_window_geometry()

        # Start Worker
        self.start_worker()

    def _save_splitter_state(self):
        """Save splitter sizes to config."""
        if 'ui_settings' not in self.config:
            self.config['ui_settings'] = {}

        # Save main splitter sizes
        if hasattr(self, 'main_splitter'):
            self.config['ui_settings']['main_splitter_sizes'] = self.main_splitter.sizes()

        # Save dashboard splitter sizes
        if hasattr(self, 'dashboard_splitter'):
            self.config['ui_settings']['dashboard_splitter_sizes'] = self.dashboard_splitter.sizes()

        # Save to file
        self.config_manager.save_config()

    def _restore_window_geometry(self):
        """Restore window position and size from config."""
        geometry = self.config.get('ui_settings', {}).get('window_geometry', {})
        if geometry:
            x = geometry.get('x', 100)
            y = geometry.get('y', 100)
            width = geometry.get('width', 1400)
            height = geometry.get('height', 900)
            self.setGeometry(x, y, width, height)

    def log_message(self, msg):
        """Log message to Dashboard and Queue Monitor log widgets."""
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        formatted_msg = f"[{ts}] {msg}"

        # Log to dashboard logs
        if hasattr(self, 'dashboard_log_text'):
            self.dashboard_log_text.append(formatted_msg)

        # Log to queue monitor logs
        if hasattr(self, 'queue_log_text'):
            self.queue_log_text.append(formatted_msg)

    def _toggle_all_models(self):
        """Wrapper for toggle_all_models to match signal signature."""
        self.toggle_all_models()

    def toggle_all_models(self):
        """Toggle only downloaded/available model checkboxes on/off."""
        select_all = self.chk_select_all_models.isChecked()

        if select_all:
            # Get available models from Ollama
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    data = response.json()
                    # Extract base model names (handle variants like llama2-uncensored, phi:latest, etc.)
                    available_models = []
                    for model in data.get('models', []):
                        name = model['name'].split(':')[0]  # Remove :latest
                        # Extract base name (handle llama2-uncensored -> llama2, etc.)
                        base_name = name.split('-')[0]  # Get first part before dash
                        available_models.append(name)  # Add full name
                        available_models.append(base_name)  # Add base name

                    # Only check models that are available
                    checked_count = 0
                    for model_name, chk in self.model_checks.items():
                        # Check if model or any variant is available
                        is_available = any(
                            model_name in avail_model or avail_model in model_name
                            for avail_model in available_models
                        )
                        chk.setChecked(is_available)
                        if is_available:
                            checked_count += 1

                    self.log_message(f"Selected {checked_count} available models")
                else:
                    # Ollama not available, show warning
                    QMessageBox.warning(self, "Ollama Not Available",
                                      "Cannot connect to Ollama. Please ensure Ollama is running.")
                    self.chk_select_all_models.setChecked(False)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to get available models: {e}")
                self.chk_select_all_models.setChecked(False)
        else:
            # Deselect all
            for chk in self.model_checks.values():
                chk.setChecked(False)

    def closeEvent(self, event):
        """Save window geometry before closing."""
        if 'ui_settings' not in self.config:
            self.config['ui_settings'] = {}

        # Save window geometry
        geometry = self.geometry()
        self.config['ui_settings']['window_geometry'] = {
            'x': geometry.x(),
            'y': geometry.y(),
            'width': geometry.width(),
            'height': geometry.height()
        }

        # Save splitter states one more time
        self._save_splitter_state()

        # Stop worker thread
        if hasattr(self, 'worker'):
            self.worker.stop()

        event.accept()

    def init_backend(self):
        self.mongo = MongoWrapper(uri=self.config['mongodb']['uri'], database=self.config['mongodb']['db_name'])
        self.sec_client = SECEdgarClient()
        self.aggregator = UnifiedSECProfileAggregator(self.mongo, self.sec_client)
        self.ticker_fetcher = CompanyTickerFetcher()
        
        # Initialize UI state dictionaries
        self.model_checks = {}  # Dictionary to store model checkboxes
        self.feature_checks = {}  # Dictionary to store feature checkboxes
        self.installed_model_list = []  # List of installed Ollama models

        # Processing queue
        self.processing_queue = []  # List of ticker identifiers to process

        self.task_queue = queue.Queue()
        self.worker_signals = WorkerSignals()
        self.worker_signals.progress.connect(self.handle_progress)
        self.worker_signals.ticker_status_changed.connect(self.update_ticker_status)
        self.worker_signals.finished.connect(self.handle_finished)
        self.worker_signals.error.connect(self.handle_error)
        self.worker_signals.stats_updated.connect(self.update_stats_ui)

    def start_worker(self):
        self.worker = EnhancedBackgroundWorker(self.task_queue, self.worker_signals, self.aggregator, self.ticker_fetcher, self.mongo, self.config)
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

        # Make Ollama status clickable
        self.lbl_ollama_status = QPushButton("Ollama: Checking...")
        self.lbl_ollama_status.setFlat(True)
        self.lbl_ollama_status.setObjectName("OllamaStatusButton")  # Add object name for styling
        self.lbl_ollama_status.setCursor(Qt.PointingHandCursor)
        self.lbl_ollama_status.clicked.connect(self.open_model_manager)
        self.lbl_ollama_status.setToolTip("Click to manage Ollama models")

        self.lbl_status = QLabel("Status: Ready")
        self.lbl_status.setStyleSheet("color: #4da6ff; font-weight: bold;")

        top_layout.addWidget(self.lbl_total_companies)
        top_layout.addSpacing(20)
        top_layout.addWidget(self.lbl_profiles_db)
        top_layout.addSpacing(20)
        top_layout.addWidget(self.lbl_ollama_status)
        top_layout.addStretch()
        top_layout.addWidget(self.lbl_status)
        
        main_layout.addWidget(self.top_bar)

        # Check Ollama status
        self._check_ollama_status()

        # Main Content - Tabs only (logs moved to Dashboard and Queue Monitor)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_dashboard_tab(), "Dashboard_Generate")
        self.tabs.addTab(self.create_queue_monitor_tab(), "Queue Monitor")
        self.tabs.addTab(self.create_profiles_tab(), "Profile Manager")
        self.tabs.addTab(self.create_settings_tab(), "Settings")
        
        main_layout.addWidget(self.tabs)

    def create_dashboard_tab(self):
        tab = QWidget()
        layout = QHBoxLayout(tab)

        # Create horizontal splitter for left and right panels
        self.dashboard_splitter = QSplitter(Qt.Horizontal)

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

        # Processing Queue Group
        grp_queue = QGroupBox("Processing Queue")
        queue_layout = QVBoxLayout(grp_queue)

        # Queue info label
        self.lbl_queue_count = QLabel("0 tickers in queue")
        self.lbl_queue_count.setStyleSheet("font-weight: bold; color: #4da6ff;")
        queue_layout.addWidget(self.lbl_queue_count)

        # Queue table (pending items before processing starts)
        self.dashboard_queue_table = QTableWidget()
        self.dashboard_queue_table.setColumnCount(3)
        self.dashboard_queue_table.setHorizontalHeaderLabels(["Ticker", "Status", "Actions"])
        self.dashboard_queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.dashboard_queue_table.setMaximumHeight(200)
        queue_layout.addWidget(self.dashboard_queue_table)

        # Queue action buttons
        queue_btn_layout = QHBoxLayout()

        btn_clear_queue = QPushButton("Clear Queue")
        btn_clear_queue.setObjectName("DangerButton")
        btn_clear_queue.clicked.connect(self.clear_queue)
        queue_btn_layout.addWidget(btn_clear_queue)

        queue_btn_layout.addStretch()

        self.btn_start_processing = QPushButton("🚀 START PROCESSING")
        self.btn_start_processing.setObjectName("SuccessButton")
        self.btn_start_processing.setMinimumHeight(50)
        self.btn_start_processing.setStyleSheet("""
            QPushButton#SuccessButton {
                font-size: 16px;
                font-weight: bold;
            }
        """)
        self.btn_start_processing.clicked.connect(self.start_queue_processing)
        queue_btn_layout.addWidget(self.btn_start_processing)

        queue_layout.addLayout(queue_btn_layout)

        left_layout.addWidget(grp_queue)

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

        # Filing Limit
        h_filing_limit = QHBoxLayout()
        h_filing_limit.addWidget(QLabel("Filing Limit:"))
        self.spin_filing_limit = QSpinBox()
        self.spin_filing_limit.setRange(0, 10000)
        self.spin_filing_limit.setSpecialValueText("All Available")
        filing_limit = self.config.get('profile_settings', {}).get('filing_limit')
        self.spin_filing_limit.setValue(0 if filing_limit is None else filing_limit)
        h_filing_limit.addWidget(self.spin_filing_limit)
        opts_layout.addLayout(h_filing_limit)

        # AI Model Selection - Load from Ollama
        h_ai_model = QHBoxLayout()
        h_ai_model.addWidget(QLabel("Primary AI Model:"))
        self.combo_ai_model = QComboBox()

        # Get installed models from Ollama
        ai_model_list = []
        try:
            from src.utils.ollama_model_manager import OllamaModelManager
            manager = OllamaModelManager()

            if manager.is_ollama_running():
                installed_models = manager.get_installed_models()
                for model in installed_models:
                    full_name = model.get('name', '')
                    # For display, prefer base name unless there are multiple versions
                    if ':' in full_name:
                        base_name = full_name.split(':', 1)[0]
                        ai_model_list.append(full_name)  # Store full name
                    else:
                        ai_model_list.append(full_name)

                # Remove duplicates while preserving order
                seen = set()
                unique_models = []
                for model in ai_model_list:
                    base = model.split(':')[0]
                    if base not in seen:
                        seen.add(base)
                        unique_models.append(base)

                ai_model_list = unique_models

            if not ai_model_list:
                # Fallback to defaults
                ai_model_list = ["llama3.2", "mistral", "llama2", "codellama", "phi", "gemma"]

        except Exception as e:
            logger.error(f"Error loading models for combo box: {e}")
            ai_model_list = ["llama3.2", "mistral", "llama2", "codellama", "phi", "gemma"]

        self.combo_ai_model.addItems(ai_model_list)
        self.combo_ai_model.setToolTip("Primary model for single-model analysis")
        h_ai_model.addWidget(self.combo_ai_model)
        opts_layout.addLayout(h_ai_model)

        # Incremental Update Checkbox
        self.chk_incremental = QCheckBox("Incremental Update (add new data only)")
        self.chk_incremental.setChecked(False)
        self.chk_incremental.setToolTip("If checked, only new filings will be added to existing profiles")
        opts_layout.addWidget(self.chk_incremental)

        # AI Enabled Checkbox
        self.chk_ai_enabled = QCheckBox("Enable AI Analysis")
        self.chk_ai_enabled.setChecked(self.config.get('profile_settings', {}).get('ai_enabled', True))
        self.chk_ai_enabled.setToolTip("Enable multi-model AI analysis of company profiles")
        opts_layout.addWidget(self.chk_ai_enabled)

        # Multi-Model Selection Section
        multi_model_label = QLabel("Multi-Model Analysis (select multiple for consensus):")
        multi_model_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        opts_layout.addWidget(multi_model_label)

        # Load available models from Ollama (with quick timeout to avoid UI freeze)
        try:
            from src.utils.ollama_model_manager import OllamaModelManager
            manager = OllamaModelManager()
            current_model = self.config.get('profile_settings', {}).get('ai_model', 'llama3.2')

            # Quick check - if this takes > 1s, skip and show placeholder
            if manager.is_ollama_running():
                installed_models = manager.get_installed_models()

                if installed_models:
                    # Group models by family
                    model_families = {}
                    for model in installed_models:
                        full_name = model.get('name', '')
                        if ':' in full_name:
                            base_name, tag = full_name.split(':', 1)
                        else:
                            base_name = full_name
                            tag = 'latest'

                        if base_name not in model_families:
                            model_families[base_name] = []
                        model_families[base_name].append({
                            'full_name': full_name,
                            'tag': tag,
                            'size': model.get('size', 0)
                        })

                    # Display checkboxes for each model (limit to first 10 to speed up UI)
                    model_count = 0
                    for base_name, versions in sorted(model_families.items()):
                        if model_count >= 10:  # Limit initial display
                            break

                        if len(versions) == 1 and versions[0]['tag'] == 'latest':
                            # Single version
                            full_name = versions[0]['full_name']
                            size_gb = versions[0]['size'] / (1024**3)
                            chk = QCheckBox(f"{base_name}  ({size_gb:.1f} GB)")
                            chk.setChecked(base_name == current_model or full_name == current_model)
                            chk.setToolTip(f"Model: {full_name}\nSize: {size_gb:.2f} GB")
                            self.model_checks[base_name] = chk
                            self.installed_model_list.append(base_name)
                            opts_layout.addWidget(chk)
                            model_count += 1
                        else:
                            # Multiple versions - show family label
                            family_label = QLabel(f"  {base_name} family:")
                            family_label.setStyleSheet("color: #6c757d; font-size: 11px; font-style: italic;")
                            opts_layout.addWidget(family_label)

                            for version in sorted(versions, key=lambda x: x['tag'])[:3]:  # Limit to 3 versions
                                full_name = version['full_name']
                                tag = version['tag']
                                size_gb = version['size'] / (1024**3)
                                chk = QCheckBox(f"    • {base_name}:{tag}  ({size_gb:.1f} GB)")
                                chk.setChecked(full_name == current_model or (base_name == current_model and tag == 'latest'))
                                chk.setToolTip(f"Model: {full_name}\nSize: {size_gb:.2f} GB")
                                model_key = full_name if tag != 'latest' else base_name
                                self.model_checks[model_key] = chk
                                self.installed_model_list.append(model_key)
                                opts_layout.addWidget(chk)
                                model_count += 1

                    # Summary
                    model_summary = QLabel(f"📊 {len(self.installed_model_list)} model(s) available")
                    model_summary.setStyleSheet("color: #198754; font-size: 11px; font-weight: bold; margin-top: 5px;")
                    opts_layout.addWidget(model_summary)

                    # Select all button
                    self.chk_select_all_models = QCheckBox("✓ Select All Models")
                    self.chk_select_all_models.stateChanged.connect(self._toggle_all_models)
                    opts_layout.addWidget(self.chk_select_all_models)
                else:
                    warning = QLabel("⚠ No models found - install models using Model Manager")
                    warning.setStyleSheet("color: #ffc107; font-size: 11px;")
                    opts_layout.addWidget(warning)
            else:
                warning = QLabel("⚠ Ollama not running - start Ollama to see available models")
                warning.setStyleSheet("color: #ffc107; font-size: 11px;")
                opts_layout.addWidget(warning)

        except Exception as e:
            logger.error(f"Error loading models: {e}")
            # Don't block UI, just show warning
            warning = QLabel("⚠ Error loading models (check logs)")
            warning.setStyleSheet("color: #dc3545; font-size: 11px;")
            opts_layout.addWidget(warning)

        left_layout.addWidget(grp_options)
        left_layout.addStretch()

        # Right Column: Quick Actions
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        grp_quick = QGroupBox("Quick Actions")
        quick_layout = QVBoxLayout(grp_quick)
        
        quick_layout.addWidget(QLabel("Single Identifier:"))
        self.input_ticker = QLineEdit()
        self.input_ticker.setPlaceholderText("Ticker or CIK")
        quick_layout.addWidget(self.input_ticker)

        btn_add_ticker = QPushButton("Add to Queue")
        btn_add_ticker.setObjectName("PrimaryButton")
        btn_add_ticker.clicked.connect(self.add_single_to_queue)
        quick_layout.addWidget(btn_add_ticker)

        quick_layout.addWidget(QLabel("Multiple Identifiers (one per line):"))
        self.input_batch = QTextEdit()
        self.input_batch.setPlaceholderText("AAPL\nMSFT\n0000789019")
        self.input_batch.setMaximumHeight(100)
        quick_layout.addWidget(self.input_batch)

        btn_add_batch = QPushButton("Add Batch to Queue")
        btn_add_batch.setObjectName("PrimaryButton")
        btn_add_batch.clicked.connect(self.add_batch_to_queue)
        quick_layout.addWidget(btn_add_batch)

        quick_layout.addWidget(QLabel("Random Selection:"))
        self.spin_top_n = QSpinBox()
        self.spin_top_n.setRange(1, 500)
        self.spin_top_n.setValue(10)
        quick_layout.addWidget(self.spin_top_n)

        btn_random = QPushButton("Add Random Tickers")
        btn_random.clicked.connect(self.add_top_n_random)
        quick_layout.addWidget(btn_random)

        btn_top_n = QPushButton("Add Top N by Market Cap")
        btn_top_n.clicked.connect(self.add_top_n)
        quick_layout.addWidget(btn_top_n)

        right_layout.addWidget(grp_quick)

        # Pipeline Execution Logs in Dashboard (on right side, below Quick Actions)
        grp_logs = QGroupBox("Pipeline Execution Logs")
        logs_layout = QVBoxLayout(grp_logs)

        self.dashboard_log_text = QTextEdit()
        self.dashboard_log_text.setReadOnly(True)
        self.dashboard_log_text.setMaximumHeight(200)
        logs_layout.addWidget(self.dashboard_log_text)

        btn_clear_logs = QPushButton("Clear Logs")
        btn_clear_logs.setObjectName("SecondaryButton")
        btn_clear_logs.clicked.connect(self.dashboard_log_text.clear)
        logs_layout.addWidget(btn_clear_logs, alignment=Qt.AlignRight)

        right_layout.addWidget(grp_logs)
        right_layout.addStretch()

        # Add panels to splitter
        self.dashboard_splitter.addWidget(left_panel)
        self.dashboard_splitter.addWidget(right_panel)

        # Restore splitter sizes if available
        saved_sizes = self.config.get('ui_settings', {}).get('dashboard_splitter_sizes', [])
        if saved_sizes:
            self.dashboard_splitter.setSizes(saved_sizes)
        else:
            # Default split: 60% left, 40% right
            total_width = self.dashboard_splitter.width()
            self.dashboard_splitter.setSizes([int(total_width * 0.6), int(total_width * 0.4)])

        layout.addWidget(self.dashboard_splitter)
        return tab

    def create_queue_monitor_tab(self):
        """Create the queue monitor tab with controls and queue table."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Controls
        ctrl_layout = QHBoxLayout()

        btn_resume = QPushButton("Resume Selected")
        btn_resume.setObjectName("SuccessButton")
        btn_resume.clicked.connect(self.resume_selected_ticker)
        ctrl_layout.addWidget(btn_resume)
        btn_cancel = QPushButton("Cancel Selected")
        btn_cancel.setObjectName("DangerButton")
        btn_cancel.clicked.connect(self.cancel_selected_ticker)
        ctrl_layout.addWidget(btn_cancel)
        
        btn_cancel_all = QPushButton("Cancel All")
        btn_cancel_all.setObjectName("DangerButton")
        btn_cancel_all.clicked.connect(self.cancel_all_tickers)
        ctrl_layout.addWidget(btn_cancel_all)

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

        # Pipeline Execution Logs in Queue Monitor
        queue_logs_group = QGroupBox("Pipeline Execution Logs")
        queue_logs_layout = QVBoxLayout(queue_logs_group)
        self.queue_log_text = QTextEdit()
        self.queue_log_text.setReadOnly(True)
        self.queue_log_text.setMinimumHeight(150)
        queue_logs_layout.addWidget(self.queue_log_text)

        btn_clear_queue_logs = QPushButton("Clear Logs")
        btn_clear_queue_logs.setObjectName("SecondaryButton")
        btn_clear_queue_logs.clicked.connect(self.queue_log_text.clear)
        queue_logs_layout.addWidget(btn_clear_queue_logs, alignment=Qt.AlignRight)

        layout.addWidget(queue_logs_group)

        return tab

    def create_profiles_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Search Bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.profile_search = QLineEdit()
        self.profile_search.setPlaceholderText("Search by Ticker, Name, or CIK...")
        self.profile_search.textChanged.connect(self.filter_profiles)
        search_layout.addWidget(self.profile_search)

        btn_clear_search = QPushButton("Clear")
        btn_clear_search.setObjectName("SecondaryButton")
        btn_clear_search.clicked.connect(lambda: self.profile_search.clear())
        search_layout.addWidget(btn_clear_search)
        layout.addLayout(search_layout)

        # Selection Mode Toggle
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Selection Mode:"))
        self.chk_multi_select = QCheckBox("Enable Multi-Select (Batch Operations)")
        self.chk_multi_select.setChecked(False)  # Start in single-select mode
        self.chk_multi_select.stateChanged.connect(self.toggle_selection_mode)
        mode_layout.addWidget(self.chk_multi_select)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)

        # Controls
        ctrl_layout = QHBoxLayout()
        self.btn_refresh_profiles = QPushButton("Refresh List")
        self.btn_refresh_profiles.clicked.connect(self.load_profiles)
        ctrl_layout.addWidget(self.btn_refresh_profiles)
        
        self.btn_find_problematic = QPushButton("Find Problematic Profiles")
        self.btn_find_problematic.setObjectName("WarningButton")
        self.btn_find_problematic.clicked.connect(self.find_problematic_profiles)
        ctrl_layout.addWidget(self.btn_find_problematic)

        self.btn_view_profile = QPushButton("View Selected")
        self.btn_view_profile.setObjectName("SecondaryButton")
        self.btn_view_profile.clicked.connect(self.view_profile)
        ctrl_layout.addWidget(self.btn_view_profile)
        
        self.btn_edit_profile = QPushButton("Edit Selected")
        self.btn_edit_profile.setObjectName("SecondaryButton")
        self.btn_edit_profile.clicked.connect(self.edit_profile)
        ctrl_layout.addWidget(self.btn_edit_profile)
        
        self.btn_edit_period = QPushButton("Edit Period")
        self.btn_edit_period.setObjectName("SecondaryButton")
        self.btn_edit_period.clicked.connect(self.edit_profile_period)
        ctrl_layout.addWidget(self.btn_edit_period)

        self.btn_visualize_profile = QPushButton("Visualize Selected")
        self.btn_visualize_profile.setObjectName("SuccessButton")
        self.btn_visualize_profile.clicked.connect(self.visualize_profile)
        ctrl_layout.addWidget(self.btn_visualize_profile)
        
        self.btn_delete_profile = QPushButton("Delete Selected")
        self.btn_delete_profile.setObjectName("DangerButton")
        self.btn_delete_profile.clicked.connect(self.delete_profile)
        ctrl_layout.addWidget(self.btn_delete_profile)

        self.btn_clear_selection = QPushButton("Clear Selection")
        self.btn_clear_selection.setObjectName("SecondaryButton")
        self.btn_clear_selection.clicked.connect(self.clear_profile_selection)
        ctrl_layout.addWidget(self.btn_clear_selection)

        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        # Table
        self.profiles_table = QTableWidget()
        self.profiles_table.setColumnCount(6)
        self.profiles_table.setHorizontalHeaderLabels(["Ticker", "Name", "CIK", "Last Generated", "Period From", "Period To"])
        self.profiles_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.profiles_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.profiles_table.setSelectionMode(QTableWidget.SingleSelection)  # Start in single-select mode
        self.profiles_table.doubleClicked.connect(self.visualize_profile_and_clear)  # Double-click to visualize
        layout.addWidget(self.profiles_table)

        # Store the multi-select preference
        self.multi_select_mode = False

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

        # AI Model Management
        grp_ai = QGroupBox("AI Model Management")
        ai_layout = QVBoxLayout(grp_ai)

        ai_desc = QLabel("Manage Ollama models for AI analysis")
        ai_layout.addWidget(ai_desc)

        btn_manage_models = QPushButton("Manage Ollama Models")
        btn_manage_models.setObjectName("SuccessButton")
        btn_manage_models.clicked.connect(self.open_model_manager)
        ai_layout.addWidget(btn_manage_models)

        layout.addWidget(grp_ai)

        # Email Notifications
        grp_email = QGroupBox("Email Notifications")
        email_layout = QVBoxLayout(grp_email)

        self.chk_email_enabled = QCheckBox("Enable Email Notifications")
        self.chk_email_enabled.setChecked(self.config.get('email_notifications', {}).get('enabled', False))
        email_layout.addWidget(self.chk_email_enabled)

        # SMTP Settings
        smtp_layout = QVBoxLayout()

        h_server = QHBoxLayout()
        h_server.addWidget(QLabel("SMTP Server:"))
        self.input_smtp_server = QLineEdit(self.config.get('email_notifications', {}).get('smtp_server', 'smtp.gmail.com'))
        h_server.addWidget(self.input_smtp_server)
        h_server.addWidget(QLabel("Port:"))
        self.input_smtp_port = QSpinBox()
        self.input_smtp_port.setRange(1, 65535)
        self.input_smtp_port.setValue(self.config.get('email_notifications', {}).get('smtp_port', 587))
        self.input_smtp_port.setMaximumWidth(80)
        h_server.addWidget(self.input_smtp_port)
        smtp_layout.addLayout(h_server)

        smtp_layout.addWidget(QLabel("Sender Email:"))
        self.input_sender_email = QLineEdit(self.config.get('email_notifications', {}).get('sender_email', ''))
        self.input_sender_email.setPlaceholderText("your-email@gmail.com")
        smtp_layout.addWidget(self.input_sender_email)

        smtp_layout.addWidget(QLabel("Sender Password (App Password for Gmail):"))
        self.input_sender_password = QLineEdit(self.config.get('email_notifications', {}).get('sender_password', ''))
        self.input_sender_password.setEchoMode(QLineEdit.Password)
        self.input_sender_password.setPlaceholderText("xxxx-xxxx-xxxx-xxxx")
        smtp_layout.addWidget(self.input_sender_password)

        smtp_layout.addWidget(QLabel("Recipient Email:"))
        self.input_recipient_email = QLineEdit(self.config.get('email_notifications', {}).get('recipient_email', ''))
        self.input_recipient_email.setPlaceholderText("notifications@example.com")
        smtp_layout.addWidget(self.input_recipient_email)

        email_layout.addLayout(smtp_layout)

        # Alert Preferences
        email_layout.addWidget(QLabel("Send Alerts For:"))
        self.chk_alert_complete = QCheckBox("Batch Processing Completion")
        self.chk_alert_complete.setChecked(self.config.get('email_notifications', {}).get('alert_on_complete', True))
        email_layout.addWidget(self.chk_alert_complete)

        self.chk_alert_error = QCheckBox("Critical Errors")
        self.chk_alert_error.setChecked(self.config.get('email_notifications', {}).get('alert_on_error', True))
        email_layout.addWidget(self.chk_alert_error)

        self.chk_alert_ticker_failed = QCheckBox("Individual Ticker Failures")
        self.chk_alert_ticker_failed.setChecked(self.config.get('email_notifications', {}).get('alert_on_ticker_failed', False))
        email_layout.addWidget(self.chk_alert_ticker_failed)

        # Test email button
        btn_test_email = QPushButton("Test Email Configuration")
        btn_test_email.setObjectName("SecondaryButton")
        btn_test_email.clicked.connect(self.test_email_config)
        email_layout.addWidget(btn_test_email)

        layout.addWidget(grp_email)

        # Save settings button
        btn_save = QPushButton("Save Settings")
        btn_save.clicked.connect(self.save_settings)
        layout.addWidget(btn_save)

        layout.addStretch()

        return tab

    def apply_styles(self):
        self.setStyleSheet(DARK_STYLESHEET)

    # --- Logic ---

    def _show_confirmation_dialog(self, tickers: List[str]) -> bool:
        """Show confirmation dialog with all processing parameters."""
        opts = self.get_options_from_ui()

        filing_limit = opts.get('filing_limit')
        filing_limit_text = "All Available" if filing_limit is None else str(filing_limit)

        # Get selected AI models
        ai_models = opts.get('ai_models', [])
        ai_models_text = ', '.join(ai_models) if ai_models else self.combo_ai_model.currentText()

        # Quick check for AI models - non-blocking
        ai_warning = ""
        if opts.get('ai_enabled'):
            # Don't block UI with model checking - just show basic info
            ai_warning = f"""
<p style="color: #4da6ff;">ℹ️ AI Analysis Enabled</p>
<p style="color: #4da6ff;">Models: {ai_models_text}</p>
<p style="color: #888; font-size: 11px;">Model availability will be verified during processing</p>
"""

        msg = f"""
<h3>Confirm Profile Generation</h3>
<p>You are about to process <b>{len(tickers)}</b> ticker(s):</p>
<p><b>{', '.join(tickers[:10])}</b>{'...' if len(tickers) > 10 else ''}</p>

<h4>Parameters:</h4>
<ul>
<li><b>Lookback Years:</b> {opts.get('lookback_years')}</li>
<li><b>Filing Limit:</b> {filing_limit_text}</li>
<li><b>AI Models:</b> {ai_models_text}</li>
<li><b>AI Analysis:</b> {'Enabled' if opts.get('ai_enabled') else 'Disabled'}</li>
<li><b>Incremental Update:</b> {'Yes' if opts.get('incremental') else 'No'}</li>
<li><b>Database:</b> {self.config['mongodb']['db_name']}</li>
<li><b>Collection:</b> {self.config['collections']['profiles']}</li>
</ul>

{ai_warning}

<p>Do you want to proceed?</p>
        """

        dlg = QMessageBox(self)
        dlg.setWindowTitle("Confirm Processing")
        dlg.setTextFormat(Qt.RichText)
        dlg.setText(msg)
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dlg.setDefaultButton(QMessageBox.Yes)
        dlg.setIcon(QMessageBox.Question)

        # Make dialog application modal to prevent clicks underneath
        dlg.setModal(True)

        return dlg.exec() == QMessageBox.Yes

        msg = f"""
<h3>Confirm Profile Generation</h3>
<p>You are about to process <b>{len(tickers)}</b> ticker(s):</p>
<p><b>{', '.join(tickers[:10])}</b>{'...' if len(tickers) > 10 else ''}</p>

<h4>Parameters:</h4>
<ul>
<li><b>Lookback Years:</b> {opts.get('lookback_years')}</li>
<li><b>Filing Limit:</b> {filing_limit_text}</li>
<li><b>AI Models:</b> {ai_models_text}</li>
<li><b>AI Analysis:</b> {'Enabled' if opts.get('ai_enabled') else 'Disabled'}</li>
<li><b>Incremental Update:</b> {'Yes' if opts.get('incremental') else 'No'}</li>
<li><b>Database:</b> {self.config['mongodb']['db_name']}</li>
<li><b>Collection:</b> {self.config['collections']['profiles']}</li>
</ul>

{ai_warning}

<p>Do you want to proceed?</p>
        """

        dlg = QMessageBox(self)
        dlg.setWindowTitle("Confirm Processing")
        dlg.setTextFormat(Qt.RichText)
        dlg.setText(msg)
        dlg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        dlg.setDefaultButton(QMessageBox.Yes)
        dlg.setIcon(QMessageBox.Question)

        return dlg.exec() == QMessageBox.Yes

    def get_options_from_ui(self):
        filing_limit_value = self.spin_filing_limit.value()
        opts = {
            'lookback_years': self.spin_lookback.value(),
            'filing_limit': None if filing_limit_value == 0 else filing_limit_value,
            'incremental': self.chk_incremental.isChecked(),
            'ai_enabled': self.chk_ai_enabled.isChecked(),
            'config': self.config  # Pass full config for AI analyzer
        }
        # Update config with selected AI model
        if 'profile_settings' not in self.config:
            self.config['profile_settings'] = {}
        self.config['profile_settings']['ai_model'] = self.combo_ai_model.currentText()

        # Get selected models for multi-model analysis
        selected_models = [model for model, chk in self.model_checks.items() if chk.isChecked()]
        if len(selected_models) > 1:
            opts['ai_models'] = selected_models  # Multiple models selected
            self.log_message(f"Multi-model analysis enabled: {', '.join(selected_models)}")
        elif len(selected_models) == 1:
            opts['ai_models'] = selected_models  # Single model
        # else: use default from combo_ai_model

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
            # Show confirmation dialog with parameters
            if not self._show_confirmation_dialog(tickers):
                return

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

        # Show confirmation dialog
        if not self._show_confirmation_dialog([ident]):
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

        # Show confirmation dialog
        if not self._show_confirmation_dialog(idents):
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
                # Add to processing queue (not immediate processing)
                added = 0
                for ticker in tickers:
                    ticker = ticker.upper()  # Normalize to uppercase
                    if ticker not in self.processing_queue:
                        self.processing_queue.append(ticker)
                        added += 1

                self._update_queue_table()
                self.lbl_status.setText(f"Added {added} random tickers to queue (skipped {len(tickers) - added} duplicates)")
                self.log_message(f"Added {added} random tickers to queue")
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
                # Add to processing queue (not immediate processing)
                added = 0
                for ticker in tickers:
                    ticker = ticker.upper()  # Normalize to uppercase
                    if ticker not in self.processing_queue:
                        self.processing_queue.append(ticker)
                        added += 1

                self._update_queue_table()
                self.lbl_status.setText(f"Added {added} top tickers to queue (skipped {len(tickers) - added} duplicates)")
                self.log_message(f"Added {added} top tickers to queue: {', '.join(tickers[:5])}...")
            else:
                QMessageBox.warning(self, "Error", "Could not extract tickers from top companies.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to select top tickers: {e}")
            logger.exception("Error selecting top tickers")

    def pause_selected_ticker(self):
        """Pause the selected ticker in queue."""
        selected_rows = self.queue_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "No Selection", "Please select a ticker from the queue to pause.")
            return
        
        ticker = self.queue_table.item(selected_rows[0].row(), 0).text()
        status = self.queue_table.item(selected_rows[0].row(), 1).text()

        if status == TickerStatus.RUNNING.value:
            self.task_queue.put({'action': 'pause_ticker', 'ticker': ticker})
            self.log_message(f"Pausing {ticker}...")
        else:
            QMessageBox.information(self, "Cannot Pause", f"{ticker} is not currently running (Status: {status})")

    # New Queue Management Methods

    def add_single_to_queue(self):
        """Add single ticker to processing queue without starting."""
        ident = self.input_ticker.text().strip().upper()  # Normalize to uppercase
        if not ident:
            QMessageBox.warning(self, "Input Error", "Please enter a ticker or CIK.")
            return

        if ident not in self.processing_queue:
            self.processing_queue.append(ident)
            self._update_queue_table()
            self.input_ticker.clear()
            self.log_message(f"Added {ident} to queue")
        else:
            QMessageBox.information(self, "Already in Queue", f"{ident} is already in the processing queue.")

    def add_batch_to_queue(self):
        """Add batch of tickers to processing queue without starting."""
        text = self.input_batch.toPlainText()
        idents = [x.strip().upper() for x in text.replace('\n', ',').split(',') if x.strip()]  # Normalize to uppercase

        if not idents:
            QMessageBox.warning(self, "Input Error", "Please enter at least one identifier.")
            return

        added = 0
        for ident in idents:
            if ident not in self.processing_queue:
                self.processing_queue.append(ident)
                added += 1

        self._update_queue_table()
        self.input_batch.clear()
        self.log_message(f"Added {added} ticker(s) to queue (skipped {len(idents) - added} duplicates)")

    def add_selected_to_queue(self):
        """Add selected tickers from search results to queue."""
        selected_rows = self.search_results.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one ticker from search results.")
            return

        added = 0
        for row in selected_rows:
            ticker = self.search_results.item(row.row(), 0).text().upper()  # Normalize to uppercase
            if ticker not in self.processing_queue:
                self.processing_queue.append(ticker)
                added += 1

        self._update_queue_table()
        self.log_message(f"Added {added} ticker(s) to queue")

    def remove_from_queue(self, ticker):
        """Remove a ticker from the processing queue."""
        if ticker in self.processing_queue:
            self.processing_queue.remove(ticker)
            self._update_queue_table()
            self.log_message(f"Removed {ticker} from queue")

    def clear_queue(self):
        """Clear all tickers from processing queue."""
        if not self.processing_queue:
            return

        reply = QMessageBox.question(
            self,
            "Clear Queue",
            f"Clear all {len(self.processing_queue)} ticker(s) from the queue?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.processing_queue.clear()
            self._update_queue_table()
            self.log_message("Processing queue cleared")

    def start_queue_processing(self):
        """Start processing all tickers in the queue."""
        if not self.processing_queue:
            QMessageBox.warning(self, "Empty Queue", "No tickers in the processing queue.")
            return

        # Disable the button immediately to prevent double-clicks
        self.btn_start_processing.setEnabled(False)
        self.btn_start_processing.setText("Starting...")

        # Process pending events to update UI immediately
        QApplication.processEvents()

        # Show confirmation dialog
        confirmed = self._show_confirmation_dialog(self.processing_queue)

        # Re-enable button
        self.btn_start_processing.setText("Start Processing")
        self.btn_start_processing.setEnabled(len(self.processing_queue) > 0)

        if not confirmed:
            return

        # Mark all as processing
        for ticker in self.processing_queue:
            self._add_ticker_to_queue_table(ticker, TickerStatus.QUEUED.value)

        # Switch to Queue Monitor tab
        self.tabs.setCurrentIndex(1)  # Queue Monitor is tab index 1

        # Start processing
        self.task_queue.put({
            'action': 'generate_profiles',
            'identifiers': self.processing_queue.copy(),
            'options': self.get_options_from_ui(),
            'collection': self.config['collections']['profiles']
        })

        self.lbl_status.setText(f"Processing {len(self.processing_queue)} tickers...")
        self.log_message(f"Started processing {len(self.processing_queue)} tickers from queue")

        # Clear the queue after starting
        self.processing_queue.clear()
        self._update_queue_table()

    def _update_queue_table(self):
        """Update the dashboard queue table to show current queue status."""
        self.dashboard_queue_table.setRowCount(0)

        for ticker in self.processing_queue:
            row = self.dashboard_queue_table.rowCount()
            self.dashboard_queue_table.insertRow(row)

            # Ticker
            self.dashboard_queue_table.setItem(row, 0, QTableWidgetItem(ticker))

            # Status
            status_item = QTableWidgetItem("Queued")
            status_item.setForeground(QColor("#ffc107"))  # Orange
            self.dashboard_queue_table.setItem(row, 1, status_item)

            # Remove button
            btn_remove = QPushButton("Remove")
            btn_remove.setObjectName("DangerButton")
            btn_remove.clicked.connect(lambda checked, t=ticker: self.remove_from_queue(t))
            self.dashboard_queue_table.setCellWidget(row, 2, btn_remove)

        # Update count label
        count = len(self.processing_queue)
        self.lbl_queue_count.setText(f"{count} ticker{'s' if count != 1 else ''} in queue")

        # Enable/disable start button
        self.btn_start_processing.setEnabled(count > 0)

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
            QMessageBox.information(self, "No Selection", "Please select a ticker from the queue to cancel.")
            return
        
        row = selected_rows[0].row()
        ticker = self.queue_table.item(row, 0).text()
        status = self.queue_table.item(row, 1).text()

        # Immediate cancellation without confirmation for better UX
        # Send cancel signal to worker
        self.task_queue.put({'action': 'cancel_ticker', 'ticker': ticker})

        # Update UI immediately
        status_item = self.queue_table.item(row, 1)
        if status_item:
            status_item.setText(TickerStatus.CANCELLED.value)
            status_item.setForeground(QColor("#6c757d"))  # Gray

        progress_item = self.queue_table.item(row, 2)
        if progress_item:
            progress_item.setText("0%")

        self.log_message(f"Cancelling {ticker}...")

    def cancel_all_tickers(self):
        """Cancel all tickers in the queue."""
        if self.queue_table.rowCount() == 0:
            QMessageBox.information(self, "Empty Queue", "No tickers to cancel.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Cancel All",
            f"Are you sure you want to cancel all {self.queue_table.rowCount()} ticker(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # Send cancel all signal
            self.task_queue.put({'action': 'cancel_all'})

            # Update all rows in UI
            for row in range(self.queue_table.rowCount()):
                ticker = self.queue_table.item(row, 0).text()
                status = self.queue_table.item(row, 1).text()

                # Only cancel if not already completed or failed
                if status not in [TickerStatus.COMPLETED.value, TickerStatus.FAILED.value]:
                    status_item = self.queue_table.item(row, 1)
                    if status_item:
                        status_item.setText(TickerStatus.CANCELLED.value)
                        status_item.setForeground(QColor("#6c757d"))  # Gray

                    progress_item = self.queue_table.item(row, 2)
                    if progress_item:
                        progress_item.setText("0%")

            self.log_message(f"Cancelling all {self.queue_table.rowCount()} tickers...")

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
                meta = p.get('filing_metadata', {})

                self.profiles_table.setItem(row, 0, QTableWidgetItem(info.get('ticker', 'N/A')))
                self.profiles_table.setItem(row, 1, QTableWidgetItem(info.get('name', 'N/A')))
                self.profiles_table.setItem(row, 2, QTableWidgetItem(str(p.get('cik', 'N/A'))))
                self.profiles_table.setItem(row, 3, QTableWidgetItem(str(p.get('generated_at', ''))[:19]))
                
                # Add period information
                oldest_filing = meta.get('oldest_filing', 'N/A')
                most_recent = meta.get('most_recent_filing', 'N/A')
                self.profiles_table.setItem(row, 4, QTableWidgetItem(str(oldest_filing)[:10]))
                self.profiles_table.setItem(row, 5, QTableWidgetItem(str(most_recent)[:10]))

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
        
        # Auto-clear selection in single-select mode
        if not self.multi_select_mode:
            self.profiles_table.clearSelection()

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
        
        # Auto-clear selection in single-select mode
        if not self.multi_select_mode:
            self.profiles_table.clearSelection()

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

    def edit_profile_period(self):
        """Open dialog to edit profile period and regenerate."""
        rows = self.profiles_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "No Selection", "Please select a profile to edit period.")
            return

        row = rows[0].row()
        ticker = self.profiles_table.item(row, 0).text()
        cik = self.profiles_table.item(row, 2).text()
        period_from = self.profiles_table.item(row, 4).text() if self.profiles_table.item(row, 4) else "1995-01-01"
        period_to = self.profiles_table.item(row, 5).text() if self.profiles_table.item(row, 5) else "2025-12-03"

        try:
            from src.ui.profile_period_editor import ProfilePeriodEditorDialog

            dialog = ProfilePeriodEditorDialog(ticker, cik, period_from, period_to, self)
            dialog.period_updated.connect(self.handle_period_update)
            dialog.exec()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open period editor: {e}")
            logger.exception("Error opening period editor")

    def handle_period_update(self, ticker, from_date, to_date, incremental):
        """Handle profile period update request."""
        self.log_message(f"Updating profile period for {ticker}: {from_date} to {to_date} ({'incremental' if incremental else 'full'})")

        # Calculate lookback years from dates
        from datetime import datetime
        try:
            from_dt = datetime.strptime(from_date, "%Y-%m-%d")
            to_dt = datetime.strptime(to_date, "%Y-%m-%d")
            lookback_years = (to_dt - from_dt).days // 365
        except:
            lookback_years = 10

        # Get current options and override period-specific ones
        options = self.get_options_from_ui()
        options['lookback_years'] = max(1, lookback_years)
        options['incremental'] = incremental

        # Add to queue and process
        self.task_queue.put({
            'action': 'generate_profiles',
            'identifiers': [ticker],
            'options': options,
            'collection': self.config['collections']['profiles']
        })

        self.lbl_status.setText(f"Updating profile for {ticker} ({from_date} to {to_date})")
        QMessageBox.information(self, "Profile Update Started",
                              f"Profile update for {ticker} has been queued.\n\n"
                              f"Period: {from_date} to {to_date}\n"
                              f"Mode: {'Incremental' if incremental else 'Full Regeneration'}")

    def toggle_selection_mode(self):
        """Toggle between single-select and multi-select modes."""
        self.multi_select_mode = self.chk_multi_select.isChecked()

        if self.multi_select_mode:
            self.profiles_table.setSelectionMode(QTableWidget.MultiSelection)
            self.log_message("Profile Manager: Switched to Multi-Select mode (batch operations enabled)")
        else:
            self.profiles_table.setSelectionMode(QTableWidget.SingleSelection)
            self.profiles_table.clearSelection()  # Clear any previous selections
            self.log_message("Profile Manager: Switched to Single-Select mode (auto-clear after action)")

    def filter_profiles(self):
        """Filter profiles table based on search text."""
        search_text = self.profile_search.text().lower()

        for row in range(self.profiles_table.rowCount()):
            should_show = False

            if not search_text:
                should_show = True
            else:
                # Search in Ticker, Name, and CIK columns
                for col in [0, 1, 2]:  # Ticker, Name, CIK
                    item = self.profiles_table.item(row, col)
                    if item and search_text in item.text().lower():
                        should_show = True
                        break

            self.profiles_table.setRowHidden(row, not should_show)

    def find_problematic_profiles(self):
        """Find and display profiles with issues (incomplete, missing data, etc.)."""
        col_name = self.config['collections']['profiles']

        try:
            # Fetch all profiles using find() instead of find_all()
            all_profiles = self.mongo.find(col_name, {})

            if not all_profiles:
                QMessageBox.information(self, "No Profiles", "No profiles found in the database.")
                return

            problematic = []

            for profile in all_profiles:
                issues = []
                ticker = profile.get('company_info', {}).get('ticker', 'Unknown')
                cik = profile.get('cik', 'Unknown')

                # Check for missing financial data
                financials = profile.get('financial_data', {})
                if not financials or len(financials) == 0:
                    issues.append("No financial data")
                elif len(financials) < 3:
                    issues.append(f"Limited financial data ({len(financials)} metrics)")

                # Check for N/A or missing key metrics
                for key in ['Revenues', 'Assets', 'NetIncomeLoss']:
                    if key in financials:
                        data_points = financials[key]
                        if not data_points or len(data_points) == 0:
                            issues.append(f"Missing {key}")
                        elif len(data_points) < 4:
                            issues.append(f"Insufficient {key} data ({len(data_points)} periods)")

                # Check AI analysis quality
                ai_analysis = profile.get('ai_analysis', {})
                if not ai_analysis:
                    issues.append("Missing AI analysis")
                else:
                    consensus = ai_analysis.get('consensus_analysis', {})
                    if not consensus or consensus.get('investment_thesis', 'N/A') == 'N/A':
                        issues.append("Poor AI analysis quality")

                # Check for missing governance data
                governance = profile.get('governance', {})
                if not governance or governance.get('total_proxy_count', 0) == 0:
                    issues.append("No governance data")

                # Check for missing insider trading data
                insider_trading = profile.get('insider_trading', {})
                if not insider_trading or insider_trading.get('total_form4_count', 0) == 0:
                    issues.append("No insider trading data")

                if issues:
                    problematic.append({
                        'ticker': ticker,
                        'cik': cik,
                        'issues': issues
                    })

            if not problematic:
                QMessageBox.information(self, "All Good!",
                                       f"All {len(all_profiles)} profiles appear to be complete and healthy.")
                return

            # Display problematic profiles
            msg = f"Found {len(problematic)} problematic profile(s) out of {len(all_profiles)} total:\n\n"

            for item in problematic[:10]:  # Show first 10
                msg += f"• {item['ticker']} (CIK: {item['cik']})\n"
                msg += f"  Issues: {', '.join(item['issues'][:3])}\n\n"

            if len(problematic) > 10:
                msg += f"...and {len(problematic) - 10} more\n\n"

            msg += "\nWould you like to retry these profiles?"

            result = QMessageBox.question(self, "Problematic Profiles Found", msg,
                                         QMessageBox.Yes | QMessageBox.No)

            if result == QMessageBox.Yes:
                # Queue retry for problematic profiles
                tickers = [p['ticker'] for p in problematic if p['ticker'] != 'Unknown']

                if tickers:
                    self.log_message(f"Queuing retry for {len(tickers)} problematic profiles...")

                    # Get options from profile settings
                    options = {
                        'lookback_years': self.config.get('profile_settings', {}).get('lookback_years', 10),
                        'filing_limit': self.config.get('profile_settings', {}).get('filing_limit'),
                        'incremental': False,  # Full regeneration for problematic profiles
                        'ai_enabled': self.config.get('profile_settings', {}).get('ai_enabled', True),
                        'config': self.config
                    }

                    self.task_queue.put({
                        'action': 'generate_profiles',
                        'identifiers': tickers,
                        'options': options,
                        'collection': self.config['collections']['profiles']
                    })

                    QMessageBox.information(self, "Retry Queued",
                                           f"Queued {len(tickers)} profiles for regeneration.")

        except Exception as e:
            logger.exception("Error finding problematic profiles")
            QMessageBox.critical(self, "Error", f"Failed to analyze profiles: {e}")

    def clear_profile_selection(self):
        """Manually clear the current profile selection."""
        self.profiles_table.clearSelection()
        self.log_message("Profile selection cleared")

    def visualize_profile_and_clear(self):
        """Visualize profile and auto-clear selection if in single-select mode."""
        self.visualize_profile()
        if not self.multi_select_mode:
            self.profiles_table.clearSelection()

    def visualize_profile(self):
        """Open visualization window for selected profile(s)."""
        rows = self.profiles_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one profile to visualize.")
            return
        
        col_name = self.config['collections']['profiles']

        # Visualize each selected profile
        for row in rows:
            cik = self.profiles_table.item(row.row(), 2).text()
            profile = self.mongo.find_one(col_name, {'cik': cik})

            if not profile:
                QMessageBox.warning(self, "Not Found", f"Profile for CIK {cik} not found.")
                continue

            try:
                from src.ui.visualization_window import ProfileVisualizationWindow
                viz_window = ProfileVisualizationWindow(profile, self.config, self)
                viz_window.exec()
            except Exception as e:
                QMessageBox.critical(self, "Visualization Error", f"Failed to open visualization for {cik}: {e}")
                logger.exception("Visualization error")

        # Auto-clear selection in single-select mode
        if not self.multi_select_mode:
            self.profiles_table.clearSelection()

    def delete_profile(self):
        """Delete selected profile(s)."""
        rows = self.profiles_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one profile to delete.")
            return

        # Get all selected CIKs
        ciks = [self.profiles_table.item(row.row(), 2).text() for row in rows]

        # Confirm deletion
        if len(ciks) == 1:
            msg = f"Delete profile for {ciks[0]}?"
        else:
            msg = f"Delete {len(ciks)} selected profiles?\n\n" + ", ".join(ciks[:5])
            if len(ciks) > 5:
                msg += f"\n...and {len(ciks) - 5} more"

        if QMessageBox.question(self, "Confirm Deletion", msg,
                              QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            col_name = self.config['collections']['profiles']
            deleted = 0
            for cik in ciks:
                try:
                    self.mongo.delete_one(col_name, {'cik': cik})
                    self.log_message(f"Deleted profile {cik}")
                    deleted += 1
                except Exception as e:
                    logger.exception(f"Error deleting profile {cik}")

            QMessageBox.information(self, "Deletion Complete", f"Deleted {deleted} profile(s).")
            self.load_profiles()
            
            # Auto-clear selection in single-select mode
            if not self.multi_select_mode:
                self.profiles_table.clearSelection()

    def save_settings(self):
        self.config['mongodb']['uri'] = self.input_mongo_uri.text()
        self.config['mongodb']['db_name'] = self.input_mongo_db.text()

        # Save email settings
        if 'email_notifications' not in self.config:
            self.config['email_notifications'] = {}

        self.config['email_notifications']['enabled'] = self.chk_email_enabled.isChecked()
        self.config['email_notifications']['smtp_server'] = self.input_smtp_server.text()
        self.config['email_notifications']['smtp_port'] = self.input_smtp_port.value()
        self.config['email_notifications']['sender_email'] = self.input_sender_email.text()
        self.config['email_notifications']['sender_password'] = self.input_sender_password.text()
        self.config['email_notifications']['recipient_email'] = self.input_recipient_email.text()
        self.config['email_notifications']['alert_on_complete'] = self.chk_alert_complete.isChecked()
        self.config['email_notifications']['alert_on_error'] = self.chk_alert_error.isChecked()
        self.config['email_notifications']['alert_on_ticker_failed'] = self.chk_alert_ticker_failed.isChecked()

        self.config_manager.save_config()
        QMessageBox.information(self, "Saved", "Settings saved successfully. Email notifications will be used in next processing batch.")

    def test_email_config(self):
        """Test email configuration by sending a test email."""
        try:
            from src.utils.email_notifier import EmailNotifier

            # Create temporary config with current UI values
            test_config = {
                'email_notifications': {
                    'enabled': self.chk_email_enabled.isChecked(),
                    'smtp_server': self.input_smtp_server.text(),
                    'smtp_port': self.input_smtp_port.value(),
                    'sender_email': self.input_sender_email.text(),
                    'sender_password': self.input_sender_password.text(),
                    'recipient_email': self.input_recipient_email.text(),
                    'alert_on_complete': True,
                    'alert_on_error': True,
                    'alert_on_ticker_failed': False
                }
            }

            notifier = EmailNotifier(test_config)

            # Test connection
            self.log_message("Testing email connection...")
            success, message = notifier.test_connection()

            if success:
                self.log_message("✓ Email connection successful!")

                # Send test email
                test_results = {
                    'total': 3,
                    'successful': 2,
                    'failed': 1,
                    'tickers': ['AAPL', 'MSFT'],
                    'failed_tickers': ['TEST'],
                    'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'end_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': '0:05:30',
                    'database': 'Entities',
                    'collection': 'profiles'
                }

                notifier.send_completion_report(test_results)
                self.log_message("✓ Test email sent!")
                QMessageBox.information(self, "Success",
                    "Email configuration is working!\n\n"
                    "A test completion report has been sent to:\n"
                    f"{self.input_recipient_email.text()}\n\n"
                    "Check your inbox (and spam folder).")
            else:
                self.log_message(f"✗ Email connection failed: {message}")
                QMessageBox.warning(self, "Connection Failed",
                    f"Could not connect to SMTP server.\n\n"
                    f"Error: {message}\n\n"
                    "Please verify:\n"
                    "- SMTP server is correct (usually smtp.gmail.com for Gmail)\n"
                    "- Port is correct (usually 587 for TLS)\n"
                    "- Email address is correct\n"
                    "- For Gmail: Use App Password, not your regular password\n"
                    "- Firewall allows outgoing SMTP connections")

        except Exception as e:
            logger.exception("Email test failed")
            self.log_message(f"✗ Email test error: {e}")
            QMessageBox.critical(self, "Error", f"Email test failed:\n\n{str(e)}")

    def open_model_manager(self):
        """Open the Ollama Model Manager dialog."""
        try:
            # Show immediate feedback
            self.lbl_status.setText("Opening Model Manager...")
            self.log_message("Opening Ollama Model Manager...")

            # Import and create dialog
            from src.ui.ollama_manager_dialog import OllamaManagerDialog
            dialog = OllamaManagerDialog(self)

            # Connect signal to update AI model dropdown when model is downloaded
            dialog.model_downloaded.connect(self.on_model_downloaded)

            # Reset status
            self.lbl_status.setText("Status: Ready")

            # Show dialog
            dialog.exec()

            # Refresh Ollama status after closing dialog
            self._check_ollama_status()

        except Exception as e:
            self.lbl_status.setText("Status: Ready")
            QMessageBox.critical(self, "Error", f"Failed to open Model Manager: {e}")
            logger.exception("Error opening model manager")

    def on_model_downloaded(self, model_name: str):
        """Called when a model is successfully downloaded."""
        self.log_message(f"Model '{model_name}' is now available for AI analysis")

        # Update the combo box if the model isn't already there
        if self.combo_ai_model.findText(model_name) == -1:
            self.combo_ai_model.addItem(model_name)

        # Refresh Ollama status
        self._check_ollama_status()

    def _check_ollama_status(self):
        """Check Ollama status and update the status indicator (fast version)."""
        try:
            from src.utils.ollama_model_manager import OllamaModelManager
            manager = OllamaModelManager()

            # Fast check - only verify if running, don't fetch all models
            if manager.is_ollama_running():
                # Use cached model count if available from previous load
                model_count = len(self.installed_model_list) if hasattr(self, 'installed_model_list') and self.installed_model_list else 0

                # Only fetch models if we don't have cached data
                if model_count == 0:
                    try:
                        models = manager.get_installed_models()
                        model_count = len(models)
                    except:
                        model_count = 0

                if model_count > 0:
                    self.lbl_ollama_status.setText(f"Ollama: ✓ Running ({model_count} models)")
                    self.lbl_ollama_status.setStyleSheet(
                        "QPushButton#OllamaStatusButton { "
                        "background-color: #198754; color: white; font-weight: bold; "
                        "padding: 5px 10px; border-radius: 4px; border: none; }"
                        "QPushButton#OllamaStatusButton:hover { "
                        "background-color: #157347; }"
                    )
                else:
                    self.lbl_ollama_status.setText("Ollama: ⚠ Running (No models)")
                    self.lbl_ollama_status.setStyleSheet(
                        "QPushButton#OllamaStatusButton { "
                        "background-color: #ffc107; color: #000; font-weight: bold; "
                        "padding: 5px 10px; border-radius: 4px; border: none; }"
                        "QPushButton#OllamaStatusButton:hover { "
                        "background-color: #ffca2c; }"
                    )
            else:
                self.lbl_ollama_status.setText("Ollama: ✗ Not Running")
                self.lbl_ollama_status.setStyleSheet(
                    "QPushButton#OllamaStatusButton { "
                    "background-color: #dc3545; color: white; font-weight: bold; "
                    "padding: 5px 10px; border-radius: 4px; border: none; }"
                    "QPushButton#OllamaStatusButton:hover { "
                    "background-color: #bb2d3b; }"
                )
        except Exception as e:
            self.lbl_ollama_status.setText("Ollama: ? Unknown")
            logger.error(f"Error checking Ollama status: {e}")
            self.lbl_ollama_status.setStyleSheet(
                "QPushButton#OllamaStatusButton { "
                "background-color: #6c757d; color: white; font-weight: bold; "
                "padding: 5px 10px; border-radius: 4px; border: none; }"
                "QPushButton#OllamaStatusButton:hover { "
                "background-color: #5c636a; }"
            )
            logger.error(f"Error checking Ollama status: {e}")


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


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

