"""
Quick test script to verify the Fundamental Data Pipeline setup.
"""
import sys

print("=" * 80)
print(" " * 25 + "SYSTEM CHECK")
print("=" * 80)
print()

# Test 1: Check imports
print("1. Testing imports...")
try:
    from mongo_client import MongoWrapper
    from config import load_config
    from sec_edgar_api_client import SECEdgarClient
    from unified_profile_aggregator import UnifiedSECProfileAggregator
    from company_ticker_fetcher import CompanyTickerFetcher
    print("   ✓ All core modules imported successfully")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Load configuration
print("\n2. Testing configuration...")
try:
    config = load_config()
    db_name = config.config['mongodb']['db_name']
    collection = config.config['mongodb'].get('collection', 'Fundamental_Data_Pipeline')
    print(f"   ✓ Configuration loaded")
    print(f"     Database: {db_name}")
    print(f"     Collection: {collection}")
except Exception as e:
    print(f"   ✗ Configuration failed: {e}")
    sys.exit(1)

# Test 3: Company ticker fetcher
print("\n3. Testing company ticker fetcher...")
try:
    ticker_fetcher = CompanyTickerFetcher()
    stats = ticker_fetcher.get_stats()
    print(f"   ✓ Ticker fetcher initialized")
    print(f"     Total companies: {stats['total_companies']:,}")
    print(f"     Companies with ticker: {stats['companies_with_ticker']:,}")

    # Test search
    apple = ticker_fetcher.get_by_ticker("AAPL")
    if apple:
        print(f"     Test search (AAPL): {apple['title']} (CIK: {apple['cik']})")
    else:
        print("     ⚠ Could not find Apple Inc. by ticker")
except Exception as e:
    print(f"   ✗ Ticker fetcher failed: {e}")
    print(f"     This might be expected if SEC website is unreachable")

# Test 4: MongoDB connection (optional - will skip if can't connect)
print("\n4. Testing MongoDB connection...")
try:
    mongo = MongoWrapper(
        uri=config.config['mongodb']['uri'],
        database=config.config['mongodb']['db_name']
    )
    # Try to ping
    mongo.db.command('ping')
    print("   ✓ MongoDB connected successfully")

    # Check collections
    collections = mongo.db.list_collection_names()
    print(f"     Available collections: {', '.join(collections) if collections else 'None'}")
except Exception as e:
    print(f"   ⚠ MongoDB connection failed: {e}")
    print("     Make sure MongoDB is running on mongodb://localhost:27017")

# Test 5: SEC API client
print("\n5. Testing SEC API client...")
try:
    sec_client = SECEdgarClient()
    print("   ✓ SEC API client initialized")
    print("     Ready to fetch company filings")
except Exception as e:
    print(f"   ✗ SEC API client failed: {e}")

# Test 6: (Optional) GUI availability
print("\n6. Testing GUI availability...")
try:
    # Prefer PyQt5 app if available, otherwise Tkinter is included with Python
    import importlib
    qt = importlib.util.find_spec('PyQt5')
    if qt is not None:
        print("   ✓ PyQt5 appears installed (may still fail on import due to binary issues)")
    else:
        print("   - PyQt5 not found; fallback Tkinter GUI will be used (part of stdlib)")
except Exception as e:
    print(f"   ⚠ GUI check failed: {e}")

print()
print("=" * 80)
print(" " * 25 + "CHECK COMPLETE")
print("=" * 80)
print()
print("Next steps:")
print("  1. Make sure MongoDB is running")
print("  2. Run the app: python app.py")
print()
