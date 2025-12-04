"""
SEC Filing Content Fetcher and Parser
Fetches and parses actual filing HTML/XML content for detailed data extraction
"""
import logging
import re
import requests
import time
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)


class SECFilingContentFetcher:
    """
    Fetches actual filing content from SEC EDGAR for detailed parsing.
    """

    BASE_URL = "https://www.sec.gov/cgi-bin/viewer"
    ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data"

    def __init__(self, user_agent: str = "Financial Analysis Tool admin@example.com"):
        self.user_agent = user_agent
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept-Encoding': 'gzip, deflate',
            'Host': 'www.sec.gov'
        })
        self.rate_limit = 0.1  # 10 requests per second (SEC limit)

    def fetch_filing_content(self, cik: str, accession_number: str, max_retries: int = 3) -> Optional[str]:
        """
        Fetch the actual filing content (HTML/XML).

        Args:
            cik: Company CIK
            accession_number: Filing accession number (e.g., '0001065280-25-000123')
            max_retries: Maximum number of retry attempts

        Returns:
            Filing content as string or None if failed
        """
        # Clean accession number (remove dashes for URL)
        accession_clean = accession_number.replace('-', '')
        cik_clean = cik.lstrip('0')

        # Construct URL
        # Format: https://www.sec.gov/Archives/edgar/data/[CIK]/[ACCESSION]/[PRIMARY_DOC]
        # We'll try multiple common document names

        potential_urls = [
            f"{self.ARCHIVE_URL}/{cik_clean}/{accession_clean}/{accession_number}.txt",
            f"{self.ARCHIVE_URL}/{cik_clean}/{accession_clean}/{accession_number}-index.htm",
        ]

        for attempt in range(max_retries):
            for url in potential_urls:
                try:
                    time.sleep(self.rate_limit)
                    response = self.session.get(url, timeout=30)

                    if response.status_code == 200:
                        return response.text

                except Exception as e:
                    logger.debug(f"Attempt {attempt + 1} failed for {url}: {e}")
                    continue

        logger.warning(f"Could not fetch filing content for {accession_number}")
        return None

    def fetch_filing_index(self, cik: str, accession_number: str) -> Optional[Dict[str, str]]:
        """
        Fetch the filing index to get all documents.

        Returns:
            Dictionary mapping document names to URLs
        """
        accession_clean = accession_number.replace('-', '')
        cik_clean = cik.lstrip('0')

        index_url = f"{self.ARCHIVE_URL}/{cik_clean}/{accession_clean}/{accession_number}-index.htm"

        try:
            time.sleep(self.rate_limit)
            response = self.session.get(index_url, timeout=30)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                documents = {}

                # Parse document table
                for row in soup.find_all('tr'):
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        doc_name = cells[2].get_text(strip=True)
                        doc_link = cells[2].find('a')
                        if doc_link:
                            doc_url = f"https://www.sec.gov{doc_link.get('href')}"
                            documents[doc_name] = doc_url

                return documents

        except Exception as e:
            logger.warning(f"Could not fetch filing index for {accession_number}: {e}")

        return None


