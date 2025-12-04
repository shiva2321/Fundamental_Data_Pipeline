"""
Key Persons Parser
Extracts key company personnel information including executives, board members,
insider holdings, and major shareholders/holding companies.
"""
import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class KeyPersonsParser:
    """
    Parse SEC filings to extract comprehensive key persons data:
    - Executives (CEO, CFO, COO, etc.)
    - Board members (names, roles, independence status)
    - Insider holdings (ownership stakes, shares)
    - Holding companies and institutional investors
    """
    
    # Configuration constants for name validation
    MIN_NAME_LENGTH = 5
    MAX_NAME_LENGTH = 50
    # Context window size for independence detection (chars before/after name)
    INDEPENDENCE_CONTEXT_WINDOW = 50
    # Maximum length for purpose text truncation
    MAX_PURPOSE_LENGTH = 500

    def __init__(self):
        """Initialize the KeyPersonsParser with content parsers."""
        try:
            from src.parsers.filing_content_parser import SECFilingContentFetcher, Form4ContentParser, DEF14AContentParser, SC13ContentParser
            self.fetcher = SECFilingContentFetcher()
            self.form4_parser = Form4ContentParser(self.fetcher)
            self.def14a_parser = DEF14AContentParser(self.fetcher)
            self.sc13_parser = SC13ContentParser(self.fetcher)
            self.parsers_available = True
        except Exception as e:
            logger.warning(f"Could not initialize content parsers: {e}")
            self.parsers_available = False

    def parse_key_persons(self, filings: List[Dict[str, Any]], cik: str, 
                          max_form4: int = 100, max_def14a: int = 10,
                          max_sc13: int = 50) -> Dict[str, Any]:
        """
        Parse all filings to extract comprehensive key persons data.

        Args:
            filings: List of all filings
            cik: Company CIK
            max_form4: Maximum Form 4 filings to parse for insider data (increased to 100)
            max_def14a: Maximum DEF 14A filings to parse for executive/board data (increased to 10)
            max_sc13: Maximum SC 13D/G filings to parse for institutional data (increased to 50)

        Returns:
            Dictionary with key persons data including:
            - executives: List of key executives with titles
            - board_members: List of board directors
            - insider_holdings: Detailed insider ownership data
            - holding_companies: Major institutional shareholders
        """
        result = {
            'executives': [],
            'board_members': [],
            'insider_holdings': [],
            'holding_companies': [],
            'summary': {},
            'generated_at': datetime.utcnow().isoformat()
        }

        if not self.parsers_available:
            result['error'] = 'Content parsers not available'
            return result

        # Extract insider holdings from Form 4 FIRST (most reliable source of names)
        try:
            insider_data = self._extract_insider_holdings(filings, cik, max_form4)
            result['insider_holdings'] = insider_data.get('holdings', [])
        except Exception as e:
            logger.warning(f"Error extracting insider holdings: {e}")
            result['insider_holdings'] = []

        # Extract executives from insider data (Form 4 has clean names and titles)
        result['executives'] = self._extract_executives_from_insiders(result['insider_holdings'])

        # Extract holding companies from SC 13D/G
        try:
            holding_data = self._extract_holding_companies(filings, cik, max_sc13)
            result['holding_companies'] = holding_data.get('holders', [])
        except Exception as e:
            logger.warning(f"Error extracting holding companies: {e}")
            result['holding_companies'] = []

        # Extract board data from DEF 14A using content parser
        try:
            board_data = self._extract_board_from_def14a(filings, cik, max_def14a)
            result['board_members'] = board_data.get('board_members', [])
        except Exception as e:
            logger.warning(f"Error extracting board: {e}")
            result['board_members'] = []

        # Generate summary
        result['summary'] = self._generate_summary(result)

        return result

    def _extract_executives_from_insiders(self, insider_holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract executives from insider holdings data (Form 4 has clean names and titles).

        Returns:
            List of executives with proper names and titles
        """
        executives = []
        seen_names = set()

        # Executive title keywords to identify key executives
        exec_keywords = ['ceo', 'cfo', 'coo', 'cto', 'president', 'chairman', 'chief', 'executive officer', 'financial officer', 'operating officer']

        for holding in insider_holdings:
            name = holding.get('name', '').strip()
            title = holding.get('title', '').lower()

            # Skip if name is invalid or already seen
            if not name or name.lower() in ['unknown', 'not applicable', 'n/a']:
                continue
            if name.lower() in seen_names:
                continue

            # Check if title indicates this is an executive
            is_executive = any(keyword in title for keyword in exec_keywords)

            if is_executive:
                # Determine primary executive title
                exec_title = 'Executive'
                if 'ceo' in title or 'chief executive officer' in title:
                    exec_title = 'CEO'
                elif 'cfo' in title or 'chief financial officer' in title:
                    exec_title = 'CFO'
                elif 'coo' in title or 'chief operating officer' in title:
                    exec_title = 'COO'
                elif 'cto' in title or 'chief technology officer' in title:
                    exec_title = 'CTO'
                elif 'president' in title:
                    exec_title = 'President'
                elif 'chairman' in title:
                    exec_title = 'Chairman'
                elif 'general counsel' in title or 'chief legal' in title:
                    exec_title = 'General Counsel'

                seen_names.add(name.lower())
                executives.append({
                    'name': name,
                    'title': exec_title,
                    'full_title': holding.get('title', ''),
                    'source': 'Form 4',
                    'filing_date': holding.get('latest_filing_date', '')
                })

        # Sort by title importance
        title_priority = {'CEO': 0, 'President': 1, 'Chairman': 2, 'CFO': 3, 'COO': 4, 'CTO': 5, 'General Counsel': 6, 'Executive': 99}
        executives.sort(key=lambda x: title_priority.get(x['title'], 99))

        return executives

    def _extract_board_from_def14a(self, filings: List[Dict[str, Any]],
                                    cik: str, max_filings: int) -> Dict[str, Any]:
        """
        Extract board composition from DEF 14A using the content parser.

        Returns:
            Dictionary with board_members list
        """
        def14a_filings = [f for f in filings if f.get('form') in ['DEF 14A', 'DEFC14A', 'DEFA14A']]
        
        if not def14a_filings:
            return {'board_members': []}

        # Sort by date, most recent first
        sorted_filings = sorted(def14a_filings, key=lambda x: x.get('filingDate', ''), reverse=True)

        board_members = []

        logger.info(f"Parsing {min(max_filings, len(sorted_filings))} DEF 14A filings for board composition")

        for filing in sorted_filings[:max_filings]:
            accession = filing.get('accessionNumber')
            filing_date = filing.get('filingDate')
            
            if not accession:
                continue

            # Use the DEF14A content parser to get board composition
            try:
                parsed = self.def14a_parser.parse_def14a_content(cik, accession)

                if parsed.get('available'):
                    board_comp = parsed.get('board_composition', {})

                    total = board_comp.get('total_directors', 0)
                    independent = board_comp.get('independent_directors', 0)
                    ratio = board_comp.get('independence_ratio', 0)

                    if total > 0:
                        board_members.append({
                            'name': 'Board Summary',
                            'role': 'Board Statistics',
                            'total_directors': total,
                            'independent_directors': independent,
                            'independence_ratio': round(ratio, 2),
                            'source': 'DEF 14A',
                            'filing_date': filing_date
                        })
                        break  # Only need one good summary
            except Exception as e:
                logger.debug(f"Error parsing DEF 14A {accession}: {e}")
                continue

        return {'board_members': board_members}

    def _extract_insider_holdings(self, filings: List[Dict[str, Any]], 
                                   cik: str, max_filings: int) -> Dict[str, Any]:
        """
        Extract insider holdings from Form 4 filings.
        
        Returns:
            Dictionary with holdings list containing insider ownership data
        """
        form4_filings = [f for f in filings if f.get('form') == '4']
        
        if not form4_filings:
            return {'holdings': []}

        # Sort by date, most recent first
        sorted_filings = sorted(form4_filings, key=lambda x: x.get('filingDate', ''), reverse=True)

        # Track unique insiders and their holdings
        insider_holdings = {}  # name -> holding data

        logger.info(f"Parsing {min(max_filings, len(sorted_filings))} Form 4 filings for insider holdings")

        for filing in sorted_filings[:max_filings]:
            accession = filing.get('accessionNumber')
            filing_date = filing.get('filingDate')
            
            if not accession:
                continue

            # Parse the Form 4
            parsed = self.form4_parser.parse_form4_transactions(cik, accession)
            
            if not parsed.get('available'):
                continue

            insider_name = parsed.get('insider_name', 'Unknown')
            insider_title = parsed.get('insider_title', 'Unknown')

            # Get shares owned after transactions
            transactions = parsed.get('transactions', [])
            shares_owned = 0
            if transactions:
                # Get the most recent shares owned after transaction
                for trans in transactions:
                    shares_after = trans.get('shares_owned_after', 0)
                    if shares_after > 0:
                        shares_owned = shares_after
                        break

            # Update or create insider record (keep most recent data)
            if insider_name != 'Unknown':
                name_key = insider_name.lower().strip()
                if name_key not in insider_holdings:
                    # Calculate net transaction value
                    net_trans = parsed.get('net_transaction', {})
                    
                    insider_holdings[name_key] = {
                        'name': insider_name,
                        'title': insider_title,
                        'shares_owned': shares_owned,
                        'latest_filing_date': filing_date,
                        'net_buy_value': net_trans.get('buy_value', 0),
                        'net_sell_value': net_trans.get('sell_value', 0),
                        'net_shares': net_trans.get('shares', 0),
                        'transaction_count': 1,
                        'signal': parsed.get('signal', 'Neutral')
                    }
                else:
                    # Update existing record
                    existing = insider_holdings[name_key]
                    net_trans = parsed.get('net_transaction', {})
                    existing['net_buy_value'] += net_trans.get('buy_value', 0)
                    existing['net_sell_value'] += net_trans.get('sell_value', 0)
                    existing['net_shares'] += net_trans.get('shares', 0)
                    existing['transaction_count'] += 1
                    # Update shares owned if we have more recent data
                    if shares_owned > 0 and filing_date > existing.get('latest_filing_date', ''):
                        existing['shares_owned'] = shares_owned
                        existing['latest_filing_date'] = filing_date

        # Convert to list and sort by shares owned
        holdings_list = list(insider_holdings.values())
        holdings_list.sort(key=lambda x: x.get('shares_owned', 0), reverse=True)

        return {'holdings': holdings_list}

    def _extract_holding_companies(self, filings: List[Dict[str, Any]], 
                                    cik: str, max_filings: int) -> Dict[str, Any]:
        """
        Extract holding companies and institutional investors from SC 13D/G filings.
        
        Returns:
            Dictionary with holders list containing institutional ownership data
        """
        sc13_filings = [f for f in filings if f.get('form') in [
            'SC 13D', 'SC 13D/A', 'SC 13G', 'SC 13G/A'
        ]]
        
        if not sc13_filings:
            return {'holders': []}

        # Sort by date, most recent first
        sorted_filings = sorted(sc13_filings, key=lambda x: x.get('filingDate', ''), reverse=True)

        # Track unique holders
        holders = {}  # name -> holder data

        logger.info(f"Parsing {min(max_filings, len(sorted_filings))} SC 13D/G filings for holding companies")

        for filing in sorted_filings[:max_filings]:
            accession = filing.get('accessionNumber')
            form_type = filing.get('form')
            filing_date = filing.get('filingDate')
            
            if not accession:
                continue

            # Parse the SC 13D/G
            parsed = self.sc13_parser.parse_sc13_ownership(cik, accession, form_type)
            
            if not parsed.get('available'):
                continue

            investor_name = parsed.get('investor_name', 'Unknown Investor')
            ownership_percent = parsed.get('ownership_percent', 0)
            shares_owned = parsed.get('shares_owned', 0)
            is_activist = parsed.get('is_activist', False)
            activist_intent = parsed.get('activist_intent', '')
            purpose = parsed.get('purpose', '')

            # Skip invalid entries - must have a valid name and either ownership or shares data
            invalid_names = ['unknown investor', 'not applicable', 'not', 'n/a', 'none', 'see', 'item']
            if (investor_name.lower() in invalid_names or
                len(investor_name) < 3 or
                (ownership_percent == 0 and shares_owned == 0)):
                logger.debug(f"Skipping invalid institutional holder: {investor_name}")
                continue

            if investor_name != 'Unknown Investor':
                name_key = investor_name.lower().strip()
                # Keep the most recent filing for each holder
                if name_key not in holders or filing_date > holders[name_key].get('latest_filing_date', ''):
                    holders[name_key] = {
                        'name': investor_name,
                        'ownership_percent': ownership_percent,
                        'shares_owned': shares_owned,
                        'is_activist': is_activist,
                        'activist_intent': activist_intent if is_activist else None,
                        'purpose': purpose[:self.MAX_PURPOSE_LENGTH] if purpose else None,
                        'form_type': form_type,
                        'filing_type': 'Activist (13D)' if is_activist else 'Passive (13G)',
                        'latest_filing_date': filing_date
                    }

        # Convert to list and sort by ownership percentage
        holders_list = list(holders.values())
        holders_list.sort(key=lambda x: x.get('ownership_percent', 0), reverse=True)

        return {'holders': holders_list}

    def _generate_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a summary of key persons data."""
        executives = data.get('executives', [])
        board_members = data.get('board_members', [])
        insider_holdings = data.get('insider_holdings', [])
        holding_companies = data.get('holding_companies', [])

        # Find key executives
        ceo = next((e for e in executives if e.get('title') == 'CEO'), None)
        cfo = next((e for e in executives if e.get('title') == 'CFO'), None)
        chairman = next((e for e in executives if e.get('title') == 'Chairman'), None)

        # Calculate insider totals
        total_insider_shares = sum(h.get('shares_owned', 0) for h in insider_holdings)
        total_insider_buy = sum(h.get('net_buy_value', 0) for h in insider_holdings)
        total_insider_sell = sum(h.get('net_sell_value', 0) for h in insider_holdings)

        # Calculate institutional totals
        total_institutional_ownership = sum(h.get('ownership_percent', 0) for h in holding_companies)
        activist_count = sum(1 for h in holding_companies if h.get('is_activist'))

        # Board independence
        board_stats = next((b for b in board_members if b.get('role') == 'Board Statistics'), None)

        summary = {
            'ceo': {
                'name': ceo.get('name') if ceo else 'Not identified',
                'identified': ceo is not None
            },
            'cfo': {
                'name': cfo.get('name') if cfo else 'Not identified',
                'identified': cfo is not None
            },
            'chairman': {
                'name': chairman.get('name') if chairman else 'Not identified',
                'identified': chairman is not None
            },
            'executive_count': len(executives),
            'board_member_count': len([b for b in board_members if b.get('role') != 'Board Statistics']),
            'board_independence': {
                'total_directors': board_stats.get('total_directors') if board_stats else None,
                'independent_directors': board_stats.get('independent_directors') if board_stats else None,
                'independence_ratio': board_stats.get('independence_ratio') if board_stats else None
            },
            'insider_holdings': {
                'count': len(insider_holdings),
                'total_shares': total_insider_shares,
                'total_buy_value': total_insider_buy,
                'total_sell_value': total_insider_sell,
                'net_activity': 'Buying' if total_insider_buy > total_insider_sell else 'Selling' if total_insider_sell > total_insider_buy else 'Neutral'
            },
            'institutional_ownership': {
                'holder_count': len(holding_companies),
                'total_ownership_percent': round(total_institutional_ownership, 2),
                'activist_count': activist_count,
                'largest_holder': holding_companies[0].get('name') if holding_companies else None,
                'largest_stake': holding_companies[0].get('ownership_percent') if holding_companies else None
            }
        }

        return summary
