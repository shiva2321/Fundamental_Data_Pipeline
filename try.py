import requests
import json
import os
from datetime import datetime
import time
from collections import defaultdict


class SECFilingFetcher:
    def __init__(self, user_agent="MyCompany myemail@example.com"):
        """
        Initialize the SEC Filing Fetcher

        Args:
            user_agent: Your contact info (SEC requires this)
        """
        self.data_url = "https://data.sec.gov"
        self.archive_url = "https://www.sec.gov"
        self.headers = {
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate"
        }
        self.ticker_cik_map = None

    def load_ticker_cik_mapping(self):
        """Load the ticker to CIK mapping from SEC"""
        if self.ticker_cik_map is not None:
            return

        try:
            url = "https://www.sec.gov/files/company_tickers.json"
            headers = {
                "User-Agent": self.headers["User-Agent"],
                "Accept": "application/json"
            }
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                self.ticker_cik_map = {}
                for key, value in data.items():
                    ticker = value['ticker'].upper()
                    cik = str(value['cik_str']).zfill(10)
                    self.ticker_cik_map[ticker] = cik
                print(f"Loaded {len(self.ticker_cik_map)} ticker mappings")
            else:
                print(f"Error loading ticker mapping: {response.status_code}")
        except Exception as e:
            print(f"Exception loading ticker mapping: {e}")

    def get_cik(self, ticker):
        """Get CIK number from ticker symbol"""
        self.load_ticker_cik_mapping()

        if self.ticker_cik_map is None:
            print("Failed to load ticker mapping")
            return None

        ticker_upper = ticker.upper()
        return self.ticker_cik_map.get(ticker_upper)

    def get_all_filings(self, ticker):
        """
        Fetch ALL filings for a given ticker

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')

        Returns:
            Dictionary with form types as keys and list of filings as values
        """
        print(f"Fetching all filings for {ticker}...")

        cik = self.get_cik(ticker)
        if not cik:
            print(f"Could not find CIK for ticker {ticker}")
            return None

        print(f"CIK: {cik}")

        # Fetch submissions
        url = f"{self.data_url}/submissions/CIK{cik}.json"

        try:
            response = requests.get(url, headers=self.headers, timeout=30)

            if response.status_code != 200:
                print(f"Error fetching data: {response.status_code}")
                return None

            data = response.json()
            recent_filings = data.get('filings', {}).get('recent', {})

            if not recent_filings:
                print("No recent filings found")
                return None

            # Group filings by form type
            filings_by_type = defaultdict(list)

            for i in range(len(recent_filings.get('form', []))):
                form_type = recent_filings['form'][i]
                filing_info = {
                    'form': form_type,
                    'filingDate': recent_filings['filingDate'][i],
                    'accessionNumber': recent_filings['accessionNumber'][i],
                    'primaryDocument': recent_filings['primaryDocument'][i],
                    'reportDate': recent_filings['reportDate'][i]
                }
                filings_by_type[form_type].append(filing_info)

            return filings_by_type, cik

        except Exception as e:
            print(f"Exception fetching filings: {e}")
            return None

    def download_filing_text(self, cik, accession_number, save_dir):
        """Download the complete filing text (txt format)"""
        acc_no_clean = accession_number.replace('-', '')
        txt_url = f"{self.archive_url}/Archives/edgar/data/{cik.lstrip('0')}/{acc_no_clean}/{accession_number}.txt"

        try:
            response = requests.get(txt_url, headers=self.headers, timeout=30)

            if response.status_code == 200:
                filename = f"{accession_number}.txt"
                filepath = os.path.join(save_dir, filename)

                with open(filepath, 'wb') as f:
                    f.write(response.content)

                return filepath
            else:
                return None
        except Exception as e:
            print(f"  Error: {e}")
            return None

    def fetch_one_of_each_type(self, ticker, save_dir=None, form_types=None):
        """
        Fetch one filing of each type for a ticker

        Args:
            ticker: Stock ticker symbol
            save_dir: Directory to save files
            form_types: List of specific form types to fetch (None = all types)
        """
        if save_dir is None:
            save_dir = os.path.join("sec_filings", ticker.upper(), "sample_forms")

        os.makedirs(save_dir, exist_ok=True)

        # Get all filings grouped by type
        result = self.get_all_filings(ticker)

        if result is None:
            return

        filings_by_type, cik = result

        print(f"\nFound {len(filings_by_type)} different form types")
        print("=" * 80)

        # Count filings by type
        form_counts = {form_type: len(filings) for form_type, filings in filings_by_type.items()}

        # Save form counts summary
        summary_file = os.path.join(save_dir, "form_types_summary.json")
        with open(summary_file, 'w') as f:
            json.dump({
                'ticker': ticker,
                'cik': cik,
                'total_form_types': len(filings_by_type),
                'form_counts': form_counts
            }, f, indent=2)

        print(f"Form types summary saved to: {summary_file}\n")

        # Filter form types if specified
        if form_types:
            filings_by_type = {k: v for k, v in filings_by_type.items() if k in form_types}

        # Download one of each type
        success_count = 0
        total_types = len(filings_by_type)

        for idx, (form_type, filings) in enumerate(sorted(filings_by_type.items()), 1):
            # Get the most recent filing of this type
            most_recent = filings[0]

            print(
                f"[{idx}/{total_types}] {form_type:15} | Date: {most_recent['filingDate']} | Total: {len(filings):4} filings")

            # Create subdirectory for this form type
            form_dir = os.path.join(save_dir, form_type.replace('/', '_'))
            os.makedirs(form_dir, exist_ok=True)

            # Download the filing
            result = self.download_filing_text(
                cik,
                most_recent['accessionNumber'],
                form_dir
            )

            if result:
                print(f"  ✓ Downloaded: {os.path.basename(result)}")
                success_count += 1

                # Save metadata for this filing
                metadata_file = os.path.join(form_dir, "filing_info.json")
                with open(metadata_file, 'w') as f:
                    json.dump(most_recent, f, indent=2)
            else:
                print(f"  ✗ Failed to download")

            # Be respectful to SEC servers
            time.sleep(0.15)

        print("\n" + "=" * 80)
        print(f"✓ Download complete: {success_count}/{total_types} form types downloaded")
        print(f"✓ Files saved to: {save_dir}")

        return form_counts

    def fetch_specific_form_types(self, ticker, form_types, count_per_type=5, save_dir=None):
        """
        Fetch multiple filings of specific form types

        Args:
            ticker: Stock ticker symbol
            form_types: List of form types to fetch (e.g., ['10-K', '10-Q', '8-K'])
            count_per_type: Number of filings to download per type
            save_dir: Directory to save files
        """
        if save_dir is None:
            save_dir = os.path.join("sec_filings", ticker.upper(), "specific_forms")

        os.makedirs(save_dir, exist_ok=True)

        result = self.get_all_filings(ticker)

        if result is None:
            return

        filings_by_type, cik = result

        print(f"\nFetching specific form types: {', '.join(form_types)}")
        print("=" * 80)

        total_downloaded = 0

        for form_type in form_types:
            if form_type not in filings_by_type:
                print(f"\n{form_type}: Not found")
                continue

            filings = filings_by_type[form_type][:count_per_type]

            print(f"\n{form_type}: Downloading {len(filings)} filings")
            print("-" * 80)

            # Create subdirectory for this form type
            form_dir = os.path.join(save_dir, form_type.replace('/', '_'))
            os.makedirs(form_dir, exist_ok=True)

            for idx, filing in enumerate(filings, 1):
                print(f"  [{idx}/{len(filings)}] {filing['filingDate']} - {filing['accessionNumber']}")

                result = self.download_filing_text(
                    cik,
                    filing['accessionNumber'],
                    form_dir
                )

                if result:
                    print(f"    ✓ Downloaded")
                    total_downloaded += 1
                else:
                    print(f"    ✗ Failed")

                time.sleep(0.15)

            # Save metadata for all filings of this type
            metadata_file = os.path.join(form_dir, "filings_metadata.json")
            with open(metadata_file, 'w') as f:
                json.dump(filings, f, indent=2)

        print("\n" + "=" * 80)
        print(f"✓ Total downloaded: {total_downloaded} filings")
        print(f"✓ Files saved to: {save_dir}")


