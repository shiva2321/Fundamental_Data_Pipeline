"""
Comprehensive Relationship Analysis Tab

Shows network graph of ALL companies in database with their relationships.
Allows filtering, zooming, and updating when new companies are added.
"""
import logging
from typing import Dict, List, Any, Optional
import json

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QComboBox, QSpinBox, QGroupBox, QCheckBox,
                               QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
                               QProgressDialog, QSlider, QTextEdit, QSplitter)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QColor

logger = logging.getLogger(__name__)


class ReprocessThread(QThread):
    """Background thread to reprocess profiles - extracts relationships from existing data"""
    finished = Signal(int, int)  # success_count, failed_count
    progress = Signal(int, str)  # Progress value and message
    error = Signal(str)

    def __init__(self, mongo, profiles_to_process):
        super().__init__()
        self.mongo = mongo
        self.profiles_to_process = profiles_to_process
        self._cancel_flag = False

    def cancel(self):
        """Cancel the reprocessing"""
        self._cancel_flag = True

    def run(self):
        try:
            from src.extractors.profile_relationship_extractor import ProfileRelationshipExtractor

            # Initialize extractor (uses existing profile data, no SEC fetch)
            extractor = ProfileRelationshipExtractor(self.mongo)

            success_count = 0
            failed_count = 0
            total = len(self.profiles_to_process)

            for idx, (ticker, cik, company_info) in enumerate(self.profiles_to_process):
                if self._cancel_flag:
                    break

                self.progress.emit(idx, f"Extracting relationships for {ticker} ({idx+1}/{total})...")

                try:
                    # Load full profile from database
                    profile = self.mongo.db['Fundamental_Data_Pipeline'].find_one({'cik': cik})

                    if not profile:
                        logger.warning(f"Profile not found for {ticker} (CIK: {cik})")
                        failed_count += 1
                        continue

                    # Extract relationships from existing profile data
                    relationships_data = extractor.extract_from_profile(
                        profile=profile,
                        progress_callback=lambda level, msg: self.progress.emit(idx, msg)
                    )

                    # Store back in profile
                    extractor.store_relationships_in_profile(
                        profile=profile,
                        relationships_data=relationships_data
                    )

                    success_count += 1

                except Exception as e:
                    logger.exception(f"Error extracting relationships for {ticker}: {e}")
                    failed_count += 1

            self.finished.emit(success_count, failed_count)

        except Exception as e:
            logger.exception(f"Thread error: {e}")
            self.error.emit(str(e))


