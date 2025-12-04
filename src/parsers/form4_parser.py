"""
Form 4 (Insider Trading) Parser
Extracts insider trading patterns and sentiment indicators
"""
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta
from collections import defaultdict

logger = logging.getLogger(__name__)


class Form4Parser:
    """
    Parse Form 4 filings to extract insider trading patterns.
    Form 4 = Statement of Changes in Beneficial Ownership
    Critical for understanding insider sentiment and timing signals.
    """

    def parse_form4_filings(self, filings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse all Form 4 filings and extract insider trading patterns.
        NOW WITH DETAILED TRANSACTION ANALYSIS.

        Args:
            filings: List of all filings (will filter for Form 4)

        Returns:
            Dictionary with insider trading analysis including detailed transactions
        """
        # Filter for Form 4 filings
        form4_filings = [f for f in filings if f.get('form') == '4']

        if not form4_filings:
            return {
                'total_form4_count': 0,
                'insider_activity': 'No data',
                'recent_activity': {},
                'sentiment': 'Neutral',
                'insights': [],
                'detailed_available': False
            }

        logger.info(f"Parsing {len(form4_filings)} Form 4 filings")

        # Analyze by time period
        recent_cutoff = (datetime.now() - timedelta(days=90)).isoformat()[:10]
        past_year_cutoff = (datetime.now() - timedelta(days=365)).isoformat()[:10]

        recent_filings = [f for f in form4_filings if f.get('filingDate', '') >= recent_cutoff]
        past_year_filings = [f for f in form4_filings if f.get('filingDate', '') >= past_year_cutoff]

        # Analyze patterns
        activity_metrics = self._analyze_activity_patterns(form4_filings, recent_filings, past_year_filings)
        sentiment = self._calculate_insider_sentiment(activity_metrics)
        insights = self._generate_insider_insights(activity_metrics, sentiment)

        # NEW: Get detailed transaction analysis
        detailed_analysis = {}
        try:
            analyzer = InsiderTransactionAnalyzer()
            # Extract CIK from first filing
            cik = form4_filings[0].get('cik', '') if form4_filings else ''
            detailed_analysis = analyzer.analyze_transactions(form4_filings, cik, max_filings=20)

            # Add detailed insights if available
            if detailed_analysis.get('available'):
                insights.append(f"📊 Detailed analysis: {detailed_analysis['summary']}")
                insights.append(f"Buy/Sell ratio: {detailed_analysis.get('buy_sell_ratio', 0):.2f}")

                # Add signal-based insights
                signal = detailed_analysis.get('overall_signal', 'Neutral')
                if 'Bullish' in signal:
                    insights.append(f"✅ {signal} signal detected from insider transactions")
                elif 'Bearish' in signal:
                    insights.append(f"⚠️ {signal} signal detected from insider transactions")
        except Exception as e:
            logger.warning(f"Could not perform detailed Form 4 analysis: {e}")
            detailed_analysis = {'available': False, 'error': str(e)}

        return {
            'total_form4_count': len(form4_filings),
            'recent_count_90d': len(recent_filings),
            'past_year_count': len(past_year_filings),
            'activity_metrics': activity_metrics,
            'sentiment': sentiment,
            'insights': insights,
            'activity_level': self._classify_activity_level(activity_metrics),
            'detailed_analysis': detailed_analysis  # NEW: Detailed transaction data
        }

    def _analyze_activity_patterns(self, all_filings: List[Dict],
                                   recent: List[Dict],
                                   past_year: List[Dict]) -> Dict[str, Any]:
        """Analyze insider trading activity patterns."""

        # Calculate filing frequency
        total_count = len(all_filings)
        recent_count = len(recent)
        past_year_count = len(past_year)

        # Analyze trends
        metrics = {
            'total_transactions': total_count,
            'recent_transactions_90d': recent_count,
            'past_year_transactions': past_year_count,
            'avg_per_month': round(past_year_count / 12, 1) if past_year_count > 0 else 0,
            'recent_vs_historical': self._compare_recent_to_historical(recent, past_year),
            'activity_trend': self._determine_activity_trend(all_filings)
        }

        return metrics

    def _compare_recent_to_historical(self, recent: List[Dict], past_year: List[Dict]) -> str:
        """Compare recent activity to historical."""
        if not past_year:
            return "Insufficient data"

        # Normalize to same time period (90 days)
        recent_count = len(recent)
        past_year_count = len(past_year)

        # Calculate expected recent count (25% of annual)
        expected_recent = past_year_count * 0.25

        if recent_count > expected_recent * 1.5:
            return "Increased activity"
        elif recent_count < expected_recent * 0.5:
            return "Decreased activity"
        else:
            return "Normal activity"

    def _determine_activity_trend(self, filings: List[Dict]) -> str:
        """Determine if insider activity is increasing or decreasing."""
        if len(filings) < 4:
            return "Insufficient data"

        # Sort by date
        sorted_filings = sorted(filings, key=lambda x: x.get('filingDate', ''))

        # Split into quarters
        total = len(sorted_filings)
        q1_count = len(sorted_filings[:total//4])
        q4_count = len(sorted_filings[3*total//4:])

        if q4_count > q1_count * 1.5:
            return "Accelerating"
        elif q4_count < q1_count * 0.5:
            return "Declining"
        else:
            return "Stable"

    def _calculate_insider_sentiment(self, metrics: Dict[str, Any]) -> str:
        """
        Calculate insider sentiment based on activity patterns.

        Note: Without actual transaction details (buy vs sell), this is based on
        activity patterns only. Full implementation would parse transaction types.
        """
        trend = metrics.get('activity_trend', 'Stable')
        recent_vs_hist = metrics.get('recent_vs_historical', 'Normal activity')

        # High activity with acceleration suggests high interest (could be bullish or bearish)
        if trend == 'Accelerating' and 'Increased' in recent_vs_hist:
            return "High Activity"

        # Declining activity suggests low interest
        elif trend == 'Declining' or 'Decreased' in recent_vs_hist:
            return "Low Activity"

        # Normal patterns
        else:
            return "Normal Activity"

    def _classify_activity_level(self, metrics: Dict[str, Any]) -> str:
        """Classify the overall level of insider activity."""
        avg_per_month = metrics.get('avg_per_month', 0)

        if avg_per_month >= 10:
            return "Very High"
        elif avg_per_month >= 5:
            return "High"
        elif avg_per_month >= 2:
            return "Moderate"
        elif avg_per_month >= 1:
            return "Low"
        else:
            return "Very Low"

    def _generate_insider_insights(self, metrics: Dict[str, Any], sentiment: str) -> List[str]:
        """Generate insights about insider trading patterns."""
        insights = []

        recent_count = metrics.get('recent_transactions_90d', 0)
        total_count = metrics.get('total_transactions', 0)
        trend = metrics.get('activity_trend', 'Unknown')
        recent_vs_hist = metrics.get('recent_vs_historical', 'Unknown')

        # Activity level insights
        if recent_count > 15:
            insights.append(f"High recent insider activity ({recent_count} transactions in 90 days)")
        elif recent_count == 0:
            insights.append("No recent insider transactions - limited insider activity data")

        # Trend insights
        if trend == 'Accelerating':
            insights.append("⚠️ Accelerating insider transaction frequency - monitor closely")
        elif trend == 'Declining':
            insights.append("Declining insider activity - may indicate reduced insider interest")

        # Comparison insights
        if 'Increased' in recent_vs_hist:
            insights.append("Recent activity elevated compared to historical patterns")
        elif 'Decreased' in recent_vs_hist:
            insights.append("Recent activity below historical averages")

        # Data quality
        if total_count >= 50:
            insights.append(f"Extensive insider transaction history ({total_count} total filings)")
        elif total_count < 10:
            insights.append("Limited insider transaction data - insights may be incomplete")

        # Note about limitations
        if total_count > 0:
            insights.append("ℹ️ Note: Detailed buy/sell analysis requires Form 4 content parsing")

        return insights


class InsiderTransactionAnalyzer:
    """
    Analyze detailed insider transactions from Form 4 content.
    FULL IMPLEMENTATION - Parses actual Form 4 XML for buy/sell analysis.
    """

    def __init__(self):
        from filing_content_parser import SECFilingContentFetcher, Form4ContentParser
        self.fetcher = SECFilingContentFetcher()
        self.parser = Form4ContentParser(self.fetcher)

    def analyze_transactions(self, filings: List[Dict[str, Any]], cik: str, max_filings: int = 20) -> Dict[str, Any]:
        """
        Analyze buy vs sell transactions and transaction sizes.
        Parses actual Form 4 content for detailed transaction data.

        Args:
            filings: List of Form 4 filings with accession numbers
            cik: Company CIK
            max_filings: Maximum number of recent filings to parse in detail

        Returns:
            Detailed transaction analysis with buy/sell breakdown
        """
        # Get recent Form 4 filings
        form4_filings = [f for f in filings if f.get('form') == '4']

        if not form4_filings:
            return {
                'available': False,
                'error': 'No Form 4 filings found'
            }

        # Sort by date, most recent first
        sorted_filings = sorted(form4_filings, key=lambda x: x.get('filingDate', ''), reverse=True)

        # Parse recent filings for detailed data
        detailed_transactions = []
        total_buy_value = 0.0
        total_sell_value = 0.0
        total_buy_shares = 0
        total_sell_shares = 0
        insider_signals = defaultdict(int)  # Track per insider

        logger.info(f"Analyzing {min(max_filings, len(sorted_filings))} recent Form 4 filings for detailed transaction data")

        for filing in sorted_filings[:max_filings]:
            accession = filing.get('accessionNumber')
            if not accession:
                continue

            # Parse this Form 4
            parsed = self.parser.parse_form4_transactions(cik, accession)

            if parsed.get('available'):
                detailed_transactions.append({
                    'filing_date': filing.get('filingDate'),
                    'insider_name': parsed.get('insider_name'),
                    'insider_title': parsed.get('insider_title'),
                    'net_shares': parsed['net_transaction']['shares'],
                    'net_value': parsed['net_transaction']['value'],
                    'buy_value': parsed['net_transaction']['buy_value'],
                    'sell_value': parsed['net_transaction']['sell_value'],
                    'signal': parsed.get('signal')
                })

                total_buy_value += parsed['net_transaction']['buy_value']
                total_sell_value += parsed['net_transaction']['sell_value']
                total_buy_shares += parsed['net_transaction']['buy_shares']
                total_sell_shares += parsed['net_transaction']['sell_shares']

                # Track by insider
                insider_key = parsed.get('insider_name', 'Unknown')
                if parsed['net_transaction']['shares'] > 0:
                    insider_signals[insider_key] += 1  # Buying
                elif parsed['net_transaction']['shares'] < 0:
                    insider_signals[insider_key] -= 1  # Selling

        # Calculate aggregates
        net_value = total_buy_value - total_sell_value
        net_shares = total_buy_shares - total_sell_shares

        # Determine overall signal
        if net_value > 1000000:
            overall_signal = "Strong Bullish"
        elif net_value > 100000:
            overall_signal = "Bullish"
        elif net_value < -1000000:
            overall_signal = "Strong Bearish"
        elif net_value < -100000:
            overall_signal = "Bearish"
        else:
            overall_signal = "Neutral"

        # Identify top buyers and sellers
        buyers = [(name, count) for name, count in insider_signals.items() if count > 0]
        sellers = [(name, count) for name, count in insider_signals.items() if count < 0]
        buyers.sort(key=lambda x: x[1], reverse=True)
        sellers.sort(key=lambda x: abs(x[1]), reverse=True)

        return {
            'available': True,
            'filings_analyzed': len(detailed_transactions),
            'total_buy_value': total_buy_value,
            'total_sell_value': total_sell_value,
            'total_buy_shares': total_buy_shares,
            'total_sell_shares': total_sell_shares,
            'net_value': net_value,
            'net_shares': net_shares,
            'overall_signal': overall_signal,
            'top_buyers': buyers[:5],
            'top_sellers': sellers[:5],
            'detailed_transactions': detailed_transactions,
            'buy_sell_ratio': total_buy_value / total_sell_value if total_sell_value > 0 else float('inf'),
            'summary': f"Net {'buying' if net_value > 0 else 'selling'} of ${abs(net_value):,.0f} ({abs(net_shares):,} shares)"
        }

