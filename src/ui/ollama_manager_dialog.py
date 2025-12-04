"""
Ollama Model Manager Dialog - UI for checking, downloading, and managing models.
"""
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                               QPushButton, QTableWidget, QTableWidgetItem,
                               QHeaderView, QProgressBar, QTextEdit, QGroupBox,
                               QMessageBox)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont

from ollama_model_manager import OllamaModelManager
import logging

logger = logging.getLogger(__name__)


class OllamaManagerDialog(QDialog):
    """Dialog for managing Ollama models with download progress."""

    model_downloaded = Signal(str)  # Emitted when a model finishes downloading

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = OllamaModelManager()
        self.download_threads = {}

        self.setWindowTitle("Ollama Model Manager")
        self.resize(900, 700)
        self.setup_ui()

        # Defer the initial refresh to after the dialog is shown for faster appearance
        QTimer.singleShot(100, self.refresh_models)

        # Auto-refresh every 5 seconds while downloading
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.check_download_status)
        self.refresh_timer.start(5000)

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("Ollama Model Manager")
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header.setStyleSheet("color: #4da6ff; padding: 10px;")
        layout.addWidget(header)

        # Status Section
        status_group = QGroupBox("Ollama Status")
        status_layout = QVBoxLayout(status_group)

        self.lbl_ollama_status = QLabel("Checking Ollama...")
        self.lbl_ollama_status.setStyleSheet("padding: 5px;")
        status_layout.addWidget(self.lbl_ollama_status)

        self.lbl_model_count = QLabel("Installed Models: 0")
        status_layout.addWidget(self.lbl_model_count)

        layout.addWidget(status_group)

        # Installed Models Table
        models_group = QGroupBox("Installed Models")
        models_layout = QVBoxLayout(models_group)

        self.installed_table = QTableWidget()
        self.installed_table.setColumnCount(4)
        self.installed_table.setHorizontalHeaderLabels(["Model", "Size", "Modified", "Actions"])
        self.installed_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.installed_table.setSelectionBehavior(QTableWidget.SelectRows)
        models_layout.addWidget(self.installed_table)

        layout.addWidget(models_group)

        # Available Models Section
        available_group = QGroupBox("Download Models")
        available_layout = QVBoxLayout(available_group)

        desc_label = QLabel("Popular models available for download:")
        available_layout.addWidget(desc_label)

        self.available_table = QTableWidget()
        self.available_table.setColumnCount(4)
        self.available_table.setHorizontalHeaderLabels(["Model", "Est. Size", "Status", "Actions"])
        self.available_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.available_table.setSelectionBehavior(QTableWidget.SelectRows)
        available_layout.addWidget(self.available_table)

        layout.addWidget(available_group)

        # Download Progress Section
        progress_group = QGroupBox("Download Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        progress_layout.addWidget(self.progress_label)

        layout.addWidget(progress_group)

        # Logs
        logs_group = QGroupBox("Activity Log")
        logs_layout = QVBoxLayout(logs_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(100)
        self.log_text.setStyleSheet("background-color: #121212; color: #00ff00; font-family: 'Consolas', monospace;")
        logs_layout.addWidget(self.log_text)

        layout.addWidget(logs_group)

        # Bottom Buttons
        btn_layout = QHBoxLayout()

        self.btn_refresh = QPushButton("Refresh")
        self.btn_refresh.clicked.connect(self.refresh_models)
        btn_layout.addWidget(self.btn_refresh)

        btn_layout.addStretch()

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        layout.addLayout(btn_layout)

    def log(self, message: str):
        """Add message to log."""
        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        logger.info(message)

    def refresh_models(self):
        """Refresh the list of installed and available models."""
        self.btn_refresh.setEnabled(False)
        self.log("Refreshing model list...")

        # Check Ollama status
        if self.manager.is_ollama_running():
            self.lbl_ollama_status.setText("✓ Ollama is running")
            self.lbl_ollama_status.setStyleSheet("color: green; padding: 5px; font-weight: bold;")
            self.log("Ollama is running")
        else:
            self.lbl_ollama_status.setText("✗ Ollama is not running - Please start Ollama first")
            self.lbl_ollama_status.setStyleSheet("color: red; padding: 5px; font-weight: bold;")
            self.log("WARNING: Ollama is not running")
            self.btn_refresh.setEnabled(True)
            return

        # Get installed models
        installed = self.manager.get_installed_models()
        self.lbl_model_count.setText(f"Installed Models: {len(installed)}")
        self.log(f"Found {len(installed)} installed model(s)")

        # Populate installed models table
        self.installed_table.setRowCount(0)
        for model in installed:
            row = self.installed_table.rowCount()
            self.installed_table.insertRow(row)

            name = model.get('name', 'Unknown')
            size = model.get('size', 0)
            size_mb = size / (1024 * 1024)
            size_str = f"{size_mb:.1f} MB" if size_mb < 1024 else f"{size_mb/1024:.1f} GB"
            modified = model.get('modified_at', 'Unknown')[:10]

            self.installed_table.setItem(row, 0, QTableWidgetItem(name))
            self.installed_table.setItem(row, 1, QTableWidgetItem(size_str))
            self.installed_table.setItem(row, 2, QTableWidgetItem(modified))

            # Delete button
            delete_btn = QPushButton("Delete")
            delete_btn.setObjectName("DangerButton")
            delete_btn.clicked.connect(lambda checked, m=name: self.delete_model(m))
            self.installed_table.setCellWidget(row, 3, delete_btn)

        # Populate available models table
        available = self.manager.get_available_models_list()
        installed_names = [m.get('name', '').split(':')[0] for m in installed]

        self.available_table.setRowCount(0)
        for model_name in available:
            row = self.available_table.rowCount()
            self.available_table.insertRow(row)

            self.available_table.setItem(row, 0, QTableWidgetItem(model_name))
            self.available_table.setItem(row, 1, QTableWidgetItem(self.manager.get_model_size_estimate(model_name)))

            # Check if installed
            is_installed = model_name in installed_names
            is_downloading = model_name in self.manager.downloading_models

            if is_downloading:
                status_item = QTableWidgetItem("Downloading...")
                status_item.setForeground(Qt.blue)
            elif is_installed:
                status_item = QTableWidgetItem("✓ Installed")
                status_item.setForeground(Qt.green)
            else:
                status_item = QTableWidgetItem("Not Installed")

            self.available_table.setItem(row, 2, status_item)

            # Download button
            if not is_installed and not is_downloading:
                download_btn = QPushButton("Download")
                download_btn.setObjectName("SuccessButton")
                download_btn.clicked.connect(lambda checked, m=model_name: self.download_model(m))
                self.available_table.setCellWidget(row, 3, download_btn)
            elif is_downloading:
                cancel_btn = QPushButton("Downloading...")
                cancel_btn.setEnabled(False)
                self.available_table.setCellWidget(row, 3, cancel_btn)
            else:
                installed_lbl = QLabel("Installed")
                installed_lbl.setAlignment(Qt.AlignCenter)
                self.available_table.setCellWidget(row, 3, installed_lbl)

        self.btn_refresh.setEnabled(True)

    def download_model(self, model_name: str):
        """Start downloading a model."""
        if not self.manager.is_ollama_running():
            QMessageBox.warning(self, "Ollama Not Running",
                              "Please start Ollama before downloading models.")
            return

        reply = QMessageBox.question(
            self,
            "Download Model",
            f"Download model '{model_name}'?\n\n"
            f"Estimated size: {self.manager.get_model_size_estimate(model_name)}\n"
            f"This may take several minutes depending on your connection.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.log(f"Starting download: {model_name}")

            # Show progress bar
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.progress_label.setVisible(True)
            self.progress_label.setText(f"Downloading {model_name}...")

            # Start download
            thread = self.manager.download_model(
                model_name,
                progress_callback=self.on_download_progress,
                completion_callback=self.on_download_complete
            )
            self.download_threads[model_name] = thread

            # Refresh to show downloading status
            self.refresh_models()

    def on_download_progress(self, message: str, progress: int):
        """Handle download progress updates."""
        self.progress_label.setText(message)
        self.progress_bar.setValue(progress)
        self.log(message)

    def on_download_complete(self, success: bool, message: str):
        """Handle download completion."""
        if success:
            self.log(f"✓ SUCCESS: {message}")
            QMessageBox.information(self, "Download Complete", message)

            # Extract model name from message
            model_name = message.split()[1] if len(message.split()) > 1 else ""
            self.model_downloaded.emit(model_name)
        else:
            self.log(f"✗ ERROR: {message}")
            QMessageBox.critical(self, "Download Failed", message)

        # Hide progress bar
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

        # Refresh the list
        self.refresh_models()

    def delete_model(self, model_name: str):
        """Delete a model."""
        reply = QMessageBox.question(
            self,
            "Delete Model",
            f"Are you sure you want to delete '{model_name}'?\n\n"
            f"This will free up disk space but the model will need to be downloaded again if needed.",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.log(f"Deleting model: {model_name}")
            success = self.manager.delete_model(model_name)

            if success:
                self.log(f"✓ Model deleted: {model_name}")
                QMessageBox.information(self, "Success", f"Model '{model_name}' has been deleted.")
                self.refresh_models()
            else:
                self.log(f"✗ Failed to delete: {model_name}")
                QMessageBox.critical(self, "Error", f"Failed to delete model '{model_name}'.")

    def check_download_status(self):
        """Periodically check if any downloads are in progress."""
        if self.manager.downloading_models:
            # Update the table to show downloading status
            for row in range(self.available_table.rowCount()):
                model_name = self.available_table.item(row, 0).text()
                if model_name in self.manager.downloading_models:
                    status_item = QTableWidgetItem("Downloading...")
                    status_item.setForeground(Qt.blue)
                    self.available_table.setItem(row, 2, status_item)

    def closeEvent(self, event):
        """Handle dialog close."""
        if self.manager.downloading_models:
            reply = QMessageBox.question(
                self,
                "Download in Progress",
                "A download is in progress. Close anyway?\n\n"
                "The download will continue in the background.",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                event.ignore()
                return

        self.refresh_timer.stop()
        event.accept()

