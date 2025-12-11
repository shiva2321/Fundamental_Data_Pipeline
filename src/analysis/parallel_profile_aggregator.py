"""
Parallel Profile Aggregator - Optimized multi-threaded version

Breaks down profile aggregation into independent tasks that run in parallel:
1. Filing metadata extraction
2. Material events parsing (8-K)
3. Corporate governance parsing (DEF 14A)
4. Insider trading parsing (Form 4)
5. Institutional ownership parsing (SC 13D/G)
6. Key persons extraction
7. Financial time series extraction
8. Relationship extraction

Each task runs in a separate thread and updates the profile when complete.
"""
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import time

logger = logging.getLogger("parallel_profile_aggregator")


class ParallelProfileAggregator:
    """
    Multi-threaded profile aggregator that processes different aspects of a company profile in parallel.
    """

    def __init__(self, mongo, sec_client=None, max_workers=8):
        """
        Initialize parallel aggregator.

        Args:
            mongo: MongoDB wrapper
            sec_client: SEC API client
            max_workers: Maximum number of parallel threads (default: 8)
        """
        self.mongo = mongo

        # Import here to avoid circular dependencies
        from src.clients.sec_edgar_api_client import SECEdgarClient
        self.sec_client = sec_client or SECEdgarClient()

        self.max_workers = max_workers
        self.profile_lock = threading.Lock()
        self._cancelled = False  # Cancellation flag

        # Use global thread pool manager for better resource utilization
        try:
            from src.utils.thread_pool_manager import get_thread_pool_manager
            self.use_global_pool = True
            logger.info("Using global thread pool manager for optimal performance")
        except ImportError:
            self.use_global_pool = False
            logger.info("Global thread pool not available, using local executor")

    def cancel(self):
        """Cancel current processing"""
        self._cancelled = True
        logger.info("Parallel processing cancellation requested")

    def is_cancelled(self):
        """Check if processing is cancelled"""
        return self._cancelled

    def aggregate_profile_parallel(
        self,
        cik: str,
        company_info: Optional[Dict[str, Any]] = None,
        output_collection: Optional[str] = None,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Aggregate profile using parallel task execution.

        Returns:
            Complete profile dict with all sections populated
        """
        def log(level: str, msg: str):
            logger.info(msg) if level == 'info' else logger.debug(msg)
            if progress_callback:
                try:
                    progress_callback(level, msg)
                except Exception:
                    pass

        opts = options or {}
        lookback_years = opts.get('lookback_years', 20)
        ticker = company_info.get('ticker', 'Unknown') if company_info else 'Unknown'

        # Reset cancellation flag for new processing
        self._cancelled = False

        # Check cancellation before starting
        if self._cancelled:
            logger.info(f"Processing cancelled before starting for {ticker}")
            return None

        log('info', f"🚀 Starting PARALLEL aggregation for {ticker} (CIK: {cik})")
        start_time = time.time()

        # Initialize base profile
        profile = {
            "cik": cik,
            "generated_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "company_info": company_info or {},
            "_processing_status": {
                "tasks_total": 0,
                "tasks_completed": 0,
                "tasks_failed": 0
            }
        }

        # Step 1: Fetch filings (must be done first)
        log('info', f"📂 Fetching filings for {ticker}...")
        filings = self._fetch_filings_with_cache(cik, ticker, lookback_years, progress_callback)

        if not filings:
            log('info', f"No filings found for {ticker}")
            return None

        log('info', f"✓ Fetched {len(filings)} filings for {ticker}")

        # Step 2: Define parallel tasks
        tasks = [
            ('filing_metadata', lambda: self._task_filing_metadata(filings)),
            ('material_events', lambda: self._task_material_events(filings)),
            ('corporate_governance', lambda: self._task_corporate_governance(filings)),
            ('insider_trading', lambda: self._task_insider_trading(filings)),
            ('institutional_ownership', lambda: self._task_institutional_ownership(filings)),
            ('key_persons', lambda: self._task_key_persons(filings, cik)),  # FIXED: pass cik
            ('financial_time_series', lambda: self._task_financial_timeseries(filings, cik)),
        ]

        # Add relationship extraction if enabled
        if opts.get('extract_relationships', True):
            tasks.append(('relationships', lambda: self._task_relationships(profile, filings, opts, progress_callback)))

        profile['_processing_status']['tasks_total'] = len(tasks)

        # Step 3: Execute tasks in parallel
        log('info', f"⚡ Executing {len(tasks)} tasks in parallel...")
        
        # Use global thread pool if available, otherwise local executor
        if self.use_global_pool:
            # Use global pool manager for better resource sharing
            from src.utils.thread_pool_manager import get_thread_pool_manager
            pool_manager = get_thread_pool_manager()
            
            # Submit all tasks to global pool
            task_funcs = [task_func for task_name, task_func in tasks]
            task_names = [task_name for task_name, task_func in tasks]
            
            def task_callback(ticker_id, task_name, result):
                """Callback when task completes"""
                with self.profile_lock:
                    profile[task_name] = result
                    profile['_processing_status']['tasks_completed'] += 1
                
                log('info', f"✓ Completed: {task_name}")
                
                # Update progress
                completed = profile['_processing_status']['tasks_completed']
                total = profile['_processing_status']['tasks_total']
                if progress_callback:
                    progress_callback('info', f"⚡ Progress: {completed}/{total} tasks completed")
            
            # Submit to global pool
            pool_manager.submit_ticker_tasks(ticker, task_funcs, task_names, task_callback)
            
            # Wait for completion (non-blocking for other tickers)
            results = pool_manager.wait_for_ticker(ticker, timeout=600)
            
            # Check if cancelled
            if self._cancelled:
                pool_manager.cancel_ticker(ticker)
                return None
            
        else:
            # Fallback to local ThreadPoolExecutor
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_task = {
                    executor.submit(task_func): task_name 
                    for task_name, task_func in tasks
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_task):
                    # Check cancellation
                    if self._cancelled:
                        logger.info("Cancellation detected - stopping task collection")
                        executor.shutdown(wait=False, cancel_futures=True)
                        return None
                    
                    task_name = future_to_task[future]
                    
                    try:
                        result = future.result(timeout=300)  # 5 minute timeout per task
                        
                        # Thread-safe update of profile
                        with self.profile_lock:
                            profile[task_name] = result
                            profile['_processing_status']['tasks_completed'] += 1
                        
                        log('info', f"✓ Completed: {task_name}")
                        
                        # Update progress
                        completed = profile['_processing_status']['tasks_completed']
                        total = profile['_processing_status']['tasks_total']
                        if progress_callback:
                            progress_callback('info', f"⚡ Progress: {completed}/{total} tasks completed")
                        
                    except Exception as e:
                        logger.error(f"✗ Task {task_name} failed: {e}")
                        
                        with self.profile_lock:
                            profile[task_name] = self._get_empty_result(task_name)
                            profile['_processing_status']['tasks_failed'] += 1
                        
                        log('error', f"✗ Failed: {task_name} - {str(e)[:100]}")

        # Step 4: Post-processing (sequential tasks that depend on multiple results)
        log('info', "🔧 Running post-processing...")

        try:
            # Calculate derived metrics
            self._post_process_financial_metrics(profile)

            # Run AI analysis if enabled
            if opts.get('ai_enabled', False):
                profile['ai_analysis'] = self._task_ai_analysis(profile, progress_callback)
            else:
                profile['ai_analysis'] = None

        except Exception as e:
            logger.error(f"Post-processing error: {e}")

        # Step 5: Store profile
        elapsed = time.time() - start_time
        log('info', f"✅ Profile aggregation complete in {elapsed:.1f}s")

        if output_collection:
            try:
                self.mongo.upsert_one(output_collection, {"cik": cik}, profile)
                log('info', f"💾 Stored profile for {ticker}")
            except Exception as e:
                log('error', f"Failed to store profile: {e}")

        return profile

    # ========================================================================
    # TASK IMPLEMENTATIONS (Each runs in parallel)
    # ========================================================================

    def _task_filing_metadata(self, filings: List[Dict]) -> Dict[str, Any]:
        """Extract filing metadata"""
        form_counts = Counter(f.get("form") for f in filings if "form" in f)
        year_counts = Counter(
            f.get("filingDate", "")[:4]
            for f in filings
            if "filingDate" in f and len(f.get("filingDate", "")) >= 4
        )
        dates = [f["filingDate"] for f in filings if "filingDate" in f]

        return {
            "total_filings": len(filings),
            "form_counts": dict(form_counts),
            "filings_per_year": dict(year_counts),
            "most_recent_filing": max(dates) if dates else None,
            "oldest_filing": min(dates) if dates else None,
            "filing_frequency": len(filings) / max(len(year_counts), 1)
        }

    def _task_material_events(self, filings: List[Dict]) -> Dict[str, Any]:
        """Parse 8-K filings for material events"""
        try:
            from src.parsers.form_8k_parser import Form8KParser
            parser = Form8KParser()
            return parser.parse_8k_filings(filings)
        except Exception as e:
            logger.error(f"Material events parsing failed: {e}")
            return {
                'total_8k_count': 0,
                'recent_count': 0,
                'events': [],
                'risk_flags': [],
                'positive_catalysts': []
            }

    def _task_corporate_governance(self, filings: List[Dict]) -> Dict[str, Any]:
        """Parse DEF 14A filings for governance data"""
        try:
            from src.parsers.def14a_parser import DEF14AParser
            parser = DEF14AParser()
            return parser.parse_def14a_filings(filings)
        except Exception as e:
            logger.error(f"Corporate governance parsing failed: {e}")
            return {
                'total_proxy_count': 0,
                'governance_score': None,
                'insights': []
            }

    def _task_insider_trading(self, filings: List[Dict]) -> Dict[str, Any]:
        """Parse Form 4 filings for insider trading"""
        try:
            from src.parsers.form4_parser import Form4Parser
            parser = Form4Parser()
            return parser.parse_form4_filings(filings)
        except Exception as e:
            logger.error(f"Insider trading parsing failed: {e}")
            return {
                'total_form4_count': 0,
                'sentiment': 'No data',
                'insights': []
            }

    def _task_institutional_ownership(self, filings: List[Dict]) -> Dict[str, Any]:
        """Parse SC 13D/G filings for institutional ownership"""
        try:
            from src.parsers.sc13_parser import SC13Parser
            parser = SC13Parser()
            return parser.parse_sc13_filings(filings)
        except Exception as e:
            logger.error(f"Institutional ownership parsing failed: {e}")
            return {
                'total_sc13_count': 0,
                'activist_count': 0,
                'insights': []
            }

    def _task_key_persons(self, filings: List[Dict], cik: str) -> Dict[str, Any]:
        """Extract key persons data"""
        try:
            from src.parsers.key_persons_parser import KeyPersonsParser
            parser = KeyPersonsParser()
            return parser.parse_key_persons(filings, cik)  # FIXED: pass CIK
        except Exception as e:
            logger.error(f"Key persons extraction failed: {e}")
            return {
                'executives': [],
                'board_members': [],
                'insider_holdings': [],
                'holding_companies': [],
                'summary': {}
            }

    def _task_financial_timeseries(self, filings: List[Dict], cik: str) -> Dict[str, Dict[str, float]]:
        """Extract financial time series data"""
        try:
            # Import here to avoid circular dependency
            from .unified_profile_aggregator import UnifiedSECProfileAggregator
            temp_aggregator = UnifiedSECProfileAggregator(self.mongo, self.sec_client)
            return temp_aggregator._extract_financial_time_series(filings, cik)  # FIXED: correct method name
        except Exception as e:
            logger.error(f"Financial timeseries extraction failed: {e}")
            return {}

    def _task_relationships(
        self,
        profile: Dict,
        filings: List[Dict],
        opts: Dict,
        progress_callback
    ) -> Dict[str, Any]:
        """Extract relationship data from comprehensive filing text"""
        try:
            from src.extractors.relationship_integrator import RelationshipDataIntegrator
            from src.clients.company_ticker_fetcher import CompanyTickerFetcher
            from datetime import datetime, timedelta

            # Initialize components needed for relationship extraction
            ticker_fetcher = CompanyTickerFetcher()
            all_companies = ticker_fetcher.get_all_companies()

            integrator = RelationshipDataIntegrator(
                mongo_wrapper=self.mongo,  # FIXED: use mongo_wrapper parameter name
                ticker_fetcher=ticker_fetcher,
                all_companies=all_companies
            )

            # Compile filing text from multiple sources
            filings_text = {}

            # COMPREHENSIVE EXTRACTION: Process filings from last 5 years minimum
            lookback_years = opts.get('lookback_years', 20)
            min_years = max(5, lookback_years)  # At least 5 years

            cutoff_date = datetime.utcnow() - timedelta(days=min_years * 365)

            # Filter 10-K/Q filings within timeframe
            ten_k_filings = [
                f for f in filings
                if f.get('form') in ['10-K', '10-Q'] and
                   'filingDate' in f and
                   datetime.fromisoformat(f['filingDate']) >= cutoff_date
            ]

            logger.info(f"Processing {len(ten_k_filings)} 10-K/Q filings from last {min_years} years for relationships")

            if ten_k_filings:
                # Fetch actual text from SEC (not just cached)
                from src.parsers.filing_content_parser import SECFilingContentFetcher
                fetcher = SECFilingContentFetcher()

                combined_text = []
                processed_count = 0
                max_filings_to_process = min(15, len(ten_k_filings))  # Process up to 15 filings

                for idx, filing in enumerate(ten_k_filings[:max_filings_to_process], 1):
                    try:
                        # Try cached text first
                        if 'text' in filing and filing['text']:
                            combined_text.append(filing['text'][:200000])  # 200KB per filing
                            processed_count += 1
                        elif 'accessionNumber' in filing and profile.get('cik'):
                            # Fetch from SEC if not cached
                            logger.info(f"Fetching filing {idx}/{max_filings_to_process}: {filing['form']} {filing.get('filingDate', 'N/A')}")

                            content = fetcher.fetch_filing_content(
                                profile['cik'],
                                filing['accessionNumber']
                            )

                            if content:
                                combined_text.append(content[:200000])  # 200KB per filing
                                processed_count += 1
                                logger.info(f"✓ Fetched {len(content)} chars from {filing['form']}")
                    except Exception as e:
                        logger.debug(f"Could not fetch filing {idx}: {e}")
                        continue

                if combined_text:
                    filings_text['10-K'] = ' '.join(combined_text)[:2000000]  # Max 2MB total
                    logger.info(f"Compiled {len(filings_text['10-K'])} chars from {processed_count} filings for relationship extraction")

            # If still no text, try other sources
            if not filings_text or sum(len(t) for t in filings_text.values()) < 10000:
                # Try to use parsed data from profile
                material_events = profile.get('material_events', {})
                if material_events and material_events.get('events'):
                    events_text = []
                    for event in material_events['events'][:50]:
                        desc = event.get('description', '')
                        if desc:
                            events_text.append(f"{event.get('event_type', 'Event')}: {desc}")

                    if events_text:
                        filings_text['8-K'] = '\n\n'.join(events_text)
                        logger.info(f"Added {len(events_text)} material events to relationship extraction")

            # Extract relationships if we have enough text
            if filings_text and sum(len(t) for t in filings_text.values()) >= 1000:
                logger.info(f"Extracting relationships from {sum(len(t) for t in filings_text.values())} chars")

                return integrator.extract_relationships_for_profile(
                    profile=profile,
                    filings_text=filings_text,
                    options=opts,
                    progress_callback=progress_callback
                )
            else:
                logger.warning(f"Insufficient text for relationship extraction: {sum(len(t) for t in filings_text.values())} chars")
                return {}

        except Exception as e:
            logger.error(f"Relationship extraction failed: {e}")
            return {}

    def _task_ai_analysis(self, profile: Dict, progress_callback) -> Optional[Dict]:
        """Run AI analysis on profile (optional - only if module exists)"""
        try:
            # Try to import AI module - may not exist
            try:
                from src.ai_ml.ollama_analyzer import OllamaAnalyzer
            except (ImportError, ModuleNotFoundError):
                logger.debug("AI/ML module not available - skipping AI analysis")
                return None

            analyzer = OllamaAnalyzer()
            return analyzer.analyze_profile(profile)

        except Exception as e:
            logger.debug(f"AI analysis skipped: {e}")
            return None

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _fetch_filings_with_cache(
        self,
        cik: str,
        ticker: str,
        lookback_years: int,
        progress_callback
    ) -> List[Dict]:
        """Fetch filings, using cache if available"""
        filings = None

        # Try cache first
        if ticker:
            try:
                from src.utils.filing_cache import get_filing_cache
                cache = get_filing_cache()
                filings = cache.get_cached_filings(cik, ticker, lookback_years)

                if filings:
                    logger.info(f"✓ Cache hit: {len(filings)} filings for {ticker}")
                    if progress_callback:
                        progress_callback('info', f"📦 Loaded {len(filings)} filings from cache")
            except Exception as e:
                logger.debug(f"Cache lookup failed: {e}")

        # Fetch from SEC if not cached
        if not filings:
            logger.info(f"Fetching filings from SEC for {ticker}...")
            filings = self.sec_client.get_company_filings(cik)

            # Cache for future use
            if filings and ticker:
                try:
                    from src.utils.filing_cache import get_filing_cache
                    cache = get_filing_cache()
                    cache.cache_filings(cik, ticker, filings, lookback_years)
                except Exception as e:
                    logger.debug(f"Could not cache filings: {e}")

        # Apply lookback filter
        if filings and lookback_years:
            cutoff = datetime.utcnow() - timedelta(days=int(lookback_years) * 365)
            filings = [
                f for f in filings
                if 'filingDate' in f and datetime.fromisoformat(f['filingDate']) >= cutoff
            ]

        return filings or []

    def _post_process_financial_metrics(self, profile: Dict):
        """Calculate derived financial metrics after all data is collected"""
        try:
            # Import here to avoid circular dependency
            from .unified_profile_aggregator import UnifiedSECProfileAggregator

            temp_aggregator = UnifiedSECProfileAggregator(self.mongo, self.sec_client)

            financials = profile.get('financial_time_series', {})

            if financials:
                # Latest values
                profile['latest_financials'] = temp_aggregator._extract_latest_values(financials)

                # Ratios
                profile['financial_ratios'] = temp_aggregator._calculate_financial_ratios(
                    profile.get('latest_financials', {})
                )

                # Growth rates
                profile['growth_rates'] = temp_aggregator._calculate_growth_rates(financials)

                # Statistical summary
                profile['statistical_summary'] = temp_aggregator._summarize_time_series(financials)

                # Trend features
                profile['trend_features'] = temp_aggregator._generate_trend_features(financials)

                # Health indicators
                profile['health_indicators'] = temp_aggregator._generate_health_indicators(profile, financials)

                # Volatility metrics
                profile['volatility_metrics'] = temp_aggregator._generate_volatility_metrics(financials)

                # ML features
                profile['ml_features'] = temp_aggregator._generate_feature_vector(profile)

        except Exception as e:
            logger.error(f"Post-processing failed: {e}")

    def _get_empty_result(self, task_name: str) -> Any:
        """Get empty result for failed task"""
        empty_results = {
            'filing_metadata': {'total_filings': 0},
            'material_events': {'total_8k_count': 0, 'events': []},
            'corporate_governance': {'total_proxy_count': 0},
            'insider_trading': {'total_form4_count': 0},
            'institutional_ownership': {'total_sc13_count': 0},
            'key_persons': {'executives': [], 'board_members': []},
            'financial_time_series': {},
            'relationships': {},
            'ai_analysis': None
        }
        return empty_results.get(task_name, {})


