"""
Enhanced Profile Visualization Window with comprehensive insights.
Uses multiple chart types appropriate for different data representations.
"""
import logging
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTabWidget,
                               QWidget, QLabel, QScrollArea, QGroupBox, QPushButton,
                               QGridLayout, QTableWidget, QTableWidgetItem,
                               QHeaderView, QHBoxLayout, QSizePolicy, QSplitter, QProgressBar, QMessageBox)
from PySide6.QtCore import Qt, QObject, QEvent, QSettings, QByteArray
from PySide6.QtGui import QFont, QColor

from types import MethodType

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvasQTAggBase, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np

logger = logging.getLogger(__name__)


class SafeFigureCanvas(FigureCanvasQTAggBase):
    """Canvas that ignores cursor changes after the widget is deleted."""

    def setCursor(self, cursor):
        try:
            return super().setCursor(cursor)
        except RuntimeError:
            # Canvas might already be destroyed when Matplotlib tries to change the cursor
            return


class SafeNavigationToolbar(NavigationToolbar):
    """Navigation toolbar that tolerates deleted status labels."""

    def set_message(self, s):
        try:
            super().set_message(s)
        except RuntimeError:
            # QLabel may already be destroyed when the dialog closes; ignore the message update.
            pass


class InteractiveChartViewer(QDialog):
    """Interactive chart viewer with zoom, pan, and data point inspection."""

    def __init__(self, fig, title="Interactive Chart", parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(1200, 800)

        layout = QVBoxLayout(self)

        # Store figure
        self.fig = fig

        # Create canvas from existing figure
        self.canvas = SafeFigureCanvas(fig)
        self.canvas.setParent(self)

        # Add navigation toolbar for zoom, pan, save functionality
        self.toolbar = SafeNavigationToolbar(self.canvas, self)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        # Info label at bottom (less intrusive)
        self.info_label = QLabel("💡 Hover over data points to see values | Use toolbar to zoom/pan/save | Scroll mouse wheel to pan left/right")
        self.info_label.setStyleSheet("padding: 5px; background-color: #2d2d2d; border-top: 1px solid #3e3e3e; font-size: 10px; color: #888;")
        layout.addWidget(self.info_label)

        # Enable cursor tracking
        self.canvas.setMouseTracking(True)

        # Store annotation for each axes (will appear ON the chart)
        self.annotations = {}
        for ax in self.fig.get_axes():
            # Create annotation that appears ON the chart near the cursor
            annot = ax.annotate("", xy=(0,0), xytext=(20, 20), textcoords="offset points",
                              bbox=dict(boxstyle="round,pad=0.7", fc="#2d2d2d", ec="#4da6ff", alpha=0.95, linewidth=2),
                              arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2",
                                            color="#4da6ff", lw=2),
                              fontsize=11, color="white", weight='bold',
                              zorder=1000)  # High z-order to appear on top
            annot.set_visible(False)
            self.annotations[ax] = annot

        # Connect mouse move event
        self.canvas.mpl_connect('motion_notify_event', self.on_mouse_move)

        # Connect scroll event for horizontal panning with mouse wheel
        self.canvas.mpl_connect('scroll_event', self.on_scroll)

        self.canvas.draw()

    def on_scroll(self, event):
        """Handle mouse wheel scrolling for horizontal panning."""
        if event.inaxes is None:
            return

        ax = event.inaxes

        # Get current x-axis limits
        xlim = ax.get_xlim()
        xrange = xlim[1] - xlim[0]

        # Calculate scroll amount (10% of visible range)
        scroll_amount = xrange * 0.1

        # Scroll left or right based on wheel direction
        if event.button == 'up':
            # Scroll right (show later data)
            new_xlim = (xlim[0] + scroll_amount, xlim[1] + scroll_amount)
        else:  # 'down'
            # Scroll left (show earlier data)
            new_xlim = (xlim[0] - scroll_amount, xlim[1] - scroll_amount)

        # Apply new limits
        ax.set_xlim(new_xlim)
        self.canvas.draw_idle()

    def on_mouse_move(self, event):
        """Display data point information on hover - annotation appears ON chart near cursor."""
        if event.inaxes is None:
            # Hide all annotations when not over any axes
            for annot in self.annotations.values():
                if annot.get_visible():
                    annot.set_visible(False)
                    self.canvas.draw_idle()
            return

        ax = event.inaxes
        x, y = event.xdata, event.ydata

        if x is None or y is None:
            return

        annot = self.annotations.get(ax)
        if annot is None:
            return

        found_point = False

        # Check lines first
        lines = ax.get_lines()
        if lines:
            for line in lines:
                xdata = line.get_xdata()
                ydata = line.get_ydata()

                if len(xdata) == 0:
                    continue

                try:
                    # Find nearest point in data coordinates
                    distances = [(abs(xdata[i] - x), i) for i in range(len(xdata))]
                    min_dist, idx = min(distances, key=lambda t: t[0])

                    # Check if close enough (in x direction)
                    if min_dist < (max(xdata) - min(xdata)) * 0.05:  # Within 5% of x-range
                        x_val = xdata[idx]
                        y_val = ydata[idx]

                        # Check y proximity too
                        y_range = max(ydata) - min(ydata) if max(ydata) != min(ydata) else 1
                        if abs(y_val - y) < y_range * 0.15:  # Within 15% of y-range
                            # Format value
                            if abs(y_val) >= 1e9:
                                y_str = f"${y_val/1e9:.2f}B"
                            elif abs(y_val) >= 1e6:
                                y_str = f"${y_val/1e6:.2f}M"
                            elif abs(y_val) >= 1e3:
                                y_str = f"${y_val/1e3:.2f}K"
                            else:
                                y_str = f"${y_val:.2f}"

                            # Try to get actual date from axes metadata
                            period_str = f"Point {idx}"
                            try:
                                # Check if axes has dates_data attribute
                                if hasattr(ax, 'dates_data') and ax.dates_data:
                                    dates_list = ax.dates_data
                                    if idx < len(dates_list):
                                        # Format date to show year-month-day
                                        date_val = dates_list[idx]
                                        if len(date_val) >= 10:
                                            period_str = date_val[:10]  # YYYY-MM-DD
                                        else:
                                            period_str = date_val
                            except Exception:
                                pass

                            # Set annotation at data point
                            annot.xy = (x_val, y_val)
                            annot.set_text(f"{period_str}\n{y_str}")
                            annot.set_visible(True)
                            found_point = True
                            break
                except (ValueError, IndexError):
                    pass

        # Check bars if no line found
        if not found_point:
            bars = [p for p in ax.patches if hasattr(p, 'get_height')]
            if bars:
                for bar in bars:
                    bar_x = bar.get_x()
                    bar_width = bar.get_width()
                    bar_height = bar.get_height()
                    bar_center = bar_x + bar_width / 2

                    # Check if mouse is over this bar
                    if bar_x <= x <= bar_x + bar_width:
                        # Format value (usually percentage for growth)
                        val_str = f"{bar_height:.2f}%"

                        # Get period label from dates_data if available
                        period_str = "Period"
                        try:
                            idx = int(bar_center)
                            # Check if axes has dates_data attribute
                            if hasattr(ax, 'dates_data') and ax.dates_data:
                                dates_list = ax.dates_data
                                if idx < len(dates_list):
                                    # Format date to show year-month-day
                                    date_val = dates_list[idx]
                                    if len(date_val) >= 10:
                                        period_str = date_val[:10]  # YYYY-MM-DD
                                    else:
                                        period_str = date_val
                        except Exception:
                            pass

                        # Set annotation at top of bar
                        annot.xy = (bar_center, bar_height)
                        annot.set_text(f"{period_str}\n{val_str}")
                        annot.set_visible(True)
                        found_point = True
                        break

        if not found_point:
            # Hide annotation if not near any point
            if annot.get_visible():
                annot.set_visible(False)

        self.canvas.draw_idle()


