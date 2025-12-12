"""
Simple SEC Data Analysis - Shows exactly what we get from SEC
"""
import logging
import json
import sys

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def show_sec_api_data():
    """Show what SEC API returns"""
    print("\n" + "="*80)
    print("PART 1: SEC EDGAR API DATA")
    print("="*80)

    from src.clients.sec_edgar_api_client import SECEdgarClient

    client = SECEdgarClient()
    cik = "0000320193"  # Apple

    print(f"\nTesting with Apple (CIK: {cik})\n")

    # Get company facts
    print("-"*80)
    print("A. Company Facts (Financial Metrics)")
    print("-"*80)

    facts = client.get_company_facts(cik)

    if facts:
        print(f"\nCompany: {facts.get('entityName')}")
        print(f"CIK: {facts.get('cik')}")

        us_gaap = facts.get('facts', {}).get('us-gaap', {})
        print(f"\nTotal US-GAAP Metrics: {len(us_gaap)}")

        # Show Revenue data structure
        if 'Revenues' in us_gaap:
            revenue = us_gaap['Revenues']
            usd = revenue.get('units', {}).get('USD', [])

            print(f"\nRevenue Data:")
            print(f"  Label: {revenue.get('label')}")
            print(f"  Description: {revenue.get('description', '')[:80]}...")
            print(f"  Data Points: {len(usd)}")

            if usd:
                # Show structure of one data point
                sample = usd[0]
                print(f"\n  Sample Data Point Structure:")
                for key, value in sample.items():
                    print(f"    {key}: {value}")

                # Show recent values
                recent = sorted(usd, key=lambda x: x.get('end', ''), reverse=True)[:3]
                print(f"\n  Recent Values:")
                for val in recent:
                    print(f"    {val['end']}: ${val['val']:,.0f} (form: {val.get('form', 'N/A')})")

    # Get submissions
    print("\n" + "-"*80)
    print("B. Company Submissions (Filing List)")
    print("-"*80)

    submissions = client.get_company_submissions(cik)

    if submissions:
        print(f"\nCompany: {submissions.get('name')}")
        print(f"Ticker: {submissions.get('tickers')}")
        print(f"Exchange: {submissions.get('exchanges')}")
        print(f"SIC: {submissions.get('sic')} - {submissions.get('sicDescription')}")

        filings = submissions.get('filings', {}).get('recent', {})
        total = len(filings.get('accessionNumber', []))
        print(f"\nTotal Filings: {total}")

        # Count by type
        from collections import Counter
        form_types = filings.get('form', [])
        counts = Counter(form_types)

        print(f"\nTop Filing Types:")
        for form, count in counts.most_common(10):
            print(f"  {form:15s}: {count:4d}")

        # Show sample filing structure
        if total > 0:
            print(f"\nSample Filing Structure (index 0):")
            for key in sorted(filings.keys()):
                if isinstance(filings[key], list) and len(filings[key]) > 0:
                    value = filings[key][0]
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"  {key:20s}: {value}")


def show_filing_content():
    """Show what raw filing content looks like"""
    print("\n" + "="*80)
    print("PART 2: RAW FILING CONTENT")
    print("="*80)

    from src.parsers.filing_content_parser import SECFilingContentFetcher

    fetcher = SECFilingContentFetcher()

    cik = "0001065280"  # Netflix

    # Try to get a recent 10-K
    print(f"\nFetching recent 10-K for Netflix (CIK: {cik})")

    # First get filing list to find a 10-K
    from src.clients.sec_edgar_api_client import SECEdgarClient
    client = SECEdgarClient()
    submissions = client.get_company_submissions(cik)

    if submissions:
        filings = submissions.get('filings', {}).get('recent', {})
        forms = filings.get('form', [])
        accessions = filings.get('accessionNumber', [])

        # Find first 10-K
        accession = None
        for i, form in enumerate(forms):
            if form == '10-K':
                accession = accessions[i]
                break

        if accession:
            print(f"Found 10-K: {accession}")

            content = fetcher.fetch_filing_content(cik, accession)

            if content:
                print(f"\nContent Retrieved:")
                print(f"  Length: {len(content):,} characters")
                print(f"  Size: {len(content) / 1024:.1f} KB")

                # Detect format
                if '<xml' in content.lower()[:500]:
                    fmt = "XML"
                elif '<html' in content.lower()[:500]:
                    fmt = "HTML"
                else:
                    fmt = "TEXT"

                print(f"  Format: {fmt}")

                # Show preview
                print(f"\n  Content Preview (first 500 chars):")
                print("  " + "-"*76)
                lines = content[:500].split('\n')
                for line in lines[:15]:
                    print(f"  {line[:74]}")
                print("  " + "-"*76)

                # If HTML, analyze structure
                if fmt == "HTML":
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')

                    headers = soup.find_all(['h1', 'h2', 'h3'])
                    tables = soup.find_all('table')
                    text = soup.get_text()

                    print(f"\n  HTML Structure:")
                    print(f"    Headers: {len(headers)}")
                    print(f"    Tables: {len(tables)}")
                    print(f"    Text length: {len(text):,} chars")

                    if headers:
                        print(f"\n    Sample Headers:")
                        for h in headers[:5]:
                            print(f"      - {h.name}: {h.get_text(strip=True)[:60]}")


