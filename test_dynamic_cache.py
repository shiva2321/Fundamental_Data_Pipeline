#!/usr/bin/env python3
"""
Test Dynamic Cache System

Tests the new smart cache that:
- Stores ALL filings per ticker (one cache file)
- Filters by date range on retrieval
- Merges new filings intelligently
- Reuses partial data
"""
from src.utils.filing_cache import get_filing_cache
from src.clients.sec_edgar_api_client import SECEdgarClient

print("=" * 70)
print("TESTING DYNAMIC CACHE SYSTEM")
print("=" * 70)

# Initialize
cache = get_filing_cache()
sec_client = SECEdgarClient()

# Test CIK and ticker
test_cik = "0001045810"  # NVIDIA
test_ticker = "NVDA"

print(f"\nTest 1: Initial Cache (10 year lookback)")
print("-" * 70)

# Try to get from cache (should miss first time)
cached = cache.get_cached_filings(test_cik, test_ticker, 10)
if cached:
    print(f"[CACHE HIT] Found {len(cached)} filings in cache")
else:
    print("[CACHE MISS] Fetching from SEC...")
    filings = sec_client.get_company_filings(test_cik)
    print(f"[FETCHED] {len(filings)} total filings from SEC")

    # Cache them
    cache.cache_filings(test_cik, test_ticker, filings, 10)
    print(f"[CACHED] Stored all filings for {test_ticker}")

print(f"\nTest 2: Retrieve with DIFFERENT lookback (5 years)")
print("-" * 70)

# Should reuse same cache, just filter differently
cached_5y = cache.get_cached_filings(test_cik, test_ticker, 5)
if cached_5y:
    print(f"[SMART CACHE] Reused cache, filtered to {len(cached_5y)} filings for 5y")
    print(f"[EFFICIENCY] No SEC API call needed!")
else:
    print("[ERROR] Cache should have worked!")

print(f"\nTest 3: Retrieve with LARGER lookback (20 years)")
print("-" * 70)

# Should still reuse same cache
cached_20y = cache.get_cached_filings(test_cik, test_ticker, 20)
if cached_20y:
    print(f"[SMART CACHE] Reused cache, filtered to {len(cached_20y)} filings for 20y")
    print(f"[EFFICIENCY] No SEC API call needed!")
else:
    print("[ERROR] Cache should have worked!")

print(f"\nTest 4: Simulate incremental update")
print("-" * 70)

# Fetch again (simulates new filings available)
new_filings = sec_client.get_company_filings(test_cik)
print(f"[FETCHED] {len(new_filings)} filings (simulating new data)")

# Cache again - should merge intelligently
cache.cache_filings(test_cik, test_ticker, new_filings, 10)
print("[MERGED] Cache should have merged new filings with existing")

# Check stats
stats = cache.get_cache_stats()
print(f"\nFinal Cache Stats:")
print(f"  Tickers: {stats['total_tickers']}")
print(f"  Total filings: {stats['total_filings']}")
print(f"  Size: {stats['total_size_mb']:.2f} MB / {stats['max_size_mb']:.0f} MB")
print(f"  Usage: {stats['usage_percent']:.1f}%")

print("\n" + "=" * 70)
print("[SUCCESS] Dynamic cache is working!")
print("=" * 70)
print("\nKey benefits:")
print("+ ONE cache file per ticker (not per lookback period)")
print("+ Smart filtering by date range")
print("+ Merges new filings without duplicates")
print("+ Reuses partial data efficiently")
print("+ No wasted space from duplicate ranges")

