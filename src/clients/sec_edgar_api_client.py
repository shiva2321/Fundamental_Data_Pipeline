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
        Uses automatic pagination to get ALL filings

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

            # Query the API with automatic pagination handling
            # handle_pagination=True (default) automatically fetches all paginated data
            submissions = self.client.get_submissions(formatted_cik, handle_pagination=True)

            if not submissions:
                logger.warning(f"No submissions found for CIK {cik}")
                return None

            # Log pagination info
            filings = submissions.get('filings', {})
            recent_count = len(filings.get('recent', {}).get('accessionNumber', []))
            logger.info(f"Retrieved submissions for CIK {cik}: {recent_count} filings (with pagination)")

            return submissions

        except Exception as e:
            logger.error(f"Error fetching submissions for CIK {cik}: {e}")
            return None

    def get_company_filings(self, cik: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get and process company filings from the SEC EDGAR API

        Args:
            cik: Company CIK identifier
            limit: Maximum number of filings to fetch (None = all available)

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

            # Map for common financial metrics with ALL possible SEC field names
            metric_mappings = {
                'Revenues': [
                    'Revenues',
                    'RevenueFromContractWithCustomerExcludingAssessedTax',
                    'RevenueFromContractWithCustomer',
                    'SalesRevenueNet',
                    'SalesRevenueGoodsNet',
                    'RevenuesNetOfInterestExpense',
                    'InterestAndDividendIncomeOperating',
                    'RegulatedAndUnregulatedOperatingRevenue',
                    'OperatingRevenue'
                ],
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

            # Extract ALL filings from submissions (including paginated data)
            all_filings = []
            if 'filings' in submissions and 'recent' in submissions['filings']:
                filing_forms = submissions['filings']['recent'].get('form', [])
                filing_dates = submissions['filings']['recent'].get('filingDate', [])
                report_dates = submissions['filings']['recent'].get('reportDate', [])
                accession_numbers = submissions['filings']['recent'].get('accessionNumber', [])

                # Process ALL filings (pagination already handled by sec-edgar-api)
                total_filings = len(filing_forms)
                logger.info(f"Processing {total_filings} total filings for CIK {cik}")

                # Determine how many filings to process (respect limit if provided)
                max_filings = total_filings if limit is None else min(limit, total_filings)

                for i in range(max_filings):
                    form_type = filing_forms[i]

                    # Create filing dict for ALL forms (not just 10-K/10-Q)
                    # This ensures we capture all filings for complete data
                    filing_dict = {
                        'cik': cik,
                        'form': form_type,
                        'filingDate': filing_dates[i],
                        'reportDate': report_dates[i] if i < len(report_dates) else filing_dates[i],
                        'accessionNumber': accession_numbers[i]
                    }
                    all_filings.append(filing_dict)

            logger.info(f"Created {len(all_filings)} filing records for CIK {cik}")


            # Process financial data for each filing
            for filing in all_filings:
                # Use report date for matching (more accurate than filing date)
                report_date = filing.get('reportDate', filing['filingDate'])
                form_type = filing.get('form', '')

                # Only extract financial data from 10-K and 10-Q forms (most reliable)
                if form_type not in ['10-K', '10-Q', '10-K/A', '10-Q/A']:
                    # Include filing but don't try to extract financial data
                    processed_filings.append(filing)
                    continue

                # Extract financial metrics for this filing date
                for metric, possible_keys in metric_mappings.items():
                    value_found = False

                    for key in possible_keys:
                        if value_found:
                            break

                        if key in us_gaap:
                            units = us_gaap[key].get('units', {})

                            # Get the appropriate unit (USD for monetary values, pure/shares for others)
                            unit_keys = ['USD'] if metric != 'CommonStockSharesOutstanding' else ['shares', 'pure']

                            for unit_key in unit_keys:
                                if unit_key not in units:
                                    continue

                                values = units[unit_key]

                                # Find exact match for report date first
                                exact_match = None
                                for value_data in values:
                                    end_date = value_data.get('end')
                                    if end_date == report_date:
                                        # Also check form type matches if available
                                        form = value_data.get('form')
                                        if form and form in ['10-K', '10-Q', '10-K/A', '10-Q/A']:
                                            exact_match = value_data.get('val')
                                            if exact_match is not None:
                                                filing[metric] = exact_match
                                                value_found = True
                                                logger.debug(f"Found {metric} = {exact_match} for {report_date} using {key}")
                                                break

                                # If exact match found, move to next metric
                                if value_found:
                                    break

                                # If no exact match, find closest date within same year
                                if not value_found:
                                    report_year = report_date[:4]
                                    closest_value = None
                                    closest_date_diff = float('inf')

                                    for value_data in values:
                                        end_date = value_data.get('end')
                                        if end_date and end_date.startswith(report_year):
                                            # Prefer values from 10-K/10-Q forms
                                            form = value_data.get('form')
                                            if form and form in ['10-K', '10-Q', '10-K/A', '10-Q/A']:
                                                date_diff = abs((datetime.fromisoformat(end_date) -
                                                               datetime.fromisoformat(report_date)).days)
                                                if date_diff < closest_date_diff:
                                                    closest_date_diff = date_diff
                                                    closest_value = value_data.get('val')

                                    if closest_value is not None and closest_date_diff <= 90:  # Within 90 days
                                        filing[metric] = closest_value
                                        value_found = True
                                        logger.debug(f"Found {metric} = {closest_value} for {report_date} using {key} (closest match)")
                                        break

                # Only include filings that have at least some financial data
                if any(key in filing for key in metric_mappings.keys()):
                    processed_filings.append(filing)
                else:
                    logger.debug(f"Skipping filing {filing['accessionNumber']} - no financial data found")

            logger.info(f"Successfully processed {len(processed_filings)} filings with financial data for CIK {cik}")

        except Exception as e:
            logger.exception(f"Error processing filings for CIK {cik}: {e}")

        return processed_filings

    def get_financial_metrics_timeseries(self, cik: str) -> Dict[str, Dict[str, float]]:
        """
        Extract financial metrics time series directly from SEC EDGAR API.
        Uses direct HTTP request for better reliability.

        Args:
            cik: Company CIK identifier

        Returns:
            Dictionary mapping metric names to {date: value} dictionaries
        """
        import requests

        result = {}

        try:
            # Pad CIK to 10 digits
            cik_padded = str(cik).lstrip('0').zfill(10)

            # Direct API call (proven to work better than sec-edgar-api package)
            url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik_padded}.json"

            headers = {
                'User-Agent': self.user_agent,
                'Accept-Encoding': 'gzip, deflate',
                'Host': 'data.sec.gov'
            }

            logger.info(f"Fetching company facts from SEC API for CIK {cik_padded}")

            # Rate limiting
            time.sleep(self.rate_limit)

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            company_name = data.get('entityName', 'Unknown')
            logger.info(f"Retrieved facts for: {company_name}")

            facts_data = data.get('facts', {})
            us_gaap = facts_data.get('us-gaap', {})


            # Comprehensive mapping of all possible revenue field names
            revenue_fields = [
                'Revenues',
                'RevenueFromContractWithCustomerExcludingAssessedTax',
                'RevenueFromContractWithCustomer',
                'SalesRevenueNet',
                'SalesRevenueGoodsNet',
                'RevenuesNetOfInterestExpense',
                'InterestAndDividendIncomeOperating',
                'RegulatedAndUnregulatedOperatingRevenue',
                'OperatingRevenue',
                'RevenueFromContractWithCustomerIncludingAssessedTax'
            ]

            # Mapping of standard metric names to all possible SEC field names
            metric_field_mappings = {
                'Revenues': revenue_fields,
                'Assets': ['Assets'],
                'Liabilities': ['Liabilities'],
                'StockholdersEquity': [
                    'StockholdersEquity',
                    'StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest'
                ],
                'NetIncomeLoss': ['NetIncomeLoss', 'ProfitLoss'],
                'CashAndCashEquivalentsAtCarryingValue': [
                    'CashAndCashEquivalentsAtCarryingValue',
                    'Cash',
                    'CashAndCashEquivalents'
                ],
                'OperatingIncomeLoss': ['OperatingIncomeLoss'],
                'GrossProfit': ['GrossProfit'],
                'EarningsPerShareBasic': ['EarningsPerShareBasic'],
                'EarningsPerShareDiluted': ['EarningsPerShareDiluted'],
                'CommonStockSharesOutstanding': ['CommonStockSharesOutstanding']
            }

            # Extract each metric
            for standard_name, possible_fields in metric_field_mappings.items():
                metric_data = {}
                field_found = None

                # Try each possible field name until we find data
                for field_name in possible_fields:
                    if field_name in us_gaap:
                        field_data = us_gaap[field_name]
                        units = field_data.get('units', {})

                        # Determine appropriate unit
                        if standard_name == 'CommonStockSharesOutstanding':
                            unit_key = 'shares' if 'shares' in units else 'pure' if 'pure' in units else None
                        else:
                            unit_key = 'USD' if 'USD' in units else None

                        if unit_key and unit_key in units:
                            values = units[unit_key]

                            # Filter for 10-K and 10-Q filings only (most reliable)
                            filtered_data = [
                                entry for entry in values
                                if entry.get('form') in ['10-K', '10-Q', '10-K/A', '10-Q/A']
                            ]

                            if filtered_data:
                                # Sort by end date (most recent first) and filed date
                                sorted_data = sorted(
                                    filtered_data,
                                    key=lambda x: (x.get('end', ''), x.get('filed', '')),
                                    reverse=True
                                )

                                # Get unique dates (in case of duplicates, keep most recent filing)
                                seen_dates = set()
                                for entry in sorted_data:
                                    end_date = entry.get('end')
                                    val = entry.get('val')

                                    if end_date and val is not None:
                                        if end_date not in seen_dates:
                                            seen_dates.add(end_date)
                                            metric_data[end_date] = val

                                if metric_data:
                                    field_found = field_name
                                    logger.info(f"Found {len(metric_data)} unique periods for {standard_name} using {field_name}")
                                    break

                if metric_data:
                    result[standard_name] = metric_data

                    # Log sample for revenue
                    if standard_name == 'Revenues' and metric_data:
                        sorted_dates = sorted(metric_data.keys(), reverse=True)[:3]
                        sample = [(date, metric_data[date]) for date in sorted_dates]
                        logger.info(f"Revenue sample (most recent): {sample}")
                else:
                    logger.warning(f"No data found for {standard_name}")

            logger.info(f"Successfully extracted {len(result)} metrics for CIK {cik_padded}")

        except requests.exceptions.RequestException as e:
            logger.error(f"HTTP error fetching company facts for CIK {cik}: {e}")
        except Exception as e:
            logger.exception(f"Error extracting financial metrics for CIK {cik}: {e}")

        return result
