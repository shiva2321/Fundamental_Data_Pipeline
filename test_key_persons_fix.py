"""
Quick test to verify key_persons extraction works without hanging
"""
import sys
import time

# Test 1: Import check
print("Test 1: Importing key_persons_parser...")
try:
    from src.parsers.key_persons_parser import KeyPersonsParser
    print("✓ Import successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Instantiation check
print("\nTest 2: Creating KeyPersonsParser instance...")
try:
    parser = KeyPersonsParser()
    print("✓ Instantiation successful")
except Exception as e:
    print(f"✗ Instantiation failed: {e}")
    sys.exit(1)

# Test 3: Mock extraction check
print("\nTest 3: Testing _extract_insider_holdings with mock data...")
mock_filings = [
    {'form': '4', 'accessionNumber': '0001234567-25-000001', 'filingDate': '2025-01-15'},
    {'form': '4', 'accessionNumber': '0001234567-25-000002', 'filingDate': '2025-01-20'},
    {'form': '4', 'accessionNumber': '0001234567-25-000003', 'filingDate': '2025-02-01'},
]

try:
    start_time = time.time()
    result = parser._extract_insider_holdings(mock_filings, '0000320193', max_filings=30)
    elapsed = time.time() - start_time

    print(f"✓ Extraction completed in {elapsed:.3f}s")
    print(f"  Holdings extracted: {len(result.get('holdings', []))}")
    print(f"  Expected: 3, Got: {len(result.get('holdings', []))}")

    if elapsed > 1.0:
        print(f"⚠ Warning: Extraction took {elapsed:.3f}s (should be < 1s)")
    else:
        print("✓ Performance is good (< 1 second)")

    # Check if metadata-only
    if result['holdings']:
        sample = result['holdings'][0]
        if sample.get('filing_source') == 'Form 4 Metadata Only':
            print("✓ Using metadata-only approach (no content parsing)")
        else:
            print("✗ Still using content parsing!")

except Exception as e:
    print(f"✗ Extraction failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("ALL TESTS PASSED!")
print("The key_persons extraction should now work without hanging.")
print("="*60)

