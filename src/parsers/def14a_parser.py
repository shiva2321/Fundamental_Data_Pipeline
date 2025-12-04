"""
DEF 14A (Proxy Statement) Parser
Extracts corporate governance and executive compensation data
"""
import logging
import re
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class DEF14AParser:
    """
    Parse DEF 14A (Proxy Statement) filings to extract governance data.
    Critical for assessing management quality and alignment with shareholders.
    """

    def parse_def14a_filings(self, filings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse all DEF 14A filings and extract governance metrics.
        NOW WITH DETAILED COMPENSATION AND BOARD ANALYSIS.

        Args:
            filings: List of all filings (will filter for DEF 14A)

        Returns:
            Dictionary with governance analysis including detailed compensation and board data
        """
        # Filter for DEF 14A filings
        def14a_filings = [f for f in filings if f.get('form') in ['DEF 14A', 'DEFC14A', 'DEFA14A']]

        if not def14a_filings:
            return {
                'total_proxy_count': 0,
                'most_recent': None,
                'governance_score': None,
                'executive_compensation': {},
                'board_metrics': {},
                'shareholder_proposals': [],
                'detailed_available': False
            }

        logger.info(f"Parsing {len(def14a_filings)} DEF 14A filings")

        # Sort by date to get most recent
        def14a_filings.sort(key=lambda x: x.get('filingDate', ''), reverse=True)
        most_recent = def14a_filings[0] if def14a_filings else None

        # Analyze proxy filing patterns
        filing_dates = [f.get('filingDate') for f in def14a_filings if f.get('filingDate')]

        # Calculate governance metrics
        governance_metrics = self._analyze_governance_patterns(def14a_filings)

        # NEW: Get detailed compensation analysis
        detailed_comp = {}
        try:
            comp_analyzer = ExecutiveCompensationAnalyzer()
            cik = def14a_filings[0].get('cik', '') if def14a_filings else ''
            detailed_comp = comp_analyzer.analyze_compensation_trends(def14a_filings, cik, max_filings=5)
        except Exception as e:
            logger.warning(f"Could not perform detailed compensation analysis: {e}")
            detailed_comp = {'available': False, 'error': str(e)}

        # NEW: Get detailed board analysis
        detailed_board = {}
        try:
            board_analyzer = BoardCompositionAnalyzer()
            cik = def14a_filings[0].get('cik', '') if def14a_filings else ''
            detailed_board = board_analyzer.analyze_board_composition(def14a_filings, cik, max_filings=3)
        except Exception as e:
            logger.warning(f"Could not perform detailed board analysis: {e}")
            detailed_board = {'available': False, 'error': str(e)}

        # Generate enhanced insights
        insights = self._generate_governance_insights(governance_metrics, len(def14a_filings))

        # Add insights from detailed analysis
        if detailed_comp.get('available'):
            red_flags = detailed_comp.get('red_flags', [])
            for flag in red_flags:
                insights.append(f"⚠️ Compensation: {flag}")

        if detailed_board.get('available'):
            board_assessment = detailed_board.get('governance_assessment', '')
            if board_assessment:
                insights.append(f"Board independence: {board_assessment}")

        return {
            'total_proxy_count': len(def14a_filings),
            'most_recent': most_recent.get('filingDate') if most_recent else None,
            'filing_frequency': self._calculate_filing_frequency(filing_dates),
            'governance_metrics': governance_metrics,
            'governance_score': self._calculate_governance_score(governance_metrics),
            'insights': insights,
            'detailed_compensation': detailed_comp,  # NEW
            'detailed_board': detailed_board  # NEW
        }

    def _analyze_governance_patterns(self, filings: List[Dict]) -> Dict[str, Any]:
        """Analyze governance patterns from DEF 14A filings."""
        metrics = {
            'regular_filings': len(filings) > 0,
            'filing_count': len(filings),
            'years_coverage': self._calculate_years_coverage(filings),
            'consistent_timing': self._check_filing_consistency(filings)
        }

        # Note: Detailed compensation and board data would require parsing actual filing content
        # For now, we track filing patterns which indicate governance quality

        return metrics

    def _calculate_years_coverage(self, filings: List[Dict]) -> float:
        """Calculate how many years of proxy statements we have."""
        if not filings:
            return 0.0

        dates = [f.get('filingDate') for f in filings if f.get('filingDate')]
        if not dates:
            return 0.0

        oldest = min(dates)
        newest = max(dates)

        try:
            oldest_date = datetime.fromisoformat(oldest)
            newest_date = datetime.fromisoformat(newest)
            years = (newest_date - oldest_date).days / 365.25
            return round(years, 1)
        except:
            return 0.0

    def _check_filing_consistency(self, filings: List[Dict]) -> bool:
        """Check if company files proxy statements regularly (annually)."""
        if len(filings) < 2:
            return len(filings) == 1  # One filing is okay

        dates = sorted([f.get('filingDate') for f in filings if f.get('filingDate')])

        # Check if filings are roughly annual (300-450 days apart)
        gaps = []
        for i in range(1, len(dates)):
            try:
                date1 = datetime.fromisoformat(dates[i-1])
                date2 = datetime.fromisoformat(dates[i])
                gap_days = (date2 - date1).days
                gaps.append(gap_days)
            except:
                continue

        if not gaps:
            return False

        # Most gaps should be roughly annual
        annual_gaps = [g for g in gaps if 300 <= g <= 450]
        consistency = len(annual_gaps) / len(gaps) if gaps else 0

        return consistency >= 0.7  # 70% of gaps are annual

    def _calculate_filing_frequency(self, dates: List[str]) -> str:
        """Calculate proxy statement filing frequency."""
        if not dates or len(dates) < 2:
            return "Insufficient data"

        years = self._calculate_years_coverage([{'filingDate': d} for d in dates])
        if years == 0:
            return "Insufficient data"

        avg_per_year = len(dates) / years if years > 0 else 0

        if avg_per_year >= 0.9:
            return "Annual (regular)"
        elif avg_per_year >= 0.5:
            return "Mostly annual"
        else:
            return "Irregular"

    def _calculate_governance_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate a governance quality score (0-100)."""
        score = 0.0

        # Regular filings (30 points)
        if metrics.get('regular_filings'):
            score += 30

        # Consistent timing (30 points)
        if metrics.get('consistent_timing'):
            score += 30

        # Coverage (20 points) - more years = better
        years = metrics.get('years_coverage', 0)
        if years >= 5:
            score += 20
        elif years >= 3:
            score += 15
        elif years >= 1:
            score += 10

        # Filing count (20 points) - shows maturity
        count = metrics.get('filing_count', 0)
        if count >= 10:
            score += 20
        elif count >= 5:
            score += 15
        elif count >= 3:
            score += 10
        elif count >= 1:
            score += 5

        return round(score, 1)

    def _generate_governance_insights(self, metrics: Dict[str, Any], filing_count: int) -> List[str]:
        """Generate insights about corporate governance."""
        insights = []

        # Positive indicators
        if metrics.get('consistent_timing'):
            insights.append("Regular proxy statement filings indicate good governance practices")

        years = metrics.get('years_coverage', 0)
        if years >= 5:
            insights.append(f"Long history of proxy disclosures ({years:.1f} years) suggests mature governance")

        if filing_count >= 10:
            insights.append("Extensive proxy filing history demonstrates transparency")

        # Negative indicators
        if not metrics.get('regular_filings'):
            insights.append("⚠️ No proxy statements found - governance data unavailable")
        elif filing_count < 3:
            insights.append("Limited proxy filing history - governance metrics incomplete")

        if not metrics.get('consistent_timing') and filing_count >= 2:
            insights.append("⚠️ Irregular proxy filing timing may indicate governance concerns")

        return insights


class ExecutiveCompensationAnalyzer:
    """
    Analyze executive compensation trends from proxy statements.
    FULL IMPLEMENTATION - Parses actual DEF 14A content.
    """

    def __init__(self):
        from src.parsers.filing_content_parser import SECFilingContentFetcher, DEF14AContentParser
        self.fetcher = SECFilingContentFetcher()
        self.parser = DEF14AContentParser(self.fetcher)

    def analyze_compensation_trends(self, filings: List[Dict[str, Any]], cik: str, max_filings: int = 5) -> Dict[str, Any]:
        """
        Analyze executive compensation trends over time.
        Parses actual DEF 14A content for compensation tables.

        Args:
            filings: List of DEF 14A filings with accession numbers
            cik: Company CIK
            max_filings: Number of recent proxy statements to analyze

        Returns:
            Multi-year compensation analysis with trends
        """
        # Get DEF 14A filings
        def14a_filings = [f for f in filings if f.get('form') in ['DEF 14A', 'DEFC14A', 'DEFA14A']]

        if not def14a_filings:
            return {
                'available': False,
                'error': 'No DEF 14A filings found'
            }

        # Sort by date, most recent first
        sorted_filings = sorted(def14a_filings, key=lambda x: x.get('filingDate', ''), reverse=True)

        # Parse recent filings
        compensation_data = []

        logger.info(f"Analyzing {min(max_filings, len(sorted_filings))} proxy statements for compensation data")

        for filing in sorted_filings[:max_filings]:
            accession = filing.get('accessionNumber')
            filing_date = filing.get('filingDate')

            if not accession:
                continue

            # Parse this DEF 14A
            parsed = self.parser.parse_def14a_content(cik, accession)

            if parsed.get('available'):
                exec_comp = parsed.get('executive_compensation', {})
                compensation_data.append({
                    'filing_date': filing_date,
                    'year': filing_date[:4] if filing_date else 'Unknown',
                    **exec_comp
                })

        if not compensation_data:
            return {
                'available': False,
                'error': 'Could not parse compensation data from filings'
            }

        # Calculate trends
        trends = self._calculate_compensation_trends(compensation_data)

        return {
            'available': True,
            'years_analyzed': len(compensation_data),
            'compensation_by_year': compensation_data,
            'latest': compensation_data[0] if compensation_data else {},
            'trends': trends,
            'red_flags': self._identify_compensation_red_flags(compensation_data, trends)
        }

    def _calculate_compensation_trends(self, data: List[Dict]) -> Dict[str, Any]:
        """Calculate compensation growth trends."""
        if len(data) < 2:
            return {}

        # Sort by year
        sorted_data = sorted(data, key=lambda x: x.get('year', ''))

        # Calculate CEO comp growth
        ceo_comps = [d.get('ceo_total_comp', 0) for d in sorted_data if d.get('ceo_total_comp', 0) > 0]

        if len(ceo_comps) >= 2:
            ceo_growth = ((ceo_comps[-1] - ceo_comps[0]) / ceo_comps[0] * 100) if ceo_comps[0] > 0 else 0
            avg_ceo_comp = sum(ceo_comps) / len(ceo_comps)
        else:
            ceo_growth = 0
            avg_ceo_comp = 0

        # Calculate pay ratio trend
        pay_ratios = [d.get('pay_ratio', 0) for d in sorted_data if d.get('pay_ratio', 0) > 0]
        pay_ratio_trend = "Increasing" if len(pay_ratios) >= 2 and pay_ratios[-1] > pay_ratios[0] else "Stable"

        return {
            'ceo_comp_growth_percent': ceo_growth,
            'average_ceo_comp': avg_ceo_comp,
            'latest_pay_ratio': pay_ratios[-1] if pay_ratios else 0,
            'pay_ratio_trend': pay_ratio_trend
        }

    def _identify_compensation_red_flags(self, data: List[Dict], trends: Dict) -> List[str]:
        """Identify potential compensation red flags."""
        flags = []

        if not data:
            return flags

        latest = data[0]

        # Excessive pay ratio
        pay_ratio = latest.get('pay_ratio', 0)
        if pay_ratio > 500:
            flags.append(f"Very high CEO-to-median pay ratio ({pay_ratio}:1)")
        elif pay_ratio > 300:
            flags.append(f"High CEO-to-median pay ratio ({pay_ratio}:1)")

        # Rapid compensation growth
        growth = trends.get('ceo_comp_growth_percent', 0)
        if growth > 50:
            flags.append(f"CEO compensation grew {growth:.1f}% (rapid increase)")

        # Compensation vs company performance would require financial data comparison

        return flags


class BoardCompositionAnalyzer:
    """
    Analyze board composition from proxy statements.
    FULL IMPLEMENTATION - Parses actual DEF 14A content.
    """

    def __init__(self):
        from src.parsers.filing_content_parser import SECFilingContentFetcher, DEF14AContentParser
        self.fetcher = SECFilingContentFetcher()
        self.parser = DEF14AContentParser(self.fetcher)

    def analyze_board_composition(self, filings: List[Dict[str, Any]], cik: str, max_filings: int = 3) -> Dict[str, Any]:
        """
        Analyze board composition and independence.
        Parses actual DEF 14A content for board information.

        Args:
            filings: List of DEF 14A filings
            cik: Company CIK
            max_filings: Number of recent proxy statements to analyze

        Returns:
            Board composition analysis with independence metrics
        """
        # Get DEF 14A filings
        def14a_filings = [f for f in filings if f.get('form') in ['DEF 14A', 'DEFC14A', 'DEFA14A']]

        if not def14a_filings:
            return {
                'available': False,
                'error': 'No DEF 14A filings found'
            }

        # Sort by date, most recent first
        sorted_filings = sorted(def14a_filings, key=lambda x: x.get('filingDate', ''), reverse=True)

        # Parse recent filings
        board_data = []

        logger.info(f"Analyzing {min(max_filings, len(sorted_filings))} proxy statements for board composition")

        for filing in sorted_filings[:max_filings]:
            accession = filing.get('accessionNumber')
            filing_date = filing.get('filingDate')

            if not accession:
                continue

            # Parse this DEF 14A
            parsed = self.parser.parse_def14a_content(cik, accession)

            if parsed.get('available'):
                board_comp = parsed.get('board_composition', {})
                board_data.append({
                    'filing_date': filing_date,
                    'year': filing_date[:4] if filing_date else 'Unknown',
                    **board_comp
                })

        if not board_data:
            return {
                'available': False,
                'error': 'Could not parse board composition from filings'
            }

        # Analyze trends
        latest = board_data[0]

        return {
            'available': True,
            'years_analyzed': len(board_data),
            'latest_composition': latest,
            'board_size': latest.get('total_directors', 0),
            'independent_directors': latest.get('independent_directors', 0),
            'independence_ratio': latest.get('independence_ratio', 0),
            'governance_assessment': self._assess_board_governance(latest),
            'board_history': board_data
        }

    def _assess_board_governance(self, board_data: Dict) -> str:
        """Assess board governance quality."""
        independence_ratio = board_data.get('independence_ratio', 0)

        if independence_ratio >= 0.75:
            return "Strong (>75% independent directors)"
        elif independence_ratio >= 0.50:
            return "Adequate (50-75% independent)"
        elif independence_ratio > 0:
            return "Weak (<50% independent)"
        else:
            return "Unknown (independence data unavailable)"

