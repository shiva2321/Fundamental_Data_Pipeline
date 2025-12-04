"""Smoke test for KeyPersonsParser integration (no network).
Creates a KeyPersonsParser instance, replaces its fetcher/form4/sc13 parsers with simple mocks,
and runs parse_key_persons on a small set of fake filings.
"""
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from key_persons_parser import KeyPersonsParser

# Sample filings metadata
filings = [
    {'form': 'DEF 14A', 'accessionNumber': '0001-DEF', 'filingDate': '2025-01-01', 'cik': '0000001'},
    {'form': '4', 'accessionNumber': '0002-F4', 'filingDate': '2025-02-01', 'cik': '0000001'},
    {'form': 'SC 13D', 'accessionNumber': '0003-SC13', 'filingDate': '2025-03-01', 'cik': '0000001'},
]

# Sample HTML for DEF 14A
sample_def14a_html = '''
<html><body>
<h1>Proxy Statement</h1>
<p>Chief Executive Officer, John A. Smith</p>
<p>Chief Financial Officer, Mary K. Johnson</p>

<h2>Board of Directors</h2>
<ul>
<li>Alice Jones, Independent Director</li>
<li>Bob Brown, Director</li>
</ul>
</body></html>
'''

# Create parser and monkeypatch internal fetchers/parsers
parser = KeyPersonsParser()

# Replace fetcher to return sample HTML for the DEF 14A accession
class MockFetcher:
    def fetch_filing_content(self, cik, accession):
        if accession == '0001-DEF':
            return sample_def14a_html
        return ''

# Replace the form4_parser to return a deterministic parsed result
class MockForm4Parser:
    def parse_form4_transactions(self, cik, accession):
        return {
            'available': True,
            'insider_name': 'John A. Smith',
            'insider_title': 'CEO',
            'transactions': [
                {'date': '2025-02-01', 'type': 'purchase', 'shares': 1000, 'price_per_share': 10.0, 'total_value': 10000.0, 'shares_owned_after': 5000}
            ],
            'net_transaction': {'shares': 1000, 'buy_value': 10000.0, 'sell_value': 0, 'shares': 1000}
        }

# Replace the sc13 parser to return a deterministic parsed result
class MockSC13Parser:
    def parse_sc13_ownership(self, cik, accession, form_type):
        return {
            'available': True,
            'investor_name': 'Big Fund LP',
            'ownership_percent': 12.5,
            'shares_owned': 1500000,
            'purpose': 'Investment',
            'is_activist': False,
            'activist_intent': ''
        }

# Apply mocks
parser.fetcher = MockFetcher()
parser.form4_parser = MockForm4Parser()
parser.sc13_parser = MockSC13Parser()
parser.parsers_available = True

# Run parser
result = parser.parse_key_persons(filings, cik='0000001')
print(json.dumps(result, indent=2))

