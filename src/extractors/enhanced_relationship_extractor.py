"""
Enhanced Relationship Extraction for Limited Data

Improves relationship extraction when full filing text is not available.
Uses alternative data sources and more aggressive matching.
"""
import re
import logging
from typing import Dict, List, Any, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class EnhancedRelationshipExtractor:
    """
    Enhanced extractor that works with limited data.

    Strategies:
    1. Extract from AI analysis summaries
    2. Use financial data (customer concentration, segments)
    3. Parse governance data for board interlocks
    4. Use aggressive fuzzy matching on any available text
    """

    def __init__(self, all_companies: List[Dict]):
        """
        Initialize with company list.

        Args:
            all_companies: List of all known companies
        """
        self.all_companies = all_companies

        # Build indices for fast lookup
        self.name_to_cik = {}
        self.ticker_to_cik = {}

        for company in all_companies:
            cik = company['cik']
            name = (company.get('name') or company.get('title', '')).lower()
            ticker = company.get('ticker', '').upper()

            if name:
                self.name_to_cik[name] = cik
            if ticker:
                self.ticker_to_cik[ticker] = cik

    def extract_relationships_from_limited_data(
        self,
        profile: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract relationships using all available data sources.

        Args:
            profile: Company profile

        Returns:
            List of relationship dicts
        """
        relationships = []
        source_cik = profile.get('cik')
        source_name = profile.get('company_info', {}).get('name') or profile.get('company_info', {}).get('title', 'Unknown')

        # Strategy 1: Extract from AI analysis
        ai_rels = self._extract_from_ai_analysis(profile, source_cik, source_name)
        relationships.extend(ai_rels)

        # Strategy 2: Extract from financial data (customer/supplier mentions)
        fin_rels = self._extract_from_financial_data(profile, source_cik, source_name)
        relationships.extend(fin_rels)

        # Strategy 3: Extract from governance (board interlocks)
        gov_rels = self._extract_from_governance(profile, source_cik, source_name)
        relationships.extend(gov_rels)

        # Strategy 4: Extract from any text fields
        text_rels = self._extract_from_text_fields(profile, source_cik, source_name)
        relationships.extend(text_rels)

        # Deduplicate
        relationships = self._deduplicate_relationships(relationships)

        logger.info(f"Extracted {len(relationships)} relationships using enhanced strategies")

        return relationships

    def _extract_from_ai_analysis(
        self,
        profile: Dict,
        source_cik: str,
        source_name: str
    ) -> List[Dict]:
        """Extract from AI analysis text"""
        relationships = []

        ai_analysis = profile.get('ai_analysis', {})
        if not ai_analysis:
            return relationships

        consensus = ai_analysis.get('consensus_analysis', {})
        if not consensus:
            return relationships

        # Check competitive position section
        competitive_text = consensus.get('competitive_position', '')
        if competitive_text and competitive_text != 'N/A':
            # Look for competitor mentions
            competitors = self._find_company_mentions(competitive_text)
            for comp_cik, comp_name, confidence in competitors:
                relationships.append({
                    'source_cik': source_cik,
                    'source_name': source_name,
                    'target_cik': comp_cik,
                    'target_name': comp_name,
                    'relationship_type': 'competitor',
                    'confidence_score': confidence * 0.8,  # Lower confidence for AI-derived
                    'context': competitive_text[:200],
                    'extraction_method': 'ai_analysis',
                    'first_mentioned': profile.get('generated_at', '')
                })

        # Check investment thesis for partnerships/suppliers
        thesis = consensus.get('investment_thesis', '')
        if thesis and thesis != 'N/A':
            mentions = self._find_company_mentions(thesis)
            for comp_cik, comp_name, confidence in mentions:
                # Determine relationship type from context
                rel_type = self._infer_relationship_type(thesis, comp_name)

                relationships.append({
                    'source_cik': source_cik,
                    'source_name': source_name,
                    'target_cik': comp_cik,
                    'target_name': comp_name,
                    'relationship_type': rel_type,
                    'confidence_score': confidence * 0.7,
                    'context': thesis[:200],
                    'extraction_method': 'ai_analysis',
                    'first_mentioned': profile.get('generated_at', '')
                })

        return relationships

    def _extract_from_financial_data(
        self,
        profile: Dict,
        source_cik: str,
        source_name: str
    ) -> List[Dict]:
        """Extract from financial segments/customers"""
        relationships = []

        # Check for segment data (often includes customer names)
        financial_data = profile.get('financial_data', {})
        if not financial_data:
            return relationships

        # Some profiles have segment revenue by customer
        # This would be in special fields or ratios

        return relationships

    def _extract_from_governance(
        self,
        profile: Dict,
        source_cik: str,
        source_name: str
    ) -> List[Dict]:
        """Extract from governance data (board members)"""
        relationships = []

        governance = profile.get('governance', {})
        if not governance:
            return relationships

        # Board composition might mention other companies where directors serve
        board_comp = governance.get('board_composition', {})

        # This would require parsing board member affiliations
        # For now, we skip this as it's complex

        return relationships

    def _extract_from_text_fields(
        self,
        profile: Dict,
        source_cik: str,
        source_name: str
    ) -> List[Dict]:
        """Extract from any available text fields"""
        relationships = []

        # Collect all text from profile
        all_text = []

        # Material events
        material_events = profile.get('material_events', {})
        if material_events:
            events = material_events.get('recent_events', [])
            for event in events[:10]:
                if isinstance(event, dict):
                    desc = event.get('description', '')
                    if desc:
                        all_text.append(desc)

        # Combine and search
        combined_text = ' '.join(all_text)
        if len(combined_text) > 100:
            mentions = self._find_company_mentions(combined_text)
            for comp_cik, comp_name, confidence in mentions:
                rel_type = self._infer_relationship_type(combined_text, comp_name)

                relationships.append({
                    'source_cik': source_cik,
                    'source_name': source_name,
                    'target_cik': comp_cik,
                    'target_name': comp_name,
                    'relationship_type': rel_type,
                    'confidence_score': confidence * 0.6,
                    'context': combined_text[:200],
                    'extraction_method': 'text_field_scan',
                    'first_mentioned': profile.get('generated_at', '')
                })

        return relationships

    def _find_company_mentions(self, text: str) -> List[Tuple[str, str, float]]:
        """
        Find company mentions in text.

        Returns:
            List of (cik, name, confidence) tuples
        """
        mentions = []
        text_lower = text.lower()

        # 1. Exact ticker matches (highest confidence)
        for ticker, cik in self.ticker_to_cik.items():
            # Look for ticker in uppercase (standalone or with $)
            pattern = r'\b' + re.escape(ticker) + r'\b|\$' + re.escape(ticker) + r'\b'
            if re.search(pattern, text, re.IGNORECASE):
                # Get company name
                company = next((c for c in self.all_companies if c['cik'] == cik), None)
                if company:
                    name = company.get('name') or company.get('title', ticker)
                    mentions.append((cik, name, 0.95))

        # 2. Company name matches (moderate confidence)
        for name, cik in list(self.name_to_cik.items())[:1000]:  # Limit to top 1000 to avoid slowdown
            if len(name) < 4:  # Skip very short names
                continue

            # Check if name appears in text
            if name in text_lower:
                # Get full company info
                company = next((c for c in self.all_companies if c['cik'] == cik), None)
                if company:
                    full_name = company.get('name') or company.get('title', name)
                    mentions.append((cik, full_name.title(), 0.85))

        # Deduplicate by CIK (keep highest confidence)
        mentions_dict = {}
        for cik, name, conf in mentions:
            if cik not in mentions_dict or conf > mentions_dict[cik][2]:
                mentions_dict[cik] = (cik, name, conf)

        return list(mentions_dict.values())

    def _infer_relationship_type(self, text: str, company_name: str) -> str:
        """
        Infer relationship type from context.

        Args:
            text: Context text
            company_name: Name of mentioned company

        Returns:
            Relationship type
        """
        text_lower = text.lower()
        context = text_lower[max(0, text_lower.find(company_name.lower()) - 100):
                            text_lower.find(company_name.lower()) + 100]

        # Supplier indicators
        supplier_keywords = ['supplier', 'supplies', 'vendor', 'provides', 'sourced from', 'manufactured by']
        if any(kw in context for kw in supplier_keywords):
            return 'supplier'

        # Customer indicators
        customer_keywords = ['customer', 'client', 'sold to', 'revenue from', 'sales to']
        if any(kw in context for kw in customer_keywords):
            return 'customer'

        # Competitor indicators
        competitor_keywords = ['competitor', 'competes', 'competitive', 'rival', 'alternative to']
        if any(kw in context for kw in competitor_keywords):
            return 'competitor'

        # Partner indicators
        partner_keywords = ['partner', 'partnership', 'collaboration', 'joint venture', 'alliance']
        if any(kw in context for kw in partner_keywords):
            return 'partner'

        # Default to generic relationship
        return 'related_company'

    def _deduplicate_relationships(self, relationships: List[Dict]) -> List[Dict]:
        """Remove duplicate relationships, keeping highest confidence"""
        unique = {}

        for rel in relationships:
            key = (rel['source_cik'], rel['target_cik'], rel['relationship_type'])

            if key not in unique or rel['confidence_score'] > unique[key]['confidence_score']:
                unique[key] = rel

        return list(unique.values())

