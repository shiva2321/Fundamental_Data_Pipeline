"""
Cache Manager Widget

UI for managing the filing cache system.
Shows cached tickers, form types, dates, and allows clearing cache.
"""
import logging
from typing import List, Dict, Any
from datetime import datetime

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
                               QGroupBox, QMessageBox, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor

from src.utils.filing_cache import get_filing_cache

logger = logging.getLogger(__name__)


class CacheManagerWidget(QWidget):
    """
    Widget for managing filing cache.

    Features:
    - View all cached tickers
    - See form types and date ranges
    - Clear individual ticker cache
    - Clear entire cache
    - Real-time size tracking
    """

    def __init__(self):
        super().__init__()
        self.cache = get_filing_cache()
        self.init_ui()
        self.load_cache_data()

    def init_ui(self):
        """Initialize the UI"""
        layout = QVBoxLayout(self)

        # === Cache Statistics ===
        stats_group = QGroupBox("Cache Statistics")
        stats_layout = QHBoxLayout()

        self.lbl_total_tickers = QLabel("Cached Tickers: 0")
        self.lbl_total_filings = QLabel("Total Filings: 0")
        self.lbl_cache_size = QLabel("Cache Size: 0 MB / 2048 MB")

        # Progress bar for cache usage
        self.progress_cache = QProgressBar()
        self.progress_cache.setMaximum(100)
        self.progress_cache.setValue(0)
        self.progress_cache.setTextVisible(True)
        self.progress_cache.setFormat("Cache Usage: %p%")

        font_bold = QFont()
        font_bold.setBold(True)
        for label in [self.lbl_total_tickers, self.lbl_total_filings, self.lbl_cache_size]:
            label.setFont(font_bold)

        stats_layout.addWidget(self.lbl_total_tickers)
        stats_layout.addWidget(self.lbl_total_filings)
        stats_layout.addWidget(self.lbl_cache_size)
        stats_layout.addWidget(self.progress_cache)
        stats_layout.addStretch()

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # === Control Buttons ===
        controls_layout = QHBoxLayout()

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setToolTip("Refresh cache data")
        btn_refresh.clicked.connect(self.load_cache_data)
        controls_layout.addWidget(btn_refresh)

        btn_clear_selected = QPushButton("🗑️ Clear Selected")
        btn_clear_selected.setToolTip("Clear cache for selected ticker(s)")
        btn_clear_selected.clicked.connect(self.clear_selected_cache)
        btn_clear_selected.setObjectName("DangerButton")
        controls_layout.addWidget(btn_clear_selected)

        btn_clear_all = QPushButton("🗑️ Clear All Cache")
        btn_clear_all.setToolTip("Clear entire cache (2GB)")
        btn_clear_all.clicked.connect(self.clear_all_cache)
        btn_clear_all.setObjectName("DangerButton")
        controls_layout.addWidget(btn_clear_all)

        controls_layout.addStretch()
        layout.addLayout(controls_layout)

        # === Cache Table ===
        cache_group = QGroupBox("Cached Filings")
        cache_layout = QVBoxLayout()

        self.table_cache = QTableWidget()
        self.table_cache.setColumnCount(7)
        self.table_cache.setHorizontalHeaderLabels([
            "Ticker", "CIK", "Filing Count", "Size (MB)", "Form Types", "Date Range", "Last Accessed"
        ])
        self.table_cache.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_cache.horizontalHeader().setSectionResizeMode(4, QHeaderView.Stretch)  # Form Types column
        self.table_cache.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_cache.setSelectionMode(QTableWidget.MultiSelection)
        cache_layout.addWidget(self.table_cache)

        cache_group.setLayout(cache_layout)
        layout.addWidget(cache_group)

        # === Help Text ===
        help_label = QLabel(
            "💡 Tip: The cache stores SEC filings to speed up reprocessing during testing. "
            "Maximum size: 2GB. Oldest entries are automatically removed when limit is reached."
        )
        help_label.setStyleSheet("color: #4da6ff; font-size: 10px; padding: 5px; font-style: italic;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

    def load_cache_data(self):
        """Load and display cache data"""
        try:
            # IMPORTANT: Reload metadata from disk to get latest changes
            self.cache.metadata = self.cache._load_metadata()

            # Get cache stats
            stats = self.cache.get_cache_stats()

            # Update statistics
            self.lbl_total_tickers.setText(f"Cached Tickers: {stats['total_tickers']}")
            self.lbl_total_filings.setText(f"Total Filings: {stats['total_filings']}")
            self.lbl_cache_size.setText(f"Cache Size: {stats['total_size_mb']:.2f} MB / {stats['max_size_mb']:.0f} MB")
            self.progress_cache.setValue(int(stats['usage_percent']))

            # Set progress bar color based on usage
            if stats['usage_percent'] > 90:
                self.progress_cache.setStyleSheet("QProgressBar::chunk { background-color: #dc3545; }")
            elif stats['usage_percent'] > 70:
                self.progress_cache.setStyleSheet("QProgressBar::chunk { background-color: #ffc107; }")
            else:
                self.progress_cache.setStyleSheet("QProgressBar::chunk { background-color: #28a745; }")

            # Load ticker data
            cached_tickers = self.cache.list_all_cached_tickers()

            logger.info(f"Reloaded cache metadata: Found {len(cached_tickers)} cached tickers")

            # Clear and populate table
            self.table_cache.setRowCount(0)

            for ticker_info in cached_tickers:
                row = self.table_cache.rowCount()
                self.table_cache.insertRow(row)

                # Ticker
                self.table_cache.setItem(row, 0, QTableWidgetItem(ticker_info['ticker']))

                # CIK
                self.table_cache.setItem(row, 1, QTableWidgetItem(ticker_info['cik']))

                # Filing Count
                self.table_cache.setItem(row, 2, QTableWidgetItem(str(ticker_info['total_filings'])))

                # Size
                size_item = QTableWidgetItem(f"{ticker_info['total_size_mb']:.2f}")
                self.table_cache.setItem(row, 3, size_item)

                # Form Types
                form_types = ticker_info.get('form_types', {})
                if form_types:
                    # Show top 5 form types
                    top_forms = sorted(form_types.items(), key=lambda x: x[1], reverse=True)[:5]
                    forms_str = ", ".join([f"{form}({count})" for form, count in top_forms])
                    if len(form_types) > 5:
                        forms_str += f" +{len(form_types) - 5} more"
                else:
                    forms_str = "N/A"
                self.table_cache.setItem(row, 4, QTableWidgetItem(forms_str))

                # Date Range
                date_range = ticker_info.get('date_range', {})
                if date_range.get('from') != 'N/A':
                    date_range_str = f"{date_range.get('from')} to {date_range.get('to')}"
                else:
                    date_range_str = "N/A"
                self.table_cache.setItem(row, 5, QTableWidgetItem(date_range_str))

                # Last Accessed
                try:
                    last_accessed = datetime.fromisoformat(ticker_info['last_accessed'])
                    time_ago = self._get_time_ago(last_accessed)
                    last_accessed_str = f"{last_accessed.strftime('%Y-%m-%d %H:%M')} ({time_ago})"
                except:
                    last_accessed_str = ticker_info['last_accessed'][:19]

                self.table_cache.setItem(row, 6, QTableWidgetItem(last_accessed_str))

            logger.info(f"Loaded cache data: {stats['total_tickers']} tickers, {stats['total_size_mb']:.2f} MB")

        except Exception as e:
            logger.exception(f"Error loading cache data: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load cache data:\n{e}")

    def _get_time_ago(self, dt: datetime) -> str:
        """Get human-readable time ago string"""
        now = datetime.now()
        delta = now - dt

        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds >= 3600:
            hours = delta.seconds // 3600
            return f"{hours}h ago"
        elif delta.seconds >= 60:
            minutes = delta.seconds // 60
            return f"{minutes}m ago"
        else:
            return "just now"

    def clear_selected_cache(self):
        """Clear cache for selected ticker(s)"""
        selected_rows = self.table_cache.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select at least one ticker to clear.")
            return

        tickers = [self.table_cache.item(row.row(), 0).text() for row in selected_rows]

        # Confirm
        if len(tickers) == 1:
            msg = f"Clear cache for {tickers[0]}?"
        else:
            msg = f"Clear cache for {len(tickers)} tickers?\n\n" + ", ".join(tickers[:5])
            if len(tickers) > 5:
                msg += f"\n... and {len(tickers) - 5} more"

        reply = QMessageBox.question(
            self, "Confirm Clear Cache", msg,
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Clear cache for each ticker
        cleared_count = 0
        for ticker in tickers:
            if self.cache.clear_ticker_cache(ticker):
                cleared_count += 1

        QMessageBox.information(
            self, "Cache Cleared",
            f"Cleared cache for {cleared_count} ticker(s)."
        )

        # Refresh display
        self.load_cache_data()

    def clear_all_cache(self):
        """Clear entire cache"""
        # Get current stats
        stats = self.cache.get_cache_stats()

        # Confirm
        msg = (f"Clear entire cache?\n\n"
               f"This will delete:\n"
               f"  • {stats['total_tickers']} tickers\n"
               f"  • {stats['total_filings']} filings\n"
               f"  • {stats['total_size_mb']:.2f} MB of data\n\n"
               f"This cannot be undone!")

        reply = QMessageBox.question(
            self, "Confirm Clear All Cache", msg,
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Clear cache
        if self.cache.clear_all_cache():
            QMessageBox.information(
                self, "Cache Cleared",
                "All cache data has been cleared."
            )

            # Refresh display
            self.load_cache_data()
        else:
            QMessageBox.critical(
                self, "Error",
                "Failed to clear cache. Check logs for details."
            )