# Example usage
if __name__ == "__main__":
    # IMPORTANT: Replace with your actual contact info
    fetcher = SECFilingFetcher(user_agent="YourName your.email@example.com")

    ticker = "AAPL"

    # Option 1: Fetch ONE of EACH form type (to see what's available)
    print("=" * 80)
    print("OPTION 1: Fetching one of each form type for", ticker)
    print("=" * 80)
    form_counts = fetcher.fetch_one_of_each_type(ticker)

    print("\n\n")

    # Option 2: Fetch multiple filings of SPECIFIC form types
    print("=" * 80)
    print("OPTION 2: Fetching multiple filings of specific types")
    print("=" * 80)

    # Common important form types
    important_forms = ['10-K', '10-Q', '8-K', 'DEF 14A', '4', 'SC 13G']
    fetcher.fetch_specific_form_types(ticker, important_forms, count_per_type=3)

    print("\n\n")
    print("=" * 80)
    print("FORM TYPE REFERENCE:")
    print("=" * 80)
    print("10-K      : Annual report")
    print("10-Q      : Quarterly report")
    print("8-K       : Current report (major events)")
    print("DEF 14A   : Proxy statement")
    print("4         : Insider trading")
    print("3         : Initial insider ownership")
    print("SC 13G    : Beneficial ownership (>5%)")
    print("S-3       : Securities registration")
    print("8-A12B    : Registration of securities")
    print("144       : Notice of proposed sale of securities")
