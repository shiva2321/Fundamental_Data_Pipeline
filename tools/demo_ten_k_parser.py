"""Demo that exercises the 10-K/10-Q parser with mock filings."""
import json
from src.parsers.ten_k_parser import TenK10QParser


class DummyFetcher:
    """Return canned HTML/text content for each accession."""

    def __init__(self, content_map):
        self.content_map = content_map

    def fetch_filing_content(self, cik: str, accession_number: str) -> str:
        return self.content_map.get(accession_number, "")


SAMPLE_CONTENT = """
Item 1.
Business Overview: We manufacture widgets that power the future of energy.
Item 1A.
Risk Factors: Cyberattacks, litigation, recession risks, and regulatory changes may impact operations.
Item 7.
Management's Discussion and Analysis: Revenue grew 12% year-over-year; cash flow remains positive despite investments.
Item 7A.
Market Risk: Exposed to interest rate changes and commodity price swings.
Item 8.
Financial Statements and Supplementary Data: Includes audited statements and notes for FY2024.
"""

FILING_FIXTURES = [
    {
        "form": "10-K",
        "filingDate": "2025-03-01",
        "reportDate": "2024-12-31",
        "accessionNumber": "0000001-25-000001",
        "cik": "0000001"
    },
    {
        "form": "10-Q",
        "filingDate": "2025-05-05",
        "reportDate": "2025-03-31",
        "accessionNumber": "0000001-25-000002",
        "cik": "0000001"
    }
]

CONTENT_MAP = {
    "0000001-25-000001": SAMPLE_CONTENT,
    "0000001-25-000002": SAMPLE_CONTENT.replace("FY2024", "Q1 2025")
}


def main() -> None:
    fetcher = DummyFetcher(CONTENT_MAP)
    parser = TenK10QParser(fetcher)
    parsed = parser.parse_reports(FILING_FIXTURES, max_reports_per_form=2)

    print("=== Extracted 10-K/10-Q Narrative Summary ===")
    print(json.dumps(parsed, indent=2))


if __name__ == "__main__":
    main()
