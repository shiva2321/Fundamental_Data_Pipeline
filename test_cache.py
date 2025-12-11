#!/usr/bin/env python3
"""
Test Filing Cache System

Tests cache creation, retrieval, and management.
"""
from src.utils.filing_cache import get_filing_cache
from src.clients.mongo_client import MongoWrapper
from src.clients.sec_edgar_api_client import SECEdgarClient
from src.utils.config import load_config

def test_cache():
    print("=" * 70)
    print("TESTING FILING CACHE SYSTEM")
    print("=" * 70)

    # Initialize
    cache = get_filing_cache()
    print(f"\n[OK] Cache initialized at: {cache.cache_dir}")

    # Get initial stats
    stats = cache.get_cache_stats()
    print(f"\nInitial Cache Stats:")
    print(f"  Tickers: {stats['total_tickers']}")
    print(f"  Filings: {stats['total_filings']}")
    print(f"  Size: {stats['total_size_mb']:.2f} MB / {stats['max_size_mb']:.0f} MB")
    print(f"  Usage: {stats['usage_percent']:.1f}%")

    # Test cache with a real company
    print("\n" + "=" * 70)
    print("TEST 1: Fetch and Cache Filings")
    print("=" * 70)

    config = load_config().config
    mongo = MongoWrapper(uri=config['mongodb']['uri'], database=config['mongodb']['db_name'])

    # Get a company from database
    profile = mongo.db['Fundamental_Data_Pipeline'].find_one({})
    if profile:
        cik = profile['cik']
        ticker = profile.get('company_info', {}).get('ticker', 'TEST')

        print(f"\nTesting with: {ticker} (CIK: {cik})")

        # Check cache (should be empty initially)
        cached = cache.get_cached_filings(cik, ticker, 5)
        if cached:
            print(f"[CACHE HIT] {len(cached)} filings already cached")
        else:
            print("[CACHE MISS] Fetching from SEC...")

            # Fetch from SEC
            sec_client = SECEdgarClient()
            filings = sec_client.get_company_filings(cik)
            print(f"[OK] Fetched {len(filings)} filings from SEC")

            # Cache them
            cache.cache_filings(cik, ticker, filings, 5)
            print(f"[OK] Cached {len(filings)} filings")

        # Try retrieving from cache again
        print("\nTesting cache retrieval...")
        cached = cache.get_cached_filings(cik, ticker, 5)
        if cached:
            print(f"[CACHE HIT] Retrieved {len(cached)} filings from cache")
        else:
            print("[ERROR] Cache retrieval failed!")

    # Get updated stats
    print("\n" + "=" * 70)
    print("FINAL CACHE STATS")
    print("=" * 70)

    stats = cache.get_cache_stats()
    print(f"\nCache Stats:")
    print(f"  Tickers: {stats['total_tickers']}")
    print(f"  Filings: {stats['total_filings']}")
    print(f"  Size: {stats['total_size_mb']:.2f} MB / {stats['max_size_mb']:.0f} MB")
    print(f"  Usage: {stats['usage_percent']:.1f}%")

    # List all cached tickers
    print("\nCached Tickers:")
    for ticker_info in cache.list_all_cached_tickers():
        print(f"  - {ticker_info['ticker']}: {ticker_info['total_filings']} filings, {ticker_info['total_size_mb']:.2f} MB")

    print("\n" + "=" * 70)
    print("[SUCCESS] CACHE TEST COMPLETE")
    print("=" * 70)
    print("\nNow run the desktop app and check the 'Cache Manager' tab!")
    print("You should see the cached ticker there.")

if __name__ == '__main__':
    test_cache()

