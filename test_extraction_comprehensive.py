"""
Comprehensive Extraction Test - Real Data

Tests HTML vs PDF extraction on actual filing sections that contain relationship data.
"""
import logging
import time
from pathlib import Path
import tempfile

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def comprehensive_test():
    """Comprehensive test with real data"""
    print("\n" + "="*80)
    print("COMPREHENSIVE EXTRACTION TEST: HTML vs PDF")
    print("="*80)

    # Test with Netflix 10-K
    ticker = "NFLX"
    cik = "0001065280"

    print(f"\nTesting with: {ticker} (CIK: {cik})")

    # Step 1: Get filing
    print("\n[1/5] Fetching 10-K filing...")
    from src.clients.sec_edgar_api_client import SECEdgarClient
    from src.parsers.filing_content_parser import SECFilingContentFetcher

    client = SECEdgarClient()
    submissions = client.get_company_submissions(cik)

    if not submissions:
        print("❌ Could not get submissions")
        return

    filings = submissions.get('filings', {}).get('recent', {})
    forms = filings.get('form', [])
    accessions = filings.get('accessionNumber', [])

    accession = None
    for i, form in enumerate(forms):
        if form == '10-K':
            accession = accessions[i]
            break

    if not accession:
        print("❌ No 10-K found")
        return

    print(f"   ✓ Found 10-K: {accession}")

    # Fetch content
    fetcher = SECFilingContentFetcher()
    content = fetcher.fetch_filing_content(cik, accession)

    if not content:
        print("❌ Could not fetch content")
        return

    print(f"   ✓ Content size: {len(content):,} chars ({len(content)/1024/1024:.1f} MB)")

    # Clean HTML
    if '<DOCUMENT>' in content:
        parts = content.split('<TEXT>')
        if len(parts) > 1:
            content = parts[1].split('</TEXT>')[0]

    # Step 2: Extract relevant sections (where customer/supplier data lives)
    print("\n[2/5] Extracting relevant sections...")
    from src.extractors.sec_section_parser import SECFilingSectionParser

    parser = SECFilingSectionParser()

    # Get business and risk sections (where relationships are mentioned)
    business = parser.extract_section(content, '10-K', 'business')
    risk = parser.extract_section(content, '10-K', 'risk_factors')

    test_content = ""
    if business:
        test_content += business + "\n\n"
        print(f"   ✓ Business section: {len(business):,} chars")
    if risk:
        test_content += risk
        print(f"   ✓ Risk factors: {len(risk):,} chars")

    if not test_content:
        print("   ⚠️  Could not extract sections, using first 500K chars")
        test_content = content[:500000]

    print(f"   ✓ Test content: {len(test_content):,} chars")

    # Step 3: HTML Extraction
    print("\n[3/5] HTML EXTRACTION (Current Method)")
    print("-" * 80)

    html_start = time.time()
    html_results = {
        'customers': [],
        'suppliers': [],
        'companies': []
    }

    try:
        from src.extractors.financial_relationships_extractor import FinancialRelationshipsExtractor
        from src.extractors.ner_company_extractor import FastCompanyExtractor

        extractor = FinancialRelationshipsExtractor()

        print("\n   Extracting customers...")
        html_results['customers'] = extractor.extract_customers(test_content)
        print(f"   ✓ Found {len(html_results['customers'])} customers")
        for c in html_results['customers'][:5]:
            pct = c.get('revenue_percent', 'N/A')
            print(f"      - {c['name']}: {pct}%")

        print("\n   Extracting suppliers...")
        html_results['suppliers'] = extractor.extract_suppliers(test_content)
        print(f"   ✓ Found {len(html_results['suppliers'])} suppliers")
        for s in html_results['suppliers'][:5]:
            print(f"      - {s['name']}")

        print("\n   Extracting company mentions...")
        ner = FastCompanyExtractor()
        html_results['companies'] = ner.extract_companies(test_content, min_mentions=2)
        print(f"   ✓ Found {len(html_results['companies'])} company mentions")
        for c in html_results['companies'][:5]:
            print(f"      - {c['name']} ({c['count']} mentions)")

    except Exception as e:
        logger.error(f"HTML extraction failed: {e}", exc_info=True)

    html_time = time.time() - html_start
    print(f"\n   ⏱️  Time: {html_time:.2f}s")

    # Step 4: PDF Extraction
    print("\n[4/5] PDF EXTRACTION")
    print("-" * 80)

    pdf_start = time.time()
    pdf_results = {
        'customers': [],
        'suppliers': [],
        'companies': [],
        'pdf_created': False,
        'text_extracted': False
    }

    try:
        print("\n   Creating PDF...")

        temp_dir = Path(tempfile.gettempdir()) / "sec_test"
        temp_dir.mkdir(exist_ok=True)

        html_file = temp_dir / "test.html"
        pdf_file = temp_dir / "test.pdf"

        # Write HTML
        with open(html_file, 'w', encoding='utf-8', errors='ignore') as f:
            # Add basic HTML structure
            html_doc = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>SEC Filing</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid black; padding: 5px; }}
                </style>
            </head>
            <body>
            {test_content}
            </body>
            </html>
            """
            f.write(html_doc)

        # Convert to PDF with reportlab (most reliable)
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            from bs4 import BeautifulSoup

            print("      Using reportlab...")

            # Extract clean text
            soup = BeautifulSoup(test_content, 'html.parser')
            text = soup.get_text()

            # Create PDF
            doc = SimpleDocTemplate(str(pdf_file), pagesize=letter,
                                  topMargin=inch, bottomMargin=inch)
            styles = getSampleStyleSheet()
            story = []

            # Split into paragraphs and add to story
            for para_text in text.split('\n\n'):
                if para_text.strip():
                    # Limit paragraph length
                    para_text = para_text[:2000]
                    try:
                        para = Paragraph(para_text, styles['Normal'])
                        story.append(para)
                        story.append(Spacer(1, 0.2*inch))
                    except:
                        pass  # Skip problematic paragraphs

                # Limit total paragraphs for speed
                if len(story) >= 500:
                    break

            doc.build(story)
            pdf_results['pdf_created'] = True
            print(f"      ✓ PDF created: {pdf_file.stat().st_size:,} bytes")

        except Exception as e:
            print(f"      ✗ PDF creation failed: {e}")
            pdf_file = None

        # Extract text from PDF
        if pdf_file and pdf_file.exists():
            print("\n   Extracting text from PDF...")

            try:
                import pdfplumber

                print("      Using pdfplumber...")
                text_parts = []

                with pdfplumber.open(str(pdf_file)) as pdf:
                    page_count = len(pdf.pages)
                    print(f"      PDF has {page_count} pages")

                    for i, page in enumerate(pdf.pages):
                        if i >= 50:  # Limit for speed
                            break
                        text = page.extract_text()
                        if text:
                            text_parts.append(text)

                pdf_text = '\n'.join(text_parts)
                pdf_results['text_extracted'] = True
                print(f"      ✓ Extracted {len(pdf_text):,} chars")

            except Exception as e:
                print(f"      ✗ Text extraction failed: {e}")
                pdf_text = None

            # Run extraction on PDF text
            if pdf_text:
                print("\n   Running extraction on PDF text...")

                try:
                    from src.extractors.financial_relationships_extractor import FinancialRelationshipsExtractor
                    from src.extractors.ner_company_extractor import FastCompanyExtractor

                    extractor = FinancialRelationshipsExtractor()

                    print("\n      Extracting customers...")
                    pdf_results['customers'] = extractor.extract_customers(pdf_text)
                    print(f"      ✓ Found {len(pdf_results['customers'])} customers")
                    for c in pdf_results['customers'][:5]:
                        pct = c.get('revenue_percent', 'N/A')
                        print(f"         - {c['name']}: {pct}%")

                    print("\n      Extracting suppliers...")
                    pdf_results['suppliers'] = extractor.extract_suppliers(pdf_text)
                    print(f"      ✓ Found {len(pdf_results['suppliers'])} suppliers")
                    for s in pdf_results['suppliers'][:5]:
                        print(f"         - {s['name']}")

                    print("\n      Extracting company mentions...")
                    ner = FastCompanyExtractor()
                    pdf_results['companies'] = ner.extract_companies(pdf_text, min_mentions=2)
                    print(f"      ✓ Found {len(pdf_results['companies'])} company mentions")
                    for c in pdf_results['companies'][:5]:
                        print(f"         - {c['name']} ({c['count']} mentions)")

                except Exception as e:
                    logger.error(f"PDF extraction failed: {e}", exc_info=True)

            # Cleanup
            try:
                html_file.unlink()
                pdf_file.unlink()
            except:
                pass

    except Exception as e:
        logger.error(f"PDF process failed: {e}", exc_info=True)

    pdf_time = time.time() - pdf_start
    print(f"\n   ⏱️  Time: {pdf_time:.2f}s")

    # Step 5: Comparison
    print("\n[5/5] COMPARISON & ANALYSIS")
    print("=" * 80)

    html_total = len(html_results['customers']) + len(html_results['suppliers']) + len(html_results['companies'])
    pdf_total = len(pdf_results['customers']) + len(pdf_results['suppliers']) + len(pdf_results['companies'])

    print(f"\nEntities Extracted:")
    print(f"   HTML:")
    print(f"      Customers: {len(html_results['customers'])}")
    print(f"      Suppliers: {len(html_results['suppliers'])}")
    print(f"      Companies: {len(html_results['companies'])}")
    print(f"      TOTAL:     {html_total}")

    print(f"\n   PDF:")
    if pdf_results['text_extracted']:
        print(f"      Customers: {len(pdf_results['customers'])}")
        print(f"      Suppliers: {len(pdf_results['suppliers'])}")
        print(f"      Companies: {len(pdf_results['companies'])}")
        print(f"      TOTAL:     {pdf_total}")
    else:
        print(f"      NOT TESTED (PDF conversion/extraction failed)")

    print(f"\nPerformance:")
    print(f"   HTML: {html_time:.2f}s")
    print(f"   PDF:  {pdf_time:.2f}s")
    if pdf_results['text_extracted']:
        speedup = ((pdf_time - html_time) / html_time * 100)
        print(f"   Difference: {abs(speedup):.1f}% {'slower' if speedup > 0 else 'faster'} (PDF vs HTML)")

    print("\n" + "=" * 80)
    print("RECOMMENDATION")
    print("=" * 80)

    if not pdf_results['text_extracted']:
        print("\n❌ PDF extraction failed - cannot compare")
        print("\n✅ STICK WITH HTML EXTRACTION:")
        print("   - Current method works")
        print("   - Fast and reliable")
        print("   - No additional dependencies")

    elif pdf_total > html_total * 1.2:
        print("\n✅ PDF EXTRACTION IS BETTER:")
        print(f"   - Finds {((pdf_total - html_total) / html_total * 100):.0f}% more entities")
        print(f"   - Worth the extra {pdf_time - html_time:.1f}s processing time")
        print("\n   RECOMMENDATION: Implement PDF extraction")

    elif html_total > pdf_total * 1.2:
        print("\n✅ HTML EXTRACTION IS BETTER:")
        print(f"   - Finds {((html_total - pdf_total) / pdf_total * 100):.0f}% more entities")
        print(f"   - {html_time:.1f}s faster than PDF")
        print("\n   RECOMMENDATION: Keep HTML extraction")

    elif pdf_time > html_time * 2:
        print("\n✅ HTML EXTRACTION IS BETTER:")
        print(f"   - Similar accuracy ({abs(html_total - pdf_total)} entity difference)")
        print(f"   - {((pdf_time - html_time) / html_time * 100):.0f}% faster")
        print("\n   RECOMMENDATION: Keep HTML extraction (speed advantage)")

    else:
        print("\n⚖️  METHODS ARE COMPARABLE:")
        print(f"   - HTML: {html_total} entities in {html_time:.1f}s")
        print(f"   - PDF:  {pdf_total} entities in {pdf_time:.1f}s")
        print("\n   RECOMMENDATION: Keep HTML extraction (simpler, no conversion needed)")

    print("\n" + "=" * 80)

    return {
        'html': html_results,
        'pdf': pdf_results,
        'html_time': html_time,
        'pdf_time': pdf_time
    }


if __name__ == "__main__":
    comprehensive_test()

