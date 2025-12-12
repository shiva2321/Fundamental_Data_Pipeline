"""
Relationship Data Integration Module

Integrates all relationship extractors into the unified profile aggregator.
Extracts relationship data during profile generation and stores in MongoDB.
"""
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime

# ✅ NEW: Use NER-based extractor instead of fuzzy matching against 10k companies
from src.extractors.ner_company_extractor import FastCompanyExtractor
from src.extractors.relationship_context_extractor import (
    RelationshipContextExtractor,
    RelationshipStrengthCalculator
)
from src.extractors.financial_relationships_extractor import (
    FinancialRelationshipsExtractor,
    CustomerConcentrationAnalyzer
)
from src.extractors.key_person_interlock_extractor import KeyPersonInterlockExtractor

logger = logging.getLogger(__name__)


class RelationshipDataIntegrator:
    """
    Main integration module that orchestrates relationship data extraction
    during profile generation.

    Workflow:
    1. Extract company mentions from filing text using NER/patterns
    2. Extract relationship context between mentioned companies
    3. Extract financial relationship data (customers, suppliers)
    4. Store all relationships in MongoDB for graph generation

    ✅ OPTIMIZATION: No longer requires loading 10k+ SEC companies.
    Uses NER-based extraction to find ALL companies (public, private, foreign).
    """

    def __init__(self, mongo_wrapper, ticker_fetcher=None, all_companies: List[Dict] = None):
        """
        Initialize integrator.

        Args:
            mongo_wrapper: MongoDB wrapper for storing data
            ticker_fetcher: Ticker fetcher for company info (optional, kept for compatibility)
            all_companies: List of all companies in database (optional, no longer needed)
        """
        self.mongo = mongo_wrapper
        self.ticker_fetcher = ticker_fetcher  # Keep for compatibility but not used
        self.all_companies = all_companies or []  # Keep for compatibility but not used

        # ✅ NEW: Initialize NER-based extractor (no company database needed)
        self.company_mention_extractor = FastCompanyExtractor()
        self.relationship_context_extractor = RelationshipContextExtractor()
        self.financial_extractor = FinancialRelationshipsExtractor()
        self.key_person_extractor = KeyPersonInterlockExtractor()
        self.parsers_available = True  # ✅ Flag to track if extraction is possible

        logger.info("RelationshipDataIntegrator initialized")

    def extract_relationships_for_profile(
        self,
        profile: Dict[str, Any],
        filings_text: Dict[str, str],
        options: Optional[Dict] = None,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Extract all relationship data for a company profile.

        Args:
            profile: Company profile dict
            filings_text: Dict mapping form_type -> text (from 10-K, 8-K, etc.)
            options: Optional extraction options
            progress_callback: Optional progress logging callback

        Returns:
            Dict with extracted relationship data
        """
        def log(level: str, msg: str):
            logger.info(msg) if level == 'info' else logger.debug(msg)
            if progress_callback:
                try:
                    progress_callback(level, f"Relationship extraction: {msg}")
                except Exception:
                    pass

        opts = options or {}
        cik = profile['cik']
        company_info = profile.get('company_info', {})
        company_name = company_info.get('name') or company_info.get('title') or 'Unknown Company'

        log('info', f"Extracting relationships for {company_name}")

        relationships_data = {
            'company_mentions': {},
            'relationships': [],
            'financial_relationships': {
                'customers': [],
                'suppliers': [],
                'segments': {},
                'supply_chain_risks': {}
            },
            'key_person_interlocks': [],
            'extraction_metadata': {
                'extracted_at': datetime.utcnow().isoformat(),
                'extraction_methods': []
            }
        }

        if not self.parsers_available:
            result['error'] = 'Content parsers not available'
            return result

        # === PARALLEL EXTRACTION: Process all relationship extraction tasks concurrently ===
        # Instead of sequential processing (mentions → context → financial → documents),
        # run extraction tasks in parallel to maintain full data while improving speed

        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        logger.info(f"Starting parallel relationship extraction for {company_name}")
        log('info', 'Extracting relationships in parallel...')

        # ✅ Send progress callback to UI
        if progress_callback:
            progress_callback('info', "Extracting company mentions and relationships...")

        # Thread-safe lock for updating shared result
        result_lock = threading.Lock()

        with ThreadPoolExecutor(max_workers=4) as executor:
            # Submit all relationship extraction tasks in parallel
            futures = {}

            # Task 1: Extract company mentions
            futures[executor.submit(
                self._task_extract_mentions, filings_text
            )] = 'mentions'

            # Task 2: Extract relationship context (if mentions available)
            futures[executor.submit(
                self._task_extract_context, filings_text, cik
            )] = 'context'

            # Task 3: Extract financial relationships
            futures[executor.submit(
                self._task_extract_financial, filings_text
            )] = 'financial'

            # Task 4: Prepare for document creation
            futures[executor.submit(
                lambda: {'cik': cik, 'name': company_name, 'generated_at': profile.get('generated_at', datetime.utcnow().isoformat())}
            )] = 'metadata'

            # Collect results as they complete
            completed_tasks = 0
            total_tasks = len(futures)

            for future in as_completed(futures, timeout=120):  # 2 minute total timeout
                completed_tasks += 1
                task_name = futures[future]
                try:
                    task_result = future.result()

                    with result_lock:
                        if task_name == 'mentions':
                            if task_result:
                                relationships_data['company_mentions'] = task_result.get('mentions', {})
                                relationships_data['extraction_metadata']['extraction_methods'].append('company_mention')
                                log('info', f"✓ Extracted {len(task_result.get('mentions', {}))} company mentions")
                                # ✅ Progress callback
                                if progress_callback:
                                    progress_pct = int(50 + (completed_tasks / total_tasks) * 15)
                                    progress_callback('info', f"Progress: Relationship extraction ({progress_pct}%)")

                        elif task_name == 'context':
                            if task_result:
                                relationships_data['relationships'] = task_result.get('relationships', [])
                                relationships_data['extraction_metadata']['extraction_methods'].append('relationship_context')
                                log('info', f"✓ Extracted {len(task_result.get('relationships', []))} relationships")
                                # ✅ Progress callback
                                if progress_callback:
                                    progress_pct = int(50 + (completed_tasks / total_tasks) * 15)
                                    progress_callback('info', f"Progress: Relationship extraction ({progress_pct}%)")

                        elif task_name == 'financial':
                            if task_result:
                                relationships_data['financial_relationships'] = task_result.get('financial_rels', {})
                                relationships_data['extraction_metadata']['extraction_methods'].append('financial_relationships')
                                log('info', f"✓ Extracted financial relationships: "
                                    f"{len(task_result.get('financial_rels', {}).get('customers', []))} customers, "
                                    f"{len(task_result.get('financial_rels', {}).get('suppliers', []))} suppliers")
                                # ✅ Progress callback
                                if progress_callback:
                                    progress_pct = int(50 + (completed_tasks / total_tasks) * 15)
                                    progress_callback('info', f"Progress: Relationship extraction ({progress_pct}%)")

                        elif task_name == 'metadata':
                            metadata = task_result
                            # Store for document creation
                            relationships_data['_metadata'] = metadata

                except Exception as e:
                    logger.error(f"Error in {task_name} extraction: {e}")
                    log('error', f"✗ {task_name} extraction failed: {str(e)[:50]}")

        # 4. CREATE RELATIONSHIP DOCUMENTS for MongoDB (sequential after parallel extraction)
        log('info', 'Creating relationship documents for storage')
        try:
            if '_metadata' in relationships_data:
                metadata = relationships_data.pop('_metadata')
                relationship_docs = self._create_relationship_documents(
                    metadata['cik'],
                    metadata['name'],
                    relationships_data,
                    metadata['generated_at']
                )
                relationships_data['relationship_documents'] = relationship_docs
                log('info', f"Created {len(relationship_docs)} relationship documents")
        except Exception as e:
            logger.error(f"Error creating relationship documents: {e}")

        log('info', 'Relationship extraction complete')
        return relationships_data

    def _task_extract_mentions(self, filings_text: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract company mentions using NER/pattern matching (parallel task)"""
        try:
            text_to_analyze = self._compile_text_for_analysis(filings_text)

            # ✅ NEW: Extract companies using NER-based approach
            # Returns: [{'name', 'count', 'confidence', 'contexts', 'relationship_type'}, ...]
            company_mentions = self.company_mention_extractor.extract_companies(
                text_to_analyze,
                min_mentions=2,  # Only companies mentioned 2+ times
                max_companies=100  # Limit to top 100 companies
            )

            logger.info(f"✓ Extracted {len(company_mentions)} company mentions using NER")

            # Convert to dict format for storage
            mentions_dict = {}
            for idx, mention in enumerate(company_mentions):
                # Use company name as key (no CIK needed for non-SEC companies)
                company_key = mention['name'].lower().replace(' ', '_')
                mentions_dict[company_key] = {
                    'target_name': mention['name'],
                    'mention_count': mention['count'],
                    'confidence': mention['confidence'],
                    'relationship_type': mention.get('relationship_type'),
                    'sample_context': mention.get('contexts', [])[0] if mention.get('contexts') else None
                }

            return {'mentions': mentions_dict}
        except Exception as e:
            logger.error(f"Error in mention extraction: {e}")
            return None

    def _task_extract_context(self, filings_text: Dict[str, str], cik: str) -> Optional[Dict[str, Any]]:
        """Extract relationship context (parallel task)"""
        try:
            text_to_analyze = self._compile_text_for_analysis(filings_text)

            # ✅ NEW: Extract companies using NER
            company_mentions = self.company_mention_extractor.extract_companies(
                text_to_analyze,
                min_mentions=2
            )

            if company_mentions and text_to_analyze:
                # Convert NER format to format expected by relationship_context_extractor
                # Old format: [(cik, name, confidence), ...]
                # New format: Use company names as unique IDs (since CIK not available)
                mention_tuples = [
                    (mention['name'].lower().replace(' ', '_'), mention['name'], mention['confidence'])
                    for mention in company_mentions
                ]

                relationships = self.relationship_context_extractor.extract_relationships(
                    text_to_analyze,
                    mention_tuples,
                    cik
                )

                # Note: target_name and source_name are now included in the relationships
                # target_cik may be a name-based ID (like "netflix_inc") instead of numeric CIK

                return {'relationships': relationships}
            return {'relationships': []}
        except Exception as e:
            logger.error(f"Error in context extraction: {e}")
            return None

    def _task_extract_financial(self, filings_text: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract financial relationships (parallel task)"""
        try:
            k_text = filings_text.get('10-K', '') or filings_text.get('10-Q', '')

            if k_text:
                customers = self.financial_extractor.extract_customers(k_text)
                suppliers = self.financial_extractor.extract_suppliers(k_text)
                segments = self.financial_extractor.extract_segments(k_text)
                risks = self.financial_extractor.extract_supply_chain_risks(k_text)

                financial_rels = {
                    'customers': customers,
                    'suppliers': suppliers,
                    'segments': segments,
                    'supply_chain_risks': risks
                }

                # Calculate concentration metrics if we have customers
                if customers:
                    hhi = CustomerConcentrationAnalyzer.calculate_herfindahl_index(customers)
                    cr5 = CustomerConcentrationAnalyzer.calculate_concentration_ratio(customers, 5)
                    financial_rels['customer_concentration'] = {
                        'herfindahl_index': hhi,
                        'hhi_level': self._classify_hhi(hhi),
                        'top_5_concentration': cr5
                    }

                return {'financial_rels': financial_rels}
            return {'financial_rels': {
                'customers': [],
                'suppliers': [],
                'segments': {},
                'supply_chain_risks': {}
            }}
        except Exception as e:
            logger.error(f"Error in financial extraction: {e}")
            return None
        return relationships_data

    def store_relationships_in_profile(
        self,
        profile: Dict[str, Any],
        relationships_data: Dict[str, Any],
        mongo_collection: str = 'Fundamental_Data_Pipeline'
    ) -> None:
        """
        Store extracted relationships in company profile and organized collection.

        Args:
            profile: Company profile to update
            relationships_data: Extracted relationship data
            mongo_collection: MongoDB collection for profiles
        """
        try:
            # 1. Add relationships to profile
            profile['relationships'] = {
                'company_mentions': relationships_data.get('company_mentions', {}),
                'relationships': relationships_data.get('relationships', []),
                'financial_relationships': relationships_data.get('financial_relationships', {}),
                'extraction_metadata': relationships_data.get('extraction_metadata', {})
            }

            # 2. Store relationships organized by ticker for efficient graph building
            # Instead of individual relationship documents, create ONE document per ticker
            # with ALL relationships organized by type

            cik = profile['cik']
            ticker = profile.get('company_info', {}).get('ticker', 'Unknown')
            company_name = profile.get('company_info', {}).get('name') or profile.get('company_info', {}).get('title', 'Unknown')

            relationships_list = relationships_data.get('relationships', [])

            if relationships_list:
                # Organize relationships by type for efficient querying
                relationships_by_type = {
                    'supplier': [],
                    'customer': [],
                    'competitor': [],
                    'partner': [],
                    'investor': [],
                    'related_company': []
                }

                # Organize relationships by target company
                relationships_by_target = {}

                for rel in relationships_list:
                    rel_type = rel.get('relationship_type', 'related_company')
                    target_cik = rel.get('target_cik')
                    target_name = rel.get('target_name', 'Unknown')

                    # Add to type-based organization (use singular keys to match relationship_type values)
                    if rel_type not in relationships_by_type:
                        relationships_by_type[rel_type] = []

                    relationships_by_type[rel_type].append({
                        'target_cik': target_cik,
                        'target_name': target_name,
                        'confidence': rel.get('confidence_score', 0),
                        'context': rel.get('context', '')[:500],  # Limit context size
                        'first_mentioned': rel.get('first_mentioned', ''),
                        'extraction_method': rel.get('extraction_method', 'unknown')
                    })

                    # Add to target-based organization (for interconnection)
                    if target_cik:
                        if target_cik not in relationships_by_target:
                            relationships_by_target[target_cik] = {
                                'target_name': target_name,
                                'relationships': []
                            }

                        relationships_by_target[target_cik]['relationships'].append({
                            'type': rel_type,
                            'confidence': rel.get('confidence_score', 0),
                            'context': rel.get('context', '')[:200]
                        })

                # Create comprehensive ticker document
                ticker_relationships_doc = {
                    'cik': cik,
                    'ticker': ticker,
                    'company_name': company_name,
                    'total_relationships': len(relationships_list),

                    # Organized by type (for filtering in graph)
                    'by_type': relationships_by_type,

                    # Organized by target (for interconnection)
                    'by_target': relationships_by_target,

                    # Statistics for quick filtering
                    'statistics': {
                        'supplier_count': len(relationships_by_type.get('supplier', [])),
                        'customer_count': len(relationships_by_type.get('customer', [])),
                        'competitor_count': len(relationships_by_type.get('competitor', [])),
                        'partner_count': len(relationships_by_type.get('partner', [])),
                        'investor_count': len(relationships_by_type.get('investor', [])),
                        'avg_confidence': sum(r.get('confidence_score', 0) for r in relationships_list) / len(relationships_list) if relationships_list else 0
                    },

                    # Metadata
                    'extraction_metadata': relationships_data.get('extraction_metadata', {}),
                    'last_updated': datetime.utcnow().isoformat()
                }

                # Upsert as single document per ticker
                self.mongo.upsert_one(
                    'company_relationships',
                    {'cik': cik},
                    ticker_relationships_doc
                )

                logger.info(f"Stored relationships for {ticker}: {len(relationships_list)} total "
                          f"(supplier: {len(relationships_by_type.get('supplier', []))}, "
                          f"customer: {len(relationships_by_type.get('customer', []))}, "
                          f"competitor: {len(relationships_by_type.get('competitor', []))})")

            # 3. Store financial relationships if available
            financial_rels = relationships_data.get('financial_relationships', {})
            if financial_rels.get('customers') or financial_rels.get('suppliers'):
                self.mongo.upsert_one(
                    'financial_relationships',
                    {'cik': cik},
                    {
                        'cik': cik,
                        'ticker': ticker,
                        'company_name': company_name,
                        'customers': financial_rels.get('customers', []),
                        'suppliers': financial_rels.get('suppliers', []),
                        'segments': financial_rels.get('segments', {}),
                        'customer_concentration': financial_rels.get('customer_concentration', {}),
                        'supply_chain_risks': financial_rels.get('supply_chain_risks', {}),
                        'last_updated': datetime.utcnow().isoformat()
                    }
                )

        except Exception as e:
            logger.error(f"Error storing relationships: {e}")

    def _compile_text_for_analysis(self, filings_text: Dict[str, str]) -> str:
        """Compile relevant filing text for analysis"""
        # Priority: 10-K MD&A > 10-Q MD&A > 10-K Risk > 10-Q Risk
        text_sections = []

        for form_type in ['10-K', '10-Q']:
            if form_type in filings_text:
                text_sections.append(filings_text[form_type])

        for form_type in ['8-K']:
            if form_type in filings_text:
                text_sections.append(filings_text[form_type][:10000])  # Limit 8-K to 10K chars

        return '\n\n'.join(text_sections)

    def _create_relationship_documents(
        self,
        source_cik: str,
        source_name: str,
        relationships_data: Dict,
        generation_date: str
    ) -> List[Dict]:
        """
        Convert extracted relationships to MongoDB documents.

        Args:
            source_cik: Source company CIK
            source_name: Source company name
            relationships_data: Extracted relationships
            generation_date: Profile generation date

        Returns:
            List of relationship documents ready for MongoDB
        """
        documents = []

        # Convert relationship extractions to documents
        for rel in relationships_data.get('relationships', []):
            doc = {
                'source_cik': rel['source_cik'],
                'source_name': source_name,
                'target_cik': rel['target_cik'],
                'target_name': rel.get('target_name', 'Unknown'),
                'relationship_type': rel.get('relationship_type', 'unknown'),
                'confidence_score': rel.get('confidence_score', 0.0),
                'extraction_method': 'nlp_text_analysis',
                'context': rel.get('context', ''),
                'first_mentioned': generation_date,
                'last_mentioned': generation_date,
                'mention_count': 1,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            documents.append(doc)

        # Add financial relationship documents
        for customer in relationships_data.get('financial_relationships', {}).get('customers', []):
            doc = {
                'source_cik': source_cik,
                'source_name': source_name,
                'target_name': customer.get('name'),
                'relationship_type': 'customer',
                'confidence_score': customer.get('confidence', 0.75),
                'revenue_percent': customer.get('revenue_percent'),
                'extraction_method': '10k_text_analysis',
                'first_mentioned': generation_date,
                'last_mentioned': generation_date,
                'created_at': datetime.utcnow().isoformat()
            }
            documents.append(doc)

        for supplier in relationships_data.get('financial_relationships', {}).get('suppliers', []):
            doc = {
                'source_cik': source_cik,
                'source_name': source_name,
                'target_name': supplier.get('name'),
                'relationship_type': 'supplier',
                'confidence_score': supplier.get('confidence', 0.75),
                'supply_percent': supplier.get('supply_percent'),
                'extraction_method': '10k_text_analysis',
                'first_mentioned': generation_date,
                'last_mentioned': generation_date,
                'created_at': datetime.utcnow().isoformat()
            }
            documents.append(doc)

        return documents

    @staticmethod
    def _classify_hhi(hhi: float) -> str:
        """Classify HHI concentration level"""
        if hhi < 1500:
            return 'LOW'
        elif hhi < 2500:
            return 'MODERATE'
        else:
            return 'HIGH'

    def refresh_key_person_interlocks(self, all_profiles: List[Dict]) -> None:
        """
        Build global key person index and identify interlocks.
        Should be called after processing all profiles.

        Args:
            all_profiles: All company profiles
        """
        try:
            log_msg = "Building key person interlock index..."
            logger.info(log_msg)

            self.key_person_extractor.build_person_index(all_profiles)

            # Find and store interlocks
            interlocks = self.key_person_extractor.find_interlocks()
            conflicts = self.key_person_extractor.find_conflict_of_interest()

            # Store in MongoDB
            if interlocks:
                self.mongo.insert_many_dedup(
                    'key_person_interlocks',
                    interlocks,
                    'person_name'
                )

            if conflicts:
                self.mongo.insert_many_dedup(
                    'conflicts_of_interest',
                    conflicts,
                    'person_name'
                )

            stats = self.key_person_extractor.get_statistics()
            logger.info(f"Key person interlock analysis: {stats}")

        except Exception as e:
            logger.error(f"Error analyzing key person interlocks: {e}")