class GraphBuilderThread(QThread):
    """Background thread to build relationship graph"""
    finished = Signal(object)  # Emits the graph object
    progress = Signal(int, str)  # Progress percentage and message
    error = Signal(str)

    def __init__(self, mongo, filters):
        super().__init__()
        self.mongo = mongo
        self.filters = filters
        self.graph_data = None

    def run(self):
        try:
            self.progress.emit(10, "Loading relationships from optimized collection...")

            # Try to load from optimized company_relationships collection first
            relationship_docs = list(self.mongo.db['company_relationships'].find({}))

            logger.info(f"GraphBuilderThread: Found {len(relationship_docs)} docs in company_relationships collection")

            # AUTO-FIX: Convert old plural keys to singular keys if needed
            fixed_count = 0
            for doc in relationship_docs:
                by_type = doc.get('by_type', {})
                needs_fix = any(k in by_type for k in ['suppliers', 'customers', 'competitors', 'partners', 'investors'])
                
                if needs_fix:
                    new_by_type = {}
                    key_mapping = {
                        'suppliers': 'supplier',
                        'customers': 'customer',
                        'competitors': 'competitor',
                        'partners': 'partner',
                        'investors': 'investor',
                        'related_companies': 'related_company'
                    }
                    
                    for old_key, new_key in key_mapping.items():
                        if old_key in by_type:
                            new_by_type[new_key] = by_type[old_key]
                        elif new_key in by_type:
                            new_by_type[new_key] = by_type[new_key]
                    
                    # Copy any other keys
                    for key, value in by_type.items():
                        if key not in key_mapping and key not in new_by_type:
                            new_by_type[key] = value
                    
                    doc['by_type'] = new_by_type
                    
                    # Update in MongoDB
                    self.mongo.db['company_relationships'].update_one(
                        {'_id': doc['_id']},
                        {'$set': {'by_type': new_by_type}}
                    )
                    fixed_count += 1
            
            if fixed_count > 0:
                logger.info(f"Auto-fixed {fixed_count} documents with old data structure")
                self.progress.emit(20, f"Fixed {fixed_count} documents with old structure...")

            if relationship_docs:
                self.progress.emit(30, f"Found {len(relationship_docs)} companies in optimized collection")
                logger.info(f"Building graph from {len(relationship_docs)} relationship documents")

                # Build graph from optimized structure
                nodes = []
                edges = []
                node_map = {}

                for idx, doc in enumerate(relationship_docs):
                    cik = doc.get('cik', '')
                    ticker = doc.get('ticker', 'N/A')
                    name = doc.get('company_name', 'Unknown')

                    # Add source node
                    if cik not in node_map:
                        nodes.append({
                            'id': cik,
                            'cik': cik,
                            'ticker': ticker,
                            'name': name
                        })
                        node_map[cik] = len(nodes) - 1

                    # Get relationships by type
                    by_type = doc.get('by_type', {})

                    # Process each relationship type
                    for rel_type, rels in by_type.items():
                        # Apply type filter
                        if self.filters.get('relationship_type') != 'all':
                            if rel_type != self.filters.get('relationship_type'):
                                continue

                        if not isinstance(rels, list):
                            continue

                        for rel in rels:
                            target_cik = rel.get('target_cik', '')
                            confidence = rel.get('confidence', 0)

                            # Apply confidence filter
                            if confidence < self.filters.get('min_confidence', 0):
                                continue

                            # Add target node if not exists
                            if target_cik and target_cik not in node_map:
                                nodes.append({
                                    'id': target_cik,
                                    'cik': target_cik,
                                    'ticker': 'N/A',
                                    'name': rel.get('target_name', 'Unknown')
                                })
                                node_map[target_cik] = len(nodes) - 1

                            # Add edge
                            if target_cik:
                                edges.append({
                                    'source': cik,
                                    'target': target_cik,
                                    'type': rel_type,
                                    'confidence': confidence,
                                    'context': rel.get('context', '')[:100]
                                })

                    if idx % 10 == 0:
                        progress_pct = 30 + int((idx / len(relationship_docs)) * 50)
                        self.progress.emit(progress_pct, f"Processing {idx}/{len(relationship_docs)} companies...")

            else:
                # Fallback: Load from profiles if optimized collection doesn't exist
                self.progress.emit(10, "Loading from company profiles...")

                profiles = list(self.mongo.db['Fundamental_Data_Pipeline'].find(
                    {'relationships': {'$exists': True}},
                    {'cik': 1, 'company_info': 1, 'relationships': 1}
                ))

                self.progress.emit(30, f"Found {len(profiles)} companies with relationships")

                if not profiles:
                    self.error.emit("No companies with relationships found in database")
                    return

                # Build nodes and edges from profiles
                nodes = []
                edges = []
                node_map = {}

                for idx, profile in enumerate(profiles):
                    cik = profile.get('cik', '')
                    company_info = profile.get('company_info', {})
                    ticker = company_info.get('ticker', 'N/A')
                    name = company_info.get('name') or company_info.get('title', 'Unknown')

                    # Add node
                    if cik not in node_map:
                        nodes.append({
                            'id': cik,
                            'cik': cik,
                            'ticker': ticker,
                            'name': name
                        })
                        node_map[cik] = len(nodes) - 1

                    # Add edges from relationships
                    relationships = profile.get('relationships', {}).get('relationships', [])

                    for rel in relationships:
                        target_cik = rel.get('target_cik', '')
                        rel_type = rel.get('relationship_type', 'unknown')
                        confidence = rel.get('confidence_score', 0)

                        # Apply filters
                        if self.filters.get('min_confidence', 0) > confidence:
                            continue

                        if self.filters.get('relationship_type') != 'all':
                            if rel_type != self.filters.get('relationship_type'):
                                continue

                        # Add target node if not exists
                        if target_cik and target_cik not in node_map:
                            nodes.append({
                                'id': target_cik,
                                'cik': target_cik,
                                'ticker': 'N/A',
                                'name': rel.get('target_name', 'Unknown')
                            })
                            node_map[target_cik] = len(nodes) - 1

                        if target_cik:
                            edges.append({
                                'source': cik,
                                'target': target_cik,
                                'type': rel_type,
                                'confidence': confidence,
                                'context': rel.get('context', '')[:100]
                            })

                    if idx % 10 == 0:
                        progress_pct = 30 + int((idx / len(profiles)) * 50)
                        self.progress.emit(progress_pct, f"Processing {idx}/{len(profiles)} companies...")

            self.progress.emit(90, "Finalizing graph...")

            self.graph_data = {
                'nodes': nodes,
                'edges': edges,
                'node_map': node_map,
                'stats': {
                    'total_companies': len(nodes),
                    'total_relationships': len(edges),
                    'relationship_types': self._count_types(edges)
                }
            }

            logger.info(f"Graph built: {len(nodes)} nodes, {len(edges)} edges")
            logger.info(f"Relationship types: {self.graph_data['stats']['relationship_types']}")

            self.progress.emit(100, "Graph built successfully!")
            self.finished.emit(self.graph_data)

        except Exception as e:
            logger.exception(f"Error building graph: {e}")
            self.error.emit(f"Failed to build graph: {e}")

    def _count_types(self, edges):
        """Count relationship types"""
        types = {}
        for edge in edges:
            rel_type = edge.get('type', 'unknown')
            types[rel_type] = types.get(rel_type, 0) + 1
        return types


