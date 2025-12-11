"""
Relationship Graph Visualization Tab

Displays company relationships as an interactive network graph.
Shows supplier, customer, competitor, and partnership relationships.
"""
import logging
import json
from typing import Dict, List, Any, Optional

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
                               QPushButton, QLabel, QSpinBox, QCheckBox, QGroupBox,
                               QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QColor

logger = logging.getLogger(__name__)


class RelationshipGraphWidget(QWidget):
    """
    Interactive relationship graph visualization.
    Displays company relationships extracted from SEC filings.
    """

    def __init__(self, mongo_wrapper):
        """
        Initialize the graph widget.

        Args:
            mongo_wrapper: MongoDB wrapper for accessing relationships
        """
        super().__init__()
        self.mongo = mongo_wrapper
        self.current_profile = None
        self.all_profiles = []
        self.init_ui()

    def init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)

        # === Control Panel ===
        control_group = QGroupBox("Relationship Graph Controls")
        control_layout = QHBoxLayout()

        # Company selector
        label_company = QLabel("Select Company:")
        self.combo_companies = QComboBox()
        self.combo_companies.currentIndexChanged.connect(self.on_company_selected)
        control_layout.addWidget(label_company)
        control_layout.addWidget(self.combo_companies)

        # Relationship type filter
        label_type = QLabel("Filter by Type:")
        self.combo_rel_type = QComboBox()
        self.combo_rel_type.addItem("All Relationships")
        self.combo_rel_type.addItem("Suppliers")
        self.combo_rel_type.addItem("Customers")
        self.combo_rel_type.addItem("Competitors")
        self.combo_rel_type.addItem("Partners")
        self.combo_rel_type.currentIndexChanged.connect(self.refresh_relationships)
        control_layout.addWidget(label_type)
        control_layout.addWidget(self.combo_rel_type)

        # Confidence threshold
        label_confidence = QLabel("Min Confidence:")
        self.spin_confidence = QSpinBox()
        self.spin_confidence.setMinimum(0)
        self.spin_confidence.setMaximum(100)
        self.spin_confidence.setValue(50)
        self.spin_confidence.setSuffix("%")
        self.spin_confidence.valueChanged.connect(self.refresh_relationships)
        control_layout.addWidget(label_confidence)
        control_layout.addWidget(self.spin_confidence)

        # Show financial data checkbox
        self.check_financial = QCheckBox("Show Financial Data")
        self.check_financial.setChecked(True)
        self.check_financial.stateChanged.connect(self.refresh_relationships)
        control_layout.addWidget(self.check_financial)

        # Refresh button
        btn_refresh = QPushButton("Refresh Data")
        btn_refresh.clicked.connect(self.load_all_companies)
        control_layout.addWidget(btn_refresh)

        control_layout.addStretch()
        control_group.setLayout(control_layout)
        layout.addWidget(control_group)

        # === Statistics Panel ===
        stats_group = QGroupBox("Relationship Statistics")
        stats_layout = QHBoxLayout()

        self.label_total_rels = QLabel("Total Relationships: 0")
        self.label_avg_confidence = QLabel("Avg Confidence: 0.00")
        self.label_supplier_count = QLabel("Suppliers: 0")
        self.label_customer_count = QLabel("Customers: 0")
        self.label_concentration_hhi = QLabel("Customer Concentration (HHI): N/A")

        font_bold = QFont()
        font_bold.setBold(True)
        for label in [self.label_total_rels, self.label_avg_confidence,
                      self.label_supplier_count, self.label_customer_count,
                      self.label_concentration_hhi]:
            label.setFont(font_bold)

        stats_layout.addWidget(self.label_total_rels)
        stats_layout.addWidget(self.label_avg_confidence)
        stats_layout.addWidget(self.label_supplier_count)
        stats_layout.addWidget(self.label_customer_count)
        stats_layout.addWidget(self.label_concentration_hhi)
        stats_layout.addStretch()

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # === Relationships Table ===
        relationships_group = QGroupBox("Relationships")
        relationships_layout = QVBoxLayout()

        self.table_relationships = QTableWidget()
        self.table_relationships.setColumnCount(6)
        self.table_relationships.setHorizontalHeaderLabels([
            "Target Company", "Type", "Confidence", "Method", "Context", "First Mentioned"
        ])
        self.table_relationships.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_relationships.setMaximumHeight(250)
        relationships_layout.addWidget(self.table_relationships)

        relationships_group.setLayout(relationships_layout)
        layout.addWidget(relationships_group)

        # === Financial Relationships ===
        financial_group = QGroupBox("Financial Relationships")
        financial_layout = QVBoxLayout()

        # Customers
        customers_label = QLabel("Top Customers:")
        customers_font = QFont()
        customers_font.setBold(True)
        customers_label.setFont(customers_font)
        financial_layout.addWidget(customers_label)

        self.table_customers = QTableWidget()
        self.table_customers.setColumnCount(3)
        self.table_customers.setHorizontalHeaderLabels([
            "Company", "Revenue %", "Confidence"
        ])
        self.table_customers.setMaximumHeight(120)
        financial_layout.addWidget(self.table_customers)

        # Suppliers
        suppliers_label = QLabel("Key Suppliers:")
        suppliers_label.setFont(customers_font)
        financial_layout.addWidget(suppliers_label)

        self.table_suppliers = QTableWidget()
        self.table_suppliers.setColumnCount(3)
        self.table_suppliers.setHorizontalHeaderLabels([
            "Company", "Supply %", "Confidence"
        ])
        self.table_suppliers.setMaximumHeight(120)
        financial_layout.addWidget(self.table_suppliers)

        financial_group.setLayout(financial_layout)
        layout.addWidget(financial_group)

        layout.addStretch()

    def load_all_companies(self):
        """Load all companies from database"""
        try:
            self.combo_companies.blockSignals(True)
            self.combo_companies.clear()

            # Get all profiles with relationships
            self.all_profiles = list(self.mongo.db['Fundamental_Data_Pipeline'].find(
                {'relationships': {'$exists': True}},
                {'cik': 1, 'company_info.name': 1, 'company_info.ticker': 1}
            ))

            # Sort by company name
            self.all_profiles.sort(key=lambda x: x.get('company_info', {}).get('name', 'Unknown'))

            # Populate combo box
            for profile in self.all_profiles:
                company_name = profile.get('company_info', {}).get('name', 'Unknown')
                ticker = profile.get('company_info', {}).get('ticker', '')
                cik = profile.get('cik', '')
                display_name = f"{company_name} ({ticker})" if ticker else company_name
                self.combo_companies.addItem(display_name, userData=cik)

            if self.combo_companies.count() > 0:
                self.combo_companies.setCurrentIndex(0)
            else:
                QMessageBox.information(self, "No Data",
                    "No company relationships found in database.\n"
                    "Process companies to extract relationships.")

            self.combo_companies.blockSignals(False)

        except Exception as e:
            logger.error(f"Error loading companies: {e}")
            QMessageBox.critical(self, "Error", f"Could not load companies: {e}")

    def on_company_selected(self, index: int):
        """Handle company selection"""
        if index < 0:
            return

        cik = self.combo_companies.itemData(index)
        if not cik:
            return

        try:
            # Load profile from database
            self.current_profile = self.mongo.db['Fundamental_Data_Pipeline'].find_one({'cik': cik})
            if self.current_profile:
                self.refresh_relationships()
            else:
                QMessageBox.warning(self, "Not Found", f"Profile for CIK {cik} not found")

        except Exception as e:
            logger.error(f"Error loading profile: {e}")
            QMessageBox.critical(self, "Error", f"Could not load profile: {e}")

    def refresh_relationships(self):
        """Refresh the relationships display"""
        if not self.current_profile:
            return

        try:
            # Clear tables
            self.table_relationships.setRowCount(0)
            self.table_customers.setRowCount(0)
            self.table_suppliers.setRowCount(0)

            cik = self.current_profile.get('cik', '')
            relationships = self.current_profile.get('relationships', {})

            if not relationships:
                self.label_total_rels.setText("Total Relationships: 0")
                return

            # Get relationships from MongoDB
            db_relationships = list(self.mongo.db['company_relationships'].find(
                {'source_cik': cik}
            ))

            # Filter by type and confidence
            rel_type_filter = self.combo_rel_type.currentText()
            min_confidence = self.spin_confidence.value() / 100.0

            filtered_rels = []
            for rel in db_relationships:
                # Filter by type
                if rel_type_filter != "All Relationships":
                    rel_type_map = {
                        'Suppliers': 'supplier',
                        'Customers': 'customer',
                        'Competitors': 'competitor',
                        'Partners': 'partner'
                    }
                    if rel.get('relationship_type') != rel_type_map.get(rel_type_filter):
                        continue

                # Filter by confidence
                if rel.get('confidence_score', 0) < min_confidence:
                    continue

                filtered_rels.append(rel)

            # Populate relationships table
            self.table_relationships.setRowCount(len(filtered_rels))

            supplier_count = 0
            customer_count = 0
            total_confidence = 0

            for row, rel in enumerate(filtered_rels):
                target_name = rel.get('target_name', 'Unknown')
                rel_type = rel.get('relationship_type', 'unknown')
                confidence = rel.get('confidence_score', 0)
                method = rel.get('extraction_method', 'unknown')
                context = rel.get('context', '')[:100]
                first_mentioned = rel.get('first_mentioned', 'N/A')

                # Count types
                if rel_type == 'supplier':
                    supplier_count += 1
                elif rel_type == 'customer':
                    customer_count += 1

                total_confidence += confidence

                # Add row
                self.table_relationships.setItem(row, 0, QTableWidgetItem(target_name))
                self.table_relationships.setItem(row, 1, QTableWidgetItem(rel_type))
                self.table_relationships.setItem(row, 2, QTableWidgetItem(f"{confidence:.2f}"))
                self.table_relationships.setItem(row, 3, QTableWidgetItem(method))
                self.table_relationships.setItem(row, 4, QTableWidgetItem(context))
                self.table_relationships.setItem(row, 5, QTableWidgetItem(first_mentioned))

            # Update statistics
            avg_conf = total_confidence / len(filtered_rels) if filtered_rels else 0
            self.label_total_rels.setText(f"Total Relationships: {len(filtered_rels)}")
            self.label_avg_confidence.setText(f"Avg Confidence: {avg_conf:.2f}")
            self.label_supplier_count.setText(f"Suppliers: {supplier_count}")
            self.label_customer_count.setText(f"Customers: {customer_count}")

            # Show financial relationships if enabled
            if self.check_financial.isChecked():
                self.show_financial_relationships(cik)
            else:
                self.table_customers.setRowCount(0)
                self.table_suppliers.setRowCount(0)

        except Exception as e:
            logger.error(f"Error refreshing relationships: {e}")
            QMessageBox.critical(self, "Error", f"Error refreshing relationships: {e}")

    def show_financial_relationships(self, cik: str):
        """Display financial relationships (customers, suppliers)"""
        try:
            financial_rel = self.mongo.db['financial_relationships'].find_one({'cik': cik})
            if not financial_rel:
                return

            # Show customers
            customers = financial_rel.get('customers', [])
            self.table_customers.setRowCount(len(customers))

            for row, customer in enumerate(customers):
                name = customer.get('name', 'Unknown')
                revenue_pct = customer.get('revenue_percent', 0)
                confidence = customer.get('confidence', 0)

                self.table_customers.setItem(row, 0, QTableWidgetItem(name))
                self.table_customers.setItem(row, 1, QTableWidgetItem(f"{revenue_pct:.1f}%"))
                self.table_customers.setItem(row, 2, QTableWidgetItem(f"{confidence:.2f}"))

            # Show suppliers
            suppliers = financial_rel.get('suppliers', [])
            self.table_suppliers.setRowCount(len(suppliers))

            for row, supplier in enumerate(suppliers):
                name = supplier.get('name', 'Unknown')
                supply_pct = supplier.get('supply_percent')
                confidence = supplier.get('confidence', 0)

                supply_pct_str = f"{supply_pct:.1f}%" if supply_pct else "N/A"

                self.table_suppliers.setItem(row, 0, QTableWidgetItem(name))
                self.table_suppliers.setItem(row, 1, QTableWidgetItem(supply_pct_str))
                self.table_suppliers.setItem(row, 2, QTableWidgetItem(f"{confidence:.2f}"))

            # Show concentration metrics
            concentration = financial_rel.get('customer_concentration', {})
            if concentration:
                hhi = concentration.get('herfindahl_index', 0)
                hhi_level = concentration.get('hhi_level', 'Unknown')
                self.label_concentration_hhi.setText(
                    f"Customer Concentration (HHI): {hhi:.0f} ({hhi_level})"
                )

        except Exception as e:
            logger.warning(f"Error showing financial relationships: {e}")