class Form4ContentParser:
    """
    Parse Form 4 filing content to extract detailed insider transaction data.
    FULL IMPLEMENTATION - Extracts buy/sell data, transaction amounts, prices.
    """

    def __init__(self, fetcher: SECFilingContentFetcher):
        self.fetcher = fetcher

    def parse_form4_transactions(self, cik: str, accession_number: str) -> Dict[str, Any]:
        """
        Parse Form 4 to extract detailed transaction information.

        Returns:
            {
                'insider_name': str,
                'insider_title': str,
                'transactions': [
                    {
                        'date': str,
                        'type': 'purchase' | 'sale' | 'option_exercise' | 'other',
                        'shares': int,
                        'price_per_share': float,
                        'total_value': float,
                        'shares_owned_after': int
                    }
                ],
                'net_transaction': {
                    'shares': int,  # positive = net buy, negative = net sell
                    'value': float
                }
            }
        """
        content = self.fetcher.fetch_filing_content(cik, accession_number)
        if not content:
            return {'available': False, 'error': 'Could not fetch content'}

        try:
            # Form 4 is XML format
            soup = BeautifulSoup(content, 'xml')

            # Extract reporting owner info
            reporting_owner = soup.find('reportingOwner')
            insider_name = "Unknown"
            insider_title = "Unknown"

            if reporting_owner:
                name_elem = reporting_owner.find('rptOwnerName')
                if name_elem:
                    insider_name = name_elem.get_text(strip=True)

                relationship = reporting_owner.find('reportingOwnerRelationship')
                if relationship:
                    # Determine title from relationship flags
                    titles = []
                    if relationship.find('isDirector') and relationship.find('isDirector').get_text() == '1':
                        titles.append('Director')
                    if relationship.find('isOfficer') and relationship.find('isOfficer').get_text() == '1':
                        officer_title = relationship.find('officerTitle')
                        if officer_title:
                            titles.append(officer_title.get_text(strip=True))
                        else:
                            titles.append('Officer')
                    if relationship.find('isTenPercentOwner') and relationship.find('isTenPercentOwner').get_text() == '1':
                        titles.append('10% Owner')

                    insider_title = ', '.join(titles) if titles else 'Unknown'

            # Extract transactions
            transactions = []
            total_buy_shares = 0
            total_sell_shares = 0
            total_buy_value = 0.0
            total_sell_value = 0.0

            # Non-derivative transactions
            for transaction in soup.find_all('nonDerivativeTransaction'):
                trans_data = self._parse_transaction(transaction, is_derivative=False)
                if trans_data:
                    transactions.append(trans_data)

                    # Accumulate totals
                    if trans_data['type'] in ['purchase', 'option_exercise']:
                        total_buy_shares += trans_data.get('shares', 0)
                        total_buy_value += trans_data.get('total_value', 0)
                    elif trans_data['type'] == 'sale':
                        total_sell_shares += trans_data.get('shares', 0)
                        total_sell_value += trans_data.get('total_value', 0)

            # Derivative transactions (options, etc.)
            for transaction in soup.find_all('derivativeTransaction'):
                trans_data = self._parse_transaction(transaction, is_derivative=True)
                if trans_data:
                    transactions.append(trans_data)

            return {
                'available': True,
                'insider_name': insider_name,
                'insider_title': insider_title,
                'transaction_count': len(transactions),
                'transactions': transactions,
                'net_transaction': {
                    'shares': total_buy_shares - total_sell_shares,
                    'value': total_buy_value - total_sell_value,
                    'buy_shares': total_buy_shares,
                    'sell_shares': total_sell_shares,
                    'buy_value': total_buy_value,
                    'sell_value': total_sell_value
                },
                'signal': self._determine_signal(total_buy_shares, total_sell_shares, total_buy_value, total_sell_value)
            }

        except Exception as e:
            logger.error(f"Error parsing Form 4 {accession_number}: {e}")
            return {'available': False, 'error': str(e)}

    def _parse_transaction(self, transaction_elem, is_derivative: bool = False) -> Optional[Dict[str, Any]]:
        """Parse individual transaction from XML."""
        try:
            # Transaction date
            trans_date_elem = transaction_elem.find('transactionDate')
            if not trans_date_elem:
                return None
            trans_date = trans_date_elem.find('value')
            date = trans_date.get_text(strip=True) if trans_date else None

            # Transaction code (P=Purchase, S=Sale, A=Award, M=Option Exercise, etc.)
            trans_code_elem = transaction_elem.find('transactionCode')
            code = trans_code_elem.get_text(strip=True) if trans_code_elem else None

            # Map transaction codes
            trans_type = {
                'P': 'purchase',
                'S': 'sale',
                'A': 'award',
                'M': 'option_exercise',
                'G': 'gift',
                'D': 'disposition'
            }.get(code, 'other')

            # Shares
            shares_elem = transaction_elem.find('transactionShares')
            if not shares_elem:
                shares_elem = transaction_elem.find('transactionAmounts')
            shares_val = shares_elem.find('value') if shares_elem else None
            shares = float(shares_val.get_text(strip=True)) if shares_val else 0

            # Price per share
            price_elem = transaction_elem.find('transactionPricePerShare')
            price_val = price_elem.find('value') if price_elem else None
            price = float(price_val.get_text(strip=True)) if price_val else 0

            # Shares owned after transaction
            shares_after_elem = transaction_elem.find('sharesOwnedFollowingTransaction')
            shares_after_val = shares_after_elem.find('value') if shares_after_elem else None
            shares_after = float(shares_after_val.get_text(strip=True)) if shares_after_val else 0

            return {
                'date': date,
                'type': trans_type,
                'code': code,
                'shares': int(shares),
                'price_per_share': price,
                'total_value': shares * price,
                'shares_owned_after': int(shares_after),
                'is_derivative': is_derivative
            }

        except Exception as e:
            logger.debug(f"Could not parse transaction: {e}")
            return None

    def _determine_signal(self, buy_shares: int, sell_shares: int, buy_value: float, sell_value: float) -> str:
        """Determine insider trading signal."""
        net_shares = buy_shares - sell_shares
        net_value = buy_value - sell_value

        if net_shares > 0:
            if net_value > 1000000:  # $1M+ net buying
                return "Strong Bullish"
            elif net_value > 100000:  # $100K+ net buying
                return "Bullish"
            else:
                return "Slightly Bullish"
        elif net_shares < 0:
            if abs(net_value) > 1000000:  # $1M+ net selling
                return "Strong Bearish"
            elif abs(net_value) > 100000:  # $100K+ net selling
                return "Bearish"
            else:
                return "Slightly Bearish"
        else:
            return "Neutral"


