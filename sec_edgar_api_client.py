"""
Client for fetching SEC filing data using the sec-edgar-api Python package
"""
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from sec_edgar_api import EdgarClient

logger = logging.getLogger("sec_edgar_api_client")


class SECEdgarClient:
    """
    Client for fetching SEC filing data from the EDGAR API
    """

    def __init__(self, user_agent: str = None, rate_limit: float = 0.1):
        """
        Initialize the SEC EDGAR API client

        Args:
            user_agent: User agent string for API calls (e.g., "name@email.com")
            rate_limit: Time to wait between API calls in seconds (default 0.1s)
        """
        self.user_agent = user_agent or "sec_profile_system@example.com"
        self.rate_limit = rate_limit
        self.client = EdgarClient(self.user_agent)

    def get_company_facts(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Get company facts data from the SEC EDGAR API

        Args:
            cik: Company CIK identifier

        Returns:
            Dictionary containing company facts or None if not found
        """
        try:
            # Format CIK by removing leading zeros
            formatted_cik = cik.lstrip('0')

            # Implement rate limiting
            time.sleep(self.rate_limit)

            # Query the API
            company_facts = self.client.get_company_facts(formatted_cik)

            if not company_facts:
                logger.warning(f"No company facts found for CIK {cik}")
                return None

            return company_facts

        except Exception as e:
            logger.error(f"Error fetching company facts for CIK {cik}: {e}")
            return None

    def get_company_submissions(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Get company submissions data from the SEC EDGAR API

        Args:
            cik: Company CIK identifier

        Returns:
            Dictionary containing company submissions or None if not found
        """
        try:
            # Format CIK by removing leading zeros
            formatted_cik = cik.lstrip('0')

            # Implement rate limiting
            time.sleep(self.rate_limit)

            # Query the API
            submissions = self.client.get_submissions(formatted_cik)

            if not submissions:
                logger.warning(f"No submissions found for CIK {cik}")
                return None

            return submissions

        except Exception as e:
            logger.error(f"Error fetching submissions for CIK {cik}: {e}")
            return None

    def get_company_filings(self, cik: str, limit: int = 1000) -> List[Dict[str, Any]]:
        """
        Get and process company filings from the SEC EDGAR API

        Args:
            cik: Company CIK identifier
            limit: Maximum number of filings to fetch

        Returns:
            List of standardized filing dictionaries
        """
        processed_filings = []

        # Get company facts
        facts = self.get_company_facts(cik)
        if not facts:
            return processed_filings

        # Get company submissions
        submissions = self.get_company_submissions(cik)
        if not submissions:
            return processed_filings

        # Process company facts data
        try:
            # Extract relevant financial metrics from facts
            facts_data = facts.get('facts', {})
            us_gaap = facts_data.get('us-gaap', {})

            # Map for common financial metrics
            metric_mappings = {
                'Revenue': ['Revenues', 'SalesRevenueNet', 'SalesRevenueGoodsNet'],
                'Assets': ['Assets', 'AssetsCurrent'],
                'Liabilities': ['Liabilities', 'LiabilitiesCurrent'],
                'StockholdersEquity': ['StockholdersEquity',
                                       'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'],
                'NetIncomeLoss': ['NetIncomeLoss', 'ProfitLoss', 'NetIncome'],
                'CashAndCashEquivalentsAtCarryingValue': ['CashAndCashEquivalentsAtCarryingValue', 'Cash'],
                'OperatingIncomeLoss': ['OperatingIncomeLoss'],
                'GrossProfit': ['GrossProfit'],
                'EarningsPerShareBasic': ['EarningsPerShareBasic'],
                'EarningsPerShareDiluted': ['EarningsPerShareDiluted'],
                'CommonStockSharesOutstanding': ['CommonStockSharesOutstanding']
            }

            # Extract recent filings from submissions
            recent_filings = []
            if 'filings' in submissions and 'recent' in submissions['filings']:
                for i, form in enumerate(submissions['filings']['recent'].get('form', [])):
                    if i >= limit:
                        break

                    filing_date = submissions['filings']['recent'].get('filingDate', [])[i]
                    filing_dict = {
                        'cik': cik,
                        'form': form,
                        'filingDate': filing_date,
                        'accessionNumber': submissions['filings']['recent'].get('accessionNumber', [])[i]
                    }
                    recent_filings.append(filing_dict)

            # Process financial data for each filing
            for filing in recent_filings:
                filing_date = filing['filingDate']
                filing_year = filing_date[:4]

                # Extract financial metrics for this filing date
                for metric, possible_keys in metric_mappings.items():
                    for key in possible_keys:
                        if key in us_gaap:
                            units = us_gaap[key].get('units', {})
                            # Get the appropriate unit (USD or pure number)
                            unit_key = 'USD' if 'USD' in units else 'pure' if 'pure' in units else None

                            if unit_key:
                                values = units[unit_key]
                                # Find the closest value to the filing date
                                closest_value = None
                                closest_date_diff = float('inf')

                                for value_data in values:
                                    end_date = value_data.get('end')
                                    if end_date and end_date.startswith(filing_year):
                                        date_diff = abs((datetime.fromisoformat(end_date) -
                                                         datetime.fromisoformat(filing_date)).days)
                                        if date_diff < closest_date_diff:
                                            closest_date_diff = date_diff
                                            closest_value = value_data.get('val')

                                if closest_value is not None:
                                    filing[metric] = closest_value
                                    break  # Found a value for this metric

                processed_filings.append(filing)

        except Exception as e:
            logger.error(f"Error processing filings for CIK {cik}: {e}")

        return processed_filings