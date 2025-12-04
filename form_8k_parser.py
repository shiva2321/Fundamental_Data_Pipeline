"""
8-K Filing Parser - Extract Material Events
Critical for AI analysis and risk assessment
"""
import logging
from typing import Dict, List, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class Form8KParser:
    """
    Parse 8-K filings to extract material events.
    8-K filings report material corporate events that occur between quarterly/annual reports.
    """

    # 8-K Item categories and their significance
    ITEM_CATEGORIES = {
        # Section 1: Corporate Events
        '1.01': {'desc': 'Entry into Material Agreement', 'category': 'corporate', 'sentiment': 'neutral'},
        '1.02': {'desc': 'Termination of Material Agreement', 'category': 'corporate', 'sentiment': 'negative'},
        '1.03': {'desc': 'Bankruptcy or Receivership', 'category': 'risk', 'sentiment': 'very_negative'},
        '1.04': {'desc': 'Mine Safety Disclosure', 'category': 'compliance', 'sentiment': 'neutral'},

        # Section 2: Financial Information
        '2.01': {'desc': 'Completion of Acquisition/Disposition', 'category': 'corporate', 'sentiment': 'neutral'},
        '2.02': {'desc': 'Results of Operations/Financial Condition', 'category': 'financial', 'sentiment': 'neutral'},
        '2.03': {'desc': 'Creation of Direct Financial Obligation', 'category': 'financial', 'sentiment': 'negative'},
        '2.04': {'desc': 'Triggering Events that Accelerate Direct Financial Obligation', 'category': 'risk', 'sentiment': 'very_negative'},
        '2.05': {'desc': 'Costs Associated with Exit/Disposal Activities', 'category': 'financial', 'sentiment': 'negative'},
        '2.06': {'desc': 'Material Impairments', 'category': 'financial', 'sentiment': 'very_negative'},

        # Section 3: Securities and Trading Markets
        '3.01': {'desc': 'Notice of Delisting', 'category': 'risk', 'sentiment': 'very_negative'},
        '3.02': {'desc': 'Unregistered Sales of Equity Securities', 'category': 'financial', 'sentiment': 'neutral'},
        '3.03': {'desc': 'Material Modification to Rights of Security Holders', 'category': 'governance', 'sentiment': 'negative'},

        # Section 4: Matters Related to Accountants
        '4.01': {'desc': 'Changes in Auditor', 'category': 'risk', 'sentiment': 'negative'},
        '4.02': {'desc': 'Non-Reliance on Previously Issued Financial Statements', 'category': 'risk', 'sentiment': 'very_negative'},

        # Section 5: Corporate Governance and Management
        '5.01': {'desc': 'Changes in Control', 'category': 'governance', 'sentiment': 'neutral'},
        '5.02': {'desc': 'Departure/Election of Directors or Officers', 'category': 'management', 'sentiment': 'negative'},
        '5.03': {'desc': 'Amendments to Charter/Bylaws', 'category': 'governance', 'sentiment': 'neutral'},
        '5.04': {'desc': 'Temporary Suspension of Trading', 'category': 'risk', 'sentiment': 'negative'},
        '5.05': {'desc': 'Amendments to Code of Ethics', 'category': 'governance', 'sentiment': 'neutral'},
        '5.06': {'desc': 'Change in Shell Company Status', 'category': 'corporate', 'sentiment': 'neutral'},
        '5.07': {'desc': 'Submission of Matters to Vote', 'category': 'governance', 'sentiment': 'neutral'},
        '5.08': {'desc': 'Shareholder Director Nominations', 'category': 'governance', 'sentiment': 'neutral'},

        # Section 6: Asset-Backed Securities (less common)

        # Section 7: Regulation FD
        '7.01': {'desc': 'Regulation FD Disclosure', 'category': 'disclosure', 'sentiment': 'neutral'},

        # Section 8: Other Events
        '8.01': {'desc': 'Other Events', 'category': 'other', 'sentiment': 'neutral'},

        # Section 9: Financial Statements and Exhibits
        '9.01': {'desc': 'Financial Statements and Exhibits', 'category': 'disclosure', 'sentiment': 'neutral'},
    }

    def parse_8k_filings(self, filings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Parse all 8-K filings and extract material events.

        Args:
            filings: List of all filings (will filter for 8-K)

        Returns:
            Dictionary with material events analysis
        """
        # Filter for 8-K filings
        eight_k_filings = [f for f in filings if f.get('form') == '8-K']

        if not eight_k_filings:
            return {
                'total_8k_count': 0,
                'events': [],
                'recent_events': [],
                'risk_flags': [],
                'positive_catalysts': [],
                'event_frequency': {}
            }

        logger.info(f"Parsing {len(eight_k_filings)} 8-K filings")

        # Extract events
        events = []
        for filing in eight_k_filings:
            filing_date = filing.get('filingDate')
            accession = filing.get('accessionNumber')

            # Try to extract items from filing
            # Note: In real implementation, would parse actual filing content
            # For now, we'll track the filings and basic metadata
            event = {
                'filing_date': filing_date,
                'accession_number': accession,
                'form': '8-K',
                # These would be extracted from actual filing content:
                # 'items': extracted_items,
                # 'description': extracted_description
            }
            events.append(event)

        # Analyze events
        recent_cutoff = (datetime.now() - timedelta(days=90)).isoformat()[:10]
        recent_events = [e for e in events if e['filing_date'] >= recent_cutoff]

        # Count event frequency by month
        event_frequency = self._calculate_event_frequency(events)

        # Identify patterns
        risk_flags = self._identify_risk_flags(events, recent_events)
        positive_catalysts = self._identify_positive_catalysts(events, recent_events)

        return {
            'total_8k_count': len(events),
            'events': events[-50:],  # Keep last 50 events
            'recent_events': recent_events,
            'recent_count': len(recent_events),
            'risk_flags': risk_flags,
            'positive_catalysts': positive_catalysts,
            'event_frequency': event_frequency,
            'avg_events_per_quarter': self._calculate_avg_frequency(event_frequency)
        }

    def _calculate_event_frequency(self, events: List[Dict]) -> Dict[str, int]:
        """Calculate number of 8-K filings per month."""
        frequency = {}

        for event in events:
            filing_date = event.get('filing_date', '')
            if filing_date:
                year_month = filing_date[:7]  # YYYY-MM
                frequency[year_month] = frequency.get(year_month, 0) + 1

        return dict(sorted(frequency.items(), reverse=True)[:24])  # Last 24 months

    def _calculate_avg_frequency(self, frequency: Dict[str, int]) -> float:
        """Calculate average events per quarter."""
        if not frequency:
            return 0.0

        # Get last 12 months
        recent_months = list(frequency.values())[:12]
        if not recent_months:
            return 0.0

        # Calculate quarterly average
        total = sum(recent_months)
        quarters = len(recent_months) / 3
        return round(total / quarters if quarters > 0 else 0, 1)

    def _identify_risk_flags(self, all_events: List[Dict], recent_events: List[Dict]) -> List[str]:
        """Identify risk flags from 8-K patterns."""
        flags = []

        # High frequency of 8-Ks
        if len(recent_events) > 10:
            flags.append(f"High 8-K frequency: {len(recent_events)} filings in last 90 days (unusual)")

        # Multiple 8-Ks in short period
        if len(recent_events) >= 3:
            # Check if clustered
            dates = sorted([e['filing_date'] for e in recent_events])
            if len(dates) >= 3:
                # Check if 3+ filings in 30 days
                for i in range(len(dates) - 2):
                    date1 = datetime.fromisoformat(dates[i])
                    date3 = datetime.fromisoformat(dates[i+2])
                    if (date3 - date1).days <= 30:
                        flags.append(f"Clustered 8-K filings: 3+ filings within 30 days (potential instability)")
                        break

        # Pattern: Many 8-Ks followed by quiet period
        if len(all_events) > 10:
            # Check recent vs historical
            historical_cutoff = (datetime.now() - timedelta(days=365)).isoformat()[:10]
            historical_events = [e for e in all_events if e['filing_date'] < historical_cutoff and e['filing_date'] >= (datetime.now() - timedelta(days=730)).isoformat()[:10]]

            if len(historical_events) > len(recent_events) * 2:
                flags.append("Decreased 8-K activity (may indicate reduced transparency)")

        return flags

    def _identify_positive_catalysts(self, all_events: List[Dict], recent_events: List[Dict]) -> List[str]:
        """Identify positive catalysts from 8-K patterns."""
        catalysts = []

        # Moderate activity = good transparency
        if 3 <= len(recent_events) <= 8:
            catalysts.append("Consistent disclosure activity (good transparency)")

        # Regular quarterly 8-Ks (earnings)
        if len(recent_events) >= 2:
            # This would be enhanced with actual item parsing
            # For now, just note consistent reporting
            frequency = len(all_events) / max((datetime.now() - datetime.fromisoformat(min([e['filing_date'] for e in all_events]))).days / 365, 1)
            if 4 <= frequency <= 12:
                catalysts.append(f"Regular reporting pattern ({frequency:.1f} filings/year)")

        return catalysts


def extract_item_numbers(filing_content: str) -> List[str]:
    """
    Extract Item numbers from 8-K filing content.
    This would parse the actual filing text to find Item declarations.

    Note: Full implementation would require parsing the actual filing HTML/text
    """
    import re

    items = []
    # Pattern: "Item 1.01" or "Item 5.02" etc.
    pattern = r'Item\s+(\d\.\d{2})'
    matches = re.findall(pattern, filing_content)

    return list(set(matches))  # Unique items


def categorize_event(item_number: str) -> Dict[str, str]:
    """
    Categorize an 8-K event by item number.

    Returns:
        Dictionary with description, category, and sentiment
    """
    parser = Form8KParser()
    return parser.ITEM_CATEGORIES.get(item_number, {
        'desc': 'Unknown Item',
        'category': 'unknown',
        'sentiment': 'neutral'
    })

