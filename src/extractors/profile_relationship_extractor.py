"""
Relationship Extractor for Existing Profiles

Extracts relationships from profiles already in MongoDB without refetching from SEC.
Uses filing metadata and extracted text already stored in profiles.
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ProfileRelationshipExtractor:
    """
    Extract relationships from existing profile data without SEC API calls.
    """

    def __init__(self, mongo_wrapper):
        """
        Initialize extractor.

        Args:
            mongo_wrapper: MongoWrapper instance
        """
        self.mongo = mongo_wrapper
        self.relationship_integrator = None

    def extract_from_profile(
        self,
        profile: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Extract relationships from an existing profile.

        Args:
            profile: Complete profile dict from database
            progress_callback: Optional callback for progress updates

        Returns:
            Relationships data dict
        """
        def log(msg):
            logger.info(msg)
            if progress_callback:
                try:
                    progress_callback('info', msg)
                except:
                    pass

        cik = profile.get('cik')
        company_info = profile.get('company_info', {})
        ticker = company_info.get('ticker', 'N/A')
        company_name = company_info.get('name') or company_info.get('title', 'Unknown')

        log(f"Extracting relationships for {ticker} from existing profile data...")

        # Initialize relationship integrator if needed
        if not self.relationship_integrator:
            from src.extractors.relationship_integrator import RelationshipDataIntegrator
            from src.clients.company_ticker_fetcher import CompanyTickerFetcher

            ticker_fetcher = CompanyTickerFetcher()
            all_companies = ticker_fetcher.get_all_companies()

            self.relationship_integrator = RelationshipDataIntegrator(
                mongo_wrapper=self.mongo,
                ticker_fetcher=ticker_fetcher,
                all_companies=all_companies
            )

        # Extract text from existing profile sections
        filings_text = self._extract_text_from_profile(profile)

        if not filings_text:
            log(f"No extractable text found in profile for {ticker}")
            return {
                'company_mentions': {},
                'relationships': [],
                'financial_relationships': {
                    'customers': [],
                    'suppliers': [],
                    'segments': {},
                    'supply_chain_risks': {}
                },
                'extraction_metadata': {
                    'extracted_at': datetime.utcnow().isoformat(),
                    'extraction_methods': ['profile_reextraction'],
                    'source': 'existing_profile_data'
                }
            }

        log(f"Extracted {len(filings_text)} text sections from profile")

        # Extract relationships using the integrator
        try:
            relationships_data = self.relationship_integrator.extract_relationships_for_profile(
                profile=profile,
                filings_text=filings_text,
                options={},
                progress_callback=progress_callback
            )

            rel_count = len(relationships_data.get('relationships', []))

            # If we got very few relationships, try enhanced extraction
            if rel_count < 3:
                log(f"Standard extraction found only {rel_count} relationships, trying enhanced extraction...")

                from src.extractors.enhanced_relationship_extractor import EnhancedRelationshipExtractor
                from src.clients.company_ticker_fetcher import CompanyTickerFetcher

                ticker_fetcher = CompanyTickerFetcher()
                all_companies = ticker_fetcher.get_all_companies()

                enhanced_extractor = EnhancedRelationshipExtractor(all_companies)
                enhanced_rels = enhanced_extractor.extract_relationships_from_limited_data(profile)

                # Merge with existing relationships
                existing_rels = relationships_data.get('relationships', [])

                # Add enhanced relationships
                for erel in enhanced_rels:
                    # Check if not already in existing
                    exists = any(
                        r.get('target_cik') == erel.get('target_cik') and
                        r.get('relationship_type') == erel.get('relationship_type')
                        for r in existing_rels
                    )
                    if not exists:
                        existing_rels.append(erel)

                relationships_data['relationships'] = existing_rels
                rel_count = len(existing_rels)
                log(f"Enhanced extraction added relationships, total now: {rel_count}")

            # Add metadata
            relationships_data['extraction_metadata'] = {
                'extracted_at': datetime.utcnow().isoformat(),
                'extraction_methods': ['profile_reextraction', 'enhanced_extraction'],
                'source': 'existing_profile_data',
                'text_sections_used': list(filings_text.keys())
            }

            log(f"Extracted {rel_count} relationships for {ticker}")

            return relationships_data

        except Exception as e:
            logger.exception(f"Error extracting relationships from profile: {e}")
            log(f"Error: {str(e)}")
            return {
                'company_mentions': {},
                'relationships': [],
                'financial_relationships': {
                    'customers': [],
                    'suppliers': [],
                    'segments': {},
                    'supply_chain_risks': {}
                },
                'extraction_metadata': {
                    'extracted_at': datetime.utcnow().isoformat(),
                    'extraction_methods': ['profile_reextraction'],
                    'source': 'existing_profile_data',
                    'error': str(e)
                }
            }

    def _extract_text_from_profile(self, profile: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract text from various profile sections for relationship analysis.

        Args:
            profile: Profile dict

        Returns:
            Dict mapping section_name -> text
        """
        filings_text = {}

        # Try to get text from various profile sections

        # 1. Material Events (8-K summaries)
        material_events = profile.get('material_events', {})
        if material_events:
            events = material_events.get('recent_events', [])
            if events:
                event_texts = []
                for event in events[:20]:  # Limit to recent 20
                    if isinstance(event, dict):
                        event_type = event.get('event_type', '')
                        description = event.get('description', '')
                        if description:
                            event_texts.append(f"{event_type}: {description}")

                if event_texts:
                    filings_text['8-K'] = '\n'.join(event_texts)

        # 2. Governance data (proxy statements)
        governance = profile.get('governance', {})
        if governance:
            # Executive compensation discussions often mention other companies
            exec_comp = governance.get('executive_compensation', {})
            if exec_comp and isinstance(exec_comp, dict):
                comp_text = str(exec_comp)
                if len(comp_text) > 100:
                    filings_text['DEF14A'] = comp_text[:50000]  # Limit size

        # 3. AI Analysis (often contains company mentions)
        ai_analysis = profile.get('ai_analysis', {})
        if ai_analysis:
            consensus = ai_analysis.get('consensus_analysis', {})
            if consensus:
                # Combine various analysis fields
                analysis_texts = []
                for key in ['investment_thesis', 'competitive_position', 'risk_factors',
                           'growth_drivers', 'financial_health_summary']:
                    text = consensus.get(key, '')
                    if text and text != 'N/A':
                        analysis_texts.append(text)

                if analysis_texts:
                    filings_text['AI_ANALYSIS'] = '\n\n'.join(analysis_texts)

        # 4. Try to construct synthetic 10-K text from financial data
        # This is a fallback - use financial ratios and trends text
        summary = profile.get('summary', {})
        if summary and isinstance(summary, dict):
            summary_text = str(summary)
            if len(summary_text) > 200:
                filings_text['SUMMARY'] = summary_text[:20000]

        return filings_text

    def store_relationships_in_profile(
        self,
        profile: Dict[str, Any],
        relationships_data: Dict[str, Any],
        collection_name: str = 'Fundamental_Data_Pipeline'
    ):
        """
        Store extracted relationships back into the profile.

        Args:
            profile: Profile dict
            relationships_data: Extracted relationships
            collection_name: MongoDB collection name
        """
        cik = profile.get('cik')

        # Update profile
        profile['relationships'] = relationships_data
        profile['last_updated'] = datetime.utcnow().isoformat()

        # Store in MongoDB
        try:
            self.mongo.replace_one(
                collection_name,
                {'cik': cik},
                profile
            )
            logger.info(f"Stored relationships for CIK {cik}")
        except Exception as e:
            logger.error(f"Failed to store relationships: {e}")

