"""
Unified SEC Profile Aggregator - Combines financial data and ML features into a single profile.
"""
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from sec_edgar_api_client import SECEdgarClient

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

        log('info', f"Starting aggregation for CIK {cik}. options={opts}")

        # Fetch filings from SEC EDGAR API
        log('info', f"Fetching filings for CIK {cik} from SEC EDGAR API")
        filings = self.sec_client.get_company_filings(cik)

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
            "Revenues", "Assets", "Liabilities", "StockholdersEquity",
            "NetIncomeLoss", "CashAndCashEquivalentsAtCarryingValue",
            "OperatingIncomeLoss", "GrossProfit", "EarningsPerShareBasic",
            "EarningsPerShareDiluted", "CommonStockSharesOutstanding"
        ]
        if metrics_include and isinstance(metrics_include, (list, tuple)):
            financial_metrics = [m for m in default_metrics if m in metrics_include]
            log('info', f"Using user-specified metrics: {financial_metrics}")
        else:
            financial_metrics = default_metrics

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
        profile["latest_financials"] = self._extract_latest_values(financials)

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
        """Extract financial time series data from filings."""
        financial_metrics = metrics or [
            "Revenues", "Assets", "Liabilities", "StockholdersEquity",
            "NetIncomeLoss", "CashAndCashEquivalentsAtCarryingValue",
            "OperatingIncomeLoss", "GrossProfit", "EarningsPerShareBasic",
            "EarningsPerShareDiluted", "CommonStockSharesOutstanding"
        ]

        financials = defaultdict(dict)
        for f in filings:
            filing_date = f.get("filingDate")
            if not filing_date:
                continue

            for key in financial_metrics:
                if key in f and f[key] is not None:
                    try:
                        financials[key][filing_date] = float(f[key])
                    except (ValueError, TypeError):
                        logger.debug(f"Could not convert {key} to float for CIK {cik}")

        return financials

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
                    "period_over_period": pop_growth[-5:],  # Last 5 periods
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