def show_extraction_examples():
    """Show what our extractors produce"""
    print("\n" + "="*80)
    print("PART 3: EXTRACTION EXAMPLES")
    print("="*80)

    print("""
What We Extract from Filings:

1. Financial Metrics (from Company Facts API):
   {
     "Revenues": 123456789.00,
     "Assets": 987654321.00,
     "NetIncomeLoss": 12345678.00,
     ...
   }

2. Insider Transactions (from Form 4):
   {
     "insider_name": "John Smith",
     "title": "CEO",
     "transactions": [
       {
         "date": "2024-12-01",
         "type": "purchase",
         "shares": 10000,
         "price_per_share": 150.50,
         "total_value": 1505000.00
       }
     ]
   }

3. Company Mentions (from 10-K text):
   [
     {
       "name": "Amazon Services LLC",
       "count": 5,
       "confidence": 0.95,
       "relationship_type": "supplier"
     },
     {
       "name": "Microsoft Corporation",
       "count": 3,
       "confidence": 0.95,
       "relationship_type": "partner"
     }
   ]

4. Customer/Supplier Data:
   {
     "customers": [
       {
         "name": "US Government",
         "revenue_percent": 15.5,
         "confidence": 0.90
       }
     ],
     "suppliers": [
       {
         "name": "Taiwan Semiconductor Manufacturing Ltd.",
         "confidence": 0.85
       }
     ]
   }
""")


def show_filing_viewer_options():
    """Show options for filing viewer"""
    print("\n" + "="*80)
    print("PART 4: FILING VIEWER OPTIONS")
    print("="*80)

    print("""
Current Situation:
==================
- SEC provides filings in HTML/XML format (NOT PDF)
- We fetch raw content via SEC EDGAR API
- Content includes: text, tables, images (as references)
- Size: typically 100KB - 10MB per filing

Filing Viewer Options:
======================

OPTION 1: HTML Viewer (RECOMMENDED - EASIEST)
----------------------------------------------
Technology: QWebEngineView (PySide6)
Pros:
  + Display raw HTML directly (no conversion)
  + Fast implementation (1-2 hours)
  + Preserves original formatting
  + Built-in navigation (links, anchors)

Cons:
  - Some images/links may not load
  - Less control over styling

Implementation:
  from PySide6.QtWebEngineWidgets import QWebEngineView
  
  viewer = QWebEngineView()
  viewer.setHtml(filing_content)


OPTION 2: Structured Section Viewer (BEST UX)
----------------------------------------------
Technology: QTreeView + QTextBrowser
Pros:
  + Best user experience
  + Navigate by sections (Item 1, 1A, 7, etc.)
  + Searchable and indexable
  + Can highlight key terms

Cons:
  - More complex (6-8 hours)
  - Need to parse sections

Implementation:
  1. Use SECFilingSectionParser to extract sections
  2. Show tree view on left (sections)
  3. Display section content on right
  4. Add search, bookmarks


OPTION 3: PDF Generation
----------------------------------------------
Technology: wkhtmltopdf or reportlab
Pros:
  + Professional PDF output
  + Printable
  + Offline viewing

Cons:
  - Conversion overhead (slow)
  - Large file sizes
  - Complex implementation (4-6 hours)


RECOMMENDATION:
===============
START WITH: Option 1 (HTML Viewer)
  - Quick to implement
  - Good enough for most users
  - Can enhance later

UPGRADE TO: Option 2 (Structured Viewer) if users need:
  - Better navigation
  - Section-based reading
  - Advanced search

What We Already Have:
=====================
+ Filing metadata (form type, date, CIK)
+ Raw HTML/XML content
+ Section parser (extracts Item 1, 1A, 7, etc.)
+ Company information
+ Extraction results

What We Need to Add:
====================
[ ] Filing viewer UI widget
[ ] Content display logic
[ ] Navigation system
[ ] Search functionality
[ ] Export options (optional)

Estimated Effort:
=================
Option 1 (HTML): 1-2 hours
Option 2 (Structured): 6-8 hours
Option 3 (PDF): 4-6 hours
""")


def main():
    print("""
================================================================================
               SEC EDGAR DATA ANALYSIS
                Understanding Our Data Sources
================================================================================
""")

    try:
        show_sec_api_data()
        show_filing_content()
        show_extraction_examples()
        show_filing_viewer_options()

        print("\n" + "="*80)
        print("ANALYSIS COMPLETE")
        print("="*80)

        print("""
KEY TAKEAWAYS:
==============
1. SEC API gives structured financial data (JSON)
2. Raw filings are HTML/XML (100KB-10MB each)
3. We already extract key data (customers, insiders, etc.)
4. Filing viewer: HTML display is easiest (1-2 hours)
5. Structured viewer would be better UX but takes longer

Next Steps:
===========
1. Review the output above
2. Decide which filing viewer option to implement
3. I can create the filing viewer widget for you
""")

    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)


if __name__ == "__main__":
    main()

