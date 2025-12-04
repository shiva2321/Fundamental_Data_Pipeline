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
            from filing_content_parser import SECFilingContentFetcher, Form4ContentParser, DEF14AContentParser, SC13ContentParser
            self.fetcher = SECFilingContentFetcher()
            self.form4_parser = Form4ContentParser(self.fetcher)
            self.def14a_parser = DEF14AContentParser(self.fetcher)
            self.sc13_parser = SC13ContentParser(self.fetcher)
            self.parsers_available = True
        except Exception as e:
            logger.warning(f"Could not initialize content parsers: {e}")
            self.parsers_available = False

    def parse_key_persons(self, filings: List[Dict[str, Any]], cik: str, 
                          max_form4: int = 50, max_def14a: int = 3, 
                          max_sc13: int = 15) -> Dict[str, Any]:
        """
        Parse all filings to extract comprehensive key persons data.

        Args:
            filings: List of all filings
            cik: Company CIK
            max_form4: Maximum Form 4 filings to parse for insider data
            max_def14a: Maximum DEF 14A filings to parse for executive/board data
            max_sc13: Maximum SC 13D/G filings to parse for institutional data

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

        # Extract executives and board members from DEF 14A
        try:
            exec_board_data = self._extract_executives_and_board(filings, cik, max_def14a)
            result['executives'] = exec_board_data.get('executives', [])
            result['board_members'] = exec_board_data.get('board_members', [])
        except Exception as e:
            logger.warning(f"Error extracting executives/board: {e}")
            result['executives'] = []
            result['board_members'] = []

        # Extract insider holdings from Form 4
        try:
            insider_data = self._extract_insider_holdings(filings, cik, max_form4)
            result['insider_holdings'] = insider_data.get('holdings', [])
        except Exception as e:
            logger.warning(f"Error extracting insider holdings: {e}")
            result['insider_holdings'] = []

        # Extract holding companies from SC 13D/G
        try:
            holding_data = self._extract_holding_companies(filings, cik, max_sc13)
            result['holding_companies'] = holding_data.get('holders', [])
        except Exception as e:
            logger.warning(f"Error extracting holding companies: {e}")
            result['holding_companies'] = []

        # Generate summary
        result['summary'] = self._generate_summary(result)

        return result

    def _extract_executives_and_board(self, filings: List[Dict[str, Any]], 
                                       cik: str, max_filings: int) -> Dict[str, Any]:
        """
        Extract executives and board members from DEF 14A filings.
        
        Returns:
            Dictionary with executives and board_members lists
        """
        def14a_filings = [f for f in filings if f.get('form') in ['DEF 14A', 'DEFC14A', 'DEFA14A']]
        
        if not def14a_filings:
            return {'executives': [], 'board_members': []}

        # Sort by date, most recent first
        sorted_filings = sorted(def14a_filings, key=lambda x: x.get('filingDate', ''), reverse=True)

        executives = []
        board_members = []
        seen_executives = set()
        seen_directors = set()

        logger.info(f"Parsing {min(max_filings, len(sorted_filings))} DEF 14A filings for executives/board")

        for filing in sorted_filings[:max_filings]:
            accession = filing.get('accessionNumber')
            filing_date = filing.get('filingDate')
            
            if not accession:
                continue

            # Fetch and parse the DEF 14A content
            content = self.fetcher.fetch_filing_content(cik, accession)
            if not content:
                continue

            # Parse executives from content
            file_executives = self._parse_executives_from_content(content, filing_date)
            for exec_info in file_executives:
                exec_key = exec_info.get('name', '').lower().strip()
                if exec_key and exec_key not in seen_executives:
                    seen_executives.add(exec_key)
                    executives.append(exec_info)

            # Parse board members from content
            file_directors = self._parse_board_from_content(content, filing_date)
            for director_info in file_directors:
                dir_key = director_info.get('name', '').lower().strip()
                if dir_key and dir_key not in seen_directors:
                    seen_directors.add(dir_key)
                    board_members.append(director_info)

        return {
            'executives': executives,
            'board_members': board_members
        }

    def _parse_executives_from_content(self, content: str, filing_date: str) -> List[Dict[str, Any]]:
        """Parse executive names and titles from DEF 14A content."""
        from bs4 import BeautifulSoup
        
        executives = []
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text()

            # Common executive title patterns
            exec_patterns = [
                # CEO patterns
                (r'(?:chief\s+executive\s+officer|ceo)[,\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)', 'CEO'),
                (r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)[,\s]+(?:chief\s+executive\s+officer|ceo)', 'CEO'),
                # CFO patterns
                (r'(?:chief\s+financial\s+officer|cfo)[,\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)', 'CFO'),
                (r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)[,\s]+(?:chief\s+financial\s+officer|cfo)', 'CFO'),
                # COO patterns
                (r'(?:chief\s+operating\s+officer|coo)[,\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)', 'COO'),
                (r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)[,\s]+(?:chief\s+operating\s+officer|coo)', 'COO'),
                # CTO patterns
                (r'(?:chief\s+technology\s+officer|cto)[,\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)', 'CTO'),
                (r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)[,\s]+(?:chief\s+technology\s+officer|cto)', 'CTO'),
                # CLO/General Counsel patterns
                (r'(?:chief\s+legal\s+officer|general\s+counsel)[,\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)', 'General Counsel'),
                # President patterns
                (r'(?:president)[,\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)', 'President'),
                (r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)[,\s]+(?:president)', 'President'),
                # Chairman patterns
                (r'(?:chairman\s+of\s+the\s+board|chairman)[,\s]+([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)', 'Chairman'),
                (r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)[,\s]+(?:chairman)', 'Chairman'),
            ]

            seen_names = set()
            for pattern, title in exec_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                for name in matches:
                    name_clean = name.strip()
                    # Validate name (at least 2 words, reasonable length)
                    if self.MIN_NAME_LENGTH <= len(name_clean) <= self.MAX_NAME_LENGTH:
                        name_key = name_clean.lower()
                        if name_key not in seen_names:
                            seen_names.add(name_key)
                            executives.append({
                                'name': name_clean,
                                'title': title,
                                'source': 'DEF 14A',
                                'filing_date': filing_date
                            })

        except Exception as e:
            logger.debug(f"Error parsing executives from content: {e}")

        return executives

    def _parse_board_from_content(self, content: str, filing_date: str) -> List[Dict[str, Any]]:
        """Parse board of directors from DEF 14A content."""
        from bs4 import BeautifulSoup
        
        board_members = []
        
        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text()

            # Look for director section patterns
            director_section_pattern = r'(?:directors?|board\s+of\s+directors?)[^\n]*\n(.*?)(?:executive\s+compensation|proposal|$)'
            section_match = re.search(director_section_pattern, text, re.IGNORECASE | re.DOTALL)

            if section_match:
                section_text = section_match.group(1)
                
                # Pattern for director names with independence indicators
                director_patterns = [
                    # Name followed by independent indicator - captures independence status per director
                    (r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)\s*[,\s]+independent\s+director', True),
                    # Name as director (no independent qualifier)
                    (r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)\s*[,\s]+director', None),
                    # Name with committee mentions (committee membership often implies independence)
                    (r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+)\s*[,\s]+(?:audit|compensation|nominating)\s+committee', None),
                ]

                seen_names = set()
                for pattern, is_ind_from_pattern in director_patterns:
                    matches = re.findall(pattern, section_text, re.IGNORECASE)
                    for name in matches:
                        name_clean = name.strip()
                        if self.MIN_NAME_LENGTH <= len(name_clean) <= self.MAX_NAME_LENGTH:
                            name_key = name_clean.lower()
                            if name_key not in seen_names:
                                seen_names.add(name_key)
                                # Check independence: use pattern-derived status if available,
                                # otherwise look for "independent" near the specific name
                                if is_ind_from_pattern is not None:
                                    is_independent = is_ind_from_pattern
                                else:
                                    # Check if "independent" appears near this director's name
                                    name_pos = section_text.lower().find(name_clean.lower())
                                    if name_pos >= 0:
                                        context_start = max(0, name_pos - self.INDEPENDENCE_CONTEXT_WINDOW)
                                        context_end = min(len(section_text), name_pos + len(name_clean) + self.INDEPENDENCE_CONTEXT_WINDOW)
                                        context = section_text[context_start:context_end].lower()
                                        is_independent = 'independent' in context
                                    else:
                                        is_independent = None  # Unknown
                                
                                board_members.append({
                                    'name': name_clean,
                                    'role': 'Director',
                                    'is_independent': is_independent,
                                    'source': 'DEF 14A',
                                    'filing_date': filing_date
                                })

            # Also look for board independence statistics
            independence_pattern = r'(\d+)\s+(?:of\s+)?(?:the\s+)?(\d+)\s+directors?\s+(?:are|is)\s+independent'
            ind_match = re.search(independence_pattern, text, re.IGNORECASE)
            if ind_match:
                independent_count = int(ind_match.group(1))
                total_count = int(ind_match.group(2))
                # Add a summary director if no individual directors found
                if not board_members:
                    board_members.append({
                        'name': 'Board Summary',
                        'role': 'Board Statistics',
                        'total_directors': total_count,
                        'independent_directors': independent_count,
                        'independence_ratio': round(independent_count / total_count, 2) if total_count > 0 else 0,
                        'source': 'DEF 14A',
                        'filing_date': filing_date
                    })

        except Exception as e:
            logger.debug(f"Error parsing board from content: {e}")

        return board_members

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
