"""
Financial Relationships Extractor

Extracts customer/supplier concentration, revenue by segment,
and material contract information from 10-K/10-Q filings.
"""
import logging
import re
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class FinancialRelationshipsExtractor:
    """
    Extract financial relationship data from 10-K/10-Q:
    - Customer concentration (top customers by revenue %)
    - Supplier concentration
    - Revenue by business segment
    - Material contracts
    """

    def __init__(self):
        """Initialize the financial relationships extractor"""
        logger.info("FinancialRelationshipsExtractor initialized")

    def extract_customers(self, filing_text: str, confidence_threshold: float = 0.75) -> List[Dict[str, Any]]:
        """
        Extract major customer information from 10-K.
        Usually found in Item 1 (Business) or Item 1A (Risk Factors).

        Args:
            filing_text: Full filing text
            confidence_threshold: Minimum confidence to include

        Returns:
            List of customer dicts with name and revenue %
        """
        customers = []

        # Patterns for customer mentions with revenue percentages
        customer_patterns = [
            # Pattern 1: "Customer X represented approximately Y% of revenue"
            r'([A-Z][a-zA-Z\s&\'.,\-]+?)\s+(?:represent|comprised|account[ed]?|constitut[ed]?|approximate)\s+(?:approximately\s+)?(\d+(?:\.\d+)?)\s*%\s+of\s+(?:revenue|revenues|sales|net\s+sales)',

            # Pattern 2: "Major customers include: X, Y, Z"
            r'(?:major|primary|largest|key)\s+(?:customers?|clients?)[:\s]+([A-Z][a-zA-Z\s&\'.,\-]+?)(?:\s+represent[s]?|$)',

            # Pattern 3: "Customer X, which represents Y% of revenue"
            r'(?:customer|client)\s+([A-Z][a-zA-Z\s&\'.,\-]+?)[,\s]+which\s+(?:represent|account[s]?)\s+(?:approximately\s+)?(\d+(?:\.\d+)?)\s*%',
        ]

        for pattern in customer_patterns:
            try:
                for match in re.finditer(pattern, filing_text, re.IGNORECASE | re.DOTALL):
                    customer_name = match.group(1).strip()[:100]

                    # Skip generic names
                    if customer_name.lower() in {'us government', 'government', 'other'}:
                        continue

                    # Try to extract percentage
                    pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', match.group(0))
                    if pct_match:
                        revenue_pct = float(pct_match.group(1))

                        customers.append({
                            'name': customer_name,
                            'revenue_percent': revenue_pct,
                            'confidence': confidence_threshold
                        })
            except Exception as e:
                logger.warning(f"Error matching customer pattern: {e}")

        # Deduplicate and sort by revenue percentage
        seen_names = set()
        unique_customers = []
        for customer in sorted(customers, key=lambda x: x['revenue_percent'], reverse=True):
            name_lower = customer['name'].lower()
            if name_lower not in seen_names:
                unique_customers.append(customer)
                seen_names.add(name_lower)

        logger.debug(f"Extracted {len(unique_customers)} customers")
        return unique_customers[:15]  # Top 15 customers

    def extract_suppliers(self, filing_text: str) -> List[Dict[str, Any]]:
        """
        Extract supplier information from 10-K.
        Usually found in Item 1 (Business) or Item 1A (Risk Factors).

        Args:
            filing_text: Full filing text

        Returns:
            List of supplier dicts
        """
        suppliers = []

        supplier_patterns = [
            # Pattern 1: "Our suppliers include..."
            r'(?:suppliers?|providers?|vendors?|manufacturers?)\s+(?:include|comprise)[s]?[:\s]+([^.]+?)(?:\.|;)',

            # Pattern 2: "Primary suppliers: X, Y, Z"
            r'(?:primary|key|major|main)\s+supplier[s]?[:\s]+([^.]+?)(?:\.|;)',

            # Pattern 3: "Depend on X for Y% of supplies"
            r'(?:depend|rely|source)\s+on\s+([A-Z][a-zA-Z\s&\'.,\-]+?)\s+for\s+(?:approximately\s+)?(\d+(?:\.\d+)?)\s*%',

            # Pattern 4: "Single source supplier: X"
            r'(?:single[- ]source|sole\s+source)\s+supplier[:\s]+([A-Z][a-zA-Z\s&\'.,\-]+?)(?:\s|,|\.)',
        ]

        for pattern in supplier_patterns:
            try:
                for match in re.finditer(pattern, filing_text, re.IGNORECASE | re.DOTALL):
                    supplier_text = match.group(1).strip()

                    # Handle comma-separated supplier lists
                    supplier_names = [s.strip() for s in re.split(r'[,;]', supplier_text)]

                    for supplier_name in supplier_names:
                        if len(supplier_name) > 3 and supplier_name.lower() not in {'and', 'or', 'others'}:
                            # Try to extract percentage if present
                            pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', supplier_name)
                            supply_pct = float(pct_match.group(1)) if pct_match else None

                            suppliers.append({
                                'name': supplier_name[:100],
                                'supply_percent': supply_pct,
                                'confidence': 0.75
                            })
            except Exception as e:
                logger.warning(f"Error matching supplier pattern: {e}")

        # Deduplicate
        seen_names = set()
        unique_suppliers = []
        for supplier in suppliers:
            name_lower = supplier['name'].lower()
            if name_lower not in seen_names:
                unique_suppliers.append(supplier)
                seen_names.add(name_lower)

        logger.debug(f"Extracted {len(unique_suppliers)} suppliers")
        return unique_suppliers[:15]

    def extract_segments(self, filing_text: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse revenue by segment from 10-K Item 8 (Financial Statements).

        Args:
            filing_text: Full filing text

        Returns:
            Dict mapping segment names to revenue data
        """
        segments = {}

        # Look for segment disclosure section
        segment_pattern = r'(?:Business|Reportable)\s+Segments?[:\s]+(.*?)(?:Item\s+\d+|Consolidated|Geographic|$)'

        try:
            match = re.search(segment_pattern, filing_text, re.IGNORECASE | re.DOTALL)
            if match:
                segment_text = match.group(1)[:5000]  # Limit to first 5000 chars

                # Extract segment entries with revenue
                # Pattern: "Segment Name ... Revenue Amount"
                segment_entries = re.finditer(
                    r'([A-Z][a-zA-Z\s&\-]+?)\s+(\d{1,3}(?:,\d{3})*)\s+(?:million|thousand|$)',
                    segment_text,
                    re.IGNORECASE
                )

                for entry in segment_entries:
                    segment_name = entry.group(1).strip()
                    revenue_str = entry.group(2).replace(',', '')

                    if len(segment_name) > 3 and segment_name.lower() not in {'total', 'other'}:
                        segments[segment_name] = {
                            'revenue': revenue_str,
                            'currency': 'millions' if 'million' in entry.group(0).lower() else 'thousands'
                        }
        except Exception as e:
            logger.warning(f"Error extracting segments: {e}")

        logger.debug(f"Extracted {len(segments)} business segments")
        return segments

    def extract_material_contracts(self, filing_text: str) -> List[Dict[str, Any]]:
        """
        Extract material contracts and agreements.

        Args:
            filing_text: Full filing text

        Returns:
            List of material contracts
        """
        contracts = []

        contract_patterns = [
            r'(?:material|significant)\s+(?:contract|agreement|arrangement)[:\s]+([^.]+?)(?:\.|;)',
            r'(?:contract|agreement|arrangement)\s+(?:with|among)\s+([^.]+?)\s+(?:for|relating to|regarding)',
        ]

        try:
            for pattern in contract_patterns:
                for match in re.finditer(pattern, filing_text, re.IGNORECASE | re.DOTALL):
                    contract_text = match.group(1).strip()[:200]

                    contracts.append({
                        'description': contract_text,
                        'confidence': 0.7
                    })
        except Exception as e:
            logger.warning(f"Error extracting contracts: {e}")

        logger.debug(f"Extracted {len(contracts)} material contracts")
        return contracts[:10]  # Top 10 contracts

    def extract_supply_chain_risks(self, filing_text: str) -> Dict[str, Any]:
        """
        Extract supply chain risk disclosures.

        Args:
            filing_text: Full filing text

        Returns:
            Supply chain risk analysis
        """
        risks = {
            'supply_concentration': [],
            'dependency_risks': [],
            'geographic_risks': [],
            'single_source_suppliers': []
        }

        # Look for supply chain concentration mentions
        concentration_pattern = r'(?:significant|material|concentrated)\s+(?:supply|supplier|source).*?([A-Z][a-zA-Z\s]+?)\s+(?:represent|supply|provide)'

        try:
            for match in re.finditer(concentration_pattern, filing_text, re.IGNORECASE | re.DOTALL):
                risks['supply_concentration'].append(match.group(1).strip())

            # Single source suppliers
            single_pattern = r'(?:single[- ]source|sole[- ]source)\s+(?:supplier|source)[:\s]+([A-Z][a-zA-Z\s&]+?)(?:\s|,|\.)'
            for match in re.finditer(single_pattern, filing_text, re.IGNORECASE):
                risks['single_source_suppliers'].append(match.group(1).strip())

            # Geographic concentration
            geo_pattern = r'(?:substantially|primarily)\s+(?:all|sourced)\s+(?:from|in)\s+([A-Za-z\s,]+?)(?:\.|;)'
            for match in re.finditer(geo_pattern, filing_text, re.IGNORECASE):
                risks['geographic_risks'].append(match.group(1).strip())

        except Exception as e:
            logger.warning(f"Error extracting supply chain risks: {e}")

        return risks


class CustomerConcentrationAnalyzer:
    """Analyze customer concentration metrics"""

    @staticmethod
    def calculate_herfindahl_index(customers: List[Dict]) -> float:
        """
        Calculate Herfindahl-Hirschman Index (HHI) for customer concentration.

        HHI = sum of (market_share%)^2
        - HHI < 1500: Low concentration
        - HHI 1500-2500: Moderate concentration
        - HHI > 2500: High concentration

        Args:
            customers: List of customer dicts with 'revenue_percent'

        Returns:
            HHI score
        """
        if not customers:
            return 0.0

        hhi = sum((customer.get('revenue_percent', 0) ** 2) for customer in customers)
        return min(hhi, 10000.0)  # Cap at 100^2

    @staticmethod
    def calculate_concentration_ratio(customers: List[Dict], n: int = 5) -> float:
        """
        Calculate n-firm concentration ratio (typically top 5 customers).

        CR(n) = sum of top n customer shares

        Args:
            customers: List of customer dicts
            n: Number of top firms to sum

        Returns:
            Concentration ratio 0-100
        """
        sorted_customers = sorted(customers, key=lambda x: x.get('revenue_percent', 0), reverse=True)
        return sum(c.get('revenue_percent', 0) for c in sorted_customers[:n])

