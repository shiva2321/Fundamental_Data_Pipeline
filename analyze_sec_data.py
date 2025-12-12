"""
SEC EDGAR API Data Analysis Tool

This script demonstrates what data we get from:
1. SEC EDGAR API (via sec-edgar-api package)
2. Raw filing content (HTML/XML)
3. Parsed structured data

Use this to understand the data structure and develop better extraction logic.
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def analyze_sec_api_response():
    """
    Analyze what we get from SEC EDGAR API
    """
    print("\n" + "="*100)
    print("PART 1: SEC EDGAR API Response Analysis")
    print("="*100)

    from src.clients.sec_edgar_api_client import SECEdgarClient

    client = SECEdgarClient()

    # Test with Apple (AAPL)
    cik = "0000320193"

    print(f"\n1️⃣  Testing with CIK: {cik} (Apple Inc.)")

    # ==========================================
    # A. Company Facts API Response
    # ==========================================
    print("\n" + "-"*80)
    print("A. Company Facts API (Financial Metrics)")
    print("-"*80)

    facts = client.get_company_facts(cik)

    if facts:
        print(f"\n✅ Facts Structure:")
        print(f"   - entityName: {facts.get('entityName')}")
        print(f"   - cik: {facts.get('cik')}")

        # Check available taxonomies
        facts_data = facts.get('facts', {})
        print(f"\n   Available Taxonomies:")
        for taxonomy in facts_data.keys():
            print(f"     • {taxonomy}")

        # Analyze US-GAAP taxonomy (most common)
        us_gaap = facts_data.get('us-gaap', {})
        print(f"\n   US-GAAP Metrics ({len(us_gaap)} total):")

        # Show sample metrics
        sample_metrics = list(us_gaap.keys())[:10]
        for metric in sample_metrics:
            metric_data = us_gaap[metric]
            units = metric_data.get('units', {})

            # Count data points
            total_points = sum(len(values) for values in units.values())

            print(f"     • {metric}")
            print(f"       - Label: {metric_data.get('label', 'N/A')}")
            print(f"       - Description: {metric_data.get('description', 'N/A')[:60]}...")
            print(f"       - Units: {list(units.keys())}")
            print(f"       - Data points: {total_points}")

        # Deep dive into Revenue metric
        print(f"\n   Deep Dive: Revenue Metric")
        if 'Revenues' in us_gaap:
            revenue_data = us_gaap['Revenues']
            units = revenue_data.get('units', {})

            if 'USD' in units:
                usd_values = units['USD']
                print(f"     Found {len(usd_values)} revenue data points")

                # Show sample data point structure
                if usd_values:
                    sample = usd_values[0]
                    print(f"\n     Sample Data Point Structure:")
                    print(json.dumps(sample, indent=6))

                # Show most recent values
                recent = sorted(usd_values, key=lambda x: x.get('end', ''), reverse=True)[:5]
                print(f"\n     Most Recent Values:")
                for val in recent:
                    print(f"       {val['end']}: ${val['val']:,.0f} (form: {val.get('form', 'N/A')})")

    # ==========================================
    # B. Company Submissions API Response
    # ==========================================
    print("\n" + "-"*80)
    print("B. Company Submissions API (Filings List)")
    print("-"*80)

    submissions = client.get_company_submissions(cik)

    if submissions:
        print(f"\n✅ Submissions Structure:")
        print(f"   - cik: {submissions.get('cik')}")
        print(f"   - entityType: {submissions.get('entityType')}")
        print(f"   - sic: {submissions.get('sic')}")
        print(f"   - sicDescription: {submissions.get('sicDescription')}")
        print(f"   - name: {submissions.get('name')}")
        print(f"   - tickers: {submissions.get('tickers')}")
        print(f"   - exchanges: {submissions.get('exchanges')}")

        filings = submissions.get('filings', {}).get('recent', {})
        print(f"\n   Filings Data Structure:")
        print(f"     Keys: {list(filings.keys())}")

        # Show sample filing
        if 'accessionNumber' in filings and len(filings['accessionNumber']) > 0:
            idx = 0
            print(f"\n     Sample Filing (index {idx}):")
            for key in filings.keys():
                if isinstance(filings[key], list) and len(filings[key]) > idx:
                    print(f"       - {key}: {filings[key][idx]}")

        # Count filings by type
        form_types = filings.get('form', [])
        from collections import Counter
        form_counts = Counter(form_types)

        print(f"\n     Filings by Type (Top 10):")
        for form_type, count in form_counts.most_common(10):
            print(f"       {form_type:15s}: {count:4d} filings")

        print(f"\n     Total Filings: {len(form_types)}")


def analyze_filing_content():
    """
    Analyze raw filing content (HTML/XML)
    """
    print("\n" + "="*100)
    print("PART 2: Raw Filing Content Analysis")
    print("="*100)

    from src.parsers.filing_content_parser import SECFilingContentFetcher

    fetcher = SECFilingContentFetcher()

    # Test with a recent Apple 10-K
    cik = "0000320193"
    accession = "0000320193-24-000123"  # Recent filing

    print(f"\n2️⃣  Fetching Filing Content")
    print(f"   CIK: {cik}")
    print(f"   Accession: {accession}")

    content = fetcher.fetch_filing_content(cik, accession)

    if content:
        print(f"\n✅ Content Retrieved:")
        print(f"   - Length: {len(content):,} characters")
        print(f"   - Size: {len(content) / 1024:.1f} KB")

        # Detect format
        if '<xml' in content.lower() or '<?xml' in content.lower():
            format_type = "XML"
        elif '<html' in content.lower() or '<!doctype html' in content.lower():
            format_type = "HTML"
        else:
            format_type = "TEXT"

        print(f"   - Format: {format_type}")

        # Show first 1000 characters
        print(f"\n   First 1000 Characters:")
        print("   " + "-"*76)
        preview = content[:1000].replace('\n', '\n   ')
        print(f"   {preview}")
        print("   " + "-"*76)

        # Analyze structure for HTML
        if format_type == "HTML":
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(content, 'html.parser')

            print(f"\n   HTML Structure Analysis:")

            # Find sections
            sections = soup.find_all(['h1', 'h2', 'h3'])
            print(f"     - Headers found: {len(sections)}")

            if sections:
                print(f"     - Sample headers:")
                for section in sections[:10]:
                    text = section.get_text(strip=True)[:80]
                    print(f"       • {section.name}: {text}")

            # Find tables
            tables = soup.find_all('table')
            print(f"     - Tables found: {len(tables)}")

            # Text content
            text = soup.get_text()
            print(f"     - Text length: {len(text):,} characters")
            print(f"     - Paragraphs (approx): {text.count('\\n\\n')}")
    else:
        print(f"\n❌ Could not fetch content")


def analyze_parsed_data():
    """
    Analyze parsed structured data from various filing types
    """
    print("\n" + "="*100)
    print("PART 3: Parsed Structured Data Analysis")
    print("="*100)

    from src.parsers.filing_content_parser import (
        SECFilingContentFetcher,
        Form4ContentParser,
        DEF14AContentParser,
        SC13ContentParser
    )

    fetcher = SECFilingContentFetcher()

    # ==========================================
    # A. Form 4 (Insider Trading)
    # ==========================================
    print("\n" + "-"*80)
    print("A. Form 4 Parsing (Insider Trading)")
    print("-"*80)

    # Use Netflix Form 4
    cik = "0001065280"  # Netflix
    accession = "0001209191-24-000001"  # Sample Form 4

    print(f"\n   Testing Form 4 Parser")
    print(f"   CIK: {cik}, Accession: {accession}")

    form4_parser = Form4ContentParser(fetcher)
    form4_data = form4_parser.parse_form4_transactions(cik, accession)

    if form4_data.get('available'):
        print(f"\n   ✅ Form 4 Parsed Successfully:")
        print(f"      Insider: {form4_data.get('insider_name')}")
        print(f"      Title: {form4_data.get('insider_title')}")

        transactions = form4_data.get('transactions', [])
        print(f"      Transactions: {len(transactions)}")

        if transactions:
            print(f"\n      Sample Transaction:")
            print(json.dumps(transactions[0], indent=8))

        net_trans = form4_data.get('net_transaction', {})
        print(f"\n      Net Transaction:")
        print(f"        Shares: {net_trans.get('shares', 0):,}")
        print(f"        Value: ${net_trans.get('value', 0):,.2f}")
    else:
        print(f"\n   ⚠️  Form 4 not available or failed to parse")

    # ==========================================
    # B. DEF 14A (Proxy Statement)
    # ==========================================
    print("\n" + "-"*80)
    print("B. DEF 14A Parsing (Proxy Statement)")
    print("-"*80)

    def14a_parser = DEF14AContentParser(fetcher)

    # Try to parse a proxy
    def14a_data = def14a_parser.parse_def14a_content(cik, accession)

    if def14a_data.get('available'):
        print(f"\n   ✅ DEF 14A Parsed:")

        board = def14a_data.get('board_composition', {})
        print(f"      Board Composition:")
        print(f"        Total Directors: {board.get('total_directors', 0)}")
        print(f"        Independent: {board.get('independent_directors', 0)}")
        print(f"        Independence Ratio: {board.get('independence_ratio', 0):.1%}")

        compensation = def14a_data.get('executive_compensation', {})
        print(f"\n      Executive Compensation:")
        print(f"        Executives found: {len(compensation.get('executives', []))}")

    # ==========================================
    # C. SC 13D/G (Beneficial Ownership)
    # ==========================================
    print("\n" + "-"*80)
    print("C. SC 13D/G Parsing (Beneficial Ownership)")
    print("-"*80)

    sc13_parser = SC13ContentParser(fetcher)

    sc13_data = sc13_parser.parse_sc13_ownership(cik, accession)

    if sc13_data.get('available'):
        print(f"\n   ✅ SC 13D/G Parsed:")
        print(f"      Investor: {sc13_data.get('investor_name')}")
        print(f"      Shares Owned: {sc13_data.get('shares_owned', 0):,}")
        print(f"      Ownership %: {sc13_data.get('ownership_percent', 0):.2f}%")
        print(f"      Purpose: {sc13_data.get('purpose', 'N/A')[:100]}...")


def analyze_relationship_extraction():
    """
    Analyze relationship extraction from 10-K/10-Q
    """
    print("\n" + "="*100)
    print("PART 4: Relationship Extraction Analysis")
    print("="*100)

    from src.extractors.financial_relationships_extractor import FinancialRelationshipsExtractor
    from src.extractors.ner_company_extractor import FastCompanyExtractor
    from src.parsers.filing_content_parser import SECFilingContentFetcher

    fetcher = SECFilingContentFetcher()

    # Get a 10-K filing
    cik = "0001065280"  # Netflix
    accession = "0001065280-25-000008"  # 10-K

    print(f"\n4️⃣  Analyzing Relationship Extraction")
    print(f"   CIK: {cik}, Accession: {accession}")

    content = fetcher.fetch_filing_content(cik, accession)

    if content:
        print(f"\n   ✅ Filing Retrieved: {len(content):,} characters")

        # Extract customers
        financial_extractor = FinancialRelationshipsExtractor()
        customers = financial_extractor.extract_customers(content)

        print(f"\n   Customers Extracted: {len(customers)}")
        for customer in customers[:5]:
            print(f"     • {customer['name']}")
            print(f"       Revenue %: {customer.get('revenue_percent', 'N/A')}")
            print(f"       Confidence: {customer.get('confidence', 0):.2f}")

        # Extract suppliers
        suppliers = financial_extractor.extract_suppliers(content)

        print(f"\n   Suppliers Extracted: {len(suppliers)}")
        for supplier in suppliers[:5]:
            print(f"     • {supplier['name']}")
            print(f"       Confidence: {supplier.get('confidence', 0):.2f}")

        # Extract all company mentions
        ner_extractor = FastCompanyExtractor()
        companies = ner_extractor.extract_companies(content[:500000], min_mentions=2)

        print(f"\n   Company Mentions Extracted: {len(companies)}")
        for company in companies[:10]:
            print(f"     • {company['name']} (mentioned {company['count']} times)")
            if company.get('relationship_type'):
                print(f"       Type: {company['relationship_type']}")


def create_filing_viewer_demo():
    """
    Demo: What we'd need for a human-readable filing viewer
    """
    print("\n" + "="*100)
    print("PART 5: Filing Viewer Requirements")
    print("="*100)

    print("""
    5️⃣  What We Need for a Human-Readable Filing Viewer:
    
    Current State:
    ═══════════════
    • Raw HTML/XML content from SEC
    • Text is embedded with formatting tags
    • Tables are in HTML format
    • No native PDF from SEC (they only provide HTML/XML)
    
    What We Can Do:
    ═══════════════
    
    Option 1: HTML Viewer (EASIEST) ⭐⭐⭐⭐⭐
    ────────────────────────────────
    • Display raw HTML in QWebEngineView (PySide6)
    • Pros: Native format, no conversion needed
    • Cons: May have broken links, images
    • Effort: LOW (1-2 hours)
    
    Option 2: Formatted Text Viewer ⭐⭐⭐⭐
    ────────────────────────────────
    • Extract text with BeautifulSoup
    • Apply basic formatting (headers, paragraphs)
    • Display in QTextBrowser
    • Pros: Clean, fast, searchable
    • Cons: Loses some formatting
    • Effort: MEDIUM (2-3 hours)
    
    Option 3: PDF Generation ⭐⭐⭐
    ────────────────────────────────
    • Convert HTML to PDF (using reportlab or wkhtmltopdf)
    • Display PDF in Qt PDF viewer
    • Pros: Professional look, printable
    • Cons: Conversion overhead, large files
    • Effort: HIGH (4-6 hours)
    
    Option 4: Structured Viewer ⭐⭐⭐⭐⭐ (RECOMMENDED)
    ────────────────────────────────
    • Parse filing into sections (Item 1, Item 1A, etc.)
    • Show tree view of sections on left
    • Display section content on right
    • Add search, highlighting, bookmarks
    • Pros: Best UX, navigable, searchable
    • Cons: More complex
    • Effort: MEDIUM-HIGH (6-8 hours)
    
    Data We Already Have:
    ═══════════════════════
    ✅ Filing metadata (date, form type, accession)
    ✅ Raw HTML/XML content
    ✅ Section parser (can extract Item 1, 1A, 7, etc.)
    ✅ Company info (name, CIK, ticker)
    
    What We Need to Add:
    ════════════════════
    📋 Filing viewer UI widget
    📋 Content formatter/renderer
    📋 Navigation system (sections)
    📋 Search functionality
    📋 Export options (PDF, text)
    
    Recommended Approach:
    ═══════════════════════
    START WITH: Option 1 (HTML Viewer)
    • Quick to implement
    • See if users need more
    
    UPGRADE TO: Option 4 (Structured Viewer)
    • If users want better navigation
    • When we have time to polish UX
    """)


def main():
    """
    Main analysis function
    """
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║               SEC EDGAR API & Filing Data Analysis Tool                   ║
║                                                                            ║
║  Purpose: Understand what data we get from SEC and how to use it          ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)

    try:
        # Part 1: SEC API Response
        analyze_sec_api_response()

        # Part 2: Raw Filing Content
        analyze_filing_content()

        # Part 3: Parsed Structured Data
        analyze_parsed_data()

        # Part 4: Relationship Extraction
        analyze_relationship_extraction()

        # Part 5: Filing Viewer Demo
        create_filing_viewer_demo()

        print("\n" + "="*100)
        print("✅ Analysis Complete!")
        print("="*100)

        print("""
Summary:
════════
1. SEC API gives us:
   • Financial metrics in structured JSON
   • Complete filing lists with metadata
   • Data points mapped to XBRL taxonomy

2. Raw filings are:
   • HTML/XML format (not PDF)
   • 100KB-10MB in size
   • Contain all disclosure text
   • Include tables in HTML format

3. We parse to extract:
   • Insider transactions (Form 4)
   • Board composition (DEF 14A)
   • Ownership data (SC 13D/G)
   • Customer/supplier relationships
   • Company mentions

4. For filing viewer:
   • Easiest: Display HTML directly
   • Best: Structured section navigation
   • All data already available!
        """)

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        print(f"\n❌ Analysis failed: {e}")


if __name__ == "__main__":
    main()

