"""
SC 13D/G (Beneficial Ownership) Parser
Extracts institutional ownership and activist investor data
"""
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SC13Parser:
    """
    Parse SC 13D/G filings to extract institutional ownership patterns.
    SC 13D = Activist investors (>5% ownership with intent to influence)
    SC 13G = Passive investors (>5% ownership, passive)
    Critical for understanding institutional confidence and activist activity.
    """

    def parse_sc13_filings(self, filings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse all SC 13D/G filings and extract ownership patterns.
        NOW WITH DETAILED OWNERSHIP ANALYSIS.

        Args:
            filings: List of all filings (will filter for SC 13D/G)

        Returns:
            Dictionary with institutional ownership analysis including detailed ownership data
        """
        # Filter for SC 13D and SC 13G filings
        sc13_filings = [f for f in filings if f.get('form') in [
            'SC 13D', 'SC 13D/A', 'SC 13G', 'SC 13G/A'
        ]]

        if not sc13_filings:
            return {
                'total_sc13_count': 0,
                'activist_count': 0,
                'passive_count': 0,
                'institutional_interest': 'No data',
                'insights': [],
                'detailed_available': False
            }

        logger.info(f"Parsing {len(sc13_filings)} SC 13D/G filings")

        # Separate activist (13D) from passive (13G)
        activist_filings = [f for f in sc13_filings if '13D' in f.get('form', '')]
        passive_filings = [f for f in sc13_filings if '13G' in f.get('form', '')]

        # Analyze patterns
        ownership_metrics = self._analyze_ownership_patterns(
            sc13_filings, activist_filings, passive_filings
        )

        insights = self._generate_ownership_insights(ownership_metrics)

        # NEW: Get detailed ownership analysis
        detailed_analysis = {}
        try:
            analyzer = InstitutionalOwnershipAnalyzer()
            # Extract CIK from first filing
            cik = sc13_filings[0].get('cik', '') if sc13_filings else ''
            detailed_analysis = analyzer.analyze_ownership_details(sc13_filings, cik, max_filings=10)

            # Add detailed insights if available
            if detailed_analysis.get('available'):
                insights.append(f"📊 {detailed_analysis['summary']}")

                # Add activist-specific insights
                if detailed_analysis.get('activist_count', 0) > 0:
                    for activist in detailed_analysis.get('activist_details', [])[:3]:
                        insights.append(
                            f"🔴 {activist['investor']} ({activist['ownership']:.1f}%): {activist['intent']}"
                        )
        except Exception as e:
            logger.warning(f"Could not perform detailed SC 13 analysis: {e}")
            detailed_analysis = {'available': False, 'error': str(e)}

        return {
            'total_sc13_count': len(sc13_filings),
            'activist_count': len(activist_filings),
            'passive_count': len(passive_filings),
            'ownership_metrics': ownership_metrics,
            'institutional_interest': self._assess_institutional_interest(ownership_metrics),
            'insights': insights,
            'most_recent_filing': self._get_most_recent_filing(sc13_filings),
            'detailed_analysis': detailed_analysis  # NEW: Detailed ownership data
        }

    def _analyze_ownership_patterns(self, all_filings: List[Dict],
                                    activist: List[Dict],
                                    passive: List[Dict]) -> Dict[str, Any]:
        """Analyze institutional ownership filing patterns."""

        # Calculate recent activity
        recent_cutoff = (datetime.now() - timedelta(days=365)).isoformat()[:10]
        recent_filings = [f for f in all_filings if f.get('filingDate', '') >= recent_cutoff]
        recent_activist = [f for f in activist if f.get('filingDate', '') >= recent_cutoff]
        recent_passive = [f for f in passive if f.get('filingDate', '') >= recent_cutoff]

        metrics = {
            'total_filings': len(all_filings),
            'activist_filings': len(activist),
            'passive_filings': len(passive),
            'recent_filings_1yr': len(recent_filings),
            'recent_activist_1yr': len(recent_activist),
            'recent_passive_1yr': len(recent_passive),
            'activist_ratio': round(len(activist) / len(all_filings), 2) if all_filings else 0,
            'has_recent_activist': len(recent_activist) > 0,
            'filing_trend': self._determine_filing_trend(all_filings)
        }

        return metrics

    def _determine_filing_trend(self, filings: List[Dict]) -> str:
        """Determine if institutional filing activity is increasing or decreasing."""
        if len(filings) < 4:
            return "Insufficient data"

        # Sort by date
        sorted_filings = sorted(filings, key=lambda x: x.get('filingDate', ''))

        # Compare first half vs second half
        midpoint = len(sorted_filings) // 2
        first_half = sorted_filings[:midpoint]
        second_half = sorted_filings[midpoint:]

        # Normalize by time period
        try:
            first_date = datetime.fromisoformat(first_half[0].get('filingDate', ''))
            mid_date = datetime.fromisoformat(first_half[-1].get('filingDate', ''))
            last_date = datetime.fromisoformat(second_half[-1].get('filingDate', ''))

            first_period_days = (mid_date - first_date).days
            second_period_days = (last_date - mid_date).days

            if first_period_days > 0 and second_period_days > 0:
                first_rate = len(first_half) / first_period_days
                second_rate = len(second_half) / second_period_days

                if second_rate > first_rate * 1.3:
                    return "Increasing"
                elif second_rate < first_rate * 0.7:
                    return "Decreasing"
                else:
                    return "Stable"
        except:
            pass

        return "Unknown"

    def _assess_institutional_interest(self, metrics: Dict[str, Any]) -> str:
        """Assess overall institutional interest level."""
        total = metrics.get('total_filings', 0)
        recent = metrics.get('recent_filings_1yr', 0)
        has_activist = metrics.get('has_recent_activist', False)

        if has_activist and recent >= 3:
            return "High (Activist presence)"
        elif recent >= 5:
            return "High"
        elif recent >= 2:
            return "Moderate"
        elif total >= 5:
            return "Moderate (Historical)"
        elif total > 0:
            return "Low"
        else:
            return "No data"

    def _get_most_recent_filing(self, filings: List[Dict]) -> Dict[str, str]:
        """Get details of most recent SC 13 filing."""
        if not filings:
            return {}

        sorted_filings = sorted(filings, key=lambda x: x.get('filingDate', ''), reverse=True)
        most_recent = sorted_filings[0]

        return {
            'form': most_recent.get('form', 'Unknown'),
            'date': most_recent.get('filingDate', 'Unknown'),
            'type': 'Activist (13D)' if '13D' in most_recent.get('form', '') else 'Passive (13G)'
        }

    def _generate_ownership_insights(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate insights about institutional ownership."""
        insights = []

        total = metrics.get('total_filings', 0)
        activist_count = metrics.get('activist_filings', 0)
        recent_activist = metrics.get('recent_activist_1yr', 0)
        trend = metrics.get('filing_trend', 'Unknown')

        # Activist investor insights (most important)
        if activist_count > 0:
            insights.append(f"⚠️ {activist_count} activist investor filing(s) detected (SC 13D)")
            if recent_activist > 0:
                insights.append(f"🔴 Recent activist activity: {recent_activist} filing(s) in past year")
                insights.append("Activist presence may indicate potential catalyst or pressure for change")

        # Institutional interest
        if total >= 10:
            insights.append(f"Strong institutional interest ({total} total SC 13 filings)")
        elif total >= 5:
            insights.append(f"Moderate institutional interest ({total} SC 13 filings)")
        elif total == 0:
            insights.append("No SC 13D/G filings - limited large institutional ownership data")

        # Trend analysis
        if trend == 'Increasing':
            insights.append("Increasing institutional filing activity - growing investor interest")
        elif trend == 'Decreasing':
            insights.append("Decreasing institutional activity - may indicate reduced interest")

        # Ratio analysis
        activist_ratio = metrics.get('activist_ratio', 0)
        if activist_ratio > 0.3 and total >= 3:
            insights.append(f"High proportion of activist filings ({activist_ratio:.0%}) - elevated activism risk")

        # Data quality note
        if total > 0:
            insights.append("ℹ️ Note: Detailed ownership percentages require SC 13 content parsing")

        return insights


class InstitutionalOwnershipAnalyzer:
    """
    Analyze detailed institutional ownership from SC 13D/G content.
    FULL IMPLEMENTATION - Parses actual filing content for ownership data.
    """

    def __init__(self):
        from src.parsers.filing_content_parser import SECFilingContentFetcher, SC13ContentParser
        self.fetcher = SECFilingContentFetcher()
        self.parser = SC13ContentParser(self.fetcher)

    def analyze_ownership_details(self, filings: List[Dict[str, Any]], cik: str, max_filings: int = 10) -> Dict[str, Any]:
        """
        Analyze specific ownership percentages and investor identities.
        Parses actual SC 13D/G content for detailed ownership data.

        Args:
            filings: List of SC 13D/G filings with accession numbers
            cik: Company CIK
            max_filings: Maximum number of recent filings to parse

        Returns:
            Detailed ownership analysis with investor names, percentages, and intents
        """
        # Get SC 13D/G filings
        sc13_filings = [f for f in filings if f.get('form') in [
            'SC 13D', 'SC 13D/A', 'SC 13G', 'SC 13G/A'
        ]]

        if not sc13_filings:
            return {
                'available': False,
                'error': 'No SC 13D/G filings found'
            }

        # Sort by date, most recent first
        sorted_filings = sorted(sc13_filings, key=lambda x: x.get('filingDate', ''), reverse=True)

        # Parse recent filings for detailed data
        ownership_records = []
        activist_investors = []
        total_ownership = 0.0

        logger.info(f"Analyzing {min(max_filings, len(sorted_filings))} recent SC 13D/G filings for ownership details")

        for filing in sorted_filings[:max_filings]:
            accession = filing.get('accessionNumber')
            form_type = filing.get('form')
            filing_date = filing.get('filingDate')

            if not accession:
                continue

            # Parse this SC 13
            parsed = self.parser.parse_sc13_ownership(cik, accession, form_type)

            if parsed.get('available'):
                record = {
                    'filing_date': filing_date,
                    'investor_name': parsed.get('investor_name'),
                    'ownership_percent': parsed.get('ownership_percent'),
                    'shares_owned': parsed.get('shares_owned'),
                    'is_activist': parsed.get('is_activist'),
                    'form_type': form_type
                }

                # Add activist details
                if parsed.get('is_activist'):
                    record['purpose'] = parsed.get('purpose', '')
                    record['activist_intent'] = parsed.get('activist_intent', 'Unknown')
                    activist_investors.append(record)

                ownership_records.append(record)
                total_ownership += parsed.get('ownership_percent', 0)

        # Identify largest shareholders
        ownership_records.sort(key=lambda x: x.get('ownership_percent', 0), reverse=True)

        # Calculate concentration
        top_3_ownership = sum([r.get('ownership_percent', 0) for r in ownership_records[:3]])

        return {
            'available': True,
            'filings_analyzed': len(ownership_records),
            'ownership_records': ownership_records,
            'largest_shareholders': ownership_records[:5],
            'activist_investors': activist_investors,
            'activist_count': len(activist_investors),
            'total_disclosed_ownership': total_ownership,
            'ownership_concentration': {
                'top_1': ownership_records[0].get('ownership_percent', 0) if ownership_records else 0,
                'top_3': top_3_ownership,
                'concentration_level': 'High' if top_3_ownership > 30 else 'Moderate' if top_3_ownership > 15 else 'Low'
            },
            'activist_details': [
                {
                    'investor': a['investor_name'],
                    'ownership': a['ownership_percent'],
                    'intent': a.get('activist_intent', 'Unknown'),
                    'filing_date': a['filing_date']
                }
                for a in activist_investors
            ],
            'summary': self._generate_ownership_summary(ownership_records, activist_investors, top_3_ownership)
        }

    def _generate_ownership_summary(self, records: List[Dict], activists: List[Dict], top_3: float) -> str:
        """Generate human-readable summary of ownership structure."""
        parts = []

        if records:
            parts.append(f"{len(records)} institutional holders disclosed")

            if records[0].get('ownership_percent'):
                parts.append(f"Largest: {records[0]['investor_name']} ({records[0]['ownership_percent']:.1f}%)")

        if activists:
            parts.append(f"{len(activists)} activist investor(s)")
            for a in activists[:2]:
                parts.append(f"  - {a['investor_name']}: {a.get('activist_intent', 'Unknown')}")

        parts.append(f"Top 3 own {top_3:.1f}% (concentration: {'High' if top_3 > 30 else 'Moderate' if top_3 > 15 else 'Low'})")

        return "; ".join(parts)