class ProfileVisualizationWindow(QDialog):
    """Enhanced visualization window with multiple chart types and AI analysis."""
    
    def __init__(self, profile: Dict[str, Any], config: Optional[Dict[str, Any]] = None, parent=None, mongo=None):
        super().__init__(parent)

        # Validate profile has required data
        if not profile or not isinstance(profile, dict):
            raise ValueError("Profile must be a non-empty dictionary")

        self.profile = profile
        self.config = config or {}
        self.mongo = mongo  # Store mongo wrapper for relationship graph access

        try:
            self.setWindowTitle(f"Profile Visualization - {self._get_company_name()}")
        except Exception as e:
            logger.error(f"Error setting window title: {e}")
            self.setWindowTitle("Profile Visualization")

        self.resize(1600, 1000)
        
        # AI analysis is already in the profile (generated during profile creation)
        self.ai_analysis = profile.get('ai_analysis')

        try:
            self.setup_ui()
        except Exception as e:
            logger.error(f"Error setting up UI: {e}")
            # Create minimal fallback UI
            layout = QVBoxLayout(self)
            error_label = QLabel(f"Error initializing visualization: {str(e)}")
            error_label.setStyleSheet("color: #ff4444; padding: 20px;")
            layout.addWidget(error_label)
            raise

    def _get_company_name(self) -> str:
        """Get company name from profile."""
        info = self.profile.get('company_info', {})
        ticker = info.get('ticker', 'N/A')
        name = info.get('name', 'Unknown')
        return f"{ticker} - {name}"
    
    def setup_ui(self):
        """Setup the UI layout with lazy-loaded tabs."""
        try:
            layout = QVBoxLayout(self)

            # Header
            header = QLabel(self._get_company_name())
            header.setFont(QFont("Segoe UI", 16, QFont.Bold))
            header.setStyleSheet("color: #4da6ff; padding: 10px;")
            layout.addWidget(header)

            # Tabs with lazy loading
            self.tabs = QTabWidget()
            self.tab_cache = {}  # Cache loaded tabs

            # Add tabs with placeholder widgets - will be rendered on first view
            self.tabs.addTab(QWidget(), "Overview")
            self.tabs.addTab(QWidget(), "Decision Summary")
            self.tabs.addTab(QWidget(), "Financial Trends")
            self.tabs.addTab(QWidget(), "Financial Ratios")
            self.tabs.addTab(QWidget(), "Growth Analysis")
            self.tabs.addTab(QWidget(), "Health Indicators")

            # Map tab indices to creator functions
            self.tab_creators = {
                0: ('Overview', self.create_overview_tab),
                1: ('Decision Summary', self.create_decision_summary_tab),
                2: ('Financial Trends', self.create_financials_tab),
                3: ('Financial Ratios', self.create_ratios_tab),
                4: ('Growth Analysis', self.create_growth_tab),
                5: ('Health Indicators', self.create_health_tab),
            }

            next_index = 6

            # Add Key Persons tab if data exists
            key_persons = self.profile.get('key_persons', {})
            if key_persons and (key_persons.get('executives') or key_persons.get('board_members')
                                or key_persons.get('insider_holdings') or key_persons.get('holding_companies')):
                self.tabs.addTab(QWidget(), "Key Persons")
                self.tab_creators[next_index] = ('Key Persons', self.create_key_persons_tab)
                next_index += 1

            # Add Relationship Graph tab if relationships data exists
            relationships = self.profile.get('relationships', {})
            if relationships and relationships.get('relationships'):
                self.tabs.addTab(QWidget(), "Relationship Graph")
                self.tab_creators[next_index] = ('Relationship Graph', self.create_relationship_graph_tab)
                next_index += 1

            # Add AI Analysis tab if analysis exists
            if self.ai_analysis:
                self.tabs.addTab(QWidget(), "AI/ML Analysis")
                self.tab_creators[next_index] = ('AI/ML Analysis', self.create_ai_analysis_tab)
                next_index += 1

            # Add Filing Viewer tab (always available)
            self.tabs.addTab(QWidget(), "SEC Filings")
            self.tab_creators[next_index] = ('SEC Filings', self.create_filing_viewer_tab)
            next_index += 1

            # Connect tab change signal for lazy loading
            self.tabs.currentChanged.connect(self._load_tab_on_view)

            layout.addWidget(self.tabs)

            # Close button
            close_btn = QPushButton("Close")
            close_btn.clicked.connect(self.close)
            close_btn.setMaximumWidth(100)
            layout.addWidget(close_btn, alignment=Qt.AlignRight)

            logger.info(f"Visualization window initialized with {len(self.tab_creators)} tabs")

        except Exception as e:
            logger.exception(f"Critical error in setup_ui: {e}")
            # Create minimal fallback layout
            layout = QVBoxLayout(self)
            error_label = QLabel(f"Fatal Error: {str(e)}")
            error_label.setStyleSheet("color: #ff0000; padding: 20px;")
            layout.addWidget(error_label)
            raise

    def _load_tab_on_view(self, index: int):
        """Load tab content when first viewed (lazy loading)."""
        try:
            if index not in self.tab_creators:
                logger.debug(f"Tab index {index} not in creators")
                return

            # Skip if already cached
            if index in self.tab_cache:
                return

            tab_name, creator_func = self.tab_creators[index]

            logger.info(f"Loading tab: {tab_name} (index {index})")

            try:
                # Create the actual tab widget
                tab_widget = creator_func()

                if tab_widget is None:
                    raise ValueError(f"Creator function returned None for {tab_name}")

                # Disconnect signal to prevent recursive calls when we modify tabs
                self.tabs.currentChanged.disconnect(self._load_tab_on_view)

                try:
                    # Replace placeholder with actual content
                    self.tabs.setTabText(index, tab_name)  # Ensure tab name is set
                    self.tabs.removeTab(index)
                    self.tabs.insertTab(index, tab_widget, tab_name)
                    self.tabs.setCurrentIndex(index)

                    # Cache it
                    self.tab_cache[index] = tab_widget
                    logger.info(f"✓ Tab loaded: {tab_name}")
                finally:
                    # Always reconnect signal
                    self.tabs.currentChanged.connect(self._load_tab_on_view)

            except Exception as e:
                logger.exception(f"Error creating {tab_name}: {e}")
                # Create error widget with details
                error_widget = QWidget()
                error_layout = QVBoxLayout(error_widget)

                error_title = QLabel(f"Error Loading {tab_name}")
                error_title.setStyleSheet("color: #ff4444; font-weight: bold; font-size: 12px;")
                error_layout.addWidget(error_title)

                error_details = QLabel(f"{type(e).__name__}: {str(e)[:200]}")
                error_details.setStyleSheet("color: #ffaa00; font-size: 10px;")
                error_details.setWordWrap(True)
                error_layout.addWidget(error_details)

                error_layout.addStretch()

                # Disconnect to avoid recursive calls
                self.tabs.currentChanged.disconnect(self._load_tab_on_view)
                try:
                    self.tabs.removeTab(index)
                    self.tabs.insertTab(index, error_widget, tab_name)
                    self.tabs.setCurrentIndex(index)
                finally:
                    self.tabs.currentChanged.connect(self._load_tab_on_view)

                logger.error(f"Failed to load {tab_name}: {e}")

        except Exception as outer_e:
            logger.exception(f"Unexpected error in _load_tab_on_view: {outer_e}")

    def create_overview_tab(self) -> QWidget:
        """Create overview tab with key information."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Company Info
        info_group = QGroupBox("Company Information")
        info_layout = QGridLayout(info_group)
        
        info = self.profile.get('company_info', {})
        meta = self.profile.get('filing_metadata', {})
        
        row = 0
        self._add_info_row(info_layout, row, "Ticker:", info.get('ticker', 'N/A'))
        row += 1
        self._add_info_row(info_layout, row, "Company Name:", info.get('name', 'N/A'))
        row += 1
        self._add_info_row(info_layout, row, "CIK:", self.profile.get('cik', 'N/A'))
        row += 1
        self._add_info_row(info_layout, row, "Total Filings:", str(meta.get('total_filings', 'N/A')))
        row += 1
        self._add_info_row(info_layout, row, "Most Recent Filing:", meta.get('most_recent_filing', 'N/A'))
        row += 1
        self._add_info_row(info_layout, row, "Profile Generated:", self.profile.get('generated_at', 'N/A')[:19])
        
        content_layout.addWidget(info_group)
        
        # Latest Financials
        latest_group = QGroupBox("Latest Financial Metrics")
        latest_layout = QGridLayout(latest_group)
        
        latest = self.profile.get('latest_financials', {})

        # Check for alternative revenue fields if Revenues is not available
        revenue_value = latest.get('Revenues')
        if not revenue_value or revenue_value == 'N/A':
            # Try alternative revenue fields
            for alt_field in ['RevenueFromContractWithCustomerExcludingAssessedTax',
                            'RevenueFromContractWithCustomer',
                            'SalesRevenueNet']:
                revenue_value = latest.get(alt_field)
                if revenue_value and revenue_value != 'N/A':
                    break

        metrics = [
            ('Revenues', revenue_value if revenue_value else 'N/A'),
            ('Assets', latest.get('Assets', 'N/A')),
            ('Liabilities', latest.get('Liabilities', 'N/A')),
            ('Stockholders Equity', latest.get('StockholdersEquity', 'N/A')),
            ('Net Income', latest.get('NetIncomeLoss', 'N/A')),
            ('Cash', latest.get('CashAndCashEquivalentsAtCarryingValue', 'N/A'))
        ]
        
        row = 0
        for label, value in metrics:
            if isinstance(value, (int, float)):
                value = f"${value:,.0f}"
            self._add_info_row(latest_layout, row, f"{label}:", str(value))
            row += 1
        
        content_layout.addWidget(latest_group)
        
        # Material Events (8-K Filings)
        material_events = self.profile.get('material_events', {})
        if material_events and material_events.get('total_8k_count', 0) > 0:
            events_group = QGroupBox("Material Events (Recent 8-K Filings)")
            events_layout = QGridLayout(events_group)

            total_8k = material_events.get('total_8k_count', 0)
            recent_count = material_events.get('recent_count', 0)
            avg_per_quarter = material_events.get('avg_events_per_quarter', 0)
            risk_flags = material_events.get('risk_flags', [])
            positive_catalysts = material_events.get('positive_catalysts', [])

            row = 0
            self._add_info_row(events_layout, row, "Total 8-K Filings:", str(total_8k))
            row += 1
            self._add_info_row(events_layout, row, "Recent Events (90 days):", str(recent_count))
            row += 1
            self._add_info_row(events_layout, row, "Avg per Quarter:", f"{avg_per_quarter:.1f}")
            row += 1

            # Risk flags
            if risk_flags:
                flags_label = QLabel("Risk Flags:")
                flags_label.setStyleSheet("color: #ff4444; font-weight: bold;")
                events_layout.addWidget(flags_label, row, 0, Qt.AlignRight)

                flags_text = QLabel("\n".join([f"⚠️ {flag}" for flag in risk_flags]))
                flags_text.setStyleSheet("color: #ff4444;")
                flags_text.setWordWrap(True)
                events_layout.addWidget(flags_text, row, 1)
                row += 1

            # Positive catalysts
            if positive_catalysts:
                catalysts_label = QLabel("Positive Indicators:")
                catalysts_label.setStyleSheet("color: #44ff44; font-weight: bold;")
                events_layout.addWidget(catalysts_label, row, 0, Qt.AlignRight)

                catalysts_text = QLabel("\n".join([f"✓ {catalyst}" for catalyst in positive_catalysts]))
                catalysts_text.setStyleSheet("color: #44ff44;")
                catalysts_text.setWordWrap(True)
                events_layout.addWidget(catalysts_text, row, 1)
                row += 1

            content_layout.addWidget(events_group)

        # Corporate Governance (DEF 14A)
        governance = self.profile.get('corporate_governance', {})
        if governance and governance.get('total_proxy_count', 0) > 0:
            gov_group = QGroupBox("Corporate Governance (Proxy Statements)")
            gov_layout = QGridLayout(gov_group)

            proxy_count = governance.get('total_proxy_count', 0)
            gov_score = governance.get('governance_score', 0)
            insights = governance.get('insights', [])

            row = 0
            self._add_info_row(gov_layout, row, "Proxy Statements Filed:", str(proxy_count))
            row += 1
            self._add_info_row(gov_layout, row, "Governance Score:", f"{gov_score}/100")
            row += 1

            # Insights
            if insights:
                insights_label = QLabel("Insights:")
                insights_label.setStyleSheet("font-weight: bold;")
                gov_layout.addWidget(insights_label, row, 0, Qt.AlignRight)

                insights_text = QLabel("\n".join([f"• {insight}" for insight in insights[:5]]))
                insights_text.setWordWrap(True)
                gov_layout.addWidget(insights_text, row, 1)
                row += 1

            content_layout.addWidget(gov_group)

        # Insider Trading (Form 4)
        insider = self.profile.get('insider_trading', {})
        if insider and insider.get('total_form4_count', 0) > 0:
            insider_group = QGroupBox("Insider Trading Activity (Form 4)")
            insider_layout = QGridLayout(insider_group)

            form4_count = insider.get('total_form4_count', 0)
            recent_count = insider.get('recent_count_90d', 0)
            sentiment = insider.get('sentiment', 'Unknown')
            activity_level = insider.get('activity_level', 'Unknown')
            insights = insider.get('insights', [])

            row = 0
            self._add_info_row(insider_layout, row, "Total Form 4 Filings:", str(form4_count))
            row += 1
            self._add_info_row(insider_layout, row, "Recent (90 days):", str(recent_count))
            row += 1
            self._add_info_row(insider_layout, row, "Activity Level:", activity_level)
            row += 1
            self._add_info_row(insider_layout, row, "Sentiment:", sentiment)
            row += 1

            # Insights
            if insights:
                insights_label = QLabel("Insights:")
                insights_label.setStyleSheet("font-weight: bold;")
                insider_layout.addWidget(insights_label, row, 0, Qt.AlignRight)

                insights_text = QLabel("\n".join([f"• {insight}" for insight in insights[:5]]))
                insights_text.setWordWrap(True)
                insider_layout.addWidget(insights_text, row, 1)
                row += 1

            content_layout.addWidget(insider_group)

        # Institutional Ownership (SC 13D/G)
        institutional = self.profile.get('institutional_ownership', {})
        if institutional and institutional.get('total_sc13_count', 0) > 0:
            inst_group = QGroupBox("Institutional Ownership (SC 13D/G)")
            inst_layout = QGridLayout(inst_group)

            total_sc13 = institutional.get('total_sc13_count', 0)
            activist_count = institutional.get('activist_count', 0)
            interest = institutional.get('institutional_interest', 'Unknown')
            insights = institutional.get('insights', [])

            row = 0
            self._add_info_row(inst_layout, row, "Total SC 13 Filings:", str(total_sc13))
            row += 1
            self._add_info_row(inst_layout, row, "Activist Investors (13D):", str(activist_count))
            row += 1
            self._add_info_row(inst_layout, row, "Institutional Interest:", interest)
            row += 1

            # Insights - highlight activist presence
            if insights:
                insights_label = QLabel("Insights:")
                insights_label.setStyleSheet("font-weight: bold;")
                inst_layout.addWidget(insights_label, row, 0, Qt.AlignRight)

                # Color code activist warnings
                insights_html = []
                for insight in insights[:5]:
                    if '🔴' in insight or 'activist' in insight.lower():
                        insights_html.append(f'<span style="color: #ff4444;">• {insight}</span>')
                    elif '⚠️' in insight:
                        insights_html.append(f'<span style="color: #ffaa00;">• {insight}</span>')
                    else:
                        insights_html.append(f'• {insight}')

                insights_text = QLabel("<br>".join(insights_html))
                insights_text.setWordWrap(True)
                insights_text.setTextFormat(Qt.RichText)
                inst_layout.addWidget(insights_text, row, 1)
                row += 1

            content_layout.addWidget(inst_group)

        # Health Summary
        health = self.profile.get('health_indicators', {})
        if health:
            health_group = QGroupBox("Health Summary")
            health_layout = QGridLayout(health_group)
            
            row = 0
            score = health.get('overall_health_score', 0)
            classification = health.get('health_classification', 'N/A')
            
            # Color-code based on score
            color = 'green' if score >= 70 else 'orange' if score >= 50 else 'red'
            
            lbl = QLabel("Overall Health Score:")
            lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
            val = QLabel(f"{score}/100")
            val.setFont(QFont("Segoe UI", 9, QFont.Bold))
            val.setStyleSheet(f"color: {color};")
            health_layout.addWidget(lbl, row, 0, Qt.AlignRight)
            health_layout.addWidget(val, row, 1, Qt.AlignLeft)
            row += 1
            
            self._add_info_row(health_layout, row, "Classification:", classification)
            row += 1
            self._add_info_row(health_layout, row, "Profitability Score:", 
                             f"{health.get('profitability_score', 'N/A')}/100")
            row += 1
            self._add_info_row(health_layout, row, "Leverage Score:", 
                             f"{health.get('leverage_score', 'N/A')}/100")
            row += 1
            self._add_info_row(health_layout, row, "Growth Score:", 
                             f"{health.get('growth_score', 'N/A')}/100")
            
            content_layout.addWidget(health_group)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return tab
    
    def create_decision_summary_tab(self) -> QWidget:
        """Create decision summary tab with key metrics for decision-making."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Key Metrics Table
        metrics_group = QGroupBox("Key Decision Metrics")
        metrics_layout = QVBoxLayout(metrics_group)
        
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Metric", "Value", "Status"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        
        ratios = self.profile.get('financial_ratios', {})
        health = self.profile.get('health_indicators', {})
        growth_rates = self.profile.get('growth_rates', {})
        
        # Prepare metrics
        metrics_data = []
        
        # ROE
        roe = ratios.get('return_on_equity', 0)
        roe_status = "Excellent" if roe > 0.20 else "Good" if roe > 0.15 else "Fair" if roe > 0.10 else "Poor"
        roe_color = "green" if roe > 0.15 else "orange" if roe > 0.10 else "red"
        metrics_data.append(("Return on Equity (ROE)", f"{roe:.2%}", roe_status, roe_color))
        
        # ROA
        roa = ratios.get('return_on_assets', 0)
        roa_status = "Excellent" if roa > 0.10 else "Good" if roa > 0.05 else "Fair" if roa > 0.02 else "Poor"
        roa_color = "green" if roa > 0.05 else "orange" if roa > 0.02 else "red"
        metrics_data.append(("Return on Assets (ROA)", f"{roa:.2%}", roa_status, roa_color))
        
        # Debt to Equity
        de = ratios.get('debt_to_equity', 0)
        de_status = "Low" if de < 1 else "Moderate" if de < 2 else "High"
        de_color = "green" if de < 1 else "orange" if de < 2 else "red"
        metrics_data.append(("Debt to Equity", f"{de:.2f}", de_status, de_color))
        
        # Revenue Growth
        rev_growth = 0
        if 'Revenues' in growth_rates:
            rev_growth = growth_rates['Revenues'].get('avg_growth_rate', 0)
        growth_status = "Strong" if rev_growth > 15 else "Good" if rev_growth > 10 else "Moderate" if rev_growth > 5 else "Weak"
        growth_color = "green" if rev_growth > 10 else "orange" if rev_growth > 5 else "red"
        metrics_data.append(("Revenue Growth (Avg)", f"{rev_growth:.1f}%", growth_status, growth_color))
        
        # Health Score
        health_score = health.get('overall_health_score', 0)
        health_status = "Excellent" if health_score >= 80 else "Good" if health_score >= 70 else "Fair" if health_score >= 50 else "Poor"
        health_color = "green" if health_score >= 70 else "orange" if health_score >= 50 else "red"
        metrics_data.append(("Overall Health Score", f"{health_score:.1f}/100", health_status, health_color))
        
        # Populate table
        table.setRowCount(len(metrics_data))
        for row, (metric, value, status, color) in enumerate(metrics_data):
            table.setItem(row, 0, QTableWidgetItem(metric))
            table.setItem(row, 1, QTableWidgetItem(value))
            
            status_item = QTableWidgetItem(status)
            status_item.setForeground(QColor(color))
            status_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
            table.setItem(row, 2, status_item)
        
        metrics_layout.addWidget(table)
        content_layout.addWidget(metrics_group)
        
        # Investment Recommendation
        rec_group = QGroupBox("Investment Recommendation")
        rec_layout = QVBoxLayout(rec_group)
        
        # Check if AI/ML analysis exists and use its recommendation
        ai_analysis = self.profile.get('ai_analysis') or {}
        multi_analysis = self.profile.get('ai_analysis_multi', {})

        recommendation = None
        rec_source = ""

        # Try to get consensus from multi-model analysis
        if multi_analysis and len(multi_analysis) > 1:
            from collections import Counter
            recommendations = [a.get('recommendation', 'N/A') for a in multi_analysis.values() if isinstance(a, dict)]
            if recommendations:
                rec_counts = Counter(recommendations)
                most_common = rec_counts.most_common(1)[0]
                recommendation = most_common[0]
                rec_source = f" (AI Consensus: {most_common[1]}/{len(recommendations)} models)"

        # If no multi-model, try single AI analysis
        if not recommendation and ai_analysis and isinstance(ai_analysis, dict):
            recommendation = ai_analysis.get('recommendation')
            if recommendation:
                rec_source = " (AI Analysis)"

        # If no AI recommendation available, calculate based on metrics
        if not recommendation:
            # Calculate recommendation score
            score = 0
            if health_score >= 70: score += 2
            if roe > 0.15: score += 2
            if rev_growth > 10: score += 2
            if de < 1: score += 1
            if rev_growth < 0: score -= 2
            if health_score < 50: score -= 2

            if score >= 5:
                recommendation = "Strong Buy"
            elif score >= 3:
                recommendation = "Buy"
            elif score >= 0:
                recommendation = "Hold"
            elif score >= -2:
                recommendation = "Sell"
            else:
                recommendation = "Strong Sell"
            rec_source = " (Rules-Based)"

        # Determine color based on recommendation
        rec_color_map = {
            "Strong Buy": "darkgreen",
            "Buy": "green",
            "Hold": "orange",
            "Sell": "red",
            "Strong Sell": "darkred"
        }
        rec_color = rec_color_map.get(recommendation, "gray")

        rec_label = QLabel(f"Recommendation: {recommendation}{rec_source}")
        rec_label.setFont(QFont("Segoe UI", 14, QFont.Bold))
        rec_label.setStyleSheet(f"color: {rec_color}; padding: 10px;")
        rec_label.setAlignment(Qt.AlignCenter)
        rec_layout.addWidget(rec_label)
        
        # Risk Level
        risk_score = 0
        if de > 2: risk_score += 2
        if health_score < 50: risk_score += 2
        if rev_growth < 0: risk_score += 1
        
        risk_level = 'Low' if risk_score <= 1 else 'Medium' if risk_score <= 3 else 'High'
        risk_color_map = {'Low': 'green', 'Medium': 'orange', 'High': 'red'}
        
        risk_label = QLabel(f"Risk Level: {risk_level}")
        risk_label.setFont(QFont("Segoe UI", 12))
        risk_label.setStyleSheet(f"color: {risk_color_map[risk_level]}; padding: 5px;")
        risk_label.setAlignment(Qt.AlignCenter)
        rec_layout.addWidget(risk_label)
        
        content_layout.addWidget(rec_group)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return tab
    
    def create_financials_tab(self) -> QWidget:
        """Create financial trends tab with improved multi-view charts."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        time_series = self.profile.get('financial_time_series', {})
        
        if not time_series:
            layout.addWidget(QLabel("No financial time series data available"))
            return tab
        
        # Add scroll area for multiple charts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        # Key metrics to display with improved visibility
        metrics_to_plot = [
            ('Assets', 'Assets'),
            ('Liabilities', 'Liabilities'),
            ('Revenues', 'Revenue'),
            ('NetIncomeLoss', 'Net Income')
        ]
        
        for metric, title in metrics_to_plot:
            if metric not in time_series or not time_series[metric]:
                continue

            data = time_series[metric]
            dates = sorted(data.keys())
            values = [data[d] for d in dates]

            # Show all data points (removed 20-point limitation for full history)
            # User can see the complete financial history

            if not values or all(v == 0 for v in values):
                continue

            # Create figure with 3 subplots for different views
            fig = Figure(figsize=(15, 4), facecolor='#1e1e1e')
            canvas = SafeFigureCanvas(fig)
            canvas.setStyleSheet("background-color: #1e1e1e;")
            canvas.setMouseTracking(True)

            # Ensure canvas has enough vertical space so titles and x-labels are not clipped
            # Use a fixed vertical size but allow horizontal expansion in the scroll area
            canvas.setMinimumHeight(480)
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self._redirect_canvas_wheel_to_scroll(canvas, scroll)

            # Calculate different views
            x_pos = list(range(len(dates)))

            # Percentage change from previous period
            pct_change = [0]
            for i in range(1, len(values)):
                if values[i-1] != 0:
                    pct_change.append(((values[i] - values[i-1]) / abs(values[i-1])) * 100)
                else:
                    pct_change.append(0)

            # Indexed values (first value = 100)
            if values[0] != 0:
                indexed = [(v / abs(values[0])) * 100 for v in values]
            else:
                indexed = [100] * len(values)

            # Subplot 1: Absolute Values with better scaling
            ax1 = fig.add_subplot(131, facecolor='#2d2d2d')
            line1, = ax1.plot(x_pos, values, marker='o', linewidth=2, markersize=3, color='#4da6ff')
            ax1.fill_between(x_pos, values, alpha=0.3, color='#4da6ff')
            ax1.set_title(f'{title} - Absolute Values', fontsize=10, fontweight='bold', color='white')
            ax1.set_xlabel('Date', fontsize=8, color='white')
            ax1.set_ylabel('Value', fontsize=8, color='white')
            ax1.grid(True, alpha=0.3, axis='y', color='white')

            # Store dates in axes metadata for tooltip access
            ax1.dates_data = dates

            # Add annotation for hover - improved styling
            annot1 = ax1.annotate("", xy=(0,0), xytext=(15, 15), textcoords="offset points",
                                bbox=dict(boxstyle="round,pad=0.7", fc="#2d2d2d", ec="#4da6ff", alpha=0.95, linewidth=2),
                                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2",
                                              color="#4da6ff", lw=2),
                                fontsize=9, color="white", weight='bold', zorder=1000)
            annot1.set_visible(False)
            ax1.tick_params(axis='both', labelsize=7, colors='white')

            # Add Y-axis padding for better visibility
            y_min, y_max = min(values), max(values)
            y_range = y_max - y_min
            if y_range > 0:
                padding = y_range * 0.15  # 15% padding
                ax1.set_ylim(y_min - padding, y_max + padding)

            # Smart formatting
            if abs(y_max) >= 1e9:
                ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e9:.1f}B'))
            elif abs(y_max) >= 1e6:
                ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.1f}M'))
            else:
                ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e3:.1f}K'))

            # Set spine colors
            for spine in ax1.spines.values():
                spine.set_edgecolor('white')
                spine.set_linewidth(0.5)

            # Subplot 2: Percentage Change (Shows volatility!)
            ax2 = fig.add_subplot(132, facecolor='#2d2d2d')
            colors_pct = ['#28a745' if v >= 0 else '#dc3545' for v in pct_change]
            # Use full width bars - they'll touch but be more visible
            bars2 = ax2.bar(x_pos, pct_change, color=colors_pct, alpha=0.7, width=1.0)
            ax2.axhline(y=0, color='white', linestyle='-', linewidth=0.5)
            ax2.set_title(f'{title} - % Change Period-over-Period', fontsize=10, fontweight='bold', color='white')
            ax2.set_xlabel('Date', fontsize=8, color='white')
            ax2.set_ylabel('% Change', fontsize=8, color='white')
            ax2.grid(True, alpha=0.3, axis='y', color='white')
            ax2.tick_params(axis='both', labelsize=7, colors='white')
            ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))

            # Store dates in axes metadata for tooltip access
            ax2.dates_data = dates

            # Add annotation for hover - bar chart
            annot2 = ax2.annotate("", xy=(0,0), xytext=(15, 15), textcoords="offset points",
                                bbox=dict(boxstyle="round,pad=0.7", fc="#2d2d2d", ec="#4da6ff", alpha=0.95, linewidth=2),
                                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2",
                                              color="#4da6ff", lw=2),
                                fontsize=9, color="white", weight='bold', zorder=1000)
            annot2.set_visible(False)

            # Set spine colors
            for spine in ax2.spines.values():
                spine.set_edgecolor('white')
                spine.set_linewidth(0.5)

            # Subplot 3: Indexed (Base = 100, relative performance)
            ax3 = fig.add_subplot(133, facecolor='#2d2d2d')
            line3, = ax3.plot(x_pos, indexed, marker='o', linewidth=2, markersize=3, color='#4da6ff')
            ax3.axhline(y=100, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Baseline (100)')
            ax3.fill_between(x_pos, 100, indexed,
                            where=[i >= 100 for i in indexed],
                            alpha=0.2, color='green', label='Above Base')
            ax3.fill_between(x_pos, 100, indexed,
                            where=[i < 100 for i in indexed],
                            alpha=0.2, color='red', label='Below Base')
            ax3.set_title(f'{title} - Indexed (First Period = 100)', fontsize=10, fontweight='bold', color='white')
            ax3.set_xlabel('Date', fontsize=8, color='white')
            ax3.set_ylabel('Index', fontsize=8, color='white')
            ax3.grid(True, alpha=0.3, axis='y', color='white')
            ax3.tick_params(axis='both', labelsize=7, colors='white')
            ax3.legend(fontsize=6, loc='best', facecolor='#2d2d2d', edgecolor='white', labelcolor='white')

            # Store dates in axes metadata for tooltip access
            ax3.dates_data = dates

            # Add annotation for hover - indexed chart
            annot3 = ax3.annotate("", xy=(0,0), xytext=(15, 15), textcoords="offset points",
                                bbox=dict(boxstyle="round,pad=0.7", fc="#2d2d2d", ec="#4da6ff", alpha=0.95, linewidth=2),
                                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2",
                                              color="#4da6ff", lw=2),
                                fontsize=9, color="white", weight='bold', zorder=1000)
            annot3.set_visible(False)

            # Set spine colors
            for spine in ax3.spines.values():
                spine.set_edgecolor('white')
                spine.set_linewidth(0.5)

            # Set x-axis labels for all subplots
            for ax in [ax1, ax2, ax3]:
                step = max(1, len(dates) // 8)
                tick_positions = range(0, len(dates), step)
                tick_labels = [dates[i][:7] if i < len(dates) else '' for i in tick_positions]
                ax.set_xticks(tick_positions)
                ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=7, color='white')

            # Adjust bottom padding to prevent rotated x-labels from being clipped, then tighten layout
            try:
                fig.subplots_adjust(bottom=0.18)
            except Exception:
                pass
            fig.tight_layout(pad=2.0)

            # Enhanced hover functionality for all three subplots - use closure to capture variables
            def make_hover_handler(chart_ax1, chart_ax2, chart_ax3, chart_annot1, chart_annot2, chart_annot3,
                                  chart_dates, chart_values, chart_pct_change, chart_indexed, chart_canvas):
                def on_hover(event):
                    """Show data point info on hover for all subplots."""
                    if event.inaxes is None:
                        # Hide all annotations when not over any axes
                        for annot in [chart_annot1, chart_annot2, chart_annot3]:
                            if annot.get_visible():
                                annot.set_visible(False)
                        chart_canvas.draw_idle()
                        return

                    x, y = event.xdata, event.ydata
                    if x is None or y is None:
                        return

                    found_point = False

                    # Handle ax1 (line chart - absolute values)
                    if event.inaxes == chart_ax1:
                        x_positions = list(range(len(chart_values)))

                        if len(x_positions) > 0:
                            # Find nearest point
                            distances = [(abs(x_positions[i] - x), i) for i in range(len(x_positions))]
                            min_dist, idx = min(distances, key=lambda t: t[0])

                            # Check if close enough (increased sensitivity)
                            x_range = len(x_positions) - 1 if len(x_positions) > 1 else 1
                            if min_dist < x_range * 0.08:  # Increased from 0.05 for better detection
                                x_val = x_positions[idx]
                                y_val = chart_values[idx]

                                # Check y proximity (increased sensitivity)
                                y_range = max(chart_values) - min(chart_values) if max(chart_values) != min(chart_values) else 1
                                if abs(y_val - y) < y_range * 0.20:  # Increased from 0.15 for better detection
                                    # Format value
                                    if abs(y_val) >= 1e9:
                                        y_str = f"${y_val/1e9:.2f}B"
                                    elif abs(y_val) >= 1e6:
                                        y_str = f"${y_val/1e6:.2f}M"
                                    elif abs(y_val) >= 1e3:
                                        y_str = f"${y_val/1e3:.2f}K"
                                    else:
                                        y_str = f"${y_val:.2f}"

                                    period_str = chart_dates[idx][:10] if idx < len(chart_dates) else f"Point {idx}"
                                    chart_annot1.xy = (x_val, y_val)
                                    chart_annot1.set_text(f"{period_str}\n{y_str}")
                                    chart_annot1.set_visible(True)
                                    found_point = True

                    # Handle ax2 (bar chart - percentage change)
                    elif event.inaxes == chart_ax2:
                        # Check each bar
                        idx = int(round(x))
                        if 0 <= idx < len(chart_pct_change):
                            bar_height = chart_pct_change[idx]
                            period_str = chart_dates[idx][:10] if idx < len(chart_dates) else f"Point {idx}"
                            chart_annot2.xy = (idx, bar_height)
                            chart_annot2.set_text(f"{period_str}\n{bar_height:.2f}%")
                            chart_annot2.set_visible(True)
                            found_point = True

                    # Handle ax3 (line chart - indexed)
                    elif event.inaxes == chart_ax3:
                        x_positions = list(range(len(chart_indexed)))

                        if len(x_positions) > 0:
                            # Find nearest point
                            distances = [(abs(x_positions[i] - x), i) for i in range(len(x_positions))]
                            min_dist, idx = min(distances, key=lambda t: t[0])

                            # Check if close enough (increased sensitivity)
                            x_range = len(x_positions) - 1 if len(x_positions) > 1 else 1
                            if min_dist < x_range * 0.08:  # Increased from 0.05 for better detection
                                x_val = x_positions[idx]
                                y_val = chart_indexed[idx]

                                # Check y proximity (increased sensitivity)
                                y_range = max(chart_indexed) - min(chart_indexed) if max(chart_indexed) != min(chart_indexed) else 1
                                if abs(y_val - y) < y_range * 0.20:  # Increased from 0.15 for better detection
                                    period_str = chart_dates[idx][:10] if idx < len(chart_dates) else f"Point {idx}"
                                    chart_annot3.xy = (x_val, y_val)
                                    chart_annot3.set_text(f"{period_str}\nIndex: {y_val:.1f}")
                                    chart_annot3.set_visible(True)
                                    found_point = True

                    # Hide annotations if not near any point
                    if not found_point:
                        if event.inaxes == chart_ax1 and chart_annot1.get_visible():
                            chart_annot1.set_visible(False)
                        elif event.inaxes == chart_ax2 and chart_annot2.get_visible():
                            chart_annot2.set_visible(False)
                        elif event.inaxes == chart_ax3 and chart_annot3.get_visible():
                            chart_annot3.set_visible(False)

                    chart_canvas.draw_idle()

                return on_hover

            canvas.mpl_connect("motion_notify_event", make_hover_handler(ax1, ax2, ax3, annot1, annot2, annot3, dates, values, pct_change, indexed, canvas))

            # Redirect the mouse wheel to the scroll area so the entire section scrolls.
            self._redirect_canvas_wheel_to_scroll(canvas, scroll)

            # Make chart clickable to open in interactive window
            def make_chart_click_handler(chart_dates, chart_values, chart_pct_change, chart_indexed, chart_x_pos, chart_title, chart_ax1, chart_ax2, chart_ax3, y_max):
                """Create click handler with properly captured variables"""
                def on_click(event):
                    if event.dblclick and event.inaxes:
                        # Create new figure with only the clicked subplot
                        new_fig = Figure(figsize=(14, 8), facecolor='#1e1e1e')
                        new_ax = new_fig.add_subplot(111, facecolor='#2d2d2d')

                        # Determine which subplot was clicked and recreate it
                        if event.inaxes == chart_ax1:
                            # Absolute values chart
                            new_ax.plot(chart_x_pos, chart_values, marker='o', linewidth=2, markersize=4, color='#4da6ff', label='Actual Values')
                            new_ax.fill_between(chart_x_pos, chart_values, alpha=0.3, color='#4da6ff')
                            new_ax.set_title(f'{chart_title} - Absolute Values', fontsize=14, fontweight='bold', color='white')
                            new_ax.set_ylabel('Value', fontsize=12, color='white')

                            # Add Y-axis padding
                            y_min, y_max = min(chart_values), max(chart_values)
                            y_range = y_max - y_min
                            if y_range > 0:
                                padding = y_range * 0.15
                                new_ax.set_ylim(y_min - padding, y_max + padding)

                            # Smart formatting
                            if abs(y_max) >= 1e9:
                                new_ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e9:.2f}B'))
                            elif abs(y_max) >= 1e6:
                                new_ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e6:.2f}M'))
                            else:
                                new_ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x/1e3:.2f}K'))

                        elif event.inaxes == chart_ax2:
                            # Percentage change chart
                            colors_pct = ['#28a745' if v >= 0 else '#dc3545' for v in chart_pct_change]
                            # Use full width bars for better visibility
                            new_ax.bar(chart_x_pos, chart_pct_change, color=colors_pct, alpha=0.8, width=1.0, edgecolor='white', linewidth=0.5)
                            new_ax.axhline(y=0, color='white', linestyle='-', linewidth=1)
                            new_ax.set_title(f'{chart_title} - % Change Period-over-Period', fontsize=14, fontweight='bold', color='white')
                            new_ax.set_ylabel('% Change', fontsize=12, color='white')
                            new_ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))

                        elif event.inaxes == chart_ax3:
                            # Indexed chart
                            new_ax.plot(chart_x_pos, chart_indexed, marker='o', linewidth=2, markersize=4, color='#4da6ff', label='Indexed Value')
                            new_ax.axhline(y=100, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Baseline (100)')
                            new_ax.fill_between(chart_x_pos, 100, chart_indexed,
                                              where=[i >= 100 for i in chart_indexed],
                                              alpha=0.2, color='green', label='Above Base')
                            new_ax.fill_between(chart_x_pos, 100, chart_indexed,
                                              where=[i < 100 for i in chart_indexed],
                                              alpha=0.2, color='red', label='Below Base')
                            new_ax.set_title(f'{chart_title} - Indexed (First Period = 100)', fontsize=14, fontweight='bold', color='white')
                            new_ax.set_ylabel('Index', fontsize=12, color='white')
                            new_ax.legend(fontsize=10, loc='best', facecolor='#2d2d2d', edgecolor='white', labelcolor='white')

                        # Common formatting
                        new_ax.set_xlabel('Date', fontsize=12, color='white')
                        new_ax.grid(True, alpha=0.2, axis='y', color='white')
                        new_ax.tick_params(colors='white')

                        # Store dates in new axes for tooltip access
                        new_ax.dates_data = chart_dates

                        # Set x-axis labels
                        step = max(1, len(chart_dates) // 10)
                        tick_positions = range(0, len(chart_dates), step)
                        tick_labels = [chart_dates[i][:10] if i < len(chart_dates) else '' for i in tick_positions]
                        new_ax.set_xticks(tick_positions)
                        new_ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=10, color='white')

                        # Set spine colors
                        for spine in new_ax.spines.values():
                            spine.set_edgecolor('white')
                            spine.set_linewidth(0.5)

                        new_fig.tight_layout()

                        # Make chart scrollable if there are many data points
                        # Show initial window of ~100 points, user can pan to see rest
                        if len(chart_dates) > 100:
                            initial_window = 100
                            new_ax.set_xlim(-2, initial_window + 2)  # Show first 100 points with small padding
                            # User can use pan tool or scroll to see rest

                        # Open interactive viewer
                        viewer = InteractiveChartViewer(new_fig, f"{chart_title} - Interactive View", self)
                        viewer.exec()
                return on_click

            canvas.mpl_connect("button_press_event", make_chart_click_handler(dates, values, pct_change, indexed, x_pos, title, ax1, ax2, ax3, y_max))

            # Add label instruction
            instruction_label = QLabel("💡 Hover over data points to see values | Double-click on any chart to open interactive view with zoom and pan")
            instruction_label.setStyleSheet("color: #4da6ff; font-size: 10px; padding: 5px; font-style: italic;")
            content_layout.addWidget(instruction_label)

            # Add canvas to layout
            content_layout.addWidget(canvas)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        return tab

    def create_ratios_tab(self) -> QWidget:
        """Create financial ratios tab with radar representation, explanations, and resizable sections."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        ratios = self.profile.get('financial_ratios', {}) or {}
        latest = self.profile.get('latest_financials', {})

        if not ratios and not latest:
            layout.addWidget(QLabel("No financial ratios or latest financials available"))
            return tab

        ratios_norm = {k.lower(): v for k, v in ratios.items()}

        def _value_from_latest(*keys):
            for key in keys:
                if key in latest and latest.get(key) not in (None, 'N/A'):
                    try:
                        return float(latest.get(key))
                    except Exception:
                        continue
            return None

        latest_values = {
            'assets': _value_from_latest('Assets', 'TotalAssets', 'assets'),
            'liabilities': _value_from_latest('Liabilities', 'TotalLiabilities', 'liabilities'),
            'equity': _value_from_latest('StockholdersEquity', 'ShareholdersEquity', 'equity'),
            'revenues': _value_from_latest('Revenues', 'Revenue', 'SalesRevenueNet'),
            'net_income': _value_from_latest('NetIncomeLoss', 'NetIncome', 'net_income'),
            'cash': _value_from_latest('CashAndCashEquivalentsAtCarryingValue', 'Cash', 'cash_and_cash_equivalents'),
            'current_assets': _value_from_latest('CurrentAssets', 'current_assets'),
            'current_liabilities': _value_from_latest('CurrentLiabilities', 'current_liabilities')
        }

        ratio_specs = [
            {'key': 'current_ratio', 'label': 'Current Ratio', 'formula': 'Current Assets / Current Liabilities',
             'explanation': 'Liquidity: ability to cover near-term obligations.', 'target': 1.5, 'precision': 2},
            {'key': 'cash_ratio', 'label': 'Cash Ratio', 'formula': 'Cash / Current Liabilities',
             'explanation': 'Cash cushion: more conservative liquidity view.', 'target': 1.0, 'precision': 2},
            {'key': 'debt_to_equity', 'label': 'Debt to Equity', 'formula': 'Total Liabilities / Equity',
             'explanation': 'Leverage: lower values preferred.', 'target': 1.5, 'precision': 2},
            {'key': 'debt_to_assets', 'label': 'Debt to Assets', 'formula': 'Total Liabilities / Assets',
             'explanation': 'Indicates what portion of assets is financed by debt.', 'target': 0.6, 'precision': 2},
            {'key': 'profit_margin', 'label': 'Profit Margin', 'formula': 'Net Income / Revenues',
             'explanation': 'How much revenue remains as profit.', 'percent': True, 'target': 0.15, 'precision': 1},
            {'key': 'asset_turnover', 'label': 'Asset Turnover', 'formula': 'Revenue / Assets',
             'explanation': 'Efficiency: revenue per dollar of assets.', 'target': 1.0, 'precision': 2},
            {'key': 'return_on_equity', 'label': 'Return on Equity (ROE)', 'formula': 'Net Income / Equity',
             'explanation': 'Shareholder return: compare to cost of equity.', 'percent': True, 'target': 0.18, 'precision': 1},
            {'key': 'return_on_assets', 'label': 'Return on Assets (ROA)', 'formula': 'Net Income / Assets',
             'explanation': 'Overall profitability independent of capital structure.', 'percent': True, 'target': 0.12, 'precision': 1},
        ]

        def _from_ratios(candidate_keys):
            for candidate in candidate_keys:
                candidate = candidate.lower()
                val = ratios_norm.get(candidate)
                if isinstance(val, (int, float)):
                    return float(val)
                try:
                    return float(str(val))
                except Exception:
                    continue
            return None

        computed = []
        for spec in ratio_specs:
            value = _from_ratios([spec['key'], spec['key'].replace('_', ''), spec['key'].replace('_', ' ')])
            source = 'Reported'
            if value is None:
                try:
                    if spec['key'] == 'current_ratio':
                        ca = latest_values['current_assets']; cl = latest_values['current_liabilities']
                        if ca is not None and cl:
                            value = ca / cl; source = 'Derived'
                    elif spec['key'] == 'cash_ratio':
                        cash = latest_values['cash']; cl = latest_values['current_liabilities']
                        if cash is not None and cl:
                            value = cash / cl; source = 'Derived'
                    elif spec['key'] == 'debt_to_equity':
                        liab = latest_values['liabilities']; equity = latest_values['equity']
                        if liab is not None and equity:
                            value = liab / equity; source = 'Derived'
                    elif spec['key'] == 'debt_to_assets':
                        liab = latest_values['liabilities']; assets = latest_values['assets']
                        if liab is not None and assets:
                            value = liab / assets; source = 'Derived'
                    elif spec['key'] == 'profit_margin':
                        ni = latest_values['net_income']; rev = latest_values['revenues']
                        if ni is not None and rev:
                            value = ni / rev; source = 'Derived'
                    elif spec['key'] == 'asset_turnover':
                        rev = latest_values['revenues']; assets = latest_values['assets']
                        if rev is not None and assets:
                            value = rev / assets; source = 'Derived'
                    elif spec['key'] == 'return_on_equity':
                        ni = latest_values['net_income']; equity = latest_values['equity']
                        if ni is not None and equity:
                            value = ni / equity; source = 'Derived'
                    elif spec['key'] == 'return_on_assets':
                        ni = latest_values['net_income']; assets = latest_values['assets']
                        if ni is not None and assets:
                            value = ni / assets; source = 'Derived'
                except Exception:
                    continue
            if value is not None:
                computed.append((spec, float(value), source))

        if not computed:
            layout.addWidget(QLabel("No numeric ratio data could be computed or reported."))
            return tab

        settings = QSettings("FundamentalDataPipeline", "ProfileVisualization")

        def _restore_splitter_state(splitter_obj, key, fallback_sizes):
            state = settings.value(key)
            if isinstance(state, QByteArray):
                try:
                    splitter_obj.restoreState(state)
                    return
                except Exception:
                    pass
            elif state:
                try:
                    splitter_obj.restoreState(QByteArray(state))
                    return
                except Exception:
                    pass
            splitter_obj.setSizes(fallback_sizes)

        def _persist_splitter_state(key, splitter_obj):
            settings.setValue(key, splitter_obj.saveState())

        main_splitter = QSplitter(Qt.Vertical)
        _restore_splitter_state(main_splitter, 'ratios/main_splitter_state', [480, 260])
        main_splitter.splitterMoved.connect(lambda pos, idx: _persist_splitter_state('ratios/main_splitter_state', main_splitter))

        top_splitter = QSplitter(Qt.Horizontal)
        _restore_splitter_state(top_splitter, 'ratios/top_horizontal_state', [800, 400])
        top_splitter.splitterMoved.connect(lambda pos, idx: _persist_splitter_state('ratios/top_horizontal_state', top_splitter))

        # Radar chart area
        chart_widget = QWidget()
        chart_layout = QVBoxLayout(chart_widget)
        chart_layout.setContentsMargins(0, 0, 0, 0)

        fig = Figure(figsize=(8, 5), facecolor='#1e1e1e')
        canvas = SafeFigureCanvas(fig)
        ax = fig.add_subplot(111, polar=True, facecolor='#1e1e1e')

        sorted_specs = sorted(computed, key=lambda item: item[0]['label'])
        labels = [item[0]['label'] for item in sorted_specs]
        targets = [item[0].get('target', 1) for item in sorted_specs]
        raw_values = [item[1] for item in sorted_specs]
        normalized = []
        for value, target in zip(raw_values, targets):
            if target and target != 0:
                normalized.append(min(1.2, max(0.0, value / target)))
            else:
                normalized.append(0.0)

        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        base_angles = angles[:]
        base_normalized = normalized[:]
        normalized.append(normalized[0])
        angles.append(angles[0])

        ax.plot(angles, normalized, color='#4da6ff', linewidth=2)
        ax.fill(angles, normalized, color='#4da6ff', alpha=0.25)
        ax.set_xticks(np.array(angles[:-1]))
        ax.set_xticklabels(labels, fontsize=10, color='white')
        ax.set_ylim(0, 1.2)
        ax.set_yticks([0.4, 0.8, 1.2])
        ax.set_yticklabels(['Subpar', 'On Track', 'Exceeds'], fontsize=8, color='white')

        def _format_value(value, percent=False):
            if value is None:
                return 'N/A'
            if percent:
                return f"{value * 100:.1f}%"
            if abs(value) >= 1e6:
                return f"{value / 1e6:.2f}M"
            if abs(value) >= 1e3:
                return f"{value / 1e3:.2f}K"
            return f"{value:.2f}"

        radar_points = []
        for (spec, raw_value, source), angle, norm_val, target in zip(sorted_specs, base_angles, base_normalized, targets):
            radar_points.append({
                'angle': angle,
                'normalized': norm_val,
                'label': spec['label'],
                'value': raw_value,
                'target': target,
                'source': source,
                'percent': spec.get('percent', False),
                'formatted_value': _format_value(raw_value, spec.get('percent', False)),
                'formatted_target': _format_value(target, spec.get('percent', False))
            })

        hover_annot = ax.annotate("", xy=(0, 0), xytext=(15, 15), textcoords="offset points",
                                 bbox=dict(boxstyle="round,pad=0.7", fc="#1e1e1e", ec="#4da6ff", alpha=0.95, linewidth=2),
                                 arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2",
                                                 color="#4da6ff", lw=2),
                                 fontsize=10, color="white", weight='bold', zorder=1000)
        hover_annot.set_visible(False)

        def on_radar_hover(event):
            if event.inaxes != ax or event.xdata is None or event.ydata is None:
                if hover_annot.get_visible():
                    hover_annot.set_visible(False)
                    canvas.draw_idle()
                return

            angle = event.xdata % (2 * np.pi)
            closest = None
            min_diff = float('inf')
            for point in radar_points:
                diff = abs((angle - point['angle'] + np.pi) % (2 * np.pi) - np.pi)
                if diff < min_diff:
                    min_diff = diff
                    closest = point

            if closest and min_diff < 0.35:
                hover_annot.xy = (closest['angle'], max(closest['normalized'], 0.05))
                text = (f"{closest['label']}\nValue: {closest['formatted_value']}\n"
                        f"Target: {closest['formatted_target']}\nSource: {closest['source']}")
                hover_annot.set_text(text)
                if not hover_annot.get_visible():
                    hover_annot.set_visible(True)
                canvas.draw_idle()
            elif hover_annot.get_visible():
                hover_annot.set_visible(False)
                canvas.draw_idle()

        canvas.mpl_connect("motion_notify_event", on_radar_hover)

        def _on_click(event):
            if event.dblclick:
                viewer = InteractiveChartViewer(fig, "Financial Ratios - Radar View", self)
                viewer.exec()

        canvas.mpl_connect("button_press_event", _on_click)
        chart_layout.addWidget(canvas)
        top_splitter.addWidget(chart_widget)

        table_group = QGroupBox('Ratio Details & Interpretation')
        table_layout = QVBoxLayout(table_group)
        table = QTableWidget()
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(['Ratio', 'Value', 'Formula / Source', 'Interpretation'])
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)

        table.setRowCount(len(sorted_specs))
        for row_idx, (spec, raw_value, source) in enumerate(sorted_specs):
            display_value = _format_value(raw_value, spec.get('percent', False))
            table.setItem(row_idx, 0, QTableWidgetItem(spec['label']))
            table.setItem(row_idx, 1, QTableWidgetItem(display_value))
            formula_text = spec.get('formula', 'Reported')
            table.setItem(row_idx, 2, QTableWidgetItem(f"{formula_text} ({source})"))
            interp_item = QTableWidgetItem(spec.get('explanation', ''))
            interp_item.setFlags(interp_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row_idx, 3, interp_item)

        table_layout.addWidget(table)
        table_group.setMinimumHeight(250)

        expl_group = QGroupBox('How to Use These Ratios')
        expl_layout = QVBoxLayout(expl_group)
        expl_text = QLabel(
            '• Liquidity (Current/Cash ratios) highlights how comfortably the firm covers short-term debts; values above 1.0 are typical comfort zones.\n'
            '• Leverage (Debt/Equity, Debt/Assets) should be compared to industry norms; higher values signal reliance on debt.\n'
            '• Profitability (ROA, ROE, Profit Margin) shows earnings efficiency; compare them to peers and the cost of capital.\n'
            '• Efficiency (Asset Turnover) reveals how effectively assets generate revenue.\n'
            '• This radar normalizes each ratio to a healthy target so you can spot strengths/weaknesses at a glance.'
        )
        expl_text.setWordWrap(True)
        expl_text.setStyleSheet('color: #ccc; padding: 5px;')
        expl_layout.addWidget(expl_text)
        top_splitter.addWidget(expl_group)

        floppy_instruction = QLabel("💡 Double-click the radar chart to open an interactive view.")
        floppy_instruction.setStyleSheet("color: #4da6ff; font-size: 10px; padding: 5px;")
        expl_layout.addWidget(floppy_instruction)

        top_container = QWidget()
        top_container.setLayout(QVBoxLayout())
        top_container.layout().setContentsMargins(0, 0, 0, 0)
        top_container.layout().addWidget(top_splitter)
        main_splitter.addWidget(top_container)
        main_splitter.addWidget(table_group)

        layout.addWidget(main_splitter)

        return tab

    def create_growth_tab(self) -> QWidget:
        """Create growth analysis tab with comprehensive period data."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        growth_rates = self.profile.get('growth_rates', {})
        
        if not growth_rates:
            layout.addWidget(QLabel("No growth rate data available"))
            return tab
        
        # Add scroll area for multiple charts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)

        metrics = ['Revenues', 'Assets', 'NetIncomeLoss']
        charts_created = 0

        for metric in metrics:
            if metric not in growth_rates:
                continue

            data = growth_rates[metric]
            pop = data.get('period_over_period', [])

            if not pop or len(pop) == 0:
                continue

            # Extract all data
            periods = [p['period'] for p in pop]
            rates = [p['growth_rate'] for p in pop]

            if len(periods) == 0 or len(rates) == 0:
                continue

            # Create larger figure for each metric - IMPORTANT: Keep reference!
            fig = Figure(figsize=(14, 5), facecolor='#1e1e1e')
            canvas = SafeFigureCanvas(fig)
            canvas.setStyleSheet("background-color: #1e1e1e;")
            canvas.setMouseTracking(True)

            # Ensure canvas has enough vertical space so titles and x-labels are not clipped
            # Use a fixed vertical size but allow horizontal expansion in the scroll area
            canvas.setMinimumHeight(480)
            canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            self._redirect_canvas_wheel_to_scroll(canvas, scroll)

            # Create main chart
            ax = fig.add_subplot(111, facecolor='#2d2d2d')

            # Line chart with filled areas for positive/negative growth
            x_positions = list(range(len(periods)))

            # Plot line chart
            ax.plot(x_positions, rates, color='#4da6ff', linewidth=2, marker='o',
                   markersize=3, markerfacecolor='#4da6ff', markeredgecolor='white',
                   markeredgewidth=0.5, label='Growth Rate', zorder=3)

            # Fill areas above/below zero with different colors
            ax.fill_between(x_positions, 0, rates,
                           where=[r >= 0 for r in rates],
                           alpha=0.3, color='#28a745', label='Positive Growth',
                           interpolate=True)
            ax.fill_between(x_positions, 0, rates,
                           where=[r < 0 for r in rates],
                           alpha=0.3, color='#dc3545', label='Negative Growth',
                           interpolate=True)

            # Add zero line
            ax.axhline(y=0, color='white', linestyle='-', linewidth=1.5, alpha=0.7, zorder=2)

            # Add average line
            avg = data.get('avg_growth_rate', 0)
            ax.axhline(y=avg, color='#FFD700', linestyle='--', linewidth=2,
                     label=f'Average: {avg:.1f}%', alpha=0.9, zorder=2)

            # Formatting
            metric_name = metric.replace('NetIncomeLoss', 'Net Income')
            ax.set_title(f'{metric_name} - Period Growth Rate', fontsize=14, fontweight='bold', color='white', pad=15)
            ax.set_xlabel('Period', fontsize=11, color='white')
            ax.set_ylabel('Growth Rate (%)', fontsize=11, color='white')
            ax.grid(True, alpha=0.2, axis='y', color='white')
            ax.tick_params(colors='white', labelsize=9)

            # Store periods data for tooltip access
            ax.dates_data = periods

            # Set x-axis labels - show subset to prevent overlap
            # Calculate step to show ~15-20 labels max
            num_labels_to_show = min(20, len(periods))
            step = max(1, len(periods) // num_labels_to_show)

            # Set tick positions at intervals
            tick_positions = list(range(0, len(periods), step))
            # Always include the last position
            if tick_positions[-1] != len(periods) - 1:
                tick_positions.append(len(periods) - 1)

            ax.set_xticks(tick_positions)

            # Format period labels (extract year-quarter if possible)
            formatted_periods = []
            for i in tick_positions:
                p = periods[i]
                try:
                    # Try to extract meaningful date
                    if '-' in p:
                        parts = p.split('-')
                        if len(parts) >= 2:
                            formatted_periods.append(f"{parts[0]}-{parts[1][:2]}")
                        else:
                            formatted_periods.append(p[:10])
                    else:
                        formatted_periods.append(p[:10])
                except:
                    formatted_periods.append(str(p)[:10])

            ax.set_xticklabels(formatted_periods, rotation=45, ha='right', fontsize=9, color='white')

            # Set y-axis limits with padding
            if len(rates) > 0:
                min_rate = min(rates)
                max_rate = max(rates)
                # Add 20% padding to y-axis
                y_range = max_rate - min_rate
                if y_range > 0:
                    padding = y_range * 0.2
                    ax.set_ylim(min_rate - padding, max_rate + padding)
                else:
                    # If all values are the same, set reasonable limits
                    if min_rate == 0:
                        ax.set_ylim(-1, 1)
                    else:
                        ax.set_ylim(min_rate * 0.8, min_rate * 1.2)

            # Add value labels on significant peaks and troughs
            if len(rates) > 0 and max(rates) != min(rates):
                # Label the highest and lowest points
                max_idx = rates.index(max(rates))
                min_idx = rates.index(min(rates))

                # Label max
                ax.annotate(f'{rates[max_idx]:.1f}%',
                           xy=(max_idx, rates[max_idx]),
                           xytext=(0, 10), textcoords='offset points',
                           ha='center', fontsize=9, color='white', weight='bold',
                           bbox=dict(boxstyle='round,pad=0.3', fc='#28a745', alpha=0.7))

                # Label min if it's negative
                if rates[min_idx] < 0:
                    ax.annotate(f'{rates[min_idx]:.1f}%',
                               xy=(min_idx, rates[min_idx]),
                               xytext=(0, -15), textcoords='offset points',
                               ha='center', fontsize=9, color='white', weight='bold',
                               bbox=dict(boxstyle='round,pad=0.3', fc='#dc3545', alpha=0.7))

            # Legend positioned to avoid obscuring data
            ax.legend(fontsize=9, loc='upper left', facecolor='#2d2d2d', edgecolor='white',
                     labelcolor='white', framealpha=0.9)
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))

            # Set spine colors
            for spine in ax.spines.values():
                spine.set_edgecolor('white')
                spine.set_linewidth(0.5)

            # Add hover annotation for embedded chart
            hover_annot = ax.annotate("", xy=(0,0), xytext=(15, 15), textcoords="offset points",
                                     bbox=dict(boxstyle="round,pad=0.7", fc="#2d2d2d", ec="#4da6ff", alpha=0.95, linewidth=2),
                                     arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=.2",
                                                   color="#4da6ff", lw=2),
                                     fontsize=10, color="white", weight='bold', zorder=1000)
            hover_annot.set_visible(False)

            # Add hover event handler for embedded chart
            def make_hover_handler(chart_ax, chart_periods, chart_rates, chart_annot, chart_canvas):
                def on_hover(event):
                    if event.inaxes != chart_ax:
                        if chart_annot.get_visible():
                            chart_annot.set_visible(False)
                            chart_canvas.draw_idle()
                        return

                    x, y = event.xdata, event.ydata
                    if x is None or y is None:
                        return

                    # Find nearest point
                    x_data = list(range(len(chart_rates)))
                    if len(x_data) == 0:
                        return

                    distances = [(abs(x_data[i] - x), i) for i in range(len(x_data))]
                    min_dist, idx = min(distances, key=lambda t: t[0])

                    # Check if close enough (increased sensitivity)
                    x_range = len(x_data) - 1 if len(x_data) > 1 else 1
                    if min_dist < x_range * 0.08:  # Increased from 0.05 for better detection
                        x_val = x_data[idx]
                        y_val = chart_rates[idx]

                        # Check y proximity
                        y_range = max(chart_rates) - min(chart_rates) if max(chart_rates) != min(chart_rates) else 1
                        if abs(y_val - y) < y_range * 0.20:  # Increased from 0.15 for better detection
                            period_str = chart_periods[idx][:10] if idx < len(chart_periods) else f"Point {idx}"
                            chart_annot.xy = (x_val, y_val)
                            chart_annot.set_text(f"{period_str}\n{y_val:.2f}%")
                            chart_annot.set_visible(True)
                            chart_canvas.draw_idle()
                            return

                    # Hide if not near any point
                    if chart_annot.get_visible():
                        chart_annot.set_visible(False)
                        chart_canvas.draw_idle()

                return on_hover

            canvas.mpl_connect("motion_notify_event", make_hover_handler(ax, periods, rates, hover_annot, canvas))

            fig.tight_layout()

            # Make chart interactive - IMPORTANT: Properly capture variables for each chart
            def make_click_handler(captured_periods, captured_rates, captured_avg, captured_formatted_periods, name):
                def handler(event):
                    if event.dblclick:
                        # Create a COPY of the figure for the interactive viewer
                        new_fig = Figure(figsize=(14, 8), facecolor='#1e1e1e')
                        new_ax = new_fig.add_subplot(111, facecolor='#2d2d2d')

                        # Recreate the chart in the new figure
                        x_pos = list(range(len(captured_periods)))

                        # Plot line chart with filled areas
                        new_ax.plot(x_pos, captured_rates, color='#4da6ff', linewidth=2.5,
                                   marker='o', markersize=4, markerfacecolor='#4da6ff',
                                   markeredgecolor='white', markeredgewidth=0.8,
                                   label='Growth Rate', zorder=3)

                        # Fill areas above/below zero
                        new_ax.fill_between(x_pos, 0, captured_rates,
                                           where=[r >= 0 for r in captured_rates],
                                           alpha=0.3, color='#28a745', label='Positive Growth',
                                           interpolate=True)
                        new_ax.fill_between(x_pos, 0, captured_rates,
                                           where=[r < 0 for r in captured_rates],
                                           alpha=0.3, color='#dc3545', label='Negative Growth',
                                           interpolate=True)

                        # Add zero line
                        new_ax.axhline(y=0, color='white', linestyle='-', linewidth=1.5, alpha=0.7, zorder=2)

                        # Add average line
                        new_ax.axhline(y=captured_avg, color='#FFD700', linestyle='--', linewidth=2.5,
                                     label=f'Average: {captured_avg:.1f}%', alpha=0.9, zorder=2)

                        new_ax.set_title(f'{name} - Period Growth Rate', fontsize=16, fontweight='bold', color='white', pad=15)
                        new_ax.set_xlabel('Period', fontsize=13, color='white')
                        new_ax.set_ylabel('Growth Rate (%)', fontsize=13, color='white')
                        new_ax.grid(True, alpha=0.2, axis='y', color='white')
                        new_ax.tick_params(colors='white', labelsize=11)

                        # Store periods data for tooltip access
                        new_ax.dates_data = captured_periods

                        # Show subset of labels to prevent overlap
                        num_labels_to_show = min(20, len(captured_periods))
                        step = max(1, len(captured_periods) // num_labels_to_show)
                        tick_positions = list(range(0, len(captured_periods), step))
                        # Always include the last position
                        if tick_positions[-1] != len(captured_periods) - 1:
                            tick_positions.append(len(captured_periods) - 1)

                        new_ax.set_xticks(tick_positions)
                        # Get labels only for the tick positions
                        tick_labels = [captured_formatted_periods[i] if i < len(captured_formatted_periods) else '' for i in tick_positions]
                        new_ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=10, color='white')

                        new_ax.legend(fontsize=11, loc='upper left', facecolor='#2d2d2d', edgecolor='white',
                                     labelcolor='white', framealpha=0.9)
                        new_ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x:.1f}%'))

                        for spine in new_ax.spines.values():
                            spine.set_edgecolor('white')
                            spine.set_linewidth(0.5)

                        new_fig.tight_layout()

                        # Make chart scrollable if there are many data points
                        # Show initial window of ~100 points, user can pan to see rest
                        if len(captured_periods) > 100:
                            initial_window = 100
                            new_ax.set_xlim(-2, initial_window + 2)  # Show first 100 points with small padding
                            # User can use pan tool or scroll to see rest

                        # Open interactive viewer
                        viewer = InteractiveChartViewer(new_fig, f"{name} Growth Rate - Interactive View", self)
                        viewer.exec()
                return handler

            canvas.mpl_connect("button_press_event", make_click_handler(periods, rates, avg, formatted_periods, metric_name))

            content_layout.addWidget(canvas)
            charts_created += 1

            # Add instruction label
            instruction_label = QLabel("💡 Hover over data points to see values | Double-click to open interactive view with zoom and pan")
            instruction_label.setStyleSheet("color: #4da6ff; font-size: 10px; padding: 5px; font-style: italic;")
            content_layout.addWidget(instruction_label)

        if charts_created == 0:
            layout.addWidget(QLabel("No growth data available to display"))
        else:
            scroll.setWidget(content)
            layout.addWidget(scroll)

        return tab
    
    def create_health_tab(self) -> QWidget:
        """Create health indicators tab with redesigned cards, radar, and guidance."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        health = self.profile.get('health_indicators', {})
        latest = self.profile.get('latest_financials', {})

        if not health:
            layout.addWidget(QLabel("No health indicator data available"))
            return tab

        def _safe_number(value):
            try:
                return float(value)
            except (TypeError, ValueError):
                return None

        def _safe_ratio(num_key, denom_key):
            numerator = _safe_number(latest.get(num_key))
            denominator = _safe_number(latest.get(denom_key))
            if numerator is None or denominator in (None, 0):
                return None
            return numerator / denominator

        indicator_summary = [
            {
                'label': 'Overall Health',
                'value': health.get('overall_health_score', 0),
                'target': '≥ 70',
                'meaning': 'Composite view across profitability, leverage, growth, and liquidity.'
            },
            {
                'label': 'Profitability',
                'value': health.get('profitability_score', 0),
                'target': '≥ 70',
                'meaning': 'Reflects ROA/ROE and margin efficiency.'
            },
            {
                'label': 'Leverage',
                'value': health.get('leverage_score', 0),
                'target': '≤ 50',
                'meaning': 'Tracks debt pressure relative to capital and cash flows.'
            },
            {
                'label': 'Growth',
                'value': health.get('growth_score', 0),
                'target': '≥ 60',
                'meaning': 'Revenue and earnings momentum compared to history.'
            }
        ]

        derived_metrics = [
            {
                'label': 'Current Ratio',
                'value': _safe_ratio('CurrentAssets', 'CurrentLiabilities'),
                'target': '≥ 1.5',
                'calc': 'Current Assets / Current Liabilities',
                'meaning': 'Liquidity buffer versus short-term debt.'
            },
            {
                'label': 'Debt to Equity',
                'value': _safe_ratio('Liabilities', 'StockholdersEquity'),
                'target': '≤ 1.25',
                'calc': 'Total Liabilities / Stockholders Equity',
                'meaning': 'Measures financial leverage.'
            },
            {
                'label': 'Profitability Premium',
                'value': _safe_ratio('NetIncomeLoss', 'Revenues'),
                'target': '≥ 10%',
                'calc': 'Net Income / Revenue',
                'meaning': 'Highlights net margin context.'
            }
        ]

        def _color_for_score(score):
            if score is None:
                return '#555555'
            if score >= 70:
                return '#4CAF50'
            if score >= 50:
                return '#FFB300'
            return '#F44336'

        main_vertical = QSplitter(Qt.Vertical)
        description_splitter = QSplitter(Qt.Horizontal)

        cards_widget = QWidget()
        cards_layout = QGridLayout(cards_widget)
        cards_layout.setSpacing(12)

        for idx, metric in enumerate(indicator_summary):
            card = QWidget()
            card.setStyleSheet("background-color: #1d1d1d; border: 1px solid #2e2e2e; border-radius: 8px;")
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 10)

            title = QLabel(metric['label'])
            title.setFont(QFont("Segoe UI", 10, QFont.Bold))
            title.setStyleSheet("color: #9aa8bd;")

            value = metric['value']
            value_label = QLabel("N/A" if value is None else f"{value:.1f}")
            value_label.setFont(QFont("Segoe UI", 24, QFont.Bold))
            value_label.setStyleSheet(f"color: {_color_for_score(value)};")

            target_label = QLabel(f"Target: {metric['target']}")
            target_label.setStyleSheet("color: #cccccc; font-size: 11px;")

            desc_label = QLabel(metric['meaning'])
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #b4b9c4; font-size: 11px;")

            progress = QProgressBar()
            progress.setRange(0, 100)
            progress_value = int(metric['value']) if metric['value'] is not None else 0
            progress.setValue(max(0, min(100, progress_value)))
            progress.setStyleSheet("QProgressBar {border: 1px solid #2e2e2e; border-radius: 6px; background: #272727;} QProgressBar::chunk {background-color: #4da6ff; border-radius: 6px;}")

            card_layout.addWidget(title)
            card_layout.addWidget(value_label)
            card_layout.addWidget(target_label)
            card_layout.addWidget(progress)
            card_layout.addWidget(desc_label)

            cards_layout.addWidget(card, idx // 2, idx % 2)

        description_splitter.addWidget(cards_widget)

        radar_widget = QWidget()
        radar_layout = QVBoxLayout(radar_widget)
        radar_layout.setContentsMargins(0, 0, 0, 0)
        radar_fig = Figure(figsize=(6, 5), facecolor='#1e1e1e')
        radar_ax = radar_fig.add_subplot(111, polar=True, facecolor='#1e1e1e')

        radar_labels = [m['label'] for m in indicator_summary]
        radar_values = [min(max(m['value'] / 100.0 if m['value'] is not None else 0, 0), 1) for m in indicator_summary]
        radar_angles = np.linspace(0, 2 * np.pi, len(radar_labels), endpoint=False).tolist()
        radar_values += [radar_values[0]]
        radar_angles += [radar_angles[0]]
        radar_ax.plot(radar_angles, radar_values, color='#4da6ff', linewidth=2)
        radar_ax.fill(radar_angles, radar_values, color='#4da6ff', alpha=0.25)
        radar_ax.set_xticks(radar_angles[:-1])
        radar_ax.set_xticklabels(radar_labels, color='white', fontsize=9)
        radar_ax.set_ylim(0, 1.1)
        radar_ax.set_yticks([0.25, 0.5, 0.75, 1.0])
        radar_ax.set_yticklabels(['25', '50', '75', '100'], color='white', fontsize=8)
        radar_ax.set_title('Health Profile vs Targets', fontweight='bold', color='white', pad=15)
        radar_canvas = SafeFigureCanvas(radar_fig)
        radar_canvas.setStyleSheet("background-color: transparent;")
        radar_canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        radar_layout.addWidget(radar_canvas)

        derived_group = QGroupBox('Derived Ratios Driving Health')
        derived_layout = QVBoxLayout(derived_group)
        derived_table = QTableWidget()
        derived_table.setColumnCount(4)
        derived_table.setHorizontalHeaderLabels(['Ratio', 'Value', 'Calculation / Target', 'Meaning'])
        derived_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        derived_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        derived_table.verticalHeader().setVisible(False)
        derived_table.setRowCount(len(derived_metrics))
        for idx, metric in enumerate(derived_metrics):
            derived_table.setItem(idx, 0, QTableWidgetItem(metric['label']))
            val = metric['value']
            derived_table.setItem(idx, 1, QTableWidgetItem('N/A' if val is None else f"{val:.2f}"))
            derived_table.setItem(idx, 2, QTableWidgetItem(f"{metric['calc']} ({metric['target']})"))
            meaning_item = QTableWidgetItem(metric['meaning'])
            meaning_item.setFlags(meaning_item.flags() & ~Qt.ItemIsEditable)
            derived_table.setItem(idx, 3, meaning_item)
        derived_layout.addWidget(derived_table)
        radar_layout.addWidget(derived_group)

        description_splitter.addWidget(radar_widget)

        guide_group = QGroupBox('Indicator Guide & Calculations')
        guide_layout = QVBoxLayout(guide_group)
        guide_text = (
            "• Overall Health Score – normalized blend of profitability, leverage, liquidity, and growth inputs.\n"
            "• Profitability Score – tracks ROA, ROE, and profit margin relative to healthy thresholds.\n"
            "• Leverage Score – measured by debt levels relative to equity/cash generation; lower is conservative.\n"
            "• Growth Score – captures recent revenue and net income momentum.\n"
            "• Current Ratio – liquidity buffer for short-term claims.\n"
            "• Debt to Equity – assessment of levered capital structure.\n"
            "• Profitability Premium – derived margin spotlight to compare earnings quality."
        )
        guide_label = QLabel(guide_text)
        guide_label.setWordWrap(True)
        guide_label.setStyleSheet('color: #ccc; font-size: 11px; padding: 8px;')
        guide_layout.addWidget(guide_label)
        main_vertical.addWidget(guide_group)

        layout.addWidget(main_vertical)

        def _open_radar(event):
            if event.dblclick:
                viewer = InteractiveChartViewer(radar_fig, "Health Indicators - Interactive View", self)
                viewer.exec()

        radar_canvas.mpl_connect("button_press_event", _open_radar)

        return tab

    def create_key_persons_tab(self) -> QWidget:
        """Create Key Persons tab showing executives, board, insiders, and holding companies."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        key_persons = self.profile.get('key_persons', {})
        summary = key_persons.get('summary', {})
        
        # Summary Section
        summary_group = QGroupBox("👥 Key Persons Summary")
        summary_layout = QGridLayout(summary_group)
        
        row = 0
        # CEO
        ceo_info = summary.get('ceo', {})
        self._add_info_row(summary_layout, row, "CEO:", 
                          ceo_info.get('name', 'Not identified') if ceo_info.get('identified') else 'Not identified')
        row += 1
        
        # CFO
        cfo_info = summary.get('cfo', {})
        self._add_info_row(summary_layout, row, "CFO:", 
                          cfo_info.get('name', 'Not identified') if cfo_info.get('identified') else 'Not identified')
        row += 1
        
        # Chairman
        chairman_info = summary.get('chairman', {})
        self._add_info_row(summary_layout, row, "Chairman:", 
                          chairman_info.get('name', 'Not identified') if chairman_info.get('identified') else 'Not identified')
        row += 1
        
        # Counts
        self._add_info_row(summary_layout, row, "Total Executives:", str(summary.get('executive_count', 0)))
        row += 1
        self._add_info_row(summary_layout, row, "Board Members:", str(summary.get('board_member_count', 0)))
        row += 1
        
        # Board Independence
        board_ind = summary.get('board_independence', {})
        if board_ind.get('total_directors'):
            ind_text = f"{board_ind.get('independent_directors', 0)} of {board_ind.get('total_directors', 0)} ({(board_ind.get('independence_ratio', 0) * 100):.1f}%)"
            self._add_info_row(summary_layout, row, "Board Independence:", ind_text)
            row += 1
        
        # Insider Holdings Summary
        insider_sum = summary.get('insider_holdings', {})
        if insider_sum.get('count', 0) > 0:
            insider_text = f"{insider_sum.get('count', 0)} insiders, {insider_sum.get('net_activity', 'Neutral')}"
            self._add_info_row(summary_layout, row, "Insider Activity:", insider_text)
            row += 1
        
        # Institutional Summary
        inst_sum = summary.get('institutional_ownership', {})
        if inst_sum.get('holder_count', 0) > 0:
            inst_text = f"{inst_sum.get('holder_count', 0)} holders ({inst_sum.get('total_ownership_percent', 0):.1f}%)"
            if inst_sum.get('activist_count', 0) > 0:
                inst_text += f", {inst_sum.get('activist_count', 0)} activist(s)"
            self._add_info_row(summary_layout, row, "Institutional Ownership:", inst_text)
            row += 1
        
        content_layout.addWidget(summary_group)
        
        # Executives Table - Make Collapsible with expand/collapse button
        executives = key_persons.get('executives', [])
        if executives:
            # Create expandable section with button
            exec_container = QWidget()
            exec_container_layout = QVBoxLayout(exec_container)
            exec_container_layout.setContentsMargins(0, 0, 0, 0)

            # Header with collapse button
            exec_header = QWidget()
            exec_header_layout = QHBoxLayout(exec_header)
            exec_header_layout.setContentsMargins(5, 5, 5, 5)

            exec_toggle_btn = QPushButton(f"▼ 👔 Key Executives ({len(executives)})")
            exec_toggle_btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px;
                    background-color: #2d2d2d;
                    border: 1px solid #3e3e3e;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #3d3d3d;
                }
            """)
            exec_header_layout.addWidget(exec_toggle_btn)
            exec_container_layout.addWidget(exec_header)

            # Content widget
            exec_content = QWidget()
            exec_layout = QVBoxLayout(exec_content)

            exec_table = QTableWidget()
            exec_table.setColumnCount(4)  # Added Active column
            exec_table.setHorizontalHeaderLabels(["Name", "Title", "Active", "Filing Date"])
            exec_table.setRowCount(len(executives))
            # Make ALL columns resizable
            header = exec_table.horizontalHeader()
            for col in range(4):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            # Set default widths
            exec_table.setColumnWidth(0, 250)
            exec_table.setColumnWidth(1, 200)
            exec_table.setColumnWidth(2, 80)
            exec_table.setColumnWidth(3, 120)

            for i, exec_info in enumerate(executives):
                exec_table.setItem(i, 0, QTableWidgetItem(exec_info.get('name', 'Unknown')))
                exec_table.setItem(i, 1, QTableWidgetItem(exec_info.get('title', 'Unknown')))

                # Check if active (filing within last 2 years)
                filing_date = exec_info.get('filing_date', '')
                is_active = self._is_recent_filing(filing_date, months=24)
                active_item = QTableWidgetItem("Yes" if is_active else "No")
                if is_active:
                    active_item.setForeground(QColor("#00ff00"))
                else:
                    active_item.setForeground(QColor("#888888"))
                exec_table.setItem(i, 2, active_item)
                exec_table.setItem(i, 3, QTableWidgetItem(filing_date))

            exec_table.setMinimumHeight(min(200, 50 + len(executives) * 30))
            exec_layout.addWidget(exec_table)
            exec_container_layout.addWidget(exec_content)

            # Toggle function
            def toggle_executives():
                is_visible = exec_content.isVisible()
                exec_content.setVisible(not is_visible)
                exec_toggle_btn.setText(f"{'▼' if not is_visible else '▶'} 👔 Key Executives ({len(executives)})")

            exec_toggle_btn.clicked.connect(toggle_executives)
            content_layout.addWidget(exec_container)

        # Board Members Table - Make Collapsible
        board_members = key_persons.get('board_members', [])
        # Filter out the summary entry
        actual_directors = [b for b in board_members if b.get('role') != 'Board Statistics']
        if actual_directors:
            board_group = QGroupBox(f"📋 Board of Directors ({len(actual_directors)})")
            board_group.setCheckable(True)
            board_group.setChecked(True)  # Expanded by default
            board_layout = QVBoxLayout(board_group)
            
            board_table = QTableWidget()
            board_table.setColumnCount(4)
            board_table.setHorizontalHeaderLabels(["Name", "Role", "Independent", "Filing Date"])
            board_table.setRowCount(len(actual_directors))
            # Make ALL columns resizable
            header = board_table.horizontalHeader()
            for col in range(4):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            # Set default widths
            board_table.setColumnWidth(0, 250)
            board_table.setColumnWidth(1, 150)
            board_table.setColumnWidth(2, 120)
            board_table.setColumnWidth(3, 120)

            for i, director in enumerate(actual_directors):
                board_table.setItem(i, 0, QTableWidgetItem(director.get('name', 'Unknown')))
                board_table.setItem(i, 1, QTableWidgetItem(director.get('role', 'Director')))
                
                # Determine independence status with clear logic
                is_independent = director.get('is_independent')
                if is_independent is True:
                    is_ind = "Yes"
                elif is_independent is False:
                    is_ind = "No"
                else:
                    is_ind = "Unknown"
                
                ind_item = QTableWidgetItem(is_ind)
                if is_ind == "Yes":
                    ind_item.setForeground(QColor("#00ff00"))
                elif is_ind == "No":
                    ind_item.setForeground(QColor("#ff6666"))
                board_table.setItem(i, 2, ind_item)
                board_table.setItem(i, 3, QTableWidgetItem(director.get('filing_date', 'N/A')))
            
            board_table.setMinimumHeight(min(200, 50 + len(actual_directors) * 30))
            board_layout.addWidget(board_table)
            content_layout.addWidget(board_group)
        
        # Insider Holdings Table - Make Collapsible
        insider_holdings = key_persons.get('insider_holdings', [])
        if insider_holdings:
            insider_group = QGroupBox(f"💼 Insider Holdings ({len(insider_holdings)})")
            insider_group.setCheckable(True)
            insider_group.setChecked(True)  # Expanded by default
            insider_layout = QVBoxLayout(insider_group)
            
            insider_table = QTableWidget()
            insider_table.setColumnCount(6)
            insider_table.setHorizontalHeaderLabels(["Name", "Title", "Shares Owned", "Net Buy $", "Net Sell $", "Signal"])
            insider_table.setRowCount(len(insider_holdings))
            # Make ALL columns resizable
            header = insider_table.horizontalHeader()
            for col in range(6):
                header.setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            # Set default widths
            insider_table.setColumnWidth(0, 200)
            insider_table.setColumnWidth(1, 150)
            insider_table.setColumnWidth(2, 120)
            insider_table.setColumnWidth(3, 120)
            insider_table.setColumnWidth(4, 120)
            insider_table.setColumnWidth(5, 120)

            for i, insider in enumerate(insider_holdings):
                insider_table.setItem(i, 0, QTableWidgetItem(insider.get('name', 'Unknown')))
                insider_table.setItem(i, 1, QTableWidgetItem(insider.get('title', 'Unknown')))
                
                shares = insider.get('shares_owned', 0)
                shares_str = f"{shares:,}" if shares else "-"
                insider_table.setItem(i, 2, QTableWidgetItem(shares_str))
                
                # Fix: Check if value exists and is > 0 explicitly
                buy_val = insider.get('net_buy_value', 0)
                if buy_val is not None and buy_val > 0:
                    buy_str = f"${buy_val:,.0f}"
                else:
                    buy_str = "-"
                insider_table.setItem(i, 3, QTableWidgetItem(buy_str))
                
                # Fix: Check if value exists and is > 0 explicitly
                sell_val = insider.get('net_sell_value', 0)
                if sell_val is not None and sell_val > 0:
                    sell_str = f"${sell_val:,.0f}"
                else:
                    sell_str = "-"
                insider_table.setItem(i, 4, QTableWidgetItem(sell_str))
                
                signal = insider.get('signal', 'Neutral')
                signal_item = QTableWidgetItem(signal)
                if 'Bullish' in signal:
                    signal_item.setForeground(QColor("#00ff00"))
                elif 'Bearish' in signal:
                    signal_item.setForeground(QColor("#ff6666"))
                insider_table.setItem(i, 5, signal_item)

            insider_table.setMinimumHeight(min(250, 50 + len(insider_holdings) * 30))
            insider_layout.addWidget(insider_table)
            content_layout.addWidget(insider_group)
        
        # Holding Companies Table - Make Collapsible
        holding_companies = key_persons.get('holding_companies', [])
        if holding_companies:
            holders_group = QGroupBox(f"🏛️ Institutional Shareholders & Holding Companies ({len(holding_companies)})")
            holders_group.setCheckable(True)
            holders_group.setChecked(True)  # Expanded by default
            holders_layout = QVBoxLayout(holders_group)
            
            holders_table = QTableWidget()
            holders_table.setColumnCount(5)
            holders_table.setHorizontalHeaderLabels(["Investor/Company", "Ownership %", "Shares", "Type", "Intent/Status"])
            holders_table.setRowCount(len(holding_companies))
            # Make columns resizable by user
            for col in range(5):
                holders_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.Interactive)
            # Set initial column widths
            holders_table.setColumnWidth(0, 300)  # Investor/Company
            holders_table.setColumnWidth(1, 120)  # Ownership %
            holders_table.setColumnWidth(2, 150)  # Shares
            holders_table.setColumnWidth(3, 120)  # Type
            holders_table.setColumnWidth(4, 200)  # Intent/Status

            for i, holder in enumerate(holding_companies):
                name_item = QTableWidgetItem(holder.get('name', 'Unknown'))
                holders_table.setItem(i, 0, name_item)
                
                # Fix: Better handling of ownership percentage - handle None, 0, and actual values
                ownership = holder.get('ownership_percent')
                if ownership is not None and ownership > 0:
                    ownership_str = f"{ownership:.2f}%"
                else:
                    ownership_str = "N/A"
                holders_table.setItem(i, 1, QTableWidgetItem(ownership_str))
                
                # Fix: Better handling of shares - handle None, 0, and actual values
                shares = holder.get('shares_owned')
                if shares is not None and shares > 0:
                    shares_str = f"{shares:,}"
                else:
                    shares_str = "N/A"
                holders_table.setItem(i, 2, QTableWidgetItem(shares_str))
                
                filing_type = holder.get('filing_type', 'Unknown')
                type_item = QTableWidgetItem(filing_type)
                # Color coding: Activist (red/warning) indicates potential pressure,
                # Passive (neutral white) indicates standard institutional holding
                if 'Activist' in filing_type:
                    type_item.setForeground(QColor("#ff6666"))  # Red for activist (attention required)
                # Leave passive investors with default color (neutral) rather than green
                holders_table.setItem(i, 3, type_item)
                
                intent = holder.get('activist_intent', '') if holder.get('is_activist') else 'Passive Investment'
                # Handle empty or None intent
                if not intent or intent.strip() == '':
                    intent = 'Passive Investment' if not holder.get('is_activist') else 'Not specified'
                holders_table.setItem(i, 4, QTableWidgetItem(intent))
            
            holders_table.setMinimumHeight(min(250, 50 + len(holding_companies) * 30))
            holders_layout.addWidget(holders_table)
            content_layout.addWidget(holders_group)
        
        # If no data, show message
        if not executives and not actual_directors and not insider_holdings and not holding_companies:
            no_data = QLabel("No key persons data available. This may be because:\n"
                            "• The company has limited SEC filings\n"
                            "• DEF 14A, Form 4, or SC 13D/G filings were not found\n"
                            "• Content parsing encountered issues")
            no_data.setStyleSheet("color: #888; padding: 20px; font-style: italic;")
            no_data.setWordWrap(True)
            content_layout.addWidget(no_data)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return tab
    
    def create_relationship_graph_tab(self) -> QWidget:
        """Display relationships with a graph, filters, and detailed table."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        relationships_data = self.profile.get('relationships', {})
        relationships = relationships_data.get('relationships', [])

        if not relationships:
            msg = QLabel("No relationship data available for visualization")
            msg.setAlignment(Qt.AlignCenter)
            msg.setStyleSheet("color: #888; padding: 20px; font-size: 14px;")
            layout.addWidget(msg)
            return tab

        main_splitter = QSplitter(Qt.Vertical)
        top_splitter = QSplitter(Qt.Horizontal)

        graph_container = QWidget()
        graph_layout = QVBoxLayout(graph_container)
        graph_layout.setSpacing(10)
        graph_layout.setContentsMargins(0, 0, 0, 0)

        info_widget = QWidget()
        info_layout = QHBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(8)

        company_info = self.profile.get('company_info', {})
        ticker = company_info.get('ticker', 'N/A')
        company_name = company_info.get('name') or company_info.get('title', 'Unknown')

        total_label = QLabel(f"<b>{ticker} - {company_name}</b>")
        total_label.setStyleSheet("color: #fff;")
        count_label = QLabel(f"Total Relationships: {len(relationships)}")
        count_label.setStyleSheet("color: #9aa8bd;")
        info_layout.addWidget(total_label)
        info_layout.addWidget(count_label)

        type_counts = {}
        for rel in relationships:
            rel_type = rel.get('relationship_type', 'unknown')
            type_counts[rel_type] = type_counts.get(rel_type, 0) + 1

        filter_combo = QPushButton("Filter by Type")
        filter_combo.setCursor(Qt.PointingHandCursor)
        filter_menu = QWidget()
        # For simplicity we use a menu-like popup list
        filter_combo.clicked.connect(lambda: QMessageBox.information(self, "Filter", "Filtering coming soon"))
        info_layout.addWidget(filter_combo)

        top_splitter.addWidget(info_widget)

        fig = Figure(figsize=(12, 8), facecolor='#1e1e1e')
        canvas = SafeFigureCanvas(fig)
        ax = fig.add_subplot(111, facecolor='#2d2d2d')

        import networkx as nx

        G = nx.DiGraph()
        source_cik = self.profile.get('cik', '')
        G.add_node(source_cik, label=ticker, node_type='source')

        cik_to_name = {source_cik: ticker}

        for rel in relationships:
            target_cik = rel.get('target_cik', '')
            target_name = rel.get('target_name', 'Unknown')
            rel_type = rel.get('relationship_type', 'unknown')
            confidence = rel.get('confidence_score', 0)
            if not target_cik or not target_name:
                continue
            if target_name.startswith('N/A - '):
                target_name = target_name.replace('N/A - ', '')
            cik_to_name[target_cik] = target_name[:20]
            G.add_node(target_cik, label=target_name, node_type=rel_type)
            G.add_edge(source_cik, target_cik, relationship=rel_type, confidence=confidence)

        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        if source_cik in pos:
            all_coords = list(pos.values())
            center_x = sum(x for x, y in all_coords) / len(all_coords)
            center_y = sum(y for x, y in all_coords) / len(all_coords)
            pos[source_cik] = (center_x, center_y)

        self.graph_G = G
        self.graph_pos = pos
        self.graph_cik_to_name = cik_to_name
        self.selected_node = None
        self.drag_offset = None
        self.is_dragging = False

        edge_colors = {
            'supplier': '#28a745',
            'customer': '#007bff',
            'competitor': '#dc3545',
            'partner': '#ffc107',
            'investor': '#17a2b8',
            'related_company': '#6c757d'
        }

        for edge in G.edges(data=True):
            src, dst, data = edge
            rel_type = data.get('relationship', 'unknown')
            color = edge_colors.get(rel_type, '#6c757d')
            confidence = data.get('confidence', 0)
            nx.draw_networkx_edges(G, pos, edgelist=[(src, dst)], edge_color=color,
                                   alpha=min(0.3 + confidence * 0.7, 1.0), width=1 + confidence * 2,
                                   arrows=True, arrowsize=10, ax=ax)

        nx.draw_networkx_nodes(G, pos, nodelist=[source_cik], node_color='#4da6ff', node_size=3000, alpha=0.9, ax=ax)
        target_nodes = [n for n in G.nodes() if n != source_cik]
        if target_nodes:
            nx.draw_networkx_nodes(G, pos, nodelist=target_nodes, node_color='#7fb3d5', node_size=1000, alpha=0.7, ax=ax)

        labels = {node: cik_to_name.get(node, 'Unknown') for node in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels={source_cik: labels[source_cik]}, font_size=12, font_weight='bold', font_color='white', ax=ax)
        nx.draw_networkx_labels(G, pos, labels={k: v for k, v in labels.items() if k != source_cik}, font_size=8, font_weight='bold', font_color='white', ax=ax)

        ax.set_title(f'Relationship Network for {ticker}', fontsize=16, fontweight='bold', color='white', pad=20)
        ax.axis('off')

        from matplotlib.patches import Patch
        legend_elements = [Patch(facecolor=color, label=rel_type.title()) for rel_type, color in edge_colors.items() if rel_type in type_counts]
        ax.legend(handles=legend_elements, loc='upper right', facecolor='#2d2d2d', edgecolor='white', labelcolor='white', fontsize=10)

        graph_layout.addWidget(canvas)
        graph_layout.addWidget(info_widget)
        top_splitter.addWidget(graph_container)

        stats_group = QGroupBox("Relationship Statistics")
        stats_layout = QVBoxLayout(stats_group)
        stats_table = QTableWidget()
        stats_table.setColumnCount(3)
        stats_table.setHorizontalHeaderLabels(["Relationship Type", "Count", "Avg Confidence"])
        stats_table.setRowCount(len(type_counts))
        for i, (rel_type, count) in enumerate(sorted(type_counts.items(), key=lambda x: x[1], reverse=True)):
            type_rels = [r for r in relationships if r.get('relationship_type') == rel_type]
            avg_conf = sum(r.get('confidence_score', 0) for r in type_rels) / len(type_rels) if type_rels else 0
            stats_table.setItem(i, 0, QTableWidgetItem(rel_type.title()))
            stats_table.setItem(i, 1, QTableWidgetItem(str(count)))
            conf_item = QTableWidgetItem(f"{avg_conf:.2f}")
            if avg_conf >= 0.8:
                conf_item.setForeground(QColor("#28a745"))
            elif avg_conf >= 0.6:
                conf_item.setForeground(QColor("#ffc107"))
            else:
                conf_item.setForeground(QColor("#dc3545"))
            stats_table.setItem(i, 2, conf_item)
        stats_table.resizeColumnsToContents()
        stats_table.setMaximumHeight(200)
        stats_layout.addWidget(stats_table)
        top_splitter.addWidget(stats_group)

        main_splitter.addWidget(top_splitter)

        relationship_group = QGroupBox("Relationship Details")
        relationship_layout = QVBoxLayout(relationship_group)
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Target", "Type", "Confidence", "Direction", "Notes"])
        table.setRowCount(len(relationships))
        for row, rel in enumerate(relationships):
            target = rel.get('target_name') or rel.get('target_cik') or 'Unknown'
            rel_type = rel.get('relationship_type', 'unknown')
            confidence = rel.get('confidence_score', 0)
            direction = "Outgoing" if rel.get('source_cik') == source_cik else "Incoming"
            notes = rel.get('notes', rel.get('context') or '')
            table.setItem(row, 0, QTableWidgetItem(target))
            table.setItem(row, 1, QTableWidgetItem(rel_type.title()))
            table.setItem(row, 2, QTableWidgetItem(f"{confidence:.2f}"))
            table.setItem(row, 3, QTableWidgetItem(direction))
            note_item = QTableWidgetItem(notes)
            note_item.setFlags(note_item.flags() & ~Qt.ItemIsEditable)
            table.setItem(row, 4, note_item)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        relationship_layout.addWidget(table)

        instruction = QLabel("💡 Select a row to highlight the node in the graph once implemented.")
        instruction.setStyleSheet("color: #4da6ff; font-size: 10px; padding: 4px;")
        relationship_layout.addWidget(instruction)

        main_splitter.addWidget(relationship_group)
        layout.addWidget(main_splitter)

        return tab

    def create_ai_analysis_tab(self) -> QWidget:
        """Create AI/ML analysis tab with multi-model comparison support."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Check if multi-model analysis exists
        multi_analysis = self.profile.get('ai_analysis_multi', {})

        if multi_analysis and len(multi_analysis) > 1:
            # Multi-model comparison view
            layout.addWidget(QLabel("Multi-Model AI Analysis Comparison"))

            # Create tabs for each model
            model_tabs = QTabWidget()

            for model_name, analysis in multi_analysis.items():
                model_tab = self._create_single_ai_tab(analysis, model_name)
                model_tabs.addTab(model_tab, model_name)

            layout.addWidget(model_tabs)

            # Consensus section - Make it expandable
            consensus_group = QGroupBox("Model Consensus")
            consensus_layout = QVBoxLayout(consensus_group)

            recommendations = [a.get('recommendation', 'N/A') for a in multi_analysis.values() if isinstance(a, dict)]
            if recommendations:
                from collections import Counter
                rec_counts = Counter(recommendations)
                most_common = rec_counts.most_common(1)[0]

                # Summary always visible
                consensus_text = f"<b>Consensus: {most_common[0]}</b> ({most_common[1]}/{len(recommendations)} models agree)"
                consensus_label = QLabel(consensus_text)
                consensus_label.setStyleSheet("font-size: 16px; padding: 10px; color: #4da6ff;")
                consensus_label.setAlignment(Qt.AlignCenter)
                consensus_layout.addWidget(consensus_label)

                # Toggle button for details
                toggle_btn = QPushButton("▼ Show Detailed Model Breakdown")
                toggle_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #2d2d2d;
                        color: #4da6ff;
                        border: 1px solid #4da6ff;
                        padding: 8px;
                        font-size: 11px;
                        text-align: left;
                    }
                    QPushButton:hover {
                        background-color: #3d3d3d;
                    }
                """)
                toggle_btn.setCursor(Qt.PointingHandCursor)
                consensus_layout.addWidget(toggle_btn)

                # Details table - initially hidden
                details_table = QTableWidget()
                details_table.setColumnCount(3)
                details_table.setHorizontalHeaderLabels(["Model", "Recommendation", "Confidence"])
                details_table.setRowCount(len(multi_analysis))
                details_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)

                row = 0
                for model_name in sorted(multi_analysis.keys()):
                    analysis = multi_analysis[model_name]
                    if isinstance(analysis, dict):
                        details_table.setItem(row, 0, QTableWidgetItem(model_name))

                        rec = analysis.get('recommendation', 'N/A')
                        rec_item = QTableWidgetItem(rec)
                        rec_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
                        details_table.setItem(row, 1, rec_item)

                        conf = analysis.get('confidence', 0)
                        try:
                            conf_val = float(conf)
                            conf_text = f"{conf_val:.0%}"
                        except (ValueError, TypeError):
                            conf_text = str(conf)
                        details_table.setItem(row, 2, QTableWidgetItem(conf_text))
                        row += 1

                details_table.setMaximumHeight(200)
                details_table.setVisible(False)  # Initially hidden
                consensus_layout.addWidget(details_table)

                # Toggle function
                def toggle_details():
                    is_visible = details_table.isVisible()
                    details_table.setVisible(not is_visible)
                    if is_visible:
                        toggle_btn.setText("▼ Show Detailed Model Breakdown")
                    else:
                        toggle_btn.setText("▲ Hide Detailed Model Breakdown")

                toggle_btn.clicked.connect(toggle_details)

            layout.addWidget(consensus_group)

        elif self.ai_analysis:
            # Single model view
            single_tab = self._create_single_ai_tab(self.ai_analysis, "AI Analysis")
            layout.addWidget(single_tab)
        else:
            # No analysis
            no_analysis_label = QLabel("AI analysis not available for this profile.\nEnable AI analysis in settings before generating profiles.")
            no_analysis_label.setAlignment(Qt.AlignCenter)
            no_analysis_label.setStyleSheet("color: gray; padding: 20px;")
            layout.addWidget(no_analysis_label)

        return tab

    def _create_single_ai_tab(self, analysis: Dict, title: str = "") -> QWidget:
        """Create AI analysis view for a single model."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        if not analysis:
            layout.addWidget(QLabel("No analysis data available"))
            return widget

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Investment Thesis
        thesis_group = QGroupBox("Investment Thesis")
        thesis_layout = QVBoxLayout(thesis_group)
        thesis_text = QLabel(analysis.get('investment_thesis', 'N/A'))
        thesis_text.setWordWrap(True)
        thesis_text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        thesis_text.setStyleSheet("padding: 10px;")
        thesis_layout.addWidget(thesis_text)
        content_layout.addWidget(thesis_group)

        # Recommendation
        rec_group = QGroupBox("AI Recommendation")
        rec_layout = QVBoxLayout(rec_group)
        
        recommendation = analysis.get('recommendation', 'N/A')
        confidence = analysis.get('confidence', 0)

        rec_label = QLabel(f"{recommendation}")
        rec_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        rec_label.setStyleSheet("color: #4da6ff; padding: 10px;")
        rec_label.setAlignment(Qt.AlignCenter)
        rec_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        rec_layout.addWidget(rec_label)
        
        # Safely format confidence
        try:
            confidence_val = float(confidence)
            conf_label = QLabel(f"Confidence: {confidence_val:.0%}")
        except (ValueError, TypeError):
            conf_label = QLabel(f"Confidence: {confidence}")
        conf_label.setAlignment(Qt.AlignCenter)
        conf_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        rec_layout.addWidget(conf_label)
        
        content_layout.addWidget(rec_group)
        
        # Strengths
        strengths_group = QGroupBox("Strengths")
        strengths_layout = QVBoxLayout(strengths_group)
        for strength in analysis.get('strengths', []):
            lbl = QLabel(f"✓ {strength}")
            lbl.setStyleSheet("color: green; padding: 5px;")
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            strengths_layout.addWidget(lbl)
        content_layout.addWidget(strengths_group)
        
        # Weaknesses
        weaknesses_group = QGroupBox("Weaknesses")
        weaknesses_layout = QVBoxLayout(weaknesses_group)
        for weakness in analysis.get('weaknesses', []):
            lbl = QLabel(f"✗ {weakness}")
            lbl.setStyleSheet("color: red; padding: 5px;")
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            weaknesses_layout.addWidget(lbl)
        content_layout.addWidget(weaknesses_group)
        
        # Growth Predictions
        pred_group = QGroupBox("Growth Predictions")
        pred_layout = QGridLayout(pred_group)
        
        predictions = analysis.get('growth_prediction', {})
        row = 0
        for period, values in predictions.items():
            period_lbl = QLabel(f"{period}:")
            period_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

            # Safely convert to float (handles string or numeric values)
            try:
                revenue_val = float(values.get('revenue', 0))
                rev_lbl = QLabel(f"Revenue: {revenue_val:.1f}%")
            except (ValueError, TypeError):
                rev_lbl = QLabel(f"Revenue: {values.get('revenue', 'N/A')}")
            rev_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

            try:
                earnings_val = float(values.get('earnings', 0))
                earn_lbl = QLabel(f"Earnings: {earnings_val:.1f}%")
            except (ValueError, TypeError):
                earn_lbl = QLabel(f"Earnings: {values.get('earnings', 'N/A')}")
            earn_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)

            pred_layout.addWidget(period_lbl, row, 0)
            pred_layout.addWidget(rev_lbl, row, 1)
            pred_layout.addWidget(earn_lbl, row, 2)
            row += 1

        content_layout.addWidget(pred_group)

        # Risk Assessment
        risk_group = QGroupBox("Risk Assessment")
        risk_layout = QVBoxLayout(risk_group)

        risk_level = analysis.get('risk_level', 'N/A')
        risk_color = {'Low': 'green', 'Medium': 'orange', 'High': 'red'}.get(risk_level, 'gray')

        risk_label = QLabel(f"Risk Level: {risk_level}")
        risk_label.setStyleSheet(f"color: {risk_color}; font-weight: bold; padding: 5px;")
        risk_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        risk_layout.addWidget(risk_label)

        # Risks
        for risk in analysis.get('risks', []):
            risk_lbl = QLabel(f"⚠ {risk}")
            risk_lbl.setWordWrap(True)
            risk_lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            risk_lbl.setStyleSheet("padding: 3px;")
            risk_layout.addWidget(risk_lbl)

        content_layout.addWidget(risk_group)

        # Catalysts
        catalysts_group = QGroupBox("Potential Catalysts")
        catalysts_layout = QVBoxLayout(catalysts_group)
        for catalyst in analysis.get('catalysts', []):
            lbl = QLabel(f"🚀 {catalyst}")
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            lbl.setStyleSheet("padding: 3px;")
            catalysts_layout.addWidget(lbl)
        content_layout.addWidget(catalysts_group)

        # Key Assumptions
        assumptions_group = QGroupBox("Key Assumptions")
        assumptions_layout = QVBoxLayout(assumptions_group)
        for assumption in analysis.get('key_assumptions', []):
            lbl = QLabel(f"• {assumption}")
            lbl.setWordWrap(True)
            lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
            assumptions_layout.addWidget(lbl)
        content_layout.addWidget(assumptions_group)

        # Provider info - show actual model from analysis
        provider = analysis.get('provider', 'unknown')
        model = analysis.get('model', title if title else 'N/A')  # Use title parameter or model from analysis
        generated_at = analysis.get('generated_at', 'N/A')

        # Format generated_at safely
        if isinstance(generated_at, str) and len(generated_at) > 19:
            generated_at_display = generated_at[:19]
        else:
            generated_at_display = str(generated_at)

        provider_label = QLabel(f"Analysis by: {provider} | Model: {model} | Generated: {generated_at_display}")
        provider_label.setStyleSheet("color: gray; font-size: 10px; padding: 10px;")
        provider_label.setAlignment(Qt.AlignCenter)
        provider_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content_layout.addWidget(provider_label)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return widget

    def _add_info_row(self, layout: QGridLayout, row: int, label: str, value: str):
        """Helper to add info row to grid layout."""
        lbl = QLabel(label)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        val = QLabel(str(value))
        val.setFont(QFont("Segoe UI", 9))
        val.setTextInteractionFlags(Qt.TextSelectableByMouse)  # Make value selectable

        layout.addWidget(lbl, row, 0, Qt.AlignRight)
        layout.addWidget(val, row, 1, Qt.AlignLeft)

    def _redirect_canvas_wheel_to_scroll(self, canvas, scroll_area):
        """Override canvas wheel event to scroll the parent scroll area."""
        def _wheel_event(self, event, scroll=scroll_area):
            delta = event.angleDelta().y()
            if delta == 0:
                event.ignore()
                return
            bar = scroll.verticalScrollBar()
            step = int(-delta / 120 * bar.singleStep())
            bar.setValue(bar.value() + step)
            event.accept()

        canvas.wheelEvent = MethodType(_wheel_event, canvas)

    def _is_recent_filing(self, filing_date: str, months: int = 24) -> bool:
        """Check if filing date is within the last N months."""
        if not filing_date or filing_date == 'N/A':
            return False
        try:
            from datetime import datetime, timedelta
            filing_dt = datetime.strptime(filing_date, '%Y-%m-%d')
            cutoff_date = datetime.now() - timedelta(days=months * 30)
            return filing_dt >= cutoff_date
        except:
            return False

    def create_filing_viewer_tab(self) -> QWidget:
        """Create SEC filing viewer tab with integrated filing browser."""
        try:
            from src.ui.filing_viewer_widget import FilingViewerWidget

            # Get company info
            company_info = self.profile.get('company_info', {})
            ticker = company_info.get('ticker', 'N/A')
            cik = company_info.get('cik', 'N/A')

            # Create filing viewer widget
            viewer = FilingViewerWidget()

            # Load company filings automatically
            if ticker != 'N/A' and cik != 'N/A':
                try:
                    viewer.load_company_filings(ticker, cik)
                    logger.info(f"Filing viewer loaded for {ticker}")
                except Exception as e:
                    logger.error(f"Error loading filings for {ticker}: {e}")

            return viewer

        except ImportError as e:
            logger.error(f"FilingViewerWidget not available: {e}")
            # Create fallback widget
            fallback = QWidget()
            layout = QVBoxLayout(fallback)

            error_label = QLabel("SEC Filing Viewer not available\n\nThe filing viewer module could not be loaded.")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: #ff6b6b; font-size: 12px; padding: 20px;")
            layout.addWidget(error_label)

            return fallback

        except Exception as e:
            logger.error(f"Error creating filing viewer tab: {e}", exc_info=True)
            # Create error widget
            error_widget = QWidget()
            layout = QVBoxLayout(error_widget)

            error_label = QLabel(f"Error loading filing viewer:\n{str(e)}")
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: #ff6b6b; padding: 20px;")
            layout.addWidget(error_label)

            return error_widget
