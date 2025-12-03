"""
Enhanced Profile Visualization Window with comprehensive insights.
Uses multiple chart types appropriate for different data representations.
"""
import sys
from typing import Dict, Any, Optional
from datetime import datetime

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, 
                               QWidget, QLabel, QScrollArea, QGroupBox, QPushButton,
                               QGridLayout, QSizePolicy, QTableWidget, QTableWidgetItem,
                               QHeaderView)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np

# Import AI analyzer
try:
    from ai_analyzer import AIAnalyzer
    HAS_AI = True
except ImportError:
    HAS_AI = False


class ProfileVisualizationWindow(QDialog):
    """Enhanced visualization window with multiple chart types and AI analysis."""
    
    def __init__(self, profile: Dict[str, Any], config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.profile = profile
        self.config = config or {}
        self.setWindowTitle(f"Profile Visualization - {self._get_company_name()}")
        self.resize(1600, 1000)
        
        # Initialize AI analyzer
        if HAS_AI:
            self.ai_analyzer = AIAnalyzer(self.config)
            self.ai_analysis = None
        
        self.setup_ui()
        
    def _get_company_name(self) -> str:
        """Get company name from profile."""
        info = self.profile.get('company_info', {})
        ticker = info.get('ticker', 'N/A')
        name = info.get('name', 'Unknown')
        return f"{ticker} - {name}"
    
    def setup_ui(self):
        """Setup the UI layout."""
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel(self._get_company_name())
        header.setFont(QFont("Segoe UI", 16, QFont.Bold))
        header.setStyleSheet("color: #4da6ff; padding: 10px;")
        layout.addWidget(header)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.addTab(self.create_overview_tab(), "Overview")
        self.tabs.addTab(self.create_decision_summary_tab(), "Decision Summary")
        self.tabs.addTab(self.create_financials_tab(), "Financial Trends")
        self.tabs.addTab(self.create_ratios_tab(), "Financial Ratios")
        self.tabs.addTab(self.create_growth_tab(), "Growth Analysis")
        self.tabs.addTab(self.create_health_tab(), "Health Indicators")
        
        if HAS_AI:
            self.tabs.addTab(self.create_ai_analysis_tab(), "AI/ML Analysis")
        
        layout.addWidget(self.tabs)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.close)
        close_btn.setMaximumWidth(100)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)
    
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
        metrics = [
            ('Revenues', 'Revenues'),
            ('Assets', 'Assets'),
            ('Liabilities', 'Liabilities'),
            ('Stockholders Equity', 'StockholdersEquity'),
            ('Net Income', 'NetIncomeLoss'),
            ('Cash', 'CashAndCashEquivalentsAtCarryingValue')
        ]
        
        row = 0
        for label, key in metrics:
            value = latest.get(key, 'N/A')
            if isinstance(value, (int, float)):
                value = f"${value:,.0f}"
            self._add_info_row(latest_layout, row, f"{label}:", str(value))
            row += 1
        
        content_layout.addWidget(latest_group)
        
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
            rec_color = "darkgreen"
        elif score >= 3:
            recommendation = "Buy"
            rec_color = "green"
        elif score >= 0:
            recommendation = "Hold"
            rec_color = "orange"
        elif score >= -2:
            recommendation = "Sell"
            rec_color = "red"
        else:
            recommendation = "Strong Sell"
            rec_color = "darkred"
        
        rec_label = QLabel(f"Recommendation: {recommendation}")
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
        """Create financial trends tab with appropriate chart types."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        time_series = self.profile.get('financial_time_series', {})
        
        if not time_series:
            layout.addWidget(QLabel("No financial time series data available"))
            return tab
        
        # Create figure with subplots
        fig = Figure(figsize=(14, 10))
        canvas = FigureCanvas(fig)
        
        # Plot key metrics with different visualization techniques
        metrics_to_plot = [
            ('Revenues', 'Revenue Trend', 'area'),
            ('Assets', 'Assets Trend', 'line'),
            ('Liabilities', 'Liabilities Trend', 'line'),
            ('NetIncomeLoss', 'Net Income Trend', 'bar')
        ]
        
        for idx, (metric, title, chart_type) in enumerate(metrics_to_plot, 1):
            if metric in time_series and time_series[metric]:
                ax = fig.add_subplot(2, 2, idx)
                data = time_series[metric]
                dates = sorted(data.keys())
                values = [data[d] for d in dates]
                
                # Limit to last 20 data points
                if len(dates) > 20:
                    dates = dates[-20:]
                    values = values[-20:]
                
                x_pos = range(len(dates))
                
                # Use appropriate chart type
                if chart_type == 'area':
                    ax.fill_between(x_pos, values, alpha=0.3, color='#4da6ff')
                    ax.plot(x_pos, values, marker='o', linewidth=2, markersize=4, color='#4da6ff')
                elif chart_type == 'bar':
                    colors = ['green' if v >= 0 else 'red' for v in values]
                    ax.bar(x_pos, values, color=colors, alpha=0.7)
                else:  # line
                    ax.plot(x_pos, values, marker='o', linewidth=2, markersize=4, color='#4da6ff')
                
                ax.set_title(title, fontsize=11, fontweight='bold')
                ax.set_xlabel('Date', fontsize=9)
                ax.set_ylabel('Value ($)', fontsize=9)
                ax.grid(True, alpha=0.3, axis='y')
                
                # Set x-ticks
                step = max(1, len(dates) // 6)
                tick_positions = range(0, len(dates), step)
                tick_labels = [dates[i][:7] for i in tick_positions]
                ax.set_xticks(tick_positions)
                ax.set_xticklabels(tick_labels, rotation=45, ha='right', fontsize=8)
                ax.tick_params(axis='y', labelsize=8)
                
                # Format y-axis
                ax.yaxis.set_major_formatter(plt.FuncFormatter(
                    lambda x, p: f'${x/1e9:.1f}B' if abs(x) >= 1e9 else f'${x/1e6:.1f}M' if abs(x) >= 1e6 else f'${x/1e3:.1f}K'
                ))
        
        fig.tight_layout()
        layout.addWidget(canvas)
        
        return tab
    
    def create_ratios_tab(self) -> QWidget:
        """Create financial ratios tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        ratios = self.profile.get('financial_ratios', {})
        
        if not ratios:
            layout.addWidget(QLabel("No financial ratios data available"))
            return tab
        
        fig = Figure(figsize=(12, 6))
        canvas = FigureCanvas(fig)
        
        ax = fig.add_subplot(111)
        
        ratio_labels = []
        ratio_values = []
        
        for key, value in ratios.items():
            if isinstance(value, (int, float)):
                ratio_labels.append(key.replace('_', ' ').title())
                ratio_values.append(value)
        
        if ratio_labels:
            bars = ax.barh(ratio_labels, ratio_values, color='#4da6ff')
            ax.set_xlabel('Value', fontsize=10)
            ax.set_title('Financial Ratios', fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3, axis='x')
            
            for bar in bars:
                width = bar.get_width()
                ax.text(width, bar.get_y() + bar.get_height()/2, 
                       f'{width:.3f}', ha='left', va='center', fontsize=8)
        
        fig.tight_layout()
        layout.addWidget(canvas)
        
        return tab
    
    def create_growth_tab(self) -> QWidget:
        """Create growth analysis tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        growth_rates = self.profile.get('growth_rates', {})
        
        if not growth_rates:
            layout.addWidget(QLabel("No growth rate data available"))
            return tab
        
        fig = Figure(figsize=(12, 8))
        canvas = FigureCanvas(fig)
        
        metrics = ['Revenues', 'Assets', 'NetIncomeLoss']
        plot_idx = 1
        
        for metric in metrics:
            if metric in growth_rates:
                data = growth_rates[metric]
                pop = data.get('period_over_period', [])
                
                if pop:
                    ax = fig.add_subplot(2, 2, plot_idx)
                    
                    periods = [p['period'] for p in pop]
                    rates = [p['growth_rate'] for p in pop]
                    
                    colors = ['green' if r >= 0 else 'red' for r in rates]
                    ax.bar(range(len(periods)), rates, color=colors, alpha=0.7)
                    ax.set_title(f'{metric} Growth Rate', fontsize=10, fontweight='bold')
                    ax.set_xlabel('Period', fontsize=8)
                    ax.set_ylabel('Growth Rate (%)', fontsize=8)
                    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                    ax.grid(True, alpha=0.3, axis='y')
                    ax.set_xticks(range(len(periods)))
                    ax.set_xticklabels(periods, rotation=45, ha='right', fontsize=7)
                    
                    avg = data.get('avg_growth_rate', 0)
                    ax.axhline(y=avg, color='blue', linestyle='--', linewidth=1, 
                             label=f'Avg: {avg:.1f}%')
                    ax.legend(fontsize=7)
                    
                    plot_idx += 1
        
        fig.tight_layout()
        layout.addWidget(canvas)
        
        return tab
    
    def create_health_tab(self) -> QWidget:
        """Create health indicators tab with gauge visualizations."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        health = self.profile.get('health_indicators', {})
        
        if not health:
            layout.addWidget(QLabel("No health indicator data available"))
            return tab
        
        fig = Figure(figsize=(12, 6))
        canvas = FigureCanvas(fig)
        
        scores = [
            ('Overall Health', health.get('overall_health_score', 0)),
            ('Profitability', health.get('profitability_score', 0)),
            ('Leverage', health.get('leverage_score', 0)),
            ('Growth', health.get('growth_score', 0))
        ]
        
        for idx, (label, score) in enumerate(scores, 1):
            ax = fig.add_subplot(2, 2, idx, projection='polar')
            
            theta = np.linspace(0, np.pi, 100)
            r = np.ones(100)
            
            ax.plot(theta, r, color='lightgray', linewidth=20, solid_capstyle='round')
            
            score_theta = np.linspace(0, np.pi * (score / 100), 100)
            color = 'green' if score >= 70 else 'orange' if score >= 50 else 'red'
            ax.plot(score_theta, r, color=color, linewidth=20, solid_capstyle='round')
            
            ax.set_ylim(0, 1.5)
            ax.set_yticks([])
            ax.set_xticks([])
            ax.spines['polar'].set_visible(False)
            
            ax.text(np.pi/2, 0.5, f'{score:.1f}', ha='center', va='center', 
                   fontsize=20, fontweight='bold')
            ax.text(np.pi/2, 0.2, label, ha='center', va='center', 
                   fontsize=10)
        
        fig.tight_layout()
        layout.addWidget(canvas)
        
        return tab
    
    def create_ai_analysis_tab(self) -> QWidget:
        """Create AI/ML analysis tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Generate analysis if not already done
        if not hasattr(self, 'ai_analysis') or self.ai_analysis is None:
            try:
                self.ai_analysis = self.ai_analyzer.analyze_profile(self.profile)
            except Exception as e:
                layout.addWidget(QLabel(f"Error generating AI analysis: {e}"))
                return tab
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        
        # Recommendation
        rec_group = QGroupBox("AI Recommendation")
        rec_layout = QVBoxLayout(rec_group)
        
        recommendation = self.ai_analysis.get('recommendation', 'N/A')
        confidence = self.ai_analysis.get('confidence', 0)
        
        rec_label = QLabel(f"{recommendation}")
        rec_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        rec_label.setStyleSheet("color: #4da6ff; padding: 10px;")
        rec_label.setAlignment(Qt.AlignCenter)
        rec_layout.addWidget(rec_label)
        
        conf_label = QLabel(f"Confidence: {confidence:.0%}")
        conf_label.setAlignment(Qt.AlignCenter)
        rec_layout.addWidget(conf_label)
        
        content_layout.addWidget(rec_group)
        
        # Strengths
        strengths_group = QGroupBox("Strengths")
        strengths_layout = QVBoxLayout(strengths_group)
        for strength in self.ai_analysis.get('strengths', []):
            lbl = QLabel(f"✓ {strength}")
            lbl.setStyleSheet("color: green; padding: 5px;")
            lbl.setWordWrap(True)
            strengths_layout.addWidget(lbl)
        content_layout.addWidget(strengths_group)
        
        # Weaknesses
        weaknesses_group = QGroupBox("Weaknesses")
        weaknesses_layout = QVBoxLayout(weaknesses_group)
        for weakness in self.ai_analysis.get('weaknesses', []):
            lbl = QLabel(f"✗ {weakness}")
            lbl.setStyleSheet("color: red; padding: 5px;")
            lbl.setWordWrap(True)
            weaknesses_layout.addWidget(lbl)
        content_layout.addWidget(weaknesses_group)
        
        # Growth Predictions
        pred_group = QGroupBox("Growth Predictions")
        pred_layout = QGridLayout(pred_group)
        
        predictions = self.ai_analysis.get('growth_prediction', {})
        row = 0
        for period, values in predictions.items():
            pred_layout.addWidget(QLabel(f"{period}:"), row, 0)
            pred_layout.addWidget(QLabel(f"Revenue: {values.get('revenue', 0):.1f}%"), row, 1)
            pred_layout.addWidget(QLabel(f"Earnings: {values.get('earnings', 0):.1f}%"), row, 2)
            row += 1
        
        content_layout.addWidget(pred_group)
        
        # Risk Assessment
        risk_group = QGroupBox("Risk Assessment")
        risk_layout = QVBoxLayout(risk_group)
        
        risk_level = self.ai_analysis.get('risk_level', 'N/A')
        risk_color = {'Low': 'green', 'Medium': 'orange', 'High': 'red'}.get(risk_level, 'gray')
        
        risk_label = QLabel(f"Risk Level: {risk_level}")
        risk_label.setStyleSheet(f"color: {risk_color}; font-weight: bold; padding: 5px;")
        risk_layout.addWidget(risk_label)
        
        content_layout.addWidget(risk_group)
        
        # Key Assumptions
        assumptions_group = QGroupBox("Key Assumptions")
        assumptions_layout = QVBoxLayout(assumptions_group)
        for assumption in self.ai_analysis.get('key_assumptions', []):
            lbl = QLabel(f"• {assumption}")
            lbl.setWordWrap(True)
            assumptions_layout.addWidget(lbl)
        content_layout.addWidget(assumptions_group)
        
        # Provider info
        provider = self.ai_analysis.get('provider', 'unknown')
        provider_label = QLabel(f"Analysis provided by: {provider}")
        provider_label.setStyleSheet("color: gray; font-size: 10px; padding: 10px;")
        provider_label.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(provider_label)
        
        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        return tab
    
    def _add_info_row(self, layout: QGridLayout, row: int, label: str, value: str):
        """Helper to add info row to grid layout."""
        lbl = QLabel(label)
        lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        val = QLabel(str(value))
        val.setFont(QFont("Segoe UI", 9))
        
        layout.addWidget(lbl, row, 0, Qt.AlignRight)
        layout.addWidget(val, row, 1, Qt.AlignLeft)