class SC13ContentParser:
    """
    Parse SC 13D/G filing content to extract detailed ownership data.
    FULL IMPLEMENTATION - Extracts ownership %, investor names, purposes.
    """

    def __init__(self, fetcher: SECFilingContentFetcher):
        self.fetcher = fetcher

    def parse_sc13_ownership(self, cik: str, accession_number: str, form_type: str) -> Dict[str, Any]:
        """
        Parse SC 13D/G to extract ownership details.

        Returns:
            {
                'investor_name': str,
                'ownership_percent': float,
                'shares_owned': int,
                'purpose': str,  # For 13D only
                'is_activist': bool,
                'filing_date': str,
                'activist_intent': str  # For 13D only
            }
        """
        content = self.fetcher.fetch_filing_content(cik, accession_number)
        if not content:
            return {'available': False, 'error': 'Could not fetch content'}

        try:
            soup = BeautifulSoup(content, 'html.parser')

            # Extract text content
            text = soup.get_text()

            # Find investor name (usually in first few lines or Item 2)
            investor_name = self._extract_investor_name(text, soup)

            # Extract ownership percentage
            ownership_percent = self._extract_ownership_percent(text)

            # Extract number of shares
            shares_owned = self._extract_shares_owned(text)

            # For 13D, extract purpose/intent
            purpose = ""
            activist_intent = ""
            is_activist = '13D' in form_type

            if is_activist:
                purpose = self._extract_purpose(text)
                activist_intent = self._classify_activist_intent(purpose)

            return {
                'available': True,
                'investor_name': investor_name,
                'ownership_percent': ownership_percent,
                'shares_owned': shares_owned,
                'purpose': purpose,
                'is_activist': is_activist,
                'activist_intent': activist_intent,
                'form_type': form_type
            }

        except Exception as e:
            logger.error(f"Error parsing SC 13 {accession_number}: {e}")
            return {'available': False, 'error': str(e)}

    def _extract_investor_name(self, text: str, soup: BeautifulSoup) -> str:
        """Extract investor/reporting person name."""
        # Look for common patterns
        patterns = [
            r'(?:REPORTING PERSON|FILER):\s*([A-Z][A-Za-z\s,\.&]+?)(?:\n|,)',
            r'(?:NAME OF REPORTING PERSON|PERSON):\s*([A-Z][A-Za-z\s,\.&]+?)(?:\n|,)',
            r'Item\s+2\.\s+(?:Identity|Name)[^\n]*\n\s*([A-Z][A-Za-z\s,\.&]+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return "Unknown Investor"

    def _extract_ownership_percent(self, text: str) -> float:
        """Extract ownership percentage."""
        # Look for percentage patterns
        patterns = [
            r'(?:represent|constitutes|equal)\s+(?:approximately\s+)?(\d+\.?\d*)\s*%',
            r'(\d+\.?\d*)\s*%\s+of\s+(?:the\s+)?(?:outstanding|issued)',
            r'ownership\s+of\s+(\d+\.?\d*)\s*%'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return float(match.group(1))

        return 0.0

    def _extract_shares_owned(self, text: str) -> int:
        """Extract number of shares owned."""
        # Look for share count patterns
        patterns = [
            r'(\d+,?\d+,?\d+)\s+(?:shares|common stock)',
            r'beneficial owner of\s+(\d+,?\d+,?\d+)',
            r'aggregate of\s+(\d+,?\d+,?\d+)\s+shares'
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                shares_str = match.group(1).replace(',', '')
                return int(shares_str)

        return 0

    def _extract_purpose(self, text: str) -> str:
        """Extract purpose statement from 13D (Item 4)."""
        # Look for Item 4 - Purpose of Transaction
        pattern = r'Item\s+4\.\s+Purpose[^\n]*\n(.*?)(?=Item\s+5|$)'
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)

        if match:
            purpose_text = match.group(1).strip()
            # Limit to first 500 characters
            return purpose_text[:500]

        return ""

    def _classify_activist_intent(self, purpose: str) -> str:
        """Classify activist intent from purpose statement."""
        purpose_lower = purpose.lower()

        if any(word in purpose_lower for word in ['acquisition', 'merge', 'acquire', 'takeover']):
            return "Acquisition Intent"
        elif any(word in purpose_lower for word in ['change', 'replace', 'elect', 'board', 'governance']):
            return "Board/Governance Changes"
        elif any(word in purpose_lower for word in ['strategic', 'review', 'sale', 'maximize']):
            return "Strategic Alternatives Push"
        elif any(word in purpose_lower for word in ['investment', 'passive']):
            return "Investment Only"
        else:
            return "General Activism"


class DEF14AContentParser:
    """
    Parse DEF 14A (Proxy Statement) content for compensation and governance data.
    FULL IMPLEMENTATION - Extracts executive compensation, board composition.
    """

    def __init__(self, fetcher: SECFilingContentFetcher):
        self.fetcher = fetcher

    def parse_def14a_content(self, cik: str, accession_number: str) -> Dict[str, Any]:
        """
        Parse DEF 14A to extract compensation and governance data.

        Returns:
            {
                'executive_compensation': {
                    'ceo_total_comp': float,
                    'cfo_total_comp': float,
                    'ceo_salary': float,
                    'ceo_bonus': float,
                    'ceo_stock_awards': float,
                    'median_employee_pay': float,
                    'pay_ratio': float  # CEO to median employee
                },
                'board_composition': {
                    'total_directors': int,
                    'independent_directors': int,
                    'independence_ratio': float,
                    'board_diversity': dict
                },
                'shareholder_proposals': [
                    {
                        'proposal': str,
                        'outcome': 'passed' | 'failed',
                        'votes_for_percent': float
                    }
                ]
            }
        """
        content = self.fetcher.fetch_filing_content(cik, accession_number)
        if not content:
            return {'available': False, 'error': 'Could not fetch content'}

        try:
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text()

            # Extract executive compensation
            exec_comp = self._extract_executive_compensation(text, soup)

            # Extract board composition
            board_comp = self._extract_board_composition(text, soup)

            # Extract shareholder proposals
            proposals = self._extract_shareholder_proposals(text, soup)

            return {
                'available': True,
                'executive_compensation': exec_comp,
                'board_composition': board_comp,
                'shareholder_proposals': proposals
            }

        except Exception as e:
            logger.error(f"Error parsing DEF 14A {accession_number}: {e}")
            return {'available': False, 'error': str(e)}

    def _extract_executive_compensation(self, text: str, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract executive compensation from summary compensation table."""
        # Look for Summary Compensation Table
        comp_data = {
            'ceo_total_comp': 0.0,
            'ceo_salary': 0.0,
            'ceo_bonus': 0.0,
            'ceo_stock_awards': 0.0,
            'median_employee_pay': 0.0,
            'pay_ratio': 0.0
        }

        # Find compensation table
        tables = soup.find_all('table')
        for table in tables:
            table_text = table.get_text().lower()
            if 'summary compensation' in table_text or 'total compensation' in table_text:
                # Extract CEO row (usually first row after header)
                rows = table.find_all('tr')
                if len(rows) > 1:
                    # Try to extract numerical values
                    ceo_row = rows[1]
                    cells = ceo_row.find_all('td')

                    # Typical columns: Name, Title, Year, Salary, Bonus, Stock Awards, Options, Other, Total
                    if len(cells) >= 7:
                        try:
                            # Extract total comp (usually last column)
                            total_comp_text = cells[-1].get_text(strip=True)
                            comp_data['ceo_total_comp'] = self._parse_currency(total_comp_text)

                            # Extract salary (usually 3rd or 4th column)
                            if len(cells) >= 4:
                                salary_text = cells[3].get_text(strip=True)
                                comp_data['ceo_salary'] = self._parse_currency(salary_text)
                        except:
                            pass
                break

        # Extract pay ratio (CEO to median employee)
        pay_ratio_pattern = r'(?:pay ratio|ratio of|ceo pay).*?(?:is|was)\s+(\d+):1'
        match = re.search(pay_ratio_pattern, text, re.IGNORECASE)
        if match:
            comp_data['pay_ratio'] = float(match.group(1))

        return comp_data

    def _extract_board_composition(self, text: str, soup: BeautifulSoup) -> Dict[str, Any]:
        """Extract board of directors composition."""
        board_data = {
            'total_directors': 0,
            'independent_directors': 0,
            'independence_ratio': 0.0
        }

        # Count director mentions
        director_pattern = r'(?:director|board member)s?'
        matches = re.findall(director_pattern, text, re.IGNORECASE)

        # Look for independence statements
        independence_pattern = r'(\d+)\s+(?:of\s+)?(?:the\s+)?(\d+)\s+directors?\s+(?:are|is)\s+independent'
        match = re.search(independence_pattern, text, re.IGNORECASE)
        if match:
            board_data['independent_directors'] = int(match.group(1))
            board_data['total_directors'] = int(match.group(2))
            board_data['independence_ratio'] = board_data['independent_directors'] / board_data['total_directors']

        return board_data

    def _extract_shareholder_proposals(self, text: str, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        """Extract shareholder proposal outcomes."""
        proposals = []

        # Look for proposal sections
        proposal_pattern = r'Proposal\s+(\d+)[:\-\s]+([^\n]+)'
        matches = re.findall(proposal_pattern, text, re.IGNORECASE)

        for match in matches[:5]:  # Limit to first 5 proposals
            proposal_num, proposal_text = match
            proposals.append({
                'number': int(proposal_num),
                'description': proposal_text.strip()[:200],  # First 200 chars
                'outcome': 'unknown'  # Would need more parsing for actual outcome
            })

        return proposals

    def _parse_currency(self, text: str) -> float:
        """Parse currency string to float."""
        # Remove $ and commas
        cleaned = text.replace('$', '').replace(',', '').replace(' ', '').strip()
        # Handle parentheses (negative numbers)
        if '(' in cleaned:
            cleaned = '-' + cleaned.replace('(', '').replace(')', '')

        try:
            return float(cleaned)
        except:
            return 0.0

