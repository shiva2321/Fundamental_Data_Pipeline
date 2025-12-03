"""
Fetches and manages company ticker data from SEC's official company tickers JSON file.
"""
import logging
import json
import requests
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os

logger = logging.getLogger("company_ticker_fetcher")

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
CACHE_FILE = "sec_company_tickers_cache.json"
CACHE_EXPIRY_DAYS = 7


class CompanyTickerFetcher:
    """
    Fetches and caches company ticker information from SEC.
    Provides search and lookup functionality for companies.
    """

    def __init__(self, cache_file: str = CACHE_FILE):
        """
        Initialize the ticker fetcher.

        Args:
            cache_file: Path to cache file for storing ticker data
        """
        self.cache_file = cache_file
        self.companies = []
        self.ticker_map = {}  # ticker -> company data
        self.cik_map = {}  # cik -> company data
        self.name_map = {}  # company name (lowercase) -> company data

        self._load_or_fetch()

    def _load_or_fetch(self):
        """Load from cache if fresh, otherwise fetch from SEC."""
        if self._is_cache_valid():
            logger.info("Loading company tickers from cache")
            self._load_from_cache()
        else:
            logger.info("Fetching company tickers from SEC")
            self._fetch_from_sec()
            self._save_to_cache()

        self._build_indexes()

    def _is_cache_valid(self) -> bool:
        """Check if cache file exists and is not expired."""
        if not os.path.exists(self.cache_file):
            return False

        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
                cache_date = datetime.fromisoformat(data.get('cached_at', ''))
                expiry_date = cache_date + timedelta(days=CACHE_EXPIRY_DAYS)
                return datetime.now() < expiry_date
        except (json.JSONDecodeError, ValueError, KeyError):
            return False

    def _load_from_cache(self):
        """Load company data from cache file."""
        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)
                self.companies = data.get('companies', [])
                logger.info(f"Loaded {len(self.companies)} companies from cache")
        except Exception as e:
            logger.error(f"Error loading from cache: {e}")
            self._fetch_from_sec()

    def _fetch_from_sec(self):
        """Fetch company ticker data from SEC."""
        try:
            headers = {
                'User-Agent': 'Company Fundamental Data Pipeline contact@example.com'
            }
            response = requests.get(SEC_TICKERS_URL, headers=headers, timeout=30)
            response.raise_for_status()

            data = response.json()

            # Convert the data structure to a more usable format
            self.companies = []
            for key, company in data.items():
                # Format CIK to 10 digits with leading zeros
                cik = str(company.get('cik_str', '')).zfill(10)

                company_data = {
                    'ticker': company.get('ticker', '').upper(),
                    'title': company.get('title', ''),
                    'cik': cik,
                    'cik_numeric': int(company.get('cik_str', 0))
                }
                self.companies.append(company_data)

            logger.info(f"Fetched {len(self.companies)} companies from SEC")

        except Exception as e:
            logger.error(f"Error fetching from SEC: {e}")
            raise

    def _save_to_cache(self):
        """Save company data to cache file."""
        try:
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'companies': self.companies
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            logger.info(f"Saved {len(self.companies)} companies to cache")
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")

    def _build_indexes(self):
        """Build lookup indexes for fast searching."""
        self.ticker_map = {}
        self.cik_map = {}
        self.name_map = {}

        for company in self.companies:
            ticker = company['ticker'].upper()
            cik = company['cik']
            name = company['title'].lower()

            self.ticker_map[ticker] = company
            self.cik_map[cik] = company
            self.name_map[name] = company

    def get_by_ticker(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get company data by ticker symbol.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            Company data dictionary or None
        """
        return self.ticker_map.get(ticker.upper())

    def get_by_cik(self, cik: str) -> Optional[Dict[str, Any]]:
        """
        Get company data by CIK.

        Args:
            cik: Company CIK (can be with or without leading zeros)

        Returns:
            Company data dictionary or None
        """
        # Try both formatted and unformatted CIK
        formatted_cik = str(cik).zfill(10)
        return self.cik_map.get(formatted_cik) or self.cik_map.get(cik)

    def search_by_name(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for companies by name (partial match).

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching company data dictionaries
        """
        query_lower = query.lower()
        results = []

        for company in self.companies:
            if query_lower in company['title'].lower():
                results.append(company)
                if len(results) >= limit:
                    break

        return results

    def get_all_tickers(self) -> List[str]:
        """Get list of all ticker symbols."""
        return sorted([c['ticker'] for c in self.companies if c['ticker']])

    def get_all_companies(self) -> List[Dict[str, Any]]:
        """Get list of all companies."""
        return self.companies.copy()

    def refresh_data(self):
        """Force refresh data from SEC."""
        logger.info("Force refreshing company ticker data")
        self._fetch_from_sec()
        self._save_to_cache()
        self._build_indexes()

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the loaded data."""
        return {
            'total_companies': len(self.companies),
            'companies_with_ticker': len([c for c in self.companies if c['ticker']]),
            'cache_file': self.cache_file,
            'last_updated': self._get_cache_date()
        }

    def _get_cache_date(self) -> Optional[str]:
        """Get the date when cache was last updated."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    return data.get('cached_at')
        except:
            pass
        return None