class RelationshipAnalysisWidget(QWidget):
    """
    Comprehensive relationship analysis showing network graph of all companies.
    Displays suppliers, customers, competitors, partners, and investors.
    """

    def __init__(self, mongo_wrapper):
        super().__init__()
        self.mongo = mongo_wrapper
        self.graph_data = None
        self.init_ui()

    def init_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)

        # === Top Control Panel ===
        control_panel = QGroupBox("Graph Controls")
        control_layout = QHBoxLayout()

        # Relationship type filter
        label_type = QLabel("Relationship Type:")
        self.combo_rel_type = QComboBox()
        self.combo_rel_type.addItem("All Relationships", "all")
        self.combo_rel_type.addItem("Suppliers", "supplier")
        self.combo_rel_type.addItem("Customers", "customer")
        self.combo_rel_type.addItem("Competitors", "competitor")
        self.combo_rel_type.addItem("Partners", "partner")
        self.combo_rel_type.addItem("Investors", "investor")
        control_layout.addWidget(label_type)
        control_layout.addWidget(self.combo_rel_type)

        # Confidence threshold
        label_confidence = QLabel("Min Confidence:")
        self.spin_confidence = QSpinBox()
        self.spin_confidence.setMinimum(0)
        self.spin_confidence.setMaximum(100)
        self.spin_confidence.setValue(50)
        self.spin_confidence.setSuffix("%")
        control_layout.addWidget(label_confidence)
        control_layout.addWidget(self.spin_confidence)

        # Update button
        btn_update = QPushButton("🔄 Update Graph")
        btn_update.setToolTip("Rebuild graph with current filters and include new companies")
        btn_update.clicked.connect(self.build_graph)
        btn_update.setStyleSheet("background-color: #0d6efd; font-weight: bold;")
        control_layout.addWidget(btn_update)

        # Export button
        btn_export = QPushButton("📥 Export Data")
        btn_export.setToolTip("Export graph data to JSON")
        btn_export.clicked.connect(self.export_graph_data)
        control_layout.addWidget(btn_export)

        # Reprocess button
        btn_reprocess = QPushButton("🔄 Reprocess All Profiles")
        btn_reprocess.setToolTip("Extract relationships from existing profiles (run this if you see 0 relationships)")
        btn_reprocess.clicked.connect(self.reprocess_all_profiles)
        btn_reprocess.setStyleSheet("background-color: #ffc107; color: #000; font-weight: bold;")
        control_layout.addWidget(btn_reprocess)

        control_layout.addStretch()
        control_panel.setLayout(control_layout)
        layout.addWidget(control_panel)

        # === Statistics Panel ===
        stats_group = QGroupBox("Network Statistics")
        stats_layout = QHBoxLayout()

        self.lbl_total_companies = QLabel("Companies: 0")
        self.lbl_total_relationships = QLabel("Relationships: 0")
        self.lbl_suppliers = QLabel("Suppliers: 0")
        self.lbl_customers = QLabel("Customers: 0")
        self.lbl_competitors = QLabel("Competitors: 0")
        self.lbl_partners = QLabel("Partners: 0")

        font_bold = QFont()
        font_bold.setBold(True)
        for label in [self.lbl_total_companies, self.lbl_total_relationships,
                      self.lbl_suppliers, self.lbl_customers, self.lbl_competitors, self.lbl_partners]:
            label.setFont(font_bold)

        stats_layout.addWidget(self.lbl_total_companies)
        stats_layout.addWidget(self.lbl_total_relationships)
        stats_layout.addWidget(self.lbl_suppliers)
        stats_layout.addWidget(self.lbl_customers)
        stats_layout.addWidget(self.lbl_competitors)
        stats_layout.addWidget(self.lbl_partners)
        stats_layout.addStretch()

        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # === Main Content Splitter ===
        splitter = QSplitter(Qt.Vertical)

        # Top: Graph Visualization Placeholder
        graph_widget = QGroupBox("Relationship Network Graph")
        self.graph_layout = QVBoxLayout()  # Store as instance variable

        # Placeholder for actual graph (can be replaced with matplotlib or networkx viz)
        self.graph_placeholder = QLabel()
        self.graph_placeholder.setAlignment(Qt.AlignCenter)
        self.graph_placeholder.setStyleSheet("background-color: #2d2d2d; border: 2px dashed #4da6ff; padding: 40px;")
        self.graph_placeholder.setWordWrap(True)
        self.graph_placeholder.setText(
            "📊 Network Graph Visualization\n\n"
            "Click 'Update Graph' to load relationship network.\n\n"
            "The graph will show:\n"
            "• Companies as nodes (sized by connection count)\n"
            "• Relationships as edges (colored by type)\n"
            "• Interactive zoom and pan\n"
            "• Click nodes to see details"
        )

        self.graph_layout.addWidget(self.graph_placeholder)
        graph_widget.setLayout(self.graph_layout)
        splitter.addWidget(graph_widget)

        # Bottom: Relationship Details Table
        details_widget = QGroupBox("Relationship Details")
        details_layout = QVBoxLayout()

        self.table_relationships = QTableWidget()
        self.table_relationships.setColumnCount(6)
        self.table_relationships.setHorizontalHeaderLabels([
            "Source Company", "Target Company", "Relationship Type",
            "Confidence", "Context", "Actions"
        ])
        self.table_relationships.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_relationships.setMaximumHeight(250)
        details_layout.addWidget(self.table_relationships)

        details_widget.setLayout(details_layout)
        splitter.addWidget(details_widget)

        # Set splitter sizes
        splitter.setSizes([500, 250])
        layout.addWidget(splitter)

        # Bottom: Instructions
        instructions = QLabel(
            "💡 Tip: Use filters to focus on specific relationship types. "
            "Click 'Update Graph' to include newly processed companies."
        )
        instructions.setStyleSheet("color: #4da6ff; font-size: 10px; padding: 5px; font-style: italic;")
        layout.addWidget(instructions)

    def build_graph(self):
        """Build relationship graph from database"""
        # Get filters
        filters = {
            'relationship_type': self.combo_rel_type.currentData(),
            'min_confidence': self.spin_confidence.value() / 100.0
        }

        # Show progress dialog
        progress = QProgressDialog("Building relationship graph...", "Cancel", 0, 100, self)
        progress.setWindowTitle("Loading")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # Start background thread
        self.graph_thread = GraphBuilderThread(self.mongo, filters)

        def on_progress(pct, msg):
            progress.setValue(pct)
            progress.setLabelText(msg)

        def on_finished(graph_data):
            progress.setValue(100)
            progress.close()
            self.graph_data = graph_data
            self.display_graph(graph_data)

        def on_error(error_msg):
            progress.close()
            QMessageBox.critical(self, "Error", f"Failed to build graph:\n{error_msg}")

        self.graph_thread.progress.connect(on_progress)
        self.graph_thread.finished.connect(on_finished)
        self.graph_thread.error.connect(on_error)
        self.graph_thread.start()

    def display_graph(self, graph_data):
        """Display the graph and update tables"""
        if not graph_data:
            return

        nodes = graph_data.get('nodes', [])
        edges = graph_data.get('edges', [])
        stats = graph_data.get('stats', {})

        # Update statistics
        self.lbl_total_companies.setText(f"Companies: {stats.get('total_companies', 0)}")
        self.lbl_total_relationships.setText(f"Relationships: {stats.get('total_relationships', 0)}")

        rel_types = stats.get('relationship_types', {})
        self.lbl_suppliers.setText(f"Suppliers: {rel_types.get('supplier', 0)}")
        self.lbl_customers.setText(f"Customers: {rel_types.get('customer', 0)}")
        self.lbl_competitors.setText(f"Competitors: {rel_types.get('competitor', 0)}")
        self.lbl_partners.setText(f"Partners: {rel_types.get('partner', 0)}")

        # Update graph visualization with actual interactive graph
        try:
            self._render_network_graph(nodes, edges, stats)
        except Exception as e:
            logger.exception(f"Error rendering graph: {e}")
            self.graph_placeholder.setText(
                f"📊 Relationship Network Graph\n\n"
                f"✓ {len(nodes)} companies\n"
                f"✓ {len(edges)} relationships\n"
                f"✓ {len(rel_types)} relationship types\n\n"
                f"Graph data loaded successfully!\n"
                f"Note: Visualization error - check logs"
            )

        # Populate relationship table
        self.table_relationships.setRowCount(min(len(edges), 100))  # Show first 100

        # Get node map for lookups
        node_map = {node['cik']: node for node in nodes}

        for row, edge in enumerate(edges[:100]):
            source_cik = edge.get('source', '')
            target_cik = edge.get('target', '')

            source_node = node_map.get(source_cik, {})
            target_node = node_map.get(target_cik, {})

            source_name = f"{source_node.get('ticker', 'N/A')} - {source_node.get('name', 'Unknown')}"
            target_name = f"{target_node.get('ticker', 'N/A')} - {target_node.get('name', 'Unknown')}"

            self.table_relationships.setItem(row, 0, QTableWidgetItem(source_name))
            self.table_relationships.setItem(row, 1, QTableWidgetItem(target_name))
            self.table_relationships.setItem(row, 2, QTableWidgetItem(edge.get('type', 'unknown')))
            self.table_relationships.setItem(row, 3, QTableWidgetItem(f"{edge.get('confidence', 0):.2f}"))
            self.table_relationships.setItem(row, 4, QTableWidgetItem(edge.get('context', '')[:100]))

            # Actions button
            btn_details = QPushButton("View")
            btn_details.clicked.connect(lambda checked, e=edge: self.show_relationship_details(e))
            self.table_relationships.setCellWidget(row, 5, btn_details)

        if len(edges) > 100:
            logger.info(f"Showing first 100 of {len(edges)} relationships")

    def _render_network_graph(self, nodes, edges, stats):
        """Render interactive network graph using matplotlib and networkx"""
        try:
            import matplotlib.pyplot as plt
            import networkx as nx
            from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
            from matplotlib.figure import Figure

            # Clear existing widget
            while self.graph_layout.count():
                item = self.graph_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            # Create interactive matplotlib figure
            fig = Figure(figsize=(14, 10), facecolor='#1e1e1e')
            canvas = FigureCanvas(fig)
            ax = fig.add_subplot(111, facecolor='#2d2d2d')

            # Build network graph
            G = nx.DiGraph()

            # First pass: collect all unique companies (sources and targets)
            source_ciks = set()
            target_ciks = set()
            cik_to_name = {}

            for node in nodes:
                cik = node['cik']
                ticker = node.get('ticker', 'N/A')
                name = node.get('name', 'Unknown')

                # Store best name available (prefer ticker if valid, else use name)
                if ticker and ticker != 'N/A':
                    cik_to_name[cik] = ticker
                elif name and name != 'Unknown':
                    cik_to_name[cik] = name[:20]  # Truncate long names
                else:
                    cik_to_name[cik] = 'N/A'

                G.add_node(cik, ticker=ticker, name=name)

            # Second pass: update target names from edges (more accurate)
            for edge in edges:
                source_cik = edge.get('source', '')
                target_cik = edge.get('target', '')
                target_name = edge.get('target', 'Unknown')  # Get from edge data

                # Track source vs target
                if source_cik:
                    source_ciks.add(source_cik)
                if target_cik:
                    target_ciks.add(target_cik)

                # Update target name if we have it from edge
                if target_cik and target_name and target_name != 'Unknown':
                    # Clean up the target name (remove "N/A - " prefix)
                    if target_name.startswith('N/A - '):
                        clean_name = target_name.replace('N/A - ', '')
                        cik_to_name[target_cik] = clean_name[:20]
                    else:
                        cik_to_name[target_cik] = target_name[:20]

                G.add_edge(source_cik, target_cik,
                          relationship=edge.get('type', 'unknown'),
                          confidence=edge.get('confidence', 0),
                          context=edge.get('context', ''))

            # Layout
            if len(nodes) <= 20:
                pos = nx.spring_layout(G, k=3, iterations=50, seed=42)
            else:
                pos = nx.circular_layout(G)

            # Store data for interactivity
            self.graph_G = G
            self.graph_pos = pos
            self.graph_nodes_data = {n['cik']: n for n in nodes}
            self.graph_edges_data = {(e['source'], e['target']): e for e in edges}
            self.graph_cik_to_name = cik_to_name

            # Color map for edges by relationship type
            edge_colors_map = {
                'supplier': '#28a745',      # Green
                'customer': '#007bff',      # Blue
                'competitor': '#dc3545',    # Red
                'partner': '#ffc107',       # Yellow
                'investor': '#17a2b8',      # Cyan
                'related_company': '#6c757d'  # Gray
            }

            # Draw edges with different colors by type
            edge_artists = []
            for edge in G.edges(data=True):
                source, target, data = edge
                rel_type = data.get('relationship', 'unknown')
                color = edge_colors_map.get(rel_type, '#6c757d')
                confidence = data.get('confidence', 0)

                edge_collection = nx.draw_networkx_edges(
                    G, pos,
                    edgelist=[(source, target)],
                    edge_color=color,
                    alpha=min(0.3 + confidence * 0.7, 1.0),
                    width=1.0 + confidence * 2.0,
                    arrows=True,
                    arrowsize=10,
                    ax=ax,
                    arrowstyle='->'
                )

                # Handle both LineCollection and list returns
                if edge_collection:
                    if isinstance(edge_collection, list):
                        if edge_collection:
                            edge_collection = edge_collection[0]
                        else:
                            continue

                    try:
                        edge_collection.set_picker(5)
                        edge_collection.edge_data = (source, target)
                        edge_artists.append(edge_collection)
                    except AttributeError:
                        pass

            # Draw nodes with different colors: source companies vs target companies
            node_degrees = dict(G.degree())
            max_degree = max(node_degrees.values()) if node_degrees else 1
            max_degree = max(max_degree, 1)  # Ensure at least 1 to avoid division by zero

            # Separate source and target nodes
            source_nodes = list(source_ciks)
            target_only_nodes = [n for n in G.nodes() if n in target_ciks and n not in source_ciks]

            # Draw source nodes (companies in our database - larger, different colors)
            source_colors = ['#4da6ff', '#ff6b6b', '#4ecdc4', '#ffe66d', '#a8dadc']  # Different colors per source
            for idx, node in enumerate(source_nodes):
                color = source_colors[idx % len(source_colors)]
                degree = node_degrees.get(node, 0)
                size = 1000 + (degree / max_degree) * 1500

                nx.draw_networkx_nodes(
                    G, pos,
                    nodelist=[node],
                    node_color=color,
                    node_size=size,
                    alpha=0.9,
                    ax=ax
                )

            # Draw target nodes (mentioned companies - uniform color, smaller)
            if target_only_nodes:
                target_sizes = [400 + (node_degrees.get(n, 0) / max_degree) * 600 for n in target_only_nodes]
                nx.draw_networkx_nodes(
                    G, pos,
                    nodelist=target_only_nodes,
                    node_color='#7fb3d5',
                    node_size=target_sizes,
                    alpha=0.7,
                    ax=ax
                )

            # Make all nodes clickable
            self.node_collection = None

            # Draw labels with actual company names
            labels = {node: cik_to_name.get(node, 'Unknown') for node in G.nodes()}
            label_dict = nx.draw_networkx_labels(
                G, pos,
                labels=labels,
                font_size=8,
                font_weight='bold',
                font_color='white',
                ax=ax
            )

            # Title
            ax.set_title(f'Relationship Network - {stats.get("total_companies", 0)} Companies, '
                        f'{stats.get("total_relationships", 0)} Relationships',
                        fontsize=14, fontweight='bold', color='white', pad=20)
            ax.axis('off')

            # Add legend
            from matplotlib.patches import Patch
            rel_types = stats.get('relationship_types', {})
            legend_elements = [
                Patch(facecolor=color, label=f"{rel_type.title()} ({rel_types.get(rel_type, 0)})")
                for rel_type, color in edge_colors_map.items()
                if rel_type in rel_types
            ]

            if legend_elements:
                ax.legend(handles=legend_elements, loc='upper right',
                         facecolor='#2d2d2d', edgecolor='white',
                         labelcolor='white', fontsize=9)

            fig.tight_layout()

            # === ADD INTERACTIVITY ===

            # Store for interaction state
            self.selected_node = None
            self.drag_offset = None
            self.is_dragging = False
            self.last_hover_node = None
            self.current_ax = ax
            self.current_canvas = canvas

            # Create annotation for hover tooltips (hidden by default)
            self.annot = ax.annotate("", xy=(0,0), xytext=(15,15),
                                    textcoords="offset points",
                                    bbox=dict(boxstyle="round,pad=0.8", fc="#1e1e1e", ec="#4da6ff", lw=2, alpha=0.95),
                                    color='white',
                                    fontsize=10,
                                    fontweight='bold',
                                    visible=False,
                                    zorder=1000)

            # Mouse event handlers
            def on_hover(event):
                """Show tooltip when hovering over nodes (ONLY when mouse stops moving)"""
                # Don't show tooltip while dragging
                if self.is_dragging:
                    return

                if event.inaxes == ax and event.xdata and event.ydata:
                    # Find closest node to mouse position
                    min_dist = float('inf')
                    closest_node = None

                    for node_cik, (x, y) in pos.items():
                        dist = ((x - event.xdata)**2 + (y - event.ydata)**2)**0.5
                        degree = node_degrees.get(node_cik, 0)
                        size = 1000 + (degree / max_degree) * 1500 if node_cik in source_ciks else 400 + (degree / max_degree) * 600
                        radius = (size / 1000) ** 0.5 * 0.05

                        if dist < radius and dist < min_dist:
                            min_dist = dist
                            closest_node = node_cik

                    # Only update tooltip if we're hovering over a different node
                    if closest_node and closest_node != self.last_hover_node:
                        self.last_hover_node = closest_node
                        node_name = self.graph_cik_to_name.get(closest_node, 'Unknown')
                        degree = node_degrees.get(closest_node, 0)
                        node_type = "Source Company" if closest_node in source_ciks else "Target Company"

                        self.annot.xy = pos[closest_node]
                        text = f"{node_name}\n{node_type}\n{degree} connections"
                        self.annot.set_text(text)
                        self.annot.set_visible(True)
                        canvas.draw_idle()
                    elif not closest_node and self.last_hover_node:
                        # Mouse left all nodes
                        self.last_hover_node = None
                        self.annot.set_visible(False)
                        canvas.draw_idle()

            def on_click(event):
                """Handle click events on nodes and edges (ONLY on button press, not movement)"""
                # Don't trigger click if we were dragging
                if self.is_dragging:
                    return

                if event.inaxes == ax and event.xdata and event.ydata:
                    # Find closest node to click position
                    min_dist = float('inf')
                    clicked_node = None

                    for node_cik, (x, y) in pos.items():
                        dist = ((x - event.xdata)**2 + (y - event.ydata)**2)**0.5
                        degree = node_degrees.get(node_cik, 0)
                        size = 1000 + (degree / max_degree) * 1500 if node_cik in source_ciks else 400 + (degree / max_degree) * 600
                        radius = (size / 1000) ** 0.5 * 0.05

                        if dist < radius and dist < min_dist:
                            min_dist = dist
                            clicked_node = node_cik

                    if clicked_node:
                        node_data = self.graph_nodes_data.get(clicked_node, {})
                        self._show_node_details(node_data, node_degrees.get(clicked_node, 0))
                        return

                    # Check for edge click
                    for edge_artist in edge_artists:
                        try:
                            if hasattr(edge_artist, 'contains') and edge_artist.contains(event)[0]:
                                source, target = edge_artist.edge_data
                                edge_data = self.graph_edges_data.get((source, target), {})
                                self._show_edge_details(edge_data)
                                return
                        except:
                            pass

            def on_press(event):
                """Start dragging a node (ONLY with middle or right button, NOT left click)"""
                # Only allow drag with right button (button 3) to avoid conflicting with click
                if event.button != 3:  # Not right-click
                    return

                if event.inaxes == ax and event.xdata and event.ydata:
                    # Find closest node
                    for node_cik, (x, y) in pos.items():
                        dist = ((x - event.xdata)**2 + (y - event.ydata)**2)**0.5
                        degree = node_degrees.get(node_cik, 0)
                        size = 1000 + (degree / max_degree) * 1500 if node_cik in source_ciks else 400 + (degree / max_degree) * 600
                        radius = (size / 1000) ** 0.5 * 0.05

                        if dist < radius:
                            self.selected_node = node_cik
                            x0, y0 = pos[node_cik]
                            self.drag_offset = (x0 - event.xdata, y0 - event.ydata)
                            self.is_dragging = False  # Not dragging yet, just pressed
                            break

            def on_motion(event):
                """Drag node if selected (ONLY after mouse moved significantly)"""
                if self.selected_node is not None and event.inaxes == ax and event.xdata and event.ydata:
                    # Mark as dragging (so click won't trigger)
                    self.is_dragging = True

                    # Hide tooltip while dragging
                    if self.annot.get_visible():
                        self.annot.set_visible(False)

                    # Update node position
                    x = event.xdata + self.drag_offset[0]
                    y = event.ydata + self.drag_offset[1]
                    pos[self.selected_node] = (x, y)

                    # Redraw graph
                    ax.clear()
                    ax.set_facecolor('#2d2d2d')
                    ax.axis('off')

                    # Redraw edges
                    for edge in G.edges(data=True):
                        source, target, data = edge
                        rel_type = data.get('relationship', 'unknown')
                        color = edge_colors_map.get(rel_type, '#6c757d')
                        confidence = data.get('confidence', 0)

                        nx.draw_networkx_edges(
                            G, pos,
                            edgelist=[(source, target)],
                            edge_color=color,
                            alpha=min(0.3 + confidence * 0.7, 1.0),
                            width=1.0 + confidence * 2.0,
                            arrows=True,
                            arrowsize=10,
                            ax=ax,
                            arrowstyle='->'
                        )

                    # Redraw source nodes
                    for idx, node in enumerate(source_nodes):
                        color = source_colors[idx % len(source_colors)]
                        degree = node_degrees.get(node, 0)
                        size = 1000 + (degree / max_degree) * 1500

                        nx.draw_networkx_nodes(
                            G, pos,
                            nodelist=[node],
                            node_color=color,
                            node_size=size,
                            alpha=0.9,
                            ax=ax
                        )

                    # Redraw target nodes
                    if target_only_nodes:
                        target_sizes = [400 + (node_degrees.get(n, 0) / max_degree) * 600 for n in target_only_nodes]
                        nx.draw_networkx_nodes(
                            G, pos,
                            nodelist=target_only_nodes,
                            node_color='#7fb3d5',
                            node_size=target_sizes,
                            alpha=0.7,
                            ax=ax
                        )

                    # Redraw labels
                    labels_redraw = {node: self.graph_cik_to_name.get(node, 'Unknown') for node in G.nodes()}
                    nx.draw_networkx_labels(
                        G, pos,
                        labels=labels_redraw,
                        font_size=8,
                        font_weight='bold',
                        font_color='white',
                        ax=ax
                    )

                    ax.set_title(f'Relationship Network - {stats.get("total_companies", 0)} Companies, '
                               f'{stats.get("total_relationships", 0)} Relationships',
                               fontsize=14, fontweight='bold', color='white', pad=20)

                    canvas.draw_idle()

            def on_release(event):
                """Stop dragging"""
                self.selected_node = None
                self.drag_offset = None
                # Small delay before allowing clicks again after drag
                if self.is_dragging:
                    self.is_dragging = False

            # Connect events
            canvas.mpl_connect('motion_notify_event', on_hover)
            canvas.mpl_connect('button_press_event', on_click)
            canvas.mpl_connect('button_press_event', on_press)
            canvas.mpl_connect('motion_notify_event', on_motion)
            canvas.mpl_connect('button_release_event', on_release)

            # Enable matplotlib navigation toolbar (zoom, pan, save)
            from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT
            toolbar = NavigationToolbar2QT(canvas, None)
            toolbar.setStyleSheet("background-color: #2d2d2d; color: white;")

            # Add toolbar and canvas to layout
            self.graph_layout.addWidget(toolbar)
            self.graph_layout.addWidget(canvas)

            logger.info(f"Rendered interactive network graph with {len(nodes)} nodes and {len(edges)} edges")

        except ImportError as e:
            logger.warning(f"Missing required library for graph visualization: {e}")
            error_label = QLabel(
                "⚠️ Graph visualization requires networkx and matplotlib\n\n"
                "Install with: pip install networkx matplotlib"
            )
            error_label.setAlignment(Qt.AlignCenter)
            error_label.setStyleSheet("color: #ffc107; padding: 40px; font-size: 12px;")
            self.graph_layout.addWidget(error_label)
        except Exception as e:
            logger.exception(f"Error rendering graph: {e}")
            raise

    def _show_node_details(self, node_data, connections_count):
        """Show detailed information about a clicked node"""
        cik = node_data.get('cik', 'Unknown')

        # Get display name (prefer ticker, then name)
        ticker = node_data.get('ticker', 'N/A')
        name = node_data.get('name', 'Unknown')
        display_name = ticker if ticker != 'N/A' else name

        # Get all relationships involving this node
        incoming = []
        outgoing = []

        for (source, target), edge_data in self.graph_edges_data.items():
            if target == cik:
                # Get source company name
                source_name = self.graph_cik_to_name.get(source, 'Unknown')
                edge_data_copy = edge_data.copy()
                edge_data_copy['source_name'] = source_name
                incoming.append(edge_data_copy)
            elif source == cik:
                # Get target company name
                target_name = self.graph_cik_to_name.get(target, 'Unknown')
                edge_data_copy = edge_data.copy()
                edge_data_copy['target_name'] = target_name
                outgoing.append(edge_data_copy)

        details = f"""
<h2 style='color: #4da6ff;'>{display_name}</h2>
<p><b>Full Name:</b> {name}</p>
<p><b>CIK:</b> {cik}</p>
<p><b>Total Connections:</b> {connections_count}</p>

<h3 style='color: #28a745;'>Outgoing Relationships ({len(outgoing)}):</h3>
"""

        if outgoing:
            for i, edge in enumerate(outgoing[:10], 1):
                target_name = edge.get('target_name', 'Unknown')
                rel_type = edge.get('type', 'unknown')
                confidence = edge.get('confidence', 0)
                details += f"<p>{i}. <b>{target_name}</b> - {rel_type.title()} (conf: {confidence:.2f})</p>"
            if len(outgoing) > 10:
                details += f"<p><i>... and {len(outgoing) - 10} more</i></p>"
        else:
            details += "<p><i>No outgoing relationships</i></p>"

        details += f"<h3 style='color: #ffc107;'>Incoming Relationships ({len(incoming)}):</h3>"

        if incoming:
            for i, edge in enumerate(incoming[:10], 1):
                source_name = edge.get('source_name', 'Unknown')
                rel_type = edge.get('type', 'unknown')
                confidence = edge.get('confidence', 0)
                details += f"<p>{i}. <b>{source_name}</b> - {rel_type.title()} (conf: {confidence:.2f})</p>"
            if len(incoming) > 10:
                details += f"<p><i>... and {len(incoming) - 10} more</i></p>"
        else:
            details += "<p><i>No incoming relationships</i></p>"

        # Create dialog
        dialog = QMessageBox(self)
        dialog.setWindowTitle(f"Node Details - {display_name}")
        dialog.setTextFormat(Qt.RichText)
        dialog.setText(details)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.setStyleSheet("""
            QMessageBox {
                background-color: #1e1e1e;
                color: white;
            }
            QLabel {
                color: white;
                min-width: 500px;
                max-width: 700px;
            }
            QPushButton {
                background-color: #0d6efd;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
        """)
        dialog.exec()

    def _show_edge_details(self, edge_data):
        """Show detailed information about a clicked edge"""
        source_cik = edge_data.get('source', '')
        target_cik = edge_data.get('target', '')

        # Get display names
        source_name = self.graph_cik_to_name.get(source_cik, 'Unknown')
        target_name = self.graph_cik_to_name.get(target_cik, 'Unknown')

        rel_type = edge_data.get('type', 'unknown')
        confidence = edge_data.get('confidence', 0)
        context = edge_data.get('context', 'No context available')

        details = f"""
<h2 style='color: #4da6ff;'>Relationship Details</h2>

<p><b>Source:</b> {source_name}</p>
<p><b>Target:</b> {target_name}</p>
<p><b>Relationship Type:</b> <span style='color: #28a745;'>{rel_type.title()}</span></p>
<p><b>Confidence Score:</b> {confidence:.2f}</p>

<h3>Context:</h3>
<p style='background-color: #2d2d2d; padding: 10px; border-radius: 5px;'>
{context[:500]}{'...' if len(context) > 500 else ''}
</p>
"""

        # Create dialog
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Relationship Details")
        dialog.setTextFormat(Qt.RichText)
        dialog.setText(details)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.setStyleSheet("""
            QMessageBox {
                background-color: #1e1e1e;
                color: white;
            }
            QLabel {
                color: white;
                min-width: 500px;
                max-width: 700px;
            }
            QPushButton {
                background-color: #0d6efd;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
        """)
        dialog.exec()

    def show_relationship_details(self, edge):
        """Show detailed information about a relationship"""
        details = f"""
Relationship Details:

Source: {edge.get('source', 'Unknown')}
Target: {edge.get('target', 'Unknown')}
Type: {edge.get('type', 'unknown')}
Confidence: {edge.get('confidence', 0):.2f}

Context:
{edge.get('context', 'No context available')}
"""
        QMessageBox.information(self, "Relationship Details", details)

    def export_graph_data(self):
        """Export graph data to JSON file"""
        if not self.graph_data:
            QMessageBox.warning(self, "No Data", "Please build the graph first before exporting.")
            return

        try:
            from PySide6.QtWidgets import QFileDialog

            filename, _ = QFileDialog.getSaveFileName(
                self, "Export Graph Data", "", "JSON Files (*.json)"
            )

            if filename:
                with open(filename, 'w') as f:
                    json.dump(self.graph_data, f, indent=2)

                QMessageBox.information(self, "Success", f"Graph data exported to:\n{filename}")

        except Exception as e:
            logger.exception(f"Error exporting graph: {e}")
            QMessageBox.critical(self, "Error", f"Failed to export graph data:\n{e}")

    def reprocess_all_profiles(self):
        """Reprocess all profiles to extract relationships"""
        try:
            # Check if profiles need reprocessing
            profiles = list(self.mongo.db['Fundamental_Data_Pipeline'].find(
                {},
                {'cik': 1, 'company_info': 1, 'relationships': 1}
            ).limit(1000))

            if not profiles:
                QMessageBox.information(self, "No Profiles", "No profiles found in database.")
                return

            # Count profiles without relationships
            need_reprocessing = []
            for profile in profiles:
                if 'relationships' not in profile or not profile.get('relationships'):
                    ticker = profile.get('company_info', {}).get('ticker', 'N/A')
                    cik = profile.get('cik', '')
                    company_info = profile.get('company_info', {})
                    need_reprocessing.append((ticker, cik, company_info))

            if not need_reprocessing:
                QMessageBox.information(self, "Already Complete",
                    "All profiles already have relationships extracted!")
                return

            # Confirm with user
            msg = (f"Found {len(need_reprocessing)} profile(s) without relationships.\n\n"
                   f"This will extract relationships from EXISTING profile data.\n"
                   f"✓ No SEC API calls (uses data already in database)\n"
                   f"✓ Fast extraction (~5 seconds per profile)\n\n"
                   f"Profiles to process:\n")

            for ticker, cik, _ in need_reprocessing[:5]:
                msg += f"  • {ticker} (CIK: {cik})\n"
            if len(need_reprocessing) > 5:
                msg += f"  ... and {len(need_reprocessing) - 5} more\n"

            msg += f"\nEstimated time: ~{len(need_reprocessing) * 5} seconds\n\nProceed?"

            reply = QMessageBox.question(self, "Reprocess Profiles", msg,
                                        QMessageBox.Yes | QMessageBox.No)

            if reply != QMessageBox.Yes:
                return

            # Create progress dialog
            self.reprocess_progress = QProgressDialog("Starting extraction...", "Cancel", 0, len(need_reprocessing), self)
            self.reprocess_progress.setWindowTitle("Extracting Relationships from Existing Profiles")
            self.reprocess_progress.setWindowModality(Qt.WindowModal)
            self.reprocess_progress.setMinimumDuration(0)
            self.reprocess_progress.setValue(0)

            # Create and start background thread (uses existing profile data, no SEC fetch!)
            self.reprocess_thread = ReprocessThread(self.mongo, need_reprocessing)

            # Connect signals
            def on_progress(value, message):
                self.reprocess_progress.setValue(value)
                self.reprocess_progress.setLabelText(message)

            def on_finished(success_count, failed_count):
                self.reprocess_progress.close()

                total = len(need_reprocessing)
                msg = (f"Reprocessing complete!\n\n"
                       f"Success: {success_count}\n"
                       f"Failed: {failed_count}\n"
                       f"Total: {total}\n\n"
                       f"Click 'Update Graph' to see the relationships!")

                QMessageBox.information(self, "Reprocessing Complete", msg)

                # Auto-refresh graph
                if success_count > 0:
                    self.build_graph()

            def on_error(error_msg):
                self.reprocess_progress.close()
                QMessageBox.critical(self, "Error", f"Reprocessing failed:\n{error_msg}")

            def on_cancel():
                if self.reprocess_thread and self.reprocess_thread.isRunning():
                    self.reprocess_thread.cancel()
                    self.reprocess_progress.setLabelText("Cancelling...")

            self.reprocess_thread.progress.connect(on_progress)
            self.reprocess_thread.finished.connect(on_finished)
            self.reprocess_thread.error.connect(on_error)
            self.reprocess_progress.canceled.connect(on_cancel)

            # Start thread
            self.reprocess_thread.start()

        except Exception as e:
            logger.exception(f"Error reprocessing profiles: {e}")
            QMessageBox.critical(self, "Error", f"Failed to reprocess profiles:\n{e}")

