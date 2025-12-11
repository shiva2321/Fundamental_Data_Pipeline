"""
Unified SEC Profile Aggregator - Combines financial data and ML features into a single profile.
"""
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from src.clients.sec_edgar_api_client import SECEdgarClient

logger = logging.getLogger("unified_sec_profile_aggregator")


class UnifiedSECProfileAggregator:
    """
    Aggregates SEC filing data into a unified profile containing:
    - Company information
    - Financial data from SEC filings
    - Derived metrics and ratios
    - ML-ready features
    - Trend analysis
    - Health indicators
    """

    def __init__(self, mongo, sec_client: Optional[SECEdgarClient] = None):
        """
        Initialize the aggregator with MongoDB connection and SEC API client.

        Args:
            mongo: MongoWrapper instance
            sec_client: Optional SEC Edgar API client
        """
        self.mongo = mongo
        self.sec_client = sec_client or SECEdgarClient()

    def aggregate_company_profile(
            self,
            cik: str,
            company_info: Optional[Dict[str, Any]] = None,
            output_collection: Optional[str] = None,
            options: Optional[Dict[str, Any]] = None,
            progress_callback: Optional[Callable[[str, str], None]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Aggregate all data for a company into a unified profile.

        New parameters:
          - options: dict supporting keys:
              - lookback_years: int | None (limit filings to N years)
              - metrics: List[str] | None (subset of financial metrics to include)
              - incremental: bool (if True, merge new filings into existing profile)
          - progress_callback: callable(level: str, message: str) for UI logging
        """
        def log(level: str, msg: str):
            logger.info(msg) if level == 'info' else logger.debug(msg)
            if progress_callback:
                try:
                    progress_callback(level, msg)
                except Exception:
                    pass

        opts = options or {}
        lookback_years = opts.get('lookback_years')
        metrics_include = opts.get('metrics')
        incremental = bool(opts.get('incremental', False))

        log('info', f"Starting aggregation for CIK {cik}")

        # Check filing cache first
        filings = None
        cache_used = False
        ticker = company_info.get('ticker', '') if company_info else ''

        if lookback_years and ticker:
            try:
                from src.utils.filing_cache import get_filing_cache
                cache = get_filing_cache()
                filings = cache.get_cached_filings(cik, ticker, lookback_years)
                if filings:
                    cache_used = True
                    log('info', f"✓ Using cached filings for {ticker} ({lookback_years}y): {len(filings)} filings")
                    if progress_callback:
                        progress_callback('info', f"📦 Cache: Loaded {len(filings)} filings from cache (fast!)")
            except Exception as e:
                logger.warning(f"Cache check failed: {e}")

        # Fetch from SEC if not in cache
        if not filings:
            log('info', f"Fetching filings for CIK {cik} from SEC EDGAR API")
            if progress_callback and ticker:
                progress_callback('info', f"🌐 Fetching filings from SEC for {ticker}...")
            filings = self.sec_client.get_company_filings(cik)

            # Cache the fetched filings for future use
            if filings and lookback_years and ticker:
                try:
                    from src.utils.filing_cache import get_filing_cache
                    cache = get_filing_cache()
                    cache.cache_filings(cik, ticker, filings, lookback_years)
                    log('info', f"✓ Cached {len(filings)} filings for {ticker}")
                except Exception as e:
                    logger.warning(f"Could not cache filings: {e}")

        if not filings:
            log('info', f"No filings found for CIK {cik}")
            return None

        # Apply lookback filter
        if lookback_years is not None and isinstance(lookback_years, (int, float)):
            cutoff = datetime.utcnow() - timedelta(days=int(lookback_years) * 365)
            orig_count = len(filings)
            filings = [f for f in filings if 'filingDate' in f and datetime.fromisoformat(f['filingDate']) >= cutoff]
            log('info', f"Filtered filings by lookback_years={lookback_years}: {len(filings)} of {orig_count} remain")

        # If incremental and output collection provided, merge with existing
        existing_profile = None
        if incremental and output_collection:
            try:
                existing_profile = self.mongo.find_one(output_collection, {"cik": cik})
            except Exception:
                existing_profile = None

            if existing_profile:
                most_recent = existing_profile.get('filing_metadata', {}).get('most_recent_filing')
                if most_recent:
                    new_filings = [f for f in filings if f.get('filingDate') and f.get('filingDate') > most_recent]
                    if not new_filings:
                        log('info', f"No new filings found since {most_recent} for CIK {cik}. Skipping update.")
                        return existing_profile
                    log('info', f"Incremental mode: {len(new_filings)} new filings will be merged")
                    filings = new_filings
                else:
                    log('info', "Existing profile has no recorded most_recent_filing; performing full aggregation on available filings")

        # Initialize unified profile (base)
        profile = {
            "cik": cik,
            "generated_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat()
        }

        if company_info:
            profile["company_info"] = {
                "ticker": company_info.get('ticker', ''),
                "name": company_info.get('title', company_info.get('name', '')),
                "cik_numeric": company_info.get('cik_numeric', int(cik) if cik and cik.isdigit() else None)
            }

        # === SECTION 1: Filing Metadata ===
        log('info', "Aggregating filing metadata")
        filing_meta = self._aggregate_filing_metadata(filings)
        profile["filing_metadata"] = filing_meta

        # Prepare financial metrics list (allow user override)
        default_metrics = [
            "Revenues",
            "RevenueFromContractWithCustomerExcludingAssessedTax",  # Alternative revenue field
            "RevenueFromContractWithCustomer",  # Another common alternative
            "SalesRevenueNet",  # Another alternative
            "Assets", "Liabilities", "StockholdersEquity",
            "NetIncomeLoss", "CashAndCashEquivalentsAtCarryingValue",
            "OperatingIncomeLoss", "GrossProfit", "EarningsPerShareBasic",
            "EarningsPerShareDiluted", "CommonStockSharesOutstanding"
        ]
        if metrics_include and isinstance(metrics_include, (list, tuple)):
            financial_metrics = [m for m in default_metrics if m in metrics_include]
            log('info', f"Using user-specified metrics: {financial_metrics}")
        else:
            financial_metrics = default_metrics

        # === SECTION 1.5: Material Events (8-K Filings) ===
        log('info', "Parsing material events from 8-K filings")
        try:
            from src.parsers.form_8k_parser import Form8KParser
            parser_8k = Form8KParser()
            material_events = parser_8k.parse_8k_filings(filings)
            profile["material_events"] = material_events
            log('info', f"Parsed {material_events['total_8k_count']} 8-K filings, {material_events['recent_count']} recent events")
        except Exception as e:
            logger.warning(f"Could not parse 8-K filings: {e}")
            profile["material_events"] = {
                'total_8k_count': 0,
                'recent_count': 0,
                'events': [],
                'risk_flags': [],
                'positive_catalysts': []
            }

        # === SECTION 1.6: Corporate Governance (DEF 14A Filings) ===
        log('info', "Parsing corporate governance from DEF 14A filings")
        try:
            from src.parsers.def14a_parser import DEF14AParser
            parser_def14a = DEF14AParser()
            governance_data = parser_def14a.parse_def14a_filings(filings)
            profile["corporate_governance"] = governance_data
            log('info', f"Parsed {governance_data['total_proxy_count']} proxy statements, governance score: {governance_data.get('governance_score', 'N/A')}")
        except Exception as e:
            logger.warning(f"Could not parse DEF 14A filings: {e}")
            profile["corporate_governance"] = {
                'total_proxy_count': 0,
                'governance_score': None,
                'insights': []
            }

        # === SECTION 1.7: Insider Trading (Form 4 Filings) ===
        log('info', "Parsing insider trading from Form 4 filings")
        try:
            from src.parsers.form4_parser import Form4Parser
            parser_form4 = Form4Parser()
            insider_data = parser_form4.parse_form4_filings(filings)
            profile["insider_trading"] = insider_data
            log('info', f"Parsed {insider_data['total_form4_count']} Form 4 filings, sentiment: {insider_data.get('sentiment', 'N/A')}")
        except Exception as e:
            logger.warning(f"Could not parse Form 4 filings: {e}")
            profile["insider_trading"] = {
                'total_form4_count': 0,
                'sentiment': 'No data',
                'insights': []
            }

        # === SECTION 1.8: Institutional Ownership (SC 13D/G Filings) ===
        log('info', "Parsing institutional ownership from SC 13D/G filings")
        try:
            from src.parsers.sc13_parser import SC13Parser
            parser_sc13 = SC13Parser()
            ownership_data = parser_sc13.parse_sc13_filings(filings)
            profile["institutional_ownership"] = ownership_data
            log('info', f"Parsed {ownership_data['total_sc13_count']} SC 13 filings, activist count: {ownership_data.get('activist_count', 0)}")
        except Exception as e:
            logger.warning(f"Could not parse SC 13 filings: {e}")
            profile["institutional_ownership"] = {
                'total_sc13_count': 0,
                'activist_count': 0,
                'insights': []
            }

        # === SECTION 1.9: Key Persons (Executives, Board, Insiders, Holdings) ===
        log('info', "Extracting key persons data (executives, board, insiders, holding companies)")
        try:
            from src.parsers.key_persons_parser import KeyPersonsParser
            key_persons_parser = KeyPersonsParser()
            key_persons_data = key_persons_parser.parse_key_persons(filings, cik)
            profile["key_persons"] = key_persons_data
            summary = key_persons_data.get('summary', {})
            exec_count = summary.get('executive_count', 0)
            board_count = summary.get('board_member_count', 0)
            insider_count = summary.get('insider_holdings', {}).get('count', 0)
            holder_count = summary.get('institutional_ownership', {}).get('holder_count', 0)
            log('info', f"Extracted key persons: {exec_count} executives, {board_count} board members, {insider_count} insiders, {holder_count} institutional holders")
        except Exception as e:
            logger.warning(f"Could not parse key persons data: {e}")
            profile["key_persons"] = {
                'executives': [],
                'board_members': [],
                'insider_holdings': [],
                'holding_companies': [],
                'summary': {},
                'error': str(e)
            }

        # === SECTION 2: Financial Data ===
        log('info', "Extracting financial time series")
        financials = self._extract_financial_time_series(filings, cik, metrics=financial_metrics)

        # If incremental and existing profile present, merge time series
        if incremental and existing_profile:
            merged_financials = defaultdict(dict)
            # start with existing
            for k, v in (existing_profile.get('financial_time_series') or {}).items():
                merged_financials[k].update(v)
            # merge new
            for k, v in financials.items():
                merged_financials[k].update(v)
            financials = merged_financials
            log('info', 'Merged new financial time series into existing profile')

        profile["financial_time_series"] = dict(financials)

        # Consolidate alternative revenue fields into "Revenues"
        self._consolidate_revenue_fields(profile["financial_time_series"])

        profile["latest_financials"] = self._extract_latest_values(profile["financial_time_series"])

        # === SECTION 3: Financial Ratios ===
        if opts.get('include_ratios', True):
            log('info', "Calculating financial ratios")
            profile["financial_ratios"] = self._calculate_financial_ratios(
                profile["latest_financials"]
            )
        else:
            profile["financial_ratios"] = {}
            log('info', "Skipping financial ratios (user option)")

        # === SECTION 4: Growth Rates ===
        if opts.get('include_growth', True):
            log('info', "Calculating growth rates")
            profile["growth_rates"] = self._calculate_growth_rates(financials)
        else:
            profile["growth_rates"] = {}
            log('info', "Skipping growth rates (user option)")

        # === SECTION 5: Statistical Summary ===
        if opts.get('include_summary', True):
            log('info', "Generating statistical summary")
            profile["statistical_summary"] = self._summarize_time_series(financials)
        else:
            profile["statistical_summary"] = {}
            log('info', "Skipping statistical summary (user option)")

        # === SECTION 6: Trend Features ===
        if opts.get('include_trends', True):
            log('info', "Generating trend features")
            profile["trend_features"] = self._generate_trend_features(financials)
        else:
            profile["trend_features"] = {}
            log('info', "Skipping trend features (user option)")

        # === SECTION 7: Health Indicators ===
        if opts.get('include_health', True):
            log('info', "Generating health indicators")
            profile["health_indicators"] = self._generate_health_indicators(profile, financials)
        else:
            profile["health_indicators"] = {}
            log('info', "Skipping health indicators (user option)")

        # === SECTION 8: Volatility Metrics ===
        if opts.get('include_volatility', True):
            log('info', "Generating volatility metrics")
            profile["volatility_metrics"] = self._generate_volatility_metrics(financials)
        else:
            profile["volatility_metrics"] = {}
            log('info', "Skipping volatility metrics (user option)")

        # === SECTION 9: Lifecycle Features ===
        if opts.get('include_lifecycle', True):
            log('info', "Generating lifecycle features")
            profile["lifecycle_features"] = self._generate_lifecycle_features(profile, financials)
        else:
            profile["lifecycle_features"] = {}
            log('info', "Skipping lifecycle features (user option)")

        # === SECTION 10: Anomaly Features ===
        if opts.get('include_anomalies', True):
            log('info', "Generating anomaly features")
            profile["anomaly_features"] = self._generate_anomaly_features(financials)
        else:
            profile["anomaly_features"] = {}
            log('info', "Skipping anomaly features (user option)")

        # === SECTION 11: ML Feature Vector ===
        if opts.get('include_ml_features', True):
            log('info', "Generating ML feature vector")
            profile["ml_features"] = self._generate_feature_vector(profile)
        else:
            profile["ml_features"] = {}
            log('info', "Skipping ML feature vector (user option)")

         # === SECTION 12: AI/ML Analysis ===
        if opts.get('ai_enabled', True):
            try:
                log('info', "Performing AI/ML analysis on profile")
                from src.analysis.ai_analyzer import AIAnalyzer
                ai_analyzer = AIAnalyzer(opts.get('config', {}))
                # Check if multi-model analysis is requested
                selected_models = opts.get('ai_models', [])
                if len(selected_models) > 1:
                    # Multi-model analysis
                    log('info', f"Multi-model analysis with: {', '.join(selected_models)}")
                    profile["ai_analysis_multi"] = {}

                    for model in selected_models:
                        try:
                            log('info', f"Analyzing with model: {model}")
                            # Temporarily set the model in config
                            original_model = opts.get('config', {}).get('profile_settings', {}).get('ai_model')
                            opts['config']['profile_settings']['ai_model'] = model

                            # Create a new analyzer instance for each model to avoid state issues
                            model_analyzer = AIAnalyzer(opts.get('config', {}))

                            # Analyze with this model (with Windows-compatible timeout protection)
                            import threading

                            analysis_result = [None]
                            analysis_error = [None]

                            def analyze_with_timeout():
                                try:
                                    analysis_result[0] = model_analyzer.analyze_profile(profile)
                                except Exception as e:
                                    analysis_error[0] = e

                            # Run analysis in a separate thread with timeout
                            thread = threading.Thread(target=analyze_with_timeout, daemon=True)
                            thread.start()
                            thread.join(timeout=90)  # 90-second timeout

                            if thread.is_alive():
                                # Thread is still running - timeout occurred
                                log('info', f"Analysis with {model} timed out after 90 seconds")
                                profile["ai_analysis_multi"][model] = {
                                    'error': 'Analysis timed out after 90 seconds',
                                    'provider': 'timeout'
                                }
                            elif analysis_error[0]:
                                # Exception occurred during analysis
                                log('info', f"Analysis with {model} failed: {analysis_error[0]}")
                                profile["ai_analysis_multi"][model] = {
                                    'error': str(analysis_error[0]),
                                    'provider': 'error'
                                }
                            elif analysis_result[0]:
                                # Analysis completed successfully
                                profile["ai_analysis_multi"][model] = analysis_result[0]
                                log('info', f"Analysis with {model} completed")
                            else:
                                # Unknown state
                                log('info', f"Analysis with {model} returned no result")
                                profile["ai_analysis_multi"][model] = {
                                    'error': 'No result returned',
                                    'provider': 'unknown_error'
                                }

                            # Restore original model
                            if original_model:
                                opts['config']['profile_settings']['ai_model'] = original_model

                        except Exception as model_error:
                            log('info', f"Critical error with model {model}: {model_error}")
                            profile["ai_analysis_multi"][model] = {'error': str(model_error), 'provider': 'critical_error'}

                    # Set primary analysis to first model's result
                    first_model = selected_models[0]
                    profile["ai_analysis"] = profile["ai_analysis_multi"].get(first_model, {})
                    log('info', f"Multi-model analysis completed with {len(selected_models)} models")
                else:
                    # Single model analysis (default behavior)
                    profile["ai_analysis"] = ai_analyzer.analyze_profile(profile)

                    # Log the provider used
                    provider = profile["ai_analysis"].get('provider', 'unknown') if profile["ai_analysis"] else 'none'
                    if provider == 'ollama':
                        model = profile["ai_analysis"].get('model', 'unknown')
                        log('info', f"AI/ML analysis completed using Ollama model: {model}")
                    elif provider == 'rule_based':
                        log('info', "AI/ML analysis completed using rule-based fallback (Ollama unavailable)")
                    else:
                        log('info', "AI/ML analysis completed successfully")
            except Exception as e:
                log('info', f"AI/ML analysis failed: {e}")
                profile["ai_analysis"] = None
        else:
            profile["ai_analysis"] = None
            log('info', "Skipping AI/ML analysis (user option)")

        # === SECTION 13: Relationship Extraction ===
        if opts.get('extract_relationships', True):
            log('info', "Extracting relationship data")
            try:
                from src.extractors.relationship_integrator import RelationshipDataIntegrator
                from src.clients.company_ticker_fetcher import CompanyTickerFetcher

                # Initialize integrator if not already done
                if not hasattr(self, 'relationship_integrator'):
                    ticker_fetcher = CompanyTickerFetcher()
                    all_companies = ticker_fetcher.get_all_companies()
                    self.relationship_integrator = RelationshipDataIntegrator(
                        mongo_wrapper=self.mongo,
                        ticker_fetcher=ticker_fetcher,
                        all_companies=all_companies
                    )

                # Compile data for relationship extraction from ALL filings
                # Strategy: Use already-parsed data (material events, governance, etc.)
                # instead of fetching full filing text from SEC
                filings_text = {}
                try:
                    log('info', f"Extracting relationships from ALL {len(filings)} filings using parsed data")

                    # Use material events data (already parsed from 8-Ks)
                    material_events = profile.get('material_events', {})
                    if material_events and material_events.get('recent_events'):
                        events_text = []
                        for event in material_events['recent_events'][:50]:  # Top 50 events
                            desc = event.get('description', '')
                            if desc:
                                events_text.append(f"{event.get('event_type', 'Event')}: {desc}")

                        if events_text:
                            filings_text['8-K'] = '\n\n'.join(events_text)
                            log('info', f"Compiled text from {len(events_text)} material events")

                    # Use governance data (already parsed from DEF 14A)
                    governance = profile.get('corporate_governance', {})
                    if governance:
                        gov_text = []

                        # Executive compensation discussions often mention other companies
                        exec_comp = governance.get('executive_compensation', {})
                        if exec_comp:
                            gov_text.append(str(exec_comp)[:10000])

                        # Board composition
                        board_comp = governance.get('board_composition', {})
                        if board_comp:
                            gov_text.append(str(board_comp)[:5000])

                        if gov_text:
                            filings_text['DEF14A'] = '\n\n'.join(gov_text)
                            log('info', f"Compiled text from governance data")

                    # Add AI analysis text (mentions competitors, partners, etc.)
                    if opts.get('ai_enabled', True) and profile.get('ai_analysis'):
                        ai_text = []
                        consensus = profile['ai_analysis'].get('consensus_analysis', {})

                        for field in ['competitive_position', 'investment_thesis', 'risk_factors', 'growth_drivers']:
                            text = consensus.get(field, '')
                            if text and text != 'N/A':
                                ai_text.append(text)

                        if ai_text:
                            filings_text['AI_ANALYSIS'] = '\n\n'.join(ai_text)
                            log('info', f"Compiled text from AI analysis")

                    # FALLBACK: If we have very little text, fetch from ALL 10-Ks/10-Qs for comprehensive relationship extraction
                    total_text_length = sum(len(t) for t in filings_text.values())
                    if total_text_length < 10000:  # Less than 10KB of text
                        log('info', f"Limited text available ({total_text_length} chars), fetching from ALL 10-Ks/10-Qs as fallback")
                        # Process MORE filings for better relationship extraction (up to 20 filings or 1MB of text)
                        ten_k_text = self._extract_section_text(filings, ['10-K', '10-Q'], max_filings=20, max_chars=1000000)  # Reduced from 2MB to 1MB for memory efficiency
                        if ten_k_text:
                            filings_text['10-K'] = ten_k_text
                            log('info', f"Fetched {len(ten_k_text)} chars from ALL 10-Ks/10-Qs")

                    log('info', f"Total text for extraction: {sum(len(t) for t in filings_text.values())} chars from {len(filings_text)} sources")

                except Exception as e:
                    logger.warning(f"Could not compile filing data: {e}")

                # Extract relationships
                if filings_text:
                    relationships_data = self.relationship_integrator.extract_relationships_for_profile(
                        profile=profile,
                        filings_text=filings_text,
                        options=opts,
                        progress_callback=progress_callback
                    )

                    # Store relationships in profile and MongoDB
                    self.relationship_integrator.store_relationships_in_profile(
                        profile=profile,
                        relationships_data=relationships_data,
                        mongo_collection=output_collection or 'Fundamental_Data_Pipeline'
                    )

                    log('info', f"Extracted {len(relationships_data.get('relationships', []))} relationships")
                else:
                    log('info', "No filing text available for relationship extraction")
                    profile["relationships"] = {}

            except Exception as e:
                logger.exception(f"Could not extract relationships: {e}")
                profile["relationships"] = {}
        else:
            profile["relationships"] = {}
            log('info', "Skipping relationship extraction (user option)")

        # Store the unified profile if output_collection provided
        if output_collection:
            try:
                # If incremental and existing profile, perform a replace with merged content
                if incremental and existing_profile:
                    # keep some historical meta if present
                    profile_to_store = existing_profile.copy()
                    profile_to_store.update(profile)
                    self.mongo.replace_one(output_collection, {"cik": cik}, profile_to_store, upsert=True)
                    log('info', f"Merged and stored unified profile for CIK {cik}")
                else:
                    self.mongo.upsert_one(output_collection, {"cik": cik}, profile)
                    log('info', f"Stored unified profile for CIK {cik}")
            except Exception as e:
                log('info', f"Error storing profile for {cik}: {e}")

        return profile

    def _aggregate_filing_metadata(self, filings: List[Dict]) -> Dict[str, Any]:
        """Aggregate filing metadata."""
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
            "filing_date_range_days": (
                (datetime.fromisoformat(max(dates)) - datetime.fromisoformat(min(dates))).days
                if len(dates) >= 2 else 0
            )
        }

    def _extract_financial_time_series(
            self,
            filings: List[Dict],
            cik: str,
            metrics: Optional[List[str]] = None
    ) -> Dict[str, Dict[str, float]]:
        """
        Extract financial time series data.
        Uses BOTH direct API extraction AND filing parsing, then merges the results.
        This ensures we get revenue data AND all filing data.
        """
        financial_metrics = metrics or [
            "Revenues", "Assets", "Liabilities", "StockholdersEquity",
            "NetIncomeLoss", "CashAndCashEquivalentsAtCarryingValue",
            "OperatingIncomeLoss", "GrossProfit", "EarningsPerShareBasic",
            "EarningsPerShareDiluted", "CommonStockSharesOutstanding"
        ]

        # METHOD 1: Extract from filings first (gets ALL filing data)
        logger.info(f"Extracting financial data from {len(filings)} filings for CIK {cik}")
        financials = defaultdict(dict)

        for f in filings:
            filing_date = f.get("filingDate") or f.get("reportDate")
            if not filing_date:
                continue

            for key in financial_metrics:
                if key in f and f[key] is not None:
                    try:
                        financials[key][filing_date] = float(f[key])
                    except (ValueError, TypeError):
                        logger.debug(f"Could not convert {key} to float for CIK {cik}")

        logger.info(f"Extracted {len(financials)} metrics from {len(filings)} filings")

        # METHOD 2: Supplement with direct API extraction (more reliable for revenue)
        logger.info(f"Supplementing with direct API extraction for CIK {cik}")
        try:
            financials_from_api = self.sec_client.get_financial_metrics_timeseries(cik)

            if financials_from_api:
                # Merge API data with filing data (API data takes precedence for revenue)
                for metric, api_data in financials_from_api.items():
                    if api_data:
                        # For Revenues, use API data (more reliable)
                        if metric == 'Revenues':
                            logger.info(f"Using API revenue data: {len(api_data)} periods")
                            financials[metric] = dict(api_data)
                        else:
                            # For other metrics, merge (prefer filing data if more complete)
                            if metric not in financials or len(api_data) > len(financials.get(metric, {})):
                                financials[metric] = dict(api_data)
                                logger.info(f"Using API data for {metric}: {len(api_data)} periods")
                            else:
                                logger.info(f"Keeping filing data for {metric}: {len(financials[metric])} periods")
        except Exception as e:
            logger.warning(f"API extraction failed: {e}, using filing data only")

        logger.info(f"Final result: {len(financials)} metrics total")
        return dict(financials)

    def _consolidate_revenue_fields(self, financials: Dict[str, Dict[str, float]]) -> None:
        """Consolidate alternative revenue field names into 'Revenues'."""
        # Alternative revenue field names used by different companies
        alt_revenue_fields = [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "RevenueFromContractWithCustomer",
            "SalesRevenueNet"
        ]

        # If Revenues doesn't exist or is empty, try alternatives
        if not financials.get("Revenues") or len(financials.get("Revenues", {})) == 0:
            for alt_field in alt_revenue_fields:
                if alt_field in financials and financials[alt_field]:
                    logger.info(f"Consolidating {alt_field} into Revenues field")
                    financials["Revenues"] = financials[alt_field]
                    break

        # Also consolidate in latest_financials later by checking alternative fields
        # This ensures revenue data is available under the standard "Revenues" key

    def _extract_latest_values(self, financials: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Extract the most recent values for each metric."""
        latest = {}
        for key, values in financials.items():
            if values:
                latest_date = max(values.keys())
                latest[key] = values[latest_date]
                latest[f"{key}_date"] = latest_date
        return latest

    def _calculate_financial_ratios(self, latest: Dict[str, Any]) -> Dict[str, float]:
        """Calculate financial ratios from latest values."""
        assets = latest.get("Assets")
        liabilities = latest.get("Liabilities")
        equity = latest.get("StockholdersEquity")
        revenue = latest.get("Revenues")
        net_income = latest.get("NetIncomeLoss")
        cash = latest.get("CashAndCashEquivalentsAtCarryingValue")

        ratios = {}
        try:
            if assets and liabilities:
                ratios["debt_to_assets"] = round(liabilities / assets, 4)
                if liabilities != 0:
                    ratios["current_ratio"] = round(assets / liabilities, 4)

            if liabilities and equity and equity != 0:
                ratios["debt_to_equity"] = round(liabilities / equity, 4)

            if revenue and revenue != 0:
                if net_income:
                    ratios["profit_margin"] = round(net_income / revenue, 4)
                if assets:
                    ratios["asset_turnover"] = round(revenue / assets, 4)

            if equity and equity != 0 and net_income:
                ratios["return_on_equity"] = round(net_income / equity, 4)

            if assets and assets != 0 and net_income:
                ratios["return_on_assets"] = round(net_income / assets, 4)

            if cash and assets:
                ratios["cash_ratio"] = round(cash / assets, 4)

        except (TypeError, ZeroDivisionError) as e:
            logger.warning(f"Could not calculate some ratios: {e}")

        return ratios

    def _calculate_growth_rates(self, financials: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Calculate growth rates for financial metrics."""
        growth_rates = {}

        for metric, period_data in financials.items():
            if not period_data or len(period_data) < 2:
                continue

            sorted_periods = sorted(period_data.keys())
            pop_growth = []

            for i in range(1, len(sorted_periods)):
                prev_val = period_data[sorted_periods[i - 1]]
                curr_val = period_data[sorted_periods[i]]

                if prev_val and prev_val != 0:
                    growth = ((curr_val - prev_val) / abs(prev_val)) * 100
                    pop_growth.append({
                        "period": sorted_periods[i],
                        "growth_rate": round(growth, 2)
                    })

            if pop_growth:
                growth_rates[metric] = {
                    "period_over_period": pop_growth,  # Store ALL periods, not just last 5
                    "avg_growth_rate": round(np.mean([g["growth_rate"] for g in pop_growth]), 2),
                    "latest_growth_rate": pop_growth[-1]["growth_rate"] if pop_growth else None,
                    "median_growth_rate": round(float(np.median([g["growth_rate"] for g in pop_growth])), 2)
                }

        return growth_rates

    def _summarize_time_series(self, time_series: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Generate summary statistics for time series data."""
        summary = {}

        for metric, period_data in time_series.items():
            if not period_data:
                continue

            values = list(period_data.values())
            summary[metric] = {
                "count": len(values),
                "mean": round(float(np.mean(values)), 2),
                "std": round(float(np.std(values)), 2),
                "min": round(float(np.min(values)), 2),
                "max": round(float(np.max(values)), 2),
                "median": round(float(np.median(values)), 2),
                "latest": values[-1] if values else None,
                "earliest": values[0] if values else None,
                "coefficient_of_variation": round(float(np.std(values) / np.mean(values)), 4) if np.mean(values) != 0 else None
            }

        return summary

    def _generate_trend_features(self, time_series: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Generate trend-based features from time series data."""
        trend_features = {}

        for metric, period_data in time_series.items():
            if not period_data or len(period_data) < 3:
                continue

            sorted_periods = sorted(period_data.keys())
            values = [period_data[p] for p in sorted_periods]

            try:
                x = np.arange(len(values))
                y = np.array(values)

                coefficients = np.polyfit(x, y, 1)
                slope = float(coefficients[0])
                intercept = float(coefficients[1])

                y_pred = slope * x + intercept
                ss_res = np.sum((y - y_pred) ** 2)
                ss_tot = np.sum((y - np.mean(y)) ** 2)
                r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

                trend_features[metric] = {
                    "slope": round(slope, 4),
                    "intercept": round(intercept, 2),
                    "r_squared": round(float(r_squared), 4),
                    "trend_direction": "increasing" if slope > 0 else "decreasing",
                    "trend_strength": "strong" if abs(r_squared) > 0.7 else "moderate" if abs(r_squared) > 0.4 else "weak"
                }

                if len(values) >= 4:
                    first_half_mean = np.mean(values[:len(values)//2])
                    second_half_mean = np.mean(values[len(values)//2:])
                    acceleration = second_half_mean - first_half_mean
                    trend_features[metric]["acceleration"] = round(float(acceleration), 2)

            except (np.linalg.LinAlgError, ValueError) as e:
                logger.debug(f"Could not calculate trend for {metric}: {e}")

        return trend_features

    def _generate_health_indicators(
            self,
            profile: Dict[str, Any],
            time_series: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Generate financial health indicators."""
        health = {}

        ratios = profile.get("financial_ratios", {})

        # Profitability health
        profit_margin = ratios.get("profit_margin", 0)
        roe = ratios.get("return_on_equity", 0)
        roa = ratios.get("return_on_assets", 0)

        health["profitability_score"] = round(
            (min(profit_margin * 100, 100) + min(roe * 100, 100) + min(roa * 100, 100)) / 3, 2
        )

        # Leverage health
        debt_to_equity = ratios.get("debt_to_equity", 0)
        debt_to_assets = ratios.get("debt_to_assets", 0)

        leverage_score = 100 - min((debt_to_equity * 10 + debt_to_assets * 50), 100)
        health["leverage_score"] = round(max(leverage_score, 0), 2)

        # Growth health
        growth_rates = profile.get("growth_rates", {})
        revenue_growth = growth_rates.get("Revenues", {}).get("avg_growth_rate", 0)

        health["growth_score"] = round(min(max(revenue_growth, 0), 100), 2)

        # Overall health score
        health["overall_health_score"] = round(
            (health["profitability_score"] * 0.4 +
             health["leverage_score"] * 0.3 +
             health["growth_score"] * 0.3), 2
        )

        # Health classification
        if health["overall_health_score"] >= 70:
            health["health_classification"] = "Excellent"
        elif health["overall_health_score"] >= 50:
            health["health_classification"] = "Good"
        elif health["overall_health_score"] >= 30:
            health["health_classification"] = "Fair"
        else:
            health["health_classification"] = "Poor"

        return health

    def _generate_volatility_metrics(self, time_series: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Generate volatility metrics for financial data."""
        volatility = {}

        for metric, period_data in time_series.items():
            if not period_data or len(period_data) < 3:
                continue

            values = list(period_data.values())

            # Calculate period-over-period percentage changes
            pct_changes = []
            for i in range(1, len(values)):
                if values[i-1] != 0:
                    pct_change = ((values[i] - values[i-1]) / abs(values[i-1])) * 100
                    pct_changes.append(pct_change)

            if pct_changes:
                volatility[metric] = {
                    "std_dev": round(float(np.std(pct_changes)), 4),
                    "variance": round(float(np.var(pct_changes)), 4),
                    "max_swing": round(float(max(pct_changes) - min(pct_changes)), 2),
                    "volatility_classification": self._classify_volatility(np.std(pct_changes))
                }

        return volatility

    def _classify_volatility(self, std_dev: float) -> str:
        """Classify volatility based on standard deviation."""
        if std_dev < 10:
            return "Low"
        elif std_dev < 25:
            return "Moderate"
        elif std_dev < 50:
            return "High"
        else:
            return "Very High"

    def _generate_lifecycle_features(
            self,
            profile: Dict[str, Any],
            time_series: Dict[str, Dict[str, float]]
    ) -> Dict[str, Any]:
        """Generate business lifecycle features."""
        lifecycle = {}

        metadata = profile.get("filing_metadata", {})
        growth_rates = profile.get("growth_rates", {})

        # Filing history duration
        filing_range_days = metadata.get("filing_date_range_days", 0)
        filing_years = filing_range_days / 365.25

        lifecycle["years_of_data"] = round(filing_years, 1)
        lifecycle["total_filings"] = metadata.get("total_filings", 0)
        lifecycle["filing_frequency"] = round(
            lifecycle["total_filings"] / filing_years, 2
        ) if filing_years > 0 else 0

        # Growth stage classification
        revenue_growth = growth_rates.get("Revenues", {}).get("avg_growth_rate", 0)

        if revenue_growth > 30:
            lifecycle["growth_stage"] = "High Growth"
        elif revenue_growth > 10:
            lifecycle["growth_stage"] = "Growth"
        elif revenue_growth > 0:
            lifecycle["growth_stage"] = "Stable"
        elif revenue_growth > -10:
            lifecycle["growth_stage"] = "Declining"
        else:
            lifecycle["growth_stage"] = "Distressed"

        # Maturity indicators
        if filing_years > 20:
            lifecycle["maturity"] = "Mature"
        elif filing_years > 10:
            lifecycle["maturity"] = "Established"
        elif filing_years > 5:
            lifecycle["maturity"] = "Developing"
        else:
            lifecycle["maturity"] = "Early Stage"

        return lifecycle

    def _generate_anomaly_features(self, time_series: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """Generate anomaly detection features."""
        anomalies = {}

        for metric, period_data in time_series.items():
            if not period_data or len(period_data) < 5:
                continue

            values = np.array(list(period_data.values()))
            mean = np.mean(values)
            std = np.std(values)

            if std == 0:
                continue

            # Z-score based anomaly detection
            z_scores = np.abs((values - mean) / std)
            anomaly_indices = np.where(z_scores > 2)[0]

            if len(anomaly_indices) > 0:
                periods = sorted(period_data.keys())
                anomalies[metric] = {
                    "anomaly_count": len(anomaly_indices),
                    "anomaly_percentage": round((len(anomaly_indices) / len(values)) * 100, 2),
                    "max_z_score": round(float(np.max(z_scores)), 4)
                }

        return anomalies

    def _generate_feature_vector(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a flat feature vector for ML models."""
        features = {}

        # Latest financial metrics
        latest = profile.get("latest_financials", {})
        for key in ["Revenues", "Assets", "Liabilities", "StockholdersEquity", "NetIncomeLoss"]:
            features[f"latest_{key}"] = latest.get(key, 0)

        # Financial ratios
        ratios = profile.get("financial_ratios", {})
        for key, value in ratios.items():
            features[f"ratio_{key}"] = value

        # Growth metrics
        growth = profile.get("growth_rates", {})
        for metric in ["Revenues", "Assets", "NetIncomeLoss"]:
            if metric in growth:
                features[f"growth_{metric}_avg"] = growth[metric].get("avg_growth_rate", 0)
                features[f"growth_{metric}_latest"] = growth[metric].get("latest_growth_rate", 0)

        # Health scores
        health = profile.get("health_indicators", {})
        for key, value in health.items():
            if isinstance(value, (int, float)):
                features[f"health_{key}"] = value

        # Volatility metrics (average)
        volatility = profile.get("volatility_metrics", {})
        vol_stds = [v.get("std_dev", 0) for v in volatility.values() if "std_dev" in v]
        features["avg_volatility"] = round(float(np.mean(vol_stds)), 4) if vol_stds else 0

        # Lifecycle features
        lifecycle = profile.get("lifecycle_features", {})
        features["years_of_data"] = lifecycle.get("years_of_data", 0)
        features["filing_frequency"] = lifecycle.get("filing_frequency", 0)

        return features

    def _extract_section_text(
        self,
        filings: List[Dict],
        form_types: List[str],
        max_chars: int = 500000,
        max_filings: int = 10
    ) -> str:
        """
        Extract text content from filings of specified types.

        Args:
            filings: List of filing dictionaries
            form_types: List of form types to extract (e.g., ['10-K', '10-Q'])
            max_chars: Maximum characters to extract
            max_filings: Maximum number of filings to process (default: 10)

        Returns:
            Combined text from matching filings
        """
        text_content = []
        processed_count = 0

        try:
            # Filter to matching form types first
            matching_filings = [f for f in filings if f.get('form') in form_types]

            # Limit to max_filings most recent
            matching_filings = matching_filings[:max_filings]

            logger.info(f"Extracting text from {len(matching_filings)} {'/'.join(form_types)} filings")

            for idx, filing in enumerate(matching_filings, 1):
                # Try to get cached text if available
                if 'text' in filing:
                    text_content.append(filing['text'])
                    processed_count += 1
                elif 'accessionNumber' in filing and filing.get('cik'):
                    # Try to fetch from SEC (this is slow!)
                    try:
                        from src.parsers.filing_content_parser import SECFilingContentFetcher
                        fetcher = SECFilingContentFetcher()

                        logger.info(f"Fetching filing {idx}/{len(matching_filings)}: {filing['form']} {filing.get('filingDate', 'N/A')}")

                        content = fetcher.fetch_filing_content(
                            filing['cik'],
                            filing['accessionNumber']
                        )
                        if content:
                            text_content.append(content)
                            processed_count += 1
                            logger.info(f"✓ Fetched {len(content)} chars from {filing['form']}")
                    except Exception as e:
                        logger.debug(f"Could not fetch filing text: {e}")
                        continue
        except Exception as e:
            logger.warning(f"Error extracting section text: {e}")

        # Combine and limit to max_chars
        combined_text = ' '.join(text_content)

        logger.info(f"Extracted {len(combined_text)} total characters from {processed_count} filings")

        return combined_text[:max_chars] if combined_text else ''

