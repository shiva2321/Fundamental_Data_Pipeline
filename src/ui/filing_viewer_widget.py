"""
SEC Filing Viewer Widget

A PySide6 widget for displaying SEC filings in human-readable format.
Supports HTML display with section navigation.
"""
import logging
from typing import Optional, List, Dict, Any
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QComboBox, QLabel, QPushButton, QLineEdit,
    QTextBrowser, QTreeWidget, QTreeWidgetItem,
    QProgressBar, QMessageBox, QGroupBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtGui import QFont

logger = logging.getLogger(__name__)


class FilingViewerWidget(QWidget):
    """
    Widget for viewing SEC filings with section navigation.

    Features:
    - Filing selection by type and date
    - HTML display (Option 1: easy)
    - Section navigation (Option 2: advanced)
    - Search functionality
    - Export options
    """

    filing_loaded = Signal(str, str)  # cik, accession

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cik = None
        self.ticker = None
        self.filings_list = []
        self.current_filing = None
        self.sections = {}

        self.setup_ui()
        logger.info("FilingViewerWidget initialized")

    def setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header section
        header_layout = self.create_header()
        layout.addLayout(header_layout)

        # Filing selector
        selector_group = self.create_filing_selector()
        layout.addWidget(selector_group)

        # Main content area (splitter for sections + content)
        splitter = QSplitter(Qt.Horizontal)

        # Left: Section navigation (tree view)
        self.section_tree = self.create_section_tree()
        splitter.addWidget(self.section_tree)

        # Right: Content viewer
        viewer_widget = self.create_content_viewer()
        splitter.addWidget(viewer_widget)

        # Set splitter sizes (20% sections, 80% content)
        splitter.setSizes([200, 800])

        layout.addWidget(splitter)

        # Status bar
        self.status_label = QLabel("No filing loaded")
        self.status_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.status_label)

    def create_header(self) -> QHBoxLayout:
        """Create header with title and controls"""
        layout = QHBoxLayout()

        # Title
        title = QLabel("SEC Filing Viewer")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        layout.addStretch()

        # Company info label
        self.company_label = QLabel("No company selected")
        layout.addWidget(self.company_label)

        return layout

    def create_filing_selector(self) -> QGroupBox:
        """Create filing selector group with improved search and filtering"""
        group = QGroupBox("Select Filing")
        main_layout = QVBoxLayout(group)

        # Top row: Form type filter and year filter
        filter_row = QHBoxLayout()

        # Form type filter
        filter_row.addWidget(QLabel("Form Type:"))
        self.form_filter = QComboBox()
        self.form_filter.addItems(['All', '10-K', '10-Q', '8-K', 'DEF 14A', 'Form 4', 'SC 13D', 'SC 13G'])
        self.form_filter.setMinimumWidth(120)
        self.form_filter.currentTextChanged.connect(self.on_form_filter_changed)
        filter_row.addWidget(self.form_filter)

        filter_row.addSpacing(20)

        # Year filter
        filter_row.addWidget(QLabel("Year:"))
        self.year_filter = QComboBox()
        self.year_filter.addItem("All Years")
        self.year_filter.setMinimumWidth(120)
        self.year_filter.currentTextChanged.connect(self.on_filter_changed)
        filter_row.addWidget(self.year_filter)

        filter_row.addSpacing(20)

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setMaximumWidth(100)
        refresh_btn.clicked.connect(self.refresh_filings)
        filter_row.addWidget(refresh_btn)

        filter_row.addStretch()

        main_layout.addLayout(filter_row)

        # Search row
        search_row = QHBoxLayout()
        search_row.addWidget(QLabel("Search:"))

        self.filing_search = QLineEdit()
        self.filing_search.setPlaceholderText("Type form type, date (YYYY-MM-DD), or year (YYYY)...")
        self.filing_search.textChanged.connect(self.on_search_changed)
        self.filing_search.setClearButtonEnabled(True)
        search_row.addWidget(self.filing_search)

        main_layout.addLayout(search_row)

        # Filing list row
        list_row = QHBoxLayout()

        # Filing combo (now populated based on search/filters)
        list_row.addWidget(QLabel("Filing:"))
        self.filing_combo = QComboBox()
        self.filing_combo.setMinimumWidth(500)
        self.filing_combo.currentIndexChanged.connect(self.on_filing_selected)
        list_row.addWidget(self.filing_combo)

        # Load button
        self.load_button = QPushButton("📄 Load Filing")
        self.load_button.setMinimumWidth(120)
        self.load_button.clicked.connect(self.load_selected_filing)
        self.load_button.setEnabled(False)
        self.load_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #999;
            }
        """)
        list_row.addWidget(self.load_button)

        main_layout.addLayout(list_row)

        # Results count label
        self.results_label = QLabel("No filings loaded")
        self.results_label.setStyleSheet("color: #888; font-size: 10px;")
        main_layout.addWidget(self.results_label)

        return group

    def create_section_tree(self) -> QTreeWidget:
        """Create section navigation tree"""
        tree = QTreeWidget()
        tree.setHeaderLabel("Sections")
        tree.setMinimumWidth(200)
        tree.itemClicked.connect(self.on_section_clicked)
        tree.hide()  # Hidden until filing is loaded
        return tree

    def create_content_viewer(self) -> QWidget:
        """Create content viewer area"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search in filing...")
        self.search_box.returnPressed.connect(self.on_search)
        search_layout.addWidget(self.search_box)

        search_btn = QPushButton("Find")
        search_btn.clicked.connect(self.on_search)
        search_layout.addWidget(search_btn)

        layout.addLayout(search_layout)

        # Content viewer (HTML)
        self.content_viewer = QWebEngineView()
        self.content_viewer.setHtml("<h3>No filing loaded</h3><p>Select a filing from the dropdown above.</p>")
        layout.addWidget(self.content_viewer)

        # Alternative: Text browser (lighter, for structured view)
        self.text_viewer = QTextBrowser()
        self.text_viewer.setHtml("<h3>No filing loaded</h3>")
        self.text_viewer.setOpenExternalLinks(True)
        self.text_viewer.hide()

        layout.addWidget(self.text_viewer)

        # Export buttons
        export_layout = QHBoxLayout()
        export_layout.addStretch()

        export_pdf_btn = QPushButton("Export to PDF")
        export_pdf_btn.clicked.connect(self.export_to_pdf)
        export_layout.addWidget(export_pdf_btn)

        export_text_btn = QPushButton("Export to Text")
        export_text_btn.clicked.connect(self.export_to_text)
        export_layout.addWidget(export_text_btn)

        layout.addLayout(export_layout)

        return widget

    def load_company_filings(self, ticker: str, cik: str):
        """Load filing list for a company"""
        self.ticker = ticker
        self.cik = cik
        self.company_label.setText(f"{ticker} (CIK: {cik})")

        self.status_label.setText(f"Loading filings for {ticker}...")
        logger.info(f"Loading filings for {ticker} (CIK: {cik})")

        try:
            from src.clients.sec_edgar_api_client import SECEdgarClient

            client = SECEdgarClient()
            submissions = client.get_company_submissions(cik)

            if not submissions:
                self.status_label.setText("Error: Could not load filings")
                QMessageBox.warning(self, "Error", f"Could not load filings for {ticker}")
                return

            # Extract filing list
            filings = submissions.get('filings', {}).get('recent', {})
            accessions = filings.get('accessionNumber', [])
            forms = filings.get('form', [])
            dates = filings.get('filingDate', [])
            report_dates = filings.get('reportDate', [])

            self.filings_list = []
            for i in range(len(accessions)):
                self.filings_list.append({
                    'accession': accessions[i],
                    'form': forms[i],
                    'filingDate': dates[i],
                    'reportDate': report_dates[i] if i < len(report_dates) else dates[i]
                })

            self.status_label.setText(f"Loaded {len(self.filings_list)} filings for {ticker}")
            logger.info(f"Loaded {len(self.filings_list)} filings")

            # Populate year filter
            self.populate_year_filter()

            # Populate filing combo box
            self.refresh_filing_combo()

        except Exception as e:
            logger.error(f"Error loading filings: {e}", exc_info=True)
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"Error loading filings:\n{str(e)}")

    def populate_year_filter(self):
        """Populate year filter dropdown with available years"""
        years = set()
        for filing in self.filings_list:
            year = filing['filingDate'][:4]  # Extract year (YYYY)
            years.add(year)

        # Clear and repopulate
        self.year_filter.clear()
        self.year_filter.addItem("All Years")

        # Add years in descending order
        for year in sorted(years, reverse=True):
            self.year_filter.addItem(year)

    def refresh_filing_combo(self):
        """Refresh filing combo box based on filters and search"""
        self.filing_combo.clear()

        form_filter = self.form_filter.currentText()
        year_filter = self.year_filter.currentText()
        search_text = self.filing_search.text().strip().lower()

        filtered_filings = []

        for filing in self.filings_list:
            # Apply form filter
            if form_filter != 'All' and filing['form'] != form_filter:
                continue

            # Apply year filter
            if year_filter != "All Years":
                filing_year = filing['filingDate'][:4]
                if filing_year != year_filter:
                    continue

            # Apply search filter
            if search_text:
                # Search in: form type, filing date, report date, accession
                searchable = (
                    filing['form'].lower() + " " +
                    filing['filingDate'] + " " +
                    filing['reportDate'] + " " +
                    filing['accession'].lower()
                )

                if search_text not in searchable:
                    continue

            filtered_filings.append(filing)

        # Add filtered filings to combo
        for filing in filtered_filings:
            display = f"{filing['form']:12s} | {filing['reportDate']} | Filed: {filing['filingDate']}"
            self.filing_combo.addItem(display, filing)

        # Update results count
        total = len(self.filings_list)
        shown = len(filtered_filings)

        if search_text or year_filter != "All Years" or form_filter != 'All':
            self.results_label.setText(f"Showing {shown} of {total} filings")
        else:
            self.results_label.setText(f"{total} filings available")

        self.load_button.setEnabled(self.filing_combo.count() > 0)

    def on_form_filter_changed(self, text: str):
        """Handle form filter change"""
        self.refresh_filing_combo()

    def on_filter_changed(self):
        """Handle any filter change (year, form type)"""
        self.refresh_filing_combo()

    def on_search_changed(self, text: str):
        """Handle search text change - updates list in real-time"""
        self.refresh_filing_combo()

    def on_filing_selected(self, index: int):
        """Handle filing selection"""
        self.load_button.setEnabled(index >= 0)

    def refresh_filings(self):
        """Refresh filing list"""
        if self.ticker and self.cik:
            self.load_company_filings(self.ticker, self.cik)

    def load_selected_filing(self):
        """Load the selected filing"""
        index = self.filing_combo.currentIndex()
        if index < 0:
            return

        filing = self.filing_combo.itemData(index)
        if not filing:
            return

        self.load_filing(filing['accession'], filing['form'])

    def load_filing(self, accession: str, form_type: str):
        """Load and display a filing"""
        self.status_label.setText(f"Loading {form_type} filing...")
        logger.info(f"Loading filing: {accession} ({form_type})")

        try:
            from src.parsers.filing_content_parser import SECFilingContentFetcher

            fetcher = SECFilingContentFetcher()
            content = fetcher.fetch_filing_content(self.cik, accession)

            if not content:
                QMessageBox.warning(self, "Error", "Could not fetch filing content")
                self.status_label.setText("Error: Could not fetch content")
                return

            self.current_filing = {
                'accession': accession,
                'form': form_type,
                'content': content
            }

            # Clean content (remove SEC headers if present)
            display_content = content
            if '<DOCUMENT>' in content:
                parts = content.split('<TEXT>')
                if len(parts) > 1:
                    display_content = parts[1].split('</TEXT>')[0]

            # Enhance HTML display with better styling
            enhanced_html = self.enhance_html_display(display_content, form_type)

            # Display in HTML viewer
            self.content_viewer.setHtml(enhanced_html, QUrl("https://www.sec.gov/"))

            self.status_label.setText(f"Loaded {form_type} filing ({len(content):,} chars)")

            # Extract sections if applicable
            if form_type in ['10-K', '10-Q']:
                self.extract_and_show_sections(display_content, form_type)
            else:
                # For other form types, hide section tree
                self.section_tree.hide()

            self.filing_loaded.emit(self.cik, accession)

        except Exception as e:
            logger.error(f"Error loading filing: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Error loading filing:\n{str(e)}")
            self.status_label.setText(f"Error: {str(e)}")

    def enhance_html_display(self, html_content: str, form_type: str) -> str:
        """Enhance HTML content with better styling for display"""
        try:
            from bs4 import BeautifulSoup

            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')

            # Remove script tags
            for script in soup(["script"]):
                script.decompose()

            # Create enhanced HTML with CSS
            enhanced = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>{form_type} Filing</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        padding: 30px;
                        line-height: 1.6;
                        color: #333;
                        background: white;
                        max-width: 1200px;
                        margin: 0 auto;
                    }}
                    
                    /* Headers */
                    h1, h2, h3, h4, h5, h6 {{
                        color: #0066cc;
                        margin-top: 25px;
                        margin-bottom: 15px;
                        font-weight: 600;
                    }}
                    h1 {{ font-size: 28px; border-bottom: 3px solid #0066cc; padding-bottom: 10px; }}
                    h2 {{ font-size: 24px; border-bottom: 2px solid #0066cc; padding-bottom: 8px; }}
                    h3 {{ font-size: 20px; }}
                    h4 {{ font-size: 18px; }}
                    
                    /* Tables */
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 20px 0;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 10px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #0066cc;
                        color: white;
                        font-weight: bold;
                    }}
                    tr:nth-child(even) {{
                        background-color: #f9f9f9;
                    }}
                    tr:hover {{
                        background-color: #f0f0f0;
                    }}
                    
                    /* Paragraphs */
                    p {{
                        margin: 12px 0;
                        text-align: justify;
                    }}
                    
                    /* Links */
                    a {{
                        color: #0066cc;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                    
                    /* Lists */
                    ul, ol {{
                        margin: 15px 0;
                        padding-left: 30px;
                    }}
                    li {{
                        margin: 8px 0;
                    }}
                    
                    /* Center aligned text */
                    .center {{
                        text-align: center;
                    }}
                    
                    /* SEC-specific formatting */
                    .page-break {{
                        page-break-after: always;
                        margin: 30px 0;
                        border-top: 2px dashed #ccc;
                    }}
                    
                    /* Improve readability */
                    div[style*="font-size"] {{
                        line-height: 1.6 !important;
                    }}
                    
                    /* Fix overly small fonts */
                    font[size="1"], font[size="2"] {{
                        font-size: 12px !important;
                    }}
                    
                    /* Header info box */
                    .filing-header {{
                        background: #f0f8ff;
                        border-left: 4px solid #0066cc;
                        padding: 15px;
                        margin-bottom: 25px;
                    }}
                </style>
            </head>
            <body>
                <div class="filing-header">
                    <strong>Form {form_type}</strong> | 
                    Company: {self.ticker} (CIK: {self.cik})
                </div>
                {str(soup)}
            </body>
            </html>
            """

            return enhanced

        except Exception as e:
            logger.error(f"Error enhancing HTML: {e}")
            # Return original with minimal styling
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    body {{ padding: 20px; font-family: Arial, sans-serif; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>{html_content}</body>
            </html>
            """

    def extract_and_show_sections(self, content: str, form_type: str):
        """Extract and display sections in tree"""
        try:
            from src.extractors.sec_section_parser import SECFilingSectionParser

            parser = SECFilingSectionParser()

            self.section_tree.clear()
            self.sections = {}

            # Define sections based on form type
            if form_type == '10-K':
                section_names = ['business', 'risk_factors', 'properties', 'md_and_a', 'financial_statements']
            elif form_type == '10-Q':
                section_names = ['financial_info', 'md_and_a', 'market_risk', 'controls']
            else:
                # Try to extract any sections
                section_names = ['business', 'risk_factors', 'md_and_a']

            # Extract each section
            for section_name in section_names:
                section_text = parser.extract_section(content, form_type, section_name)

                if section_text and len(section_text) > 100:  # Only include if substantial content
                    self.sections[section_name] = section_text

                    # Add to tree with actual size
                    item = QTreeWidgetItem(self.section_tree)
                    display_name = section_name.replace('_', ' ').title()
                    item.setText(0, f"{display_name} ({len(section_text):,} chars)")
                    item.setData(0, Qt.UserRole, section_name)

            if self.sections:
                self.section_tree.show()
                logger.info(f"Extracted {len(self.sections)} sections")
            else:
                # If no sections extracted, hide the tree
                self.section_tree.hide()
                logger.warning("No sections could be extracted from filing")

        except Exception as e:
            logger.warning(f"Could not extract sections: {e}", exc_info=True)
            self.section_tree.hide()

    def on_section_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle section click - display the section content"""
        section_name = item.data(0, Qt.UserRole)
        if section_name and section_name in self.sections:
            section_content = self.sections[section_name]

            # Clean up the section content for better display
            from bs4 import BeautifulSoup

            try:
                # Parse and clean HTML
                soup = BeautifulSoup(section_content, 'html.parser')

                # Remove script and style tags
                for script in soup(["script", "style"]):
                    script.decompose()

                # Get cleaned HTML
                cleaned_html = str(soup)

                # Create styled HTML document
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            padding: 20px;
                            line-height: 1.6;
                            color: #333;
                            background: white;
                        }}
                        h1, h2, h3, h4, h5, h6 {{
                            color: #0066cc;
                            margin-top: 20px;
                            margin-bottom: 10px;
                        }}
                        table {{
                            border-collapse: collapse;
                            width: 100%;
                            margin: 15px 0;
                        }}
                        th, td {{
                            border: 1px solid #ddd;
                            padding: 8px;
                            text-align: left;
                        }}
                        th {{
                            background-color: #f2f2f2;
                            font-weight: bold;
                        }}
                        tr:nth-child(even) {{
                            background-color: #f9f9f9;
                        }}
                        p {{
                            margin: 10px 0;
                        }}
                        .section-header {{
                            background: #0066cc;
                            color: white;
                            padding: 15px;
                            margin: -20px -20px 20px -20px;
                            font-size: 20px;
                            font-weight: bold;
                        }}
                    </style>
                </head>
                <body>
                    <div class="section-header">{section_name.replace('_', ' ').title()}</div>
                    {cleaned_html}
                </body>
                </html>
                """

                self.content_viewer.setHtml(html, QUrl("https://www.sec.gov/"))
                self.status_label.setText(f"Viewing: {section_name.replace('_', ' ').title()}")

            except Exception as e:
                logger.error(f"Error displaying section: {e}")
                # Fallback to plain text display
                html = f"""
                <!DOCTYPE html>
                <html>
                <body style="font-family: monospace; padding: 20px;">
                    <h2>{section_name.replace('_', ' ').title()}</h2>
                    <pre>{section_content}</pre>
                </body>
                </html>
                """
                self.content_viewer.setHtml(html, QUrl("https://www.sec.gov/"))

    def on_search(self):
        """Handle search"""
        query = self.search_box.text()
        if not query:
            return

        # Find in page (QWebEngineView has built-in search)
        self.content_viewer.findText(query)
        self.status_label.setText(f"Searching for: {query}")

    def export_to_pdf(self):
        """Export filing to PDF"""
        if not self.current_filing:
            QMessageBox.warning(self, "No Filing", "Please load a filing first")
            return

        from PySide6.QtWidgets import QFileDialog

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export to PDF",
            f"{self.ticker}_{self.current_filing['form']}_{self.current_filing['accession']}.pdf",
            "PDF Files (*.pdf)"
        )

        if filename:
            # Use QWebEngineView's print to PDF
            self.content_viewer.page().printToPdf(filename)
            self.status_label.setText(f"Exported to: {filename}")
            QMessageBox.information(self, "Success", f"Filing exported to:\n{filename}")

    def export_to_text(self):
        """Export filing to text file"""
        if not self.current_filing:
            QMessageBox.warning(self, "No Filing", "Please load a filing first")
            return

        from PySide6.QtWidgets import QFileDialog
        from bs4 import BeautifulSoup

        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export to Text",
            f"{self.ticker}_{self.current_filing['form']}_{self.current_filing['accession']}.txt",
            "Text Files (*.txt)"
        )

        if filename:
            try:
                # Extract text from HTML
                soup = BeautifulSoup(self.current_filing['content'], 'html.parser')
                text = soup.get_text()

                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text)

                self.status_label.setText(f"Exported to: {filename}")
                QMessageBox.information(self, "Success", f"Filing exported to:\n{filename}")

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed:\n{str(e)}")


# Standalone test
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    viewer = FilingViewerWidget()
    viewer.setWindowTitle("SEC Filing Viewer - Test")
    viewer.resize(1200, 800)

    # Test with Netflix
    viewer.load_company_filings("NFLX", "0001065280")

    viewer.show()
    sys.exit(app.exec())

